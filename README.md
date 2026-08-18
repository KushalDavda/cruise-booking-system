# Odysseus Cruise Booking System

An enterprise-grade, full-stack Cruise Booking System built in **Python** for the **Odysseus Solutions Technical Assessment**.

The system features a dynamic configurable pricing engine, promo code validation with explicit rejection reasons, atomic database inventory management, historical pricing reconstructability, an administrative rule management dashboard, and a comprehensive `pytest` unit testing suite.

---

## 📚 Deliverable Documents

Per Section 3 of the assessment brief, the required documentation files are available in the repository root:

1. **[`BusinessRequirements.md`](file:///Users/janvidavda/Documents/cruise/BusinessRequirements.md)** — Comprehensive breakdown of functional requirements, pricing rules, promo validation logic, capacity constraints, and identified gaps/ambiguities.
2. **[`TechnicalApproach.md`](file:///Users/janvidavda/Documents/cruise/TechnicalApproach.md)** — Architecture overview, 3NF + snapshot database schema design, calculation engine determinism, reconstructability strategy, and scope completion matrix.
3. **[`UnitTestCases.md`](file:///Users/janvidavda/Documents/cruise/UnitTestCases.md)** — Detailed test suite matrix covering positive pricing cases, boundary conditions, promo rejection codes, capacity locking, and historical price reconstruction.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.9+**
- Standard Python package manager (`pip`)

### 1. Installation
Clone the repository and install dependencies:
```bash
# Navigate to project root
cd /Users/janvidavda/Documents/cruise

# Install required dependencies
pip install fastapi uvicorn pytest requests
```

### 2. Run the Application
Start the FastAPI server:
```bash
python main.py
```
Or using `uvicorn` directly:
```bash
uvicorn main:app --reload --port 8000
```
Open your web browser and navigate to **`http://localhost:8000`** to access the interactive web interface!

### 3. Run the Automated Unit Test Suite
Execute the `pytest` test suite:
```bash
pytest -v
```

---

## 🛠️ Key System Features

### 1. Dynamic Configurable Pricing Engine
- **Adult Base Fares**: Configurable per cruise.
- **Child Age Bands**:
  - **0–4 Years**: Free (0% of adult fare)
  - **5–11 Years**: 50% of adult fare
  - **12–17 Years**: 75% of adult fare
- **Group Discounts** (Applied to cruise fare):
  - **1–2 Passengers**: 0%
  - **3–4 Passengers**: 5%
  - **5–6 Passengers**: 10%
- **Optional Services**: Insurance ($80/pax), Wi-Fi ($15/pax/night), Shore Excursions ($120/pax).
- **Tax Application**: 12% tax calculated on post-discount net taxable subtotal.

### 2. Promo Code Validator with Explicit Failure Reasons
Returns specific rejection responses:
- `INVALID_CODE`: Code does not exist in system.
- `EXPIRED_CODE`: Code outside valid date range (e.g. `WINTER5`).
- `TOTAL_LIMIT_REACHED`: Global total redemption limit reached.
- `CUSTOMER_LIMIT_REACHED`: Personal per-customer redemption limit reached.
- `MINIMUM_SPEND_NOT_MET`: Booking subtotal below minimum required spend.

### 3. Historical Price Reconstructability
Stores immutable JSON pricing snapshots upon booking confirmation. Any past booking can be re-evaluated via `/api/bookings/{reference}/reconstruct` to verify that historical pricing remains exact down to the cent, even after base fares or tax rates are changed in the database.

### 4. Admin Management Dashboard
Allows system administrators to add/update cruises, promotional codes, child age bands, group discount brackets, optional service rates, and global tax rates without modifying code or restarting the server.

---

## 🗄️ Seed Data Summary

The database automatically initializes and populates Section 6.2 and 6.3 seed data on first launch:

### Cruises
| Cruise Line | Ship Name | Destination | Nights | Base Fare | Capacity Left |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Royal Caribbean | Wonder of the Seas | Caribbean | 7 | $1,200 | 12 |
| Celebrity Cruises | Celebrity Beyond | Mediterranean | 10 | $1,850 | 4 |
| Norwegian Cruise Line | Norwegian Prima | Alaska | 5 | $950 | 20 |
| Princess Cruises | Sky Princess | Northern Europe | 12 | $2,100 | 2 |
| MSC Cruises | MSC Seascape | Bahamas | 4 | $700 | 0 *(Sold Out)* |

### Promotional Codes
| Code | Type | Value | Valid From - To | Max Uses | Per Customer | Min Spend |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `SUMMER10` | Percentage | 10% | 01-Jun-2026 to 31-Aug-2026 | 100 | 1 | $1,000 |
| `FIRST150` | Fixed | $150 | 01-Jan-2026 to 31-Dec-2026 | 500 | 1 | $2,000 |
| `CREW25` | Percentage | 25% | 01-Jan-2026 to 31-Dec-2026 | 3 | 3 | None |
| `WINTER5` | Percentage | 5% | 01-Jan-2025 to 31-Mar-2025 | 1000 | 5 | None *(Expired)* |

---

## 📡 REST API Summary

- `GET /api/cruises`: List active cruises with live capacity.
- `POST /api/pricing/calculate`: Dynamic pricing calculation endpoint.
- `POST /api/bookings`: Create booking inside SQL transaction with capacity lock.
- `GET /api/bookings/{reference}`: Get booking details.
- `GET /api/bookings/{reference}/reconstruct`: Reconstruct price snapshot.
- `GET /api/admin/config`: Fetch dynamic system rules.
- `POST /api/admin/cruises`: Add or update cruise parameters.
- `POST /api/admin/promos`: Add or update promo codes.
