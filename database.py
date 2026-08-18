"""
Database connection and seeding utility for Odysseus Cruise Booking System.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cruise.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

def get_db_connection(db_file=DB_PATH):
    """Establishes and returns a sqlite3 connection with Row factory enabled."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_file=DB_PATH):
    """Initializes the database schema and seeds initial data if empty."""
    conn = get_db_connection(db_file)
    cursor = conn.cursor()

    # Load and execute schema
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)

    # Seed System Config (Tax Rate = 12%)
    cursor.execute("SELECT COUNT(*) FROM system_config WHERE key = 'tax_rate'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO system_config (key, value, description) VALUES ('tax_rate', '0.12', 'Standard System Tax Rate (12%)')"
        )

    # Seed Child Age Bands (0-4: 0%, 5-11: 50%, 12-17: 75%)
    cursor.execute("SELECT COUNT(*) FROM child_age_bands")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO child_age_bands (min_age, max_age, fare_percentage, label) VALUES (?, ?, ?, ?)",
            [
                (0, 4, 0.0, "Infant / Toddler (Free)"),
                (5, 11, 50.0, "Child (50% fare)"),
                (12, 17, 75.0, "Youth (75% fare)"),
            ],
        )

    # Seed Group Discount Tiers (1-2: 0%, 3-4: 5%, 5-6: 10%)
    cursor.execute("SELECT COUNT(*) FROM group_discounts")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO group_discounts (min_passengers, max_passengers, discount_percentage) VALUES (?, ?, ?)",
            [
                (1, 2, 0.0),
                (3, 4, 5.0),
                (5, 6, 10.0),
            ],
        )

    # Seed Optional Services ($80 Insurance, $15/night Wi-Fi, $120 Shore Excursion)
    cursor.execute("SELECT COUNT(*) FROM optional_services")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO optional_services (code, name, price, price_type) VALUES (?, ?, ?, ?)",
            [
                ("INSURANCE", "Travel Insurance", 80.0, "PerPassenger"),
                ("WIFI", "Wi-Fi Access", 15.0, "PerPassengerPerNight"),
                ("EXCURSION", "Shore Excursion Pass", 120.0, "PerPassenger"),
            ],
        )

    # Seed Section 6.2 Cruise Data
    cursor.execute("SELECT COUNT(*) FROM cruises")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """INSERT INTO cruises 
               (cruise_line, ship_name, departure_port, destination, nights, adult_fare, total_capacity, capacity_left) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("Royal Caribbean", "Wonder of the Seas", "PortMiami, Florida, USA", "Caribbean", 7, 1200.0, 12, 12),
                ("Celebrity Cruises", "Celebrity Beyond", "Port of Barcelona, Spain", "Mediterranean", 10, 1850.0, 4, 4),
                ("Norwegian Cruise Line", "Norwegian Prima", "Port of Seattle, Washington, USA", "Alaska", 5, 950.0, 20, 20),
                ("Princess Cruises", "Sky Princess", "Port of Southampton, UK", "Northern Europe", 12, 2100.0, 2, 2),
                ("MSC Cruises", "MSC Seascape", "Port Everglades, Fort Lauderdale, USA", "Bahamas", 4, 700.0, 0, 0),
            ],
        )

    # Seed Section 6.3 Promotional Code Data
    cursor.execute("SELECT COUNT(*) FROM promotional_codes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """INSERT INTO promotional_codes 
               (code, type, value, valid_from, valid_to, max_total_uses, max_uses_per_customer, min_spend) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("SUMMER10", "Percentage", 10.0, "2026-06-01", "2026-08-31", 100, 1, 1000.0),
                ("FIRST150", "Fixed", 150.0, "2026-01-01", "2026-12-31", 500, 1, 2000.0),
                ("CREW25", "Percentage", 25.0, "2026-01-01", "2026-12-31", 3, 3, 0.0),
                ("WINTER5", "Percentage", 5.0, "2025-01-01", "2025-03-31", 1000, 5, 0.0), # Expired seed
            ],
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded successfully.")
