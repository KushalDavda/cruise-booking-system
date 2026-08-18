# Unit Test Cases Document - Cruise Booking System

**Client**: Odysseus Solutions  
**Project**: Cruise Booking System Assessment  
**Author**: Quality Assurance & Testing Team  
**Framework**: `pytest` (Python)  

---

## 1. Overview & Testing Strategy

This document details the comprehensive test suite for the Odysseus Cruise Booking System. The test suite covers positive functional scenarios, negative boundary conditions, exact promo code rejection failure reasons, capacity concurrency constraints, dynamic rule updates, and historical pricing reconstructability.

Every test case maps directly to business requirements defined in `BusinessRequirements.md`.

---

## 2. Test Suite Matrix

### Category 1: Base Pricing & Child Age Band Calculations (FR-02, FR-03)

| Test ID | Test Scenario | Inputs | Expected Outcome | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TC-PRICE-01` | Adult Single Passenger | 1 Adult ($1200 base fare) | Adult fare: $1200, Group discount: 0%, Total pre-tax: $1200 | FR-03 |
| `TC-PRICE-02` | Child Age Band 0–4 (Free) | 1 Adult + 1 Child (Age 3) | Adult: $1200, Child: $0 (0%). Total pre-tax: $1200 | FR-02, FR-03 |
| `TC-PRICE-03` | Child Age Band 5–11 (50%) | 1 Adult + 1 Child (Age 8) | Adult: $1200, Child: $600 (50%). Total pre-tax: $1800 | FR-02, FR-03 |
| `TC-PRICE-04` | Child Age Band 12–17 (75%) | 1 Adult + 1 Child (Age 14) | Adult: $1200, Child: $900 (75%). Total pre-tax: $2100 | FR-02, FR-03 |
| `TC-PRICE-05` | Boundary Age 4 vs Age 5 | Compare Age 4 vs Age 5 child | Age 4 child charged $0; Age 5 child charged 50% fare ($600). | Section 5.1 |
| `TC-PRICE-06` | Boundary Age 11 vs Age 12 | Compare Age 11 vs Age 12 child | Age 11 child charged 50% fare ($600); Age 12 child charged 75% ($900). | Section 5.1 |

---

### Category 2: Group Discount Rules (FR-03, Section 5.3)

| Test ID | Test Scenario | Inputs | Expected Outcome | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TC-GRP-01` | Group Discount 1–2 Passengers | 2 Adults ($1200 each = $2400) | Group discount: 0% ($0). Pre-tax total: $2400 | Section 5.3 |
| `TC-GRP-02` | Group Discount 3–4 Passengers | 3 Adults ($1200 each = $3600) | Group discount: 5% ($180). Cruise fare after discount: $3420 | Section 5.3 |
| `TC-GRP-03` | Group Discount 5–6 Passengers | 5 Adults ($1200 each = $6000) | Group discount: 10% ($600). Cruise fare after discount: $5400 | Section 5.3 |
| `TC-GRP-04` | Group Discount Scope | 3 Adults + Wi-Fi ($15 * 3 * 7 = $315) | 5% discount applies **only** to $3600 cruise fare ($180 off), NOT to $315 Wi-Fi. | Section 5.3 |

---

### Category 3: Optional Travel Services (FR-03, Section 5.4)

| Test ID | Test Scenario | Inputs | Expected Outcome | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TC-SVC-01` | Travel Insurance Calculation | 2 Pax, Insurance selected | Insurance cost: $80 * 2 = $160 flat rate. | Section 5.4 |
| `TC-SVC-02` | Wi-Fi Package Calculation | 2 Pax, 7-Night Cruise | Wi-Fi cost: $15 * 2 pax * 7 nights = $210. | Section 5.4 |
| `TC-SVC-03` | Shore Excursion Calculation | 2 Pax, Excursion selected | Excursion cost: $120 * 2 = $240 flat rate. | Section 5.4 |
| `TC-SVC-04` | All Optional Services Combined | 2 Pax, 7 Nights, All Services | Extras total: $160 + $210 + $240 = $610. | Section 5.4 |

---

### Category 4: Promotional Code Validation & Rejection Messaging (FR-04, FR-06)

| Test ID | Test Scenario | Inputs | Expected Code / Reason | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TC-PROMO-01` | Valid Percentage Code | `SUMMER10` on $1800 spend | Status: Valid. Discount: 10% ($180). | FR-04, Section 5.5 |
| `TC-PROMO-02` | Valid Fixed Amount Code | `FIRST150` on $2200 spend | Status: Valid. Discount: $150 fixed amount. | FR-04, Section 5.5 |
| `TC-PROMO-03` | Non-existent Code | Code: `FAKECODE99` | Status: Rejected. Reason: `INVALID_CODE` ("Promo code does not exist.") | FR-04 |
| `TC-PROMO-04` | Expired Promo Code | Code: `WINTER5` (Valid Jan–Mar 2025; Current date Aug 2026) | Status: Rejected. Reason: `EXPIRED_CODE` ("Promo code has expired.") | FR-04 |
| `TC-PROMO-05` | Total Usage Limit Reached | Code with `max_total_uses=3`, redemptions=3 | Status: Rejected. Reason: `TOTAL_LIMIT_REACHED` ("Total usage limit reached.") | FR-04, FR-06 |
| `TC-PROMO-06` | Customer Usage Limit Exceeded | Customer email has redeemed `SUMMER10` once (`max_uses_per_customer=1`) | Status: Rejected. Reason: `CUSTOMER_LIMIT_REACHED` ("Personal redemption limit reached.") | FR-04, FR-06 |
| `TC-PROMO-07` | Minimum Spend Not Met | `FIRST150` (min spend $2000) applied on $1500 spend | Status: Rejected. Reason: `MINIMUM_SPEND_NOT_MET` ("Minimum spend of $2000 required.") | FR-04, Section 5.5 |

---

### Category 5: Capacity & Passenger Boundary Validation (FR-02, FR-05)

| Test ID | Test Scenario | Inputs | Expected Outcome | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TC-CAP-01` | Book Within Capacity | Cruise capacity: 12. Book 3 pax | Booking confirmed. Capacity left updated to 9. | FR-05 |
| `TC-CAP-02` | Book Sold-out Cruise | `MSC Seascape` (capacity left = 0) | Rejection HTTP 400: `"Cruise is sold out."` | FR-05 |
| `TC-CAP-03` | Passenger Count Exceeds Capacity | Capacity left: 2. Attempt to book 3 pax | Rejection HTTP 400: `"Insufficient remaining capacity."` | FR-05 |
| `TC-BOUND-01` | Zero Adult Passengers | 0 Adults, 2 Children | Rejection HTTP 400: `"At least one adult required."` | Section 5.2 |
| `TC-BOUND-02` | Exceed Maximum Passengers | 7 Passengers (3 Adults, 4 Children) | Rejection HTTP 400: `"Maximum 6 passengers allowed."` | Section 5.2 |

---

### Category 6: Historical Pricing Reconstructability Audit (FR-08)

| Test ID | Test Scenario | Verification Actions | Expected Outcome | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TC-RECON-01` | Historic Price Reconstruction | 1. Create booking `REF-100`. Total charged: $1920.80.<br>2. Modify cruise base fare in DB from $1200 to $2500.<br>3. Modify tax rate in DB from 12% to 20%.<br>4. Call `GET /api/bookings/REF-100/reconstruct`. | Endpoint calculates total using stored snapshot line items. Reconstructed total matches $1920.80 exactly with zero variance. | FR-08 |

---

### Category 7: Dynamic Configuration Modifications (FR-10)

| Test ID | Test Scenario | Verification Actions | Expected Outcome | Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `TC-ADMIN-01` | Update Base Fare via Admin API | Update cruise fare from $1200 to $1400. Calculate new booking. | Subsequent booking reflects $1400 base fare immediately without server restart. | FR-10 |
| `TC-ADMIN-02` | Create New Promo Code via Admin API | Add promo code `FLASH50` ($50 off). Calculate price. | `FLASH50` validates successfully and deducts $50. | FR-10 |
