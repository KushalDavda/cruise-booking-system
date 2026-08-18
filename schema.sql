-- Odysseus Cruise Booking System Database Schema

CREATE TABLE IF NOT EXISTS cruises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cruise_line TEXT NOT NULL,
    ship_name TEXT NOT NULL,
    departure_port TEXT NOT NULL DEFAULT 'Miami, FL',
    destination TEXT NOT NULL,
    nights INTEGER NOT NULL,
    adult_fare REAL NOT NULL,
    total_capacity INTEGER NOT NULL,
    capacity_left INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS promotional_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('Percentage', 'Fixed')),
    value REAL NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT NOT NULL,
    max_total_uses INTEGER NOT NULL,
    current_total_uses INTEGER DEFAULT 0,
    max_uses_per_customer INTEGER NOT NULL,
    min_spend REAL DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS child_age_bands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    min_age INTEGER NOT NULL,
    max_age INTEGER NOT NULL,
    fare_percentage REAL NOT NULL,
    label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS group_discounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    min_passengers INTEGER NOT NULL,
    max_passengers INTEGER NOT NULL,
    discount_percentage REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS optional_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    price_type TEXT NOT NULL CHECK(price_type IN ('PerPassenger', 'PerPassengerPerNight'))
);

CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference TEXT UNIQUE NOT NULL,
    cruise_id INTEGER NOT NULL,
    customer_email TEXT NOT NULL,
    adult_count INTEGER NOT NULL,
    child_count INTEGER NOT NULL,
    total_passengers INTEGER NOT NULL,
    cruise_subtotal REAL NOT NULL,
    group_discount_amount REAL NOT NULL,
    promo_code_applied TEXT,
    promo_discount_amount REAL NOT NULL,
    services_total_amount REAL NOT NULL,
    net_subtotal REAL NOT NULL,
    tax_rate REAL NOT NULL,
    tax_amount REAL NOT NULL,
    total_price REAL NOT NULL,
    status TEXT DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cruise_id) REFERENCES cruises(id)
);

CREATE TABLE IF NOT EXISTS booking_passengers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    passenger_type TEXT NOT NULL,
    age INTEGER NOT NULL,
    fare_charged REAL NOT NULL,
    FOREIGN KEY(booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS booking_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL,
    service_code TEXT NOT NULL,
    service_name TEXT NOT NULL,
    unit_price REAL NOT NULL,
    total_amount REAL NOT NULL,
    FOREIGN KEY(booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS booking_pricing_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER UNIQUE NOT NULL,
    snapshot_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS promo_redemptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_code_id INTEGER NOT NULL,
    customer_email TEXT NOT NULL,
    booking_id INTEGER NOT NULL,
    redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(promo_code_id) REFERENCES promotional_codes(id),
    FOREIGN KEY(booking_id) REFERENCES bookings(id)
);
