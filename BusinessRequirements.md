# Business Requirements Document - Cruise Booking System

**Client**: Odysseus Solutions  
**Project**: Cruise Booking System Assessment  
**Author**: Engineering Team  
**Date**: August 2026  

---

## 1. Executive Summary

Odysseus Solutions operates a cruise holiday booking platform. This document defines the business requirements, pricing rules, promo code validation logic, inventory constraints, and architectural assumptions governing the Cruise Booking System.

The system empowers customers to browse available cruise itineraries, configure passenger compositions (adults and children of varying age groups), select optional travel services, validate promotional discount codes, receive instant itemized pricing breakdowns, and complete bookings with guaranteed capacity locks and permanent pricing reconstructability.

---

## 2. Business Objectives & High-Level Scope

1. **Self-Service Cruise Booking**: Customers can search, filter, configure, price, and confirm cruise bookings seamlessly.
2. **Transparent Itemized Pricing**: Customers are shown an explicit, itemized calculation breakdown before paying—never a plain total.
3. **Strict Validation & Failure Messaging**: Invalid, expired, exhausted, or ineligible promotional codes must be rejected with explicit, transparent feedback explaining the exact reason for rejection.
4. **Guaranteed Capacity Control**: A cruise must **never** be overbooked under any circumstances.
5. **Historical Pricing Reconstructability**: Stored bookings must preserve complete price itemization snapshots. The exact price charged must be mathematically reconstructable at any future date, regardless of subsequent fare, tax, or discount rule changes.
6. **Dynamic Rule Management**: Base fares, child age band discounts, group discount tiers, optional service rates, tax rates, and promo codes must be dynamically configurable via administrative capabilities without requiring code changes or system redeployments.

---

## 3. Functional Requirements Mapping

| Req # | Assessment Brief Requirement | Implementation Strategy |
| :--- | :--- | :--- |
| **FR-01** | Find cruises available to book. | Filterable catalog listing active cruises with destination, duration (nights), adult fare, and real-time available capacity. |
| **FR-02** | Specify passengers (adult count, child count, child ages) and optional services. | Dynamic passenger selector validating 1 to 6 total passengers, mandatory adult count (>= 1), age inputs for each child (0–17), and checkboxes for optional services. |
| **FR-03** | Price booking according to rules and show itemized breakdown. | Calculation engine generating itemized breakdown: Adult Cruise Subtotal, Child Cruise Subtotal (by age band), Group Discount (if 3+ pax), Optional Extras breakdown, Pre-tax Subtotal, Promo Discount, Tax Amount, and Final Total. |
| **FR-04** | Apply promotional code with specific rejection feedback. | Promo code engine validating existence, active status, date validity, total usage limit, customer usage limit, and minimum spend. Specific error code & explanation returned on failure. |
| **FR-05** | Cruise capacity must never be exceeded under any circumstances. | Database row locking (`BEGIN TRANSACTION`) with atomic decrement check `capacity_left = capacity_left - N WHERE capacity_left >= N`. Rejects booking if capacity insufficient. |
| **FR-06** | Promo code limit enforcement (total redemptions & per-customer limits). | `promo_redemptions` table records every redemption per customer email. System enforces total usage <= `max_total_uses` and customer usage <= `max_uses_per_customer`. |
| **FR-07** | Confirmed booking storage & unique reference generation. | Unique, human-readable reference code generated upon confirmation (e.g. `CRZ-2026-A89F12`). |
| **FR-08** | Full reconstructability of historical bookings. | Immutable `booking_pricing_snapshots` stored in database capturing exact parameters, rule versions, line items, and final total at confirmation time. |
| **FR-09** | Price lock before confirmation. | Price calculated during review is guaranteed during checkout session. Database transaction verifies price integrity before locking capacity. |
| **FR-10** | Dynamic rule administration without code changes/redeployments. | Admin API and UI managing `cruises`, `promotional_codes`, `child_age_bands`, `group_discounts`, `optional_services`, and `system_config` (tax rate). |

---

## 4. Pricing & Discount Rules

### 4.1 Base Cruise Fare & Passenger Eligibility
- **Adults**: Defined as age 18+. Charged 100% of cruise base fare.
- **Children**: Defined as age 0 to 17. Fare percentage is determined by age at booking:
  - **Age 0–4**: 0% of adult fare (**Free**).
  - **Age 5–11**: 50% of adult fare.
  - **Age 12–17**: 75% of adult fare.
- **Booking Limits**:
  - Every booking **must** contain at least 1 adult passenger.
  - Total passengers (adults + children) cannot exceed 6 passengers.

### 4.2 Group Discount
- Applied **exclusively to the Cruise Fare subtotal** (sum of adult and child cruise fares):
  - **1–2 Total Passengers**: 0% discount
  - **3–4 Total Passengers**: 5% discount on cruise fare subtotal
  - **5–6 Total Passengers**: 10% discount on cruise fare subtotal

### 4.3 Optional Travel Services
- **Travel Insurance**: $80 per passenger (flat rate regardless of cruise duration).
- **Wi-Fi Package**: $15 per passenger per night of the cruise (`$15 * total_passengers * cruise_nights`).
- **Shore Excursions**: $120 per passenger (flat rate).

### 4.4 Promotional Codes
A booking can apply at most one promotional code:
- **Percentage Discount**: Reduces net subtotal by specified percentage.
- **Fixed Discount**: Reduces net subtotal by specified fixed monetary value (capped at subtotal).
- **Validation Constraints & Rejection Reasons**:
  1. `INVALID_CODE`: Code does not exist in active registry.
  2. `EXPIRED_CODE`: Booking date is outside `[valid_from, valid_to]`.
  3. `TOTAL_LIMIT_REACHED`: Cumulative redemptions across all customers >= `max_total_uses`.
  4. `CUSTOMER_LIMIT_REACHED`: Redemptions by this customer email >= `max_uses_per_customer`.
  5. `MINIMUM_SPEND_NOT_MET`: Booking pre-promo subtotal < `min_spend`.

### 4.5 Tax Application Rule
- System tax rate: **12%** (configurable via system settings).
- **Tax Calculation Point**: Tax applies to the **net taxable subtotal after group discounts and promotional code discounts** have been subtracted.
  - Formula: `Tax Amount = (Subtotal_After_Group_Discount + Optional_Services - Promo_Discount) * Tax_Rate`
  - Total Price: `Net_Subtotal_After_Discount + Tax_Amount`

---

## 5. Identification of Gaps, Conflicts & Business Assumptions

As instructed in Section 2 of the design brief, the following gaps and ambiguous requirements were identified, analyzed, and resolved with clear business rationale:

| Gap / Ambiguity Identified | Resolution & Business Decision | Business Rationale |
| :--- | :--- | :--- |
| **Tax Point of Application (Section 5.6)** | Tax (12%) is applied after all group discounts and promotional discounts are deducted. | Standard e-commerce and tax regulatory practice mandates that sales tax is assessed on actual revenue realized from customer (net post-discount price). |
| **Minimum Spend Evaluation Basis (Section 5.5)** | Minimum spend threshold is evaluated against pre-promo subtotal (Cruise Fares after Group Discount + Optional Extras). | Prevents circular dependencies in promo evaluation and accurately reflects customer total spend before discount. |
| **Child Age Verification Timing** | Child age is evaluated at date of booking entry. | Ensures deterministic pricing at checkout. |
| **Customer Identification** | Customer is identified by unique Email Address. | Enables promo redemption tracking without requiring full customer registration upfront. |
| **Journey Source Port (Section 6.1)** | Extended data model with `departure_port` (e.g. PortMiami, Port of Barcelona, Port of Seattle, Port of Southampton). | The Section 6.2 seed data table only listed Destination region. Real-world cruise bookings mandate knowing both the origin departure port (source) and destination region. |
| **Capacity Lock Timing** | Capacity is decremented atomically inside SQL transaction upon booking submission. | Prevents race conditions and guarantees zero overbooking under high concurrent load. |
