# Technical Approach Document - Cruise Booking System

**Client**: Odysseus Solutions  
**Project**: Cruise Booking System Assessment  
**Author**: Lead Systems Architect  
**Tech Stack**: Python 3, FastAPI, SQLite3, HTML5 / CSS3 / Modern JS, Pytest  

---

## 1. System Architecture Overview

The Odysseus Cruise Booking System is built following a modular **Layered Service Architecture** in Python. The system decouples database persistence, business calculation logic, RESTful API endpoints, and user interface components.

```
                  +-----------------------------------+
                  |        Web UI Component           |
                  | (HTML5 / Vanilla JS / Glass CSS)  |
                  +-----------------+-----------------+
                                    |
                                HTTP|REST (JSON API)
                                    v
                  +-----------------------------------+
                  |         FastAPI Server            |
                  |     (Routing & Validation)        |
                  +-----------------+-----------------+
                                    |
                  +-----------------+-----------------+
                  |                                   |
                  v                                   v
   +------------------------------+   +------------------------------+
   |   Pricing Calculation Engine |   |   Promo Validation Engine    |
   |     (Pure Python Module)     |   |    (Explicit Error Codes)    |
   +--------------+---------------+   +--------------+---------------+
                  |                                   |
                  +-----------------+-----------------+
                                    |
                                    v
                  +-----------------------------------+
                  |        SQLite Database Layer      |
                  |  (ACID Transactions & Snapshots)  |
                  +-----------------------------------+
```

### Core Architectural Principles:
1. **Determinism**: The pricing engine is a pure side-effect-free Python function. Given identical input parameters and active rule configurations, it returns exact, reproducible pricing line items.
2. **Immutability of Bookings**: When a booking is confirmed, a complete JSON snapshot of the mathematical calculation matrix is serialized and stored in the database (`booking_pricing_snapshots`).
3. **Database-Driven Rule Configuration (FR-10)**: Fares, child age bands, group discount brackets, optional service prices, promo codes, and tax rates reside in SQL tables. Changing them via the Admin API modifies current database parameters immediately without requiring code modifications or server restarts.
4. **Concurrency Safety (FR-05)**: Cruise capacity decrements use SQL-level atomic checks inside explicit database transactions to prevent overbooking.

---

## 2. Database Schema & Data Modeling

The system uses a relational database schema designed for third-normal-form (3NF) normalized configuration tables combined with denormalized snapshot storage for historical auditability.

```
  +------------------+         +------------------+         +------------------+
  |     cruises      |         |  child_age_bands |         | group_discounts  |
  +------------------+         +------------------+         +------------------+
  | id               |         | id               |         | id               |
  | cruise_line      |         | min_age          |         | min_passengers   |
  | ship_name        |         | max_age          |         | max_passengers   |
  | destination      |         | fare_percentage  |         | discount_pct     |
  | nights           |         +------------------+         +------------------+
  | adult_fare       |
  | capacity_left    |         +------------------+         +------------------+
  +--------+---------+         |promotional_codes |         | optional_services|
           |                   +------------------+         +------------------+
           |                   | id, code, type   |         | id, code, name   |
           | 1                 | value, valid_from|         | price, price_type|
           |                   | valid_to, max_use|         +------------------+
           v N                 | min_spend        |
  +--------+---------+         +--------+---------+
  |     bookings     |                  | 1
  +------------------+                  v N
  | id               |         +--------+---------+
  | booking_ref      |<--------| promo_redemption |
  | cruise_id        |         +------------------+
  | customer_email   |
  | total_paid       |         +------------------+
  | created_at       |<--------| booking_snapshot |
  +--------+---------+ 1       +------------------+
           | 1:N 
           +------------------> [ booking_passengers ]
           +------------------> [ booking_services ]
```

### Table Definitions & Purpose:
- `cruises`: Stores cruise metadata, departure port (source of journey), destination region, base adult fare, total capacity, and remaining capacity.
- `promotional_codes`: Holds code attributes, valid date ranges, max uses, per-customer cap, and minimum spend.
- `child_age_bands`: Configurable child age ranges and fare percentages (e.g., 0–4: 0%, 5–11: 50%, 12–17: 75%).
- `group_discounts`: Passenger count brackets and percentage discounts (e.g., 3-4 pax: 5%, 5-6 pax: 10%).
- `optional_services`: Rates for travel insurance ($80), Wi-Fi ($15/night), and excursions ($120).
- `system_config`: Key-value store for global settings (e.g. `tax_rate` = 0.12).
- `bookings`: Master header record with customer info, passenger counts, totals, tax, and unique reference.
- `booking_passengers`: Itemized breakdown of each passenger's age, type, and individual fare charged.
- `booking_services`: Selected optional extras with unit prices and calculated totals.
- `booking_pricing_snapshots`: Complete, raw JSON payload containing full calculation context at booking time.
- `promo_redemptions`: Audit table linking promo codes to customer emails and booking IDs.

---

## 3. Pricing Calculation Engine & Promo Validation Logic

The pricing calculation is isolated in `pricing_engine.py` and `promo_validator.py`.

### Calculation Workflow:
1. **Base Adult Fare**: `adult_count * cruise.adult_fare`.
2. **Child Fares**: For each child age, query `child_age_bands` where `min_age <= child_age <= max_age`. Calculate `child_fare = cruise.adult_fare * (fare_percentage / 100)`. Sum all child fares.
3. **Cruise Subtotal**: `Adult_Subtotal + Child_Subtotal`.
4. **Group Discount**: Count total passengers `(adults + children)`. Query `group_discounts` where `min_passengers <= total_pax <= max_passengers`. Apply discount percentage to Cruise Subtotal only.
5. **Optional Services**:
   - `Insurance`: `80 * total_passengers`
   - `Wi-Fi`: `15 * total_passengers * cruise.nights`
   - `Shore Excursions`: `120 * total_passengers`
6. **Pre-Promo Subtotal**: `(Cruise_Subtotal - Group_Discount_Amount) + Total_Optional_Services`.
7. **Promo Code Validation**:
   If a code is supplied, `promo_validator.py` executes sequential checks:
   - Check code exists and `is_active == 1` -> If not, return `INVALID_CODE`.
   - Check current date between `valid_from` and `valid_to` -> If not, return `EXPIRED_CODE`.
   - Check `current_total_uses < max_total_uses` -> If not, return `TOTAL_LIMIT_REACHED`.
   - Check customer redemptions in `promo_redemptions` < `max_uses_per_customer` -> If not, return `CUSTOMER_LIMIT_REACHED`.
   - Check `Pre-Promo Subtotal >= min_spend` -> If not, return `MINIMUM_SPEND_NOT_MET`.
   - Calculate discount:
     - Percentage: `Pre_Promo_Subtotal * (value / 100)`
     - Fixed: `min(value, Pre_Promo_Subtotal)`
8. **Net Subtotal**: `Pre_Promo_Subtotal - Promo_Discount`.
9. **Tax Amount**: `Net_Subtotal * tax_rate` (12%).
10. **Final Total Charged**: `Net_Subtotal + Tax_Amount`.

---

## 4. Reconstructability Strategy (FR-08)

To guarantee that any booking can be mathematically reconstructed in the future—even after adult fares, child age bands, discount rates, promo code rules, or tax rates have changed—the system employs an **Immutable Pricing Snapshot** architecture.

When `POST /api/bookings` confirms a booking:
1. The pricing engine calculates the full itemized price breakdown.
2. A complete JSON payload containing all input parameters, age band definitions used, group discount rates applied, optional service rates, promo code rules, sub-totals, tax amounts, and total price is saved to `booking_pricing_snapshots`.
3. An audit endpoint `GET /api/bookings/{reference}/reconstruct` retrieves this stored snapshot, re-evaluates the mathematical verification, and displays the exact itemized breakdown proving that zero deviation occurred.

---

## 5. Capacity Control & Concurrency Strategy (FR-05)

To ensure a cruise is never sold to more passengers than available capacity under high concurrent load:
1. Every booking creation request opens an explicit SQLite transaction (`BEGIN IMMEDIATE TRANSACTION`).
2. The transaction executes an atomic atomic SQL update:
   ```sql
   UPDATE cruises 
   SET capacity_left = capacity_left - ? 
   WHERE id = ? AND capacity_left >= ?;
   ```
3. If `db.changes() == 0`, the transaction rolls back immediately and returns an HTTP 400 error: `"Selected cruise does not have sufficient remaining capacity."`
4. If capacity is successfully decremented, passenger records, booking line items, promo redemptions, and pricing snapshots are written, and the transaction is committed (`COMMIT`).

---

## 6. What Would Be Done Differently With More Time

1. **Multi-Currency Support**: Add real-time foreign exchange rate conversion for international customers.
2. **Payment Gateway Integration**: Integrate Stripe/PayPal sandbox for credit card processing and webhooks.
3. **Interactive Deck Plan & Cabin Selection**: Allow customers to select specific stateroom numbers on an SVG ship deck map.
4. **JWT Authentication & RBAC**: Formalize JWT bearer tokens for Customer, Travel Agent, and System Administrator roles.
5. **PostgreSQL Database**: Migrate from SQLite to PostgreSQL with row-level locks (`SELECT ... FOR UPDATE`) for high-throughput enterprise scalability.

---

## 7. Scope Matrix: Finished vs Unfinished Features

| Feature Component | Status | Details |
| :--- | :--- | :--- |
| **Cruise Catalog & Search** | Completed | Full catalog, filtering by destination/nights, real-time capacity badges. |
| **Passenger Selector & Eligibility** | Completed | Age validation, 1-6 passenger limit, minimum 1 adult rule. |
| **Dynamic Pricing Calculation Engine** | Completed | Adult & child age bands, group discount, optional extras, tax. |
| **Promo Code Engine & Rejection Messaging**| Completed | Full validation suite returning specific failure reasons. |
| **Atomic Inventory Lock & Overbooking Protection**| Completed | Transactional capacity decrement ensuring zero overbooking. |
| **Booking Reference & Snapshot Persistence**| Completed | Unique reference generation & immutable snapshot JSON storage. |
| **Pricing Reconstructability Audit Engine**| Completed | Historical verification endpoint & audit breakdown UI. |
| **Dynamic Rule Management (Admin API/UI)**| Completed | Live CRUD for fares, age bands, discounts, services, promo codes, tax. |
| **Automated Unit Test Suite (pytest)** | Completed | Comprehensive test suite covering pricing, promo validation, capacity, and reconstructability. |
