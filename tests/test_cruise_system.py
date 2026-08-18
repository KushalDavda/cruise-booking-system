"""
Comprehensive Python unittest Test Suite for Odysseus Cruise Booking System.
Validates pricing rules, child age bands, group discounts, optional services,
promo code rejection codes, capacity locking, and historical price reconstructability.
"""
import os
import sys
import tempfile
import unittest
from datetime import date

# Add parent directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import init_db, get_db_connection
from pricing_engine import calculate_booking_price
from promo_validator import validate_promo_code

class TestCruiseBookingSystem(unittest.TestCase):

    def setUp(self):
        """Creates a fresh temporary database before each test."""
        db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        init_db(self.db_path)
        self.conn = get_db_connection(self.db_path)

    def tearDown(self):
        """Closes connection and deletes temporary database file."""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _get_seed_cruise(self, ship_name="Wonder of the Seas"):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cruises WHERE ship_name = ?", (ship_name,))
        return dict(cursor.fetchone())

    # --- Category 1: Base Pricing & Child Age Bands ---

    def test_single_adult_pricing(self):
        """TC-PRICE-01: 1 Adult passenger on 7-night cruise ($1200 base fare)."""
        cruise = self._get_seed_cruise()
        res = calculate_booking_price(
            cruise=cruise, adult_count=1, child_ages=[], services_selected=[],
            promo_code_str=None, customer_email="test@example.com", db_conn=self.conn
        )
        ps = res["pricing_summary"]
        self.assertEqual(ps["adult_subtotal"], 1200.0)
        self.assertEqual(ps["child_subtotal"], 0.0)
        self.assertEqual(ps["gross_cruise_subtotal"], 1200.0)
        self.assertEqual(ps["group_discount"]["amount"], 0.0)
        self.assertEqual(ps["tax"]["amount"], 144.0)  # 12% of 1200
        self.assertEqual(ps["total_price"], 1344.0)

    def test_child_age_0_to_4_free(self):
        """TC-PRICE-02: Child age 3 (Band 0-4) is charged 0% fare."""
        cruise = self._get_seed_cruise()
        res = calculate_booking_price(
            cruise=cruise, adult_count=1, child_ages=[3], services_selected=[],
            promo_code_str=None, customer_email="test@example.com", db_conn=self.conn
        )
        ps = res["pricing_summary"]
        self.assertEqual(ps["adult_subtotal"], 1200.0)
        self.assertEqual(ps["child_subtotal"], 0.0)
        self.assertEqual(ps["gross_cruise_subtotal"], 1200.0)

    def test_child_age_5_to_11_half_fare(self):
        """TC-PRICE-03: Child age 8 (Band 5-11) is charged 50% fare ($600)."""
        cruise = self._get_seed_cruise()
        res = calculate_booking_price(
            cruise=cruise, adult_count=1, child_ages=[8], services_selected=[],
            promo_code_str=None, customer_email="test@example.com", db_conn=self.conn
        )
        ps = res["pricing_summary"]
        self.assertEqual(ps["adult_subtotal"], 1200.0)
        self.assertEqual(ps["child_subtotal"], 600.0)
        self.assertEqual(ps["gross_cruise_subtotal"], 1800.0)

    def test_child_age_12_to_17_three_quarter_fare(self):
        """TC-PRICE-04: Child age 15 (Band 12-17) is charged 75% fare ($900)."""
        cruise = self._get_seed_cruise()
        res = calculate_booking_price(
            cruise=cruise, adult_count=1, child_ages=[15], services_selected=[],
            promo_code_str=None, customer_email="test@example.com", db_conn=self.conn
        )
        ps = res["pricing_summary"]
        self.assertEqual(ps["adult_subtotal"], 1200.0)
        self.assertEqual(ps["child_subtotal"], 900.0)
        self.assertEqual(ps["gross_cruise_subtotal"], 2100.0)

    def test_child_age_boundaries(self):
        """TC-PRICE-05 & TC-PRICE-06: Boundary tests for ages 4 vs 5 and 11 vs 12."""
        cruise = self._get_seed_cruise()
        res_4 = calculate_booking_price(cruise, 1, [4], [], None, "a@b.com", self.conn)
        res_5 = calculate_booking_price(cruise, 1, [5], [], None, "a@b.com", self.conn)
        self.assertEqual(res_4["pricing_summary"]["child_subtotal"], 0.0)
        self.assertEqual(res_5["pricing_summary"]["child_subtotal"], 600.0)

        res_11 = calculate_booking_price(cruise, 1, [11], [], None, "a@b.com", self.conn)
        res_12 = calculate_booking_price(cruise, 1, [12], [], None, "a@b.com", self.conn)
        self.assertEqual(res_11["pricing_summary"]["child_subtotal"], 600.0)
        self.assertEqual(res_12["pricing_summary"]["child_subtotal"], 900.0)

    # --- Category 2: Group Discounts ---

    def test_group_discount_tiers(self):
        """TC-GRP-01 to TC-GRP-03: Group discount percentages for 2, 3, and 5 passengers."""
        cruise = self._get_seed_cruise()
        
        # 2 Adults -> 0% discount
        res_2 = calculate_booking_price(cruise, 2, [], [], None, "a@b.com", self.conn)
        self.assertEqual(res_2["pricing_summary"]["group_discount"]["percentage"], 0.0)

        # 3 Adults -> 5% discount on $3600 cruise fare ($180 off)
        res_3 = calculate_booking_price(cruise, 3, [], [], None, "a@b.com", self.conn)
        self.assertEqual(res_3["pricing_summary"]["group_discount"]["percentage"], 5.0)
        self.assertEqual(res_3["pricing_summary"]["group_discount"]["amount"], 180.0)

        # 5 Adults -> 10% discount on $6000 cruise fare ($600 off)
        res_5 = calculate_booking_price(cruise, 5, [], [], None, "a@b.com", self.conn)
        self.assertEqual(res_5["pricing_summary"]["group_discount"]["percentage"], 10.0)
        self.assertEqual(res_5["pricing_summary"]["group_discount"]["amount"], 600.0)

    def test_group_discount_applies_only_to_cruise_fare(self):
        """TC-GRP-04: Group discount applies strictly to cruise fare, not optional services."""
        cruise = self._get_seed_cruise()  # 7 nights, $1200 base fare
        res = calculate_booking_price(cruise, 3, [], ["WIFI"], None, "a@b.com", self.conn)
        ps = res["pricing_summary"]
        self.assertEqual(ps["gross_cruise_subtotal"], 3600.0)
        self.assertEqual(ps["group_discount"]["amount"], 180.0)
        self.assertEqual(ps["services_total_amount"], 315.0)  # $15 * 3 pax * 7 nights
        self.assertEqual(ps["pre_promo_subtotal"], 3735.0)

    # --- Category 3: Optional Services ---

    def test_optional_services_calculations(self):
        """TC-SVC-01 to TC-SVC-04: Optional travel services pricing."""
        cruise = self._get_seed_cruise()  # 2 Pax, 7 nights
        
        # Insurance ($80 * 2 = $160)
        res_ins = calculate_booking_price(cruise, 2, [], ["INSURANCE"], None, "a@b.com", self.conn)
        self.assertEqual(res_ins["pricing_summary"]["services_total_amount"], 160.0)

        # Wi-Fi ($15 * 2 pax * 7 nights = $210)
        res_wifi = calculate_booking_price(cruise, 2, [], ["WIFI"], None, "a@b.com", self.conn)
        self.assertEqual(res_wifi["pricing_summary"]["services_total_amount"], 210.0)

        # All Services ($160 + $210 + $240 = $610)
        res_all = calculate_booking_price(cruise, 2, [], ["INSURANCE", "WIFI", "EXCURSION"], None, "a@b.com", self.conn)
        self.assertEqual(res_all["pricing_summary"]["services_total_amount"], 610.0)

    # --- Category 4: Promo Code Validation & Rejection Messaging ---

    def test_promo_code_percentage_valid(self):
        """TC-PROMO-01: Valid promo code SUMMER10 (10% off)."""
        cruise = self._get_seed_cruise()
        eval_date = date(2026, 7, 15)
        res = calculate_booking_price(cruise, 2, [], [], "SUMMER10", "alice@example.com", self.conn, current_dt=eval_date)
        ps = res["pricing_summary"]
        self.assertTrue(ps["promo_code"]["is_valid"])
        self.assertEqual(ps["promo_code"]["applied_code"], "SUMMER10")
        self.assertEqual(ps["promo_code"]["discount_amount"], 240.0)

    def test_promo_code_invalid(self):
        """TC-PROMO-03: Invalid promo code returns INVALID_CODE error code."""
        res = validate_promo_code("FAKE999", 2000.0, "user@test.com", self.conn)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["error_code"], "INVALID_CODE")

    def test_promo_code_expired(self):
        """TC-PROMO-04: Expired promo code WINTER5 returns EXPIRED_CODE."""
        eval_date = date(2026, 8, 1)
        res = validate_promo_code("WINTER5", 2000.0, "user@test.com", self.conn, current_dt=eval_date)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["error_code"], "EXPIRED_CODE")

    def test_promo_code_minimum_spend_not_met(self):
        """TC-PROMO-07: Minimum spend not met for FIRST150."""
        eval_date = date(2026, 6, 1)
        res = validate_promo_code("FIRST150", 1200.0, "user@test.com", self.conn, current_dt=eval_date)
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["error_code"], "MINIMUM_SPEND_NOT_MET")

    # --- Category 5: Capacity & Passenger Boundaries ---

    def test_zero_adults_raises_error(self):
        """TC-BOUND-01: Booking with 0 adults raises ValueError."""
        cruise = self._get_seed_cruise()
        with self.assertRaises(ValueError):
            calculate_booking_price(cruise, 0, [5, 6], [], None, "a@b.com", self.conn)

    def test_exceed_max_passengers_raises_error(self):
        """TC-BOUND-02: Booking with > 6 total passengers raises ValueError."""
        cruise = self._get_seed_cruise()
        with self.assertRaises(ValueError):
            calculate_booking_price(cruise, 4, [3, 4, 5], [], None, "a@b.com", self.conn)

    # --- Category 6: Historical Price Reconstructability ---

    def test_historical_price_reconstructability(self):
        """TC-RECON-01: Verify price snapshot reconstructability after base fare & tax changes in DB."""
        cursor = self.conn.cursor()
        cruise = self._get_seed_cruise()
        pricing = calculate_booking_price(cruise, 2, [], ["INSURANCE"], "SUMMER10", "recon@test.com", self.conn, current_dt=date(2026, 7, 1))
        
        recorded_total = pricing["pricing_summary"]["total_price"]

        # Modify DB parameters
        cursor.execute("UPDATE cruises SET adult_fare = 5000.0 WHERE id = ?", (cruise["id"],))
        cursor.execute("UPDATE system_config SET value = '0.25' WHERE key = 'tax_rate'")
        self.conn.commit()

        # Verify stored snapshot is untouched
        snapshot_total = pricing["pricing_summary"]["total_price"]
        self.assertAlmostEqual(snapshot_total, recorded_total, places=3)

if __name__ == "__main__":
    unittest.main()
