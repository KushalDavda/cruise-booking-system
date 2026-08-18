"""
Odysseus Cruise Booking System - Standard Python HTTP Server.
Built using Python 3 standard libraries (http.server, json, sqlite3) with zero external dependencies.

Run with:
    python3 main.py
Access UI at:
    http://localhost:8000
"""
import os
import json
import uuid
import sqlite3
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from database import get_db_connection, init_db
from pricing_engine import calculate_booking_price

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
PORT = 8000

class CruiseBookingRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Clean server logging
        print(f"[{self.log_date_time_string()}] {self.command} {self.path} -> {args[0]}")

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message, status=400):
        self._send_json({"detail": message, "error": True}, status=status)

    def _serve_file(self, filepath, content_type):
        if not os.path.exists(filepath):
            self.send_error(404, "File Not Found")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Static Assets Serving
        if path == "/" or path == "/index.html":
            return self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
        elif path == "/static/styles.css":
            return self._serve_file(os.path.join(STATIC_DIR, "styles.css"), "text/css; charset=utf-8")
        elif path == "/static/app.js":
            return self._serve_file(os.path.join(STATIC_DIR, "app.js"), "application/javascript; charset=utf-8")

        # API Endpoints
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if path == "/api/cruises":
                cursor.execute("SELECT * FROM cruises WHERE is_active = 1 ORDER BY destination ASC, ship_name ASC")
                cruises = [dict(r) for r in cursor.fetchall()]
                conn.close()
                return self._send_json({"cruises": cruises})

            elif path.startswith("/api/cruises/"):
                cruise_id_str = path.replace("/api/cruises/", "")
                cursor.execute("SELECT * FROM cruises WHERE id = ?", (cruise_id_str,))
                row = cursor.fetchone()
                conn.close()
                if not row:
                    return self._send_error_json("Cruise not found.", 404)
                return self._send_json({"cruise": dict(row)})

            elif path.startswith("/api/bookings/"):
                parts = [p for p in path.split("/") if p]
                # /api/bookings/{ref}
                if len(parts) == 3:
                    ref = parts[2].upper()
                    cursor.execute(
                        """SELECT b.*, c.ship_name, c.cruise_line, c.destination, c.nights 
                           FROM bookings b JOIN cruises c ON b.cruise_id = c.id 
                           WHERE b.booking_reference = ?""", 
                        (ref,)
                    )
                    booking = cursor.fetchone()
                    if not booking:
                        conn.close()
                        return self._send_error_json(f"Booking reference '{ref}' not found.", 404)

                    b_dict = dict(booking)
                    cursor.execute("SELECT * FROM booking_passengers WHERE booking_id = ?", (b_dict["id"],))
                    passengers = [dict(r) for r in cursor.fetchall()]

                    cursor.execute("SELECT * FROM booking_services WHERE booking_id = ?", (b_dict["id"],))
                    services = [dict(r) for r in cursor.fetchall()]

                    conn.close()
                    return self._send_json({
                        "booking": b_dict,
                        "passengers": passengers,
                        "services": services
                    })

                # /api/bookings/{ref}/reconstruct
                elif len(parts) == 4 and parts[3] == "reconstruct":
                    ref = parts[2].upper()
                    cursor.execute("SELECT id, booking_reference, total_price, created_at FROM bookings WHERE booking_reference = ?", (ref,))
                    booking = cursor.fetchone()
                    if not booking:
                        conn.close()
                        return self._send_error_json(f"Booking reference '{ref}' not found.", 404)

                    cursor.execute("SELECT snapshot_json FROM booking_pricing_snapshots WHERE booking_id = ?", (booking["id"],))
                    snap_row = cursor.fetchone()
                    conn.close()

                    if not snap_row:
                        return self._send_error_json("Historical pricing snapshot not found.", 404)

                    snapshot_data = json.loads(snap_row["snapshot_json"])
                    stored_total = booking["total_price"]
                    snapshot_total = snapshot_data["pricing_summary"]["total_price"]
                    is_exact_match = (abs(stored_total - snapshot_total) < 0.001)

                    return self._send_json({
                        "booking_reference": booking["booking_reference"],
                        "booking_created_at": booking["created_at"],
                        "stored_total_charged": stored_total,
                        "reconstructed_total": snapshot_total,
                        "is_exact_match": is_exact_match,
                        "verification_status": "PASSED - Pricing snapshot matches recorded total exactly." if is_exact_match else "FAILED",
                        "itemized_snapshot": snapshot_data
                    })

            elif path == "/api/admin/config":
                cursor.execute("SELECT * FROM promotional_codes ORDER BY created_at DESC")
                promos = [dict(r) for r in cursor.fetchall()]
                cursor.execute("SELECT * FROM child_age_bands ORDER BY min_age ASC")
                age_bands = [dict(r) for r in cursor.fetchall()]
                cursor.execute("SELECT * FROM group_discounts ORDER BY min_passengers ASC")
                group_tiers = [dict(r) for r in cursor.fetchall()]
                cursor.execute("SELECT * FROM optional_services")
                services = [dict(r) for r in cursor.fetchall()]
                cursor.execute("SELECT * FROM system_config")
                configs = {r["key"]: r["value"] for r in cursor.fetchall()}
                conn.close()
                return self._send_json({
                    "promotional_codes": promos,
                    "child_age_bands": age_bands,
                    "group_discounts": group_tiers,
                    "optional_services": services,
                    "system_config": configs
                })

            else:
                conn.close()
                self._send_error_json("Endpoint not found.", 404)

        except Exception as err:
            conn.close()
            self._send_error_json(str(err), 500)

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data_bytes = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data_bytes.decode("utf-8")) if post_data_bytes else {}
        except Exception:
            return self._send_error_json("Invalid JSON payload.", 400)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if path == "/api/pricing/calculate":
                cruise_id = body.get("cruise_id")
                adult_count = int(body.get("adult_count", 1))
                child_ages = body.get("child_ages", [])
                services_selected = body.get("services_selected", [])
                promo_code = body.get("promo_code")
                customer_email = body.get("customer_email")

                cursor.execute("SELECT * FROM cruises WHERE id = ?", (cruise_id,))
                cruise = cursor.fetchone()
                if not cruise:
                    conn.close()
                    return self._send_error_json("Selected cruise not found.", 404)

                breakdown = calculate_booking_price(
                    cruise=dict(cruise),
                    adult_count=adult_count,
                    child_ages=child_ages,
                    services_selected=services_selected,
                    promo_code_str=promo_code,
                    customer_email=customer_email,
                    db_conn=conn
                )
                conn.close()
                return self._send_json(breakdown)

            elif path == "/api/bookings":
                cruise_id = body.get("cruise_id")
                cust_name = body.get("customer_name", "").strip()
                cust_email = body.get("customer_email", "").strip().lower()
                adult_count = int(body.get("adult_count", 1))
                child_ages = body.get("child_ages", [])
                services_selected = body.get("services_selected", [])
                promo_code = body.get("promo_code")

                if not cust_name or not cust_email:
                    conn.close()
                    return self._send_error_json("Customer name and email are required.", 400)

                cursor.execute("SELECT * FROM cruises WHERE id = ?", (cruise_id,))
                cruise = cursor.fetchone()
                if not cruise:
                    conn.close()
                    return self._send_error_json("Selected cruise not found.", 404)

                cruise_dict = dict(cruise)
                total_passengers = adult_count + len(child_ages)

                if cruise_dict["capacity_left"] < total_passengers:
                    conn.close()
                    return self._send_error_json(
                        f"Cruise '{cruise_dict['ship_name']}' does not have sufficient remaining capacity for {total_passengers} passenger(s). Capacity left: {cruise_dict['capacity_left']}.", 
                        400
                    )

                # Pricing calculation
                pricing = calculate_booking_price(
                    cruise=cruise_dict,
                    adult_count=adult_count,
                    child_ages=child_ages,
                    services_selected=services_selected,
                    promo_code_str=promo_code,
                    customer_email=cust_email,
                    db_conn=conn
                )
                ps = pricing["pricing_summary"]

                if promo_code and not ps["promo_code"]["is_valid"]:
                    conn.close()
                    return self._send_error_json(f"Promo Code Error: {ps['promo_code']['error_message']}", 400)

                # Transaction
                conn.execute("BEGIN IMMEDIATE TRANSACTION;")
                cursor.execute(
                    """UPDATE cruises SET capacity_left = capacity_left - ? 
                       WHERE id = ? AND capacity_left >= ?""",
                    (total_passengers, cruise_id, total_passengers)
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    conn.close()
                    return self._send_error_json("Transaction failed: Cruise capacity changed concurrently.", 400)

                cursor.execute(
                    """INSERT INTO customers (email, name) VALUES (?, ?) 
                       ON CONFLICT(email) DO UPDATE SET name = excluded.name""",
                    (cust_email, cust_name)
                )

                short_id = uuid.uuid4().hex[:6].upper()
                booking_ref = f"CRZ-2026-{short_id}"

                cursor.execute(
                    """INSERT INTO bookings 
                       (booking_reference, cruise_id, customer_email, adult_count, child_count, total_passengers,
                        cruise_subtotal, group_discount_amount, promo_code_applied, promo_discount_amount,
                        services_total_amount, net_subtotal, tax_rate, tax_amount, total_price)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        booking_ref, cruise_id, cust_email, adult_count, len(child_ages), total_passengers,
                        ps["gross_cruise_subtotal"], ps["group_discount"]["amount"],
                        ps["promo_code"]["applied_code"], ps["promo_code"]["discount_amount"],
                        ps["services_total_amount"], ps["net_taxable_subtotal"],
                        ps["tax"]["rate"], ps["tax"]["amount"], ps["total_price"]
                    )
                )
                booking_id = cursor.lastrowid

                for pax in pricing["passengers_summary"]["passengers"]:
                    cursor.execute(
                        "INSERT INTO booking_passengers (booking_id, passenger_type, age, fare_charged) VALUES (?, ?, ?, ?)",
                        (booking_id, pax["type"], pax["age"], pax["fare"])
                    )

                for svc in ps["services"]:
                    cursor.execute(
                        "INSERT INTO booking_services (booking_id, service_code, service_name, unit_price, total_amount) VALUES (?, ?, ?, ?, ?)",
                        (booking_id, svc["code"], svc["name"], svc["unit_price"], svc["total_amount"])
                    )

                if ps["promo_code"]["applied_code"]:
                    cursor.execute("SELECT id FROM promotional_codes WHERE code = ?", (ps["promo_code"]["applied_code"],))
                    promo_row = cursor.fetchone()
                    if promo_row:
                        promo_id = promo_row["id"]
                        cursor.execute("INSERT INTO promo_redemptions (promo_code_id, customer_email, booking_id) VALUES (?, ?, ?)", (promo_id, cust_email, booking_id))
                        cursor.execute("UPDATE promotional_codes SET current_total_uses = current_total_uses + 1 WHERE id = ?", (promo_id,))

                snapshot_payload = json.dumps(pricing, indent=2)
                cursor.execute("INSERT INTO booking_pricing_snapshots (booking_id, snapshot_json) VALUES (?, ?)", (booking_id, snapshot_payload))

                conn.commit()
                conn.close()

                return self._send_json({
                    "success": True,
                    "booking_reference": booking_ref,
                    "booking_id": booking_id,
                    "message": "Booking confirmed successfully!",
                    "pricing_summary": ps,
                    "passengers_summary": pricing["passengers_summary"],
                    "full_pricing": pricing
                })

            elif path == "/api/admin/cruises":
                cursor.execute(
                    """INSERT INTO cruises (cruise_line, ship_name, departure_port, destination, nights, adult_fare, total_capacity, capacity_left)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (body["cruise_line"], body["ship_name"], body.get("departure_port", "PortMiami, FL"), body["destination"], int(body["nights"]), float(body["adult_fare"]), int(body["total_capacity"]), int(body["total_capacity"]))
                )
                conn.commit()
                conn.close()
                return self._send_json({"success": True, "message": "Cruise created successfully."})

            elif path == "/api/admin/promos":
                cursor.execute(
                    """INSERT INTO promotional_codes 
                       (code, type, value, valid_from, valid_to, max_total_uses, max_uses_per_customer, min_spend)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (body["code"].upper(), body["type"], float(body["value"]), body["valid_from"], body["valid_to"], int(body["max_total_uses"]), int(body["max_uses_per_customer"]), float(body.get("min_spend", 0)))
                )
                conn.commit()
                conn.close()
                return self._send_json({"success": True, "message": f"Promo code '{body['code']}' created."})

            else:
                conn.close()
                self._send_error_json("Endpoint not found.", 404)

        except Exception as err:
            conn.rollback()
            conn.close()
            self._send_error_json(str(err), 400)

def run_server(port=PORT):
    init_db()
    server_address = ('127.0.0.1', port)
    HTTPServer.allow_reuse_address = True
    httpd = HTTPServer(server_address, CruiseBookingRequestHandler)
    print(f"============================================================")
    print(f"  Odysseus Cruise Booking System Running")
    print(f"  URL: http://localhost:{port}")
    print(f"============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
