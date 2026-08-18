"""
Pure Python Pricing Engine for Odysseus Cruise Booking System.
Computes adult & child fares, group discounts, optional travel services,
promotional discounts, tax, and itemized line-item breakdowns.
"""
from promo_validator import validate_promo_code

def calculate_booking_price(
    cruise,
    adult_count,
    child_ages,
    services_selected,
    promo_code_str,
    customer_email,
    db_conn,
    current_dt=None
):
    """
    Calculates itemized pricing for a cruise booking.

    Args:
        cruise (dict/Row): Cruise metadata containing adult_fare and nights.
        adult_count (int): Number of adult passengers (18+).
        child_ages (list of int): List of ages for child passengers (0-17).
        services_selected (list of str): List of optional service codes selected ('INSURANCE', 'WIFI', 'EXCURSION').
        promo_code_str (str): Optional promotional code.
        customer_email (str): Customer email address.
        db_conn (sqlite3.Connection): SQLite database connection.
        current_dt (date, optional): Evaluation date.

    Returns:
        dict: Full itemized calculation breakdown.
    """
    if child_ages is None:
        child_ages = []
    if services_selected is None:
        services_selected = []

    total_passengers = adult_count + len(child_ages)

    # 1. Passenger Count Boundaries Validation
    if adult_count < 1:
        raise ValueError("Booking must include at least 1 adult passenger.")
    if total_passengers > 6:
        raise ValueError(f"Booking cannot exceed 6 passengers in total (currently {total_passengers}).")

    for age in child_ages:
        if not isinstance(age, int) or age < 0 or age > 17:
            raise ValueError(f"Child age must be an integer between 0 and 17 (received {age}).")

    cursor = db_conn.cursor()

    # 2. Fetch Active Child Age Bands
    cursor.execute("SELECT * FROM child_age_bands ORDER BY min_age ASC")
    age_bands = [dict(r) for r in cursor.fetchall()]

    # 3. Adult Fare Calculation
    adult_base_fare = float(cruise["adult_fare"])
    adult_subtotal = round(adult_count * adult_base_fare, 2)

    # 4. Child Fares Calculation
    passengers_breakdown = []
    for i in range(adult_count):
        passengers_breakdown.append({
            "type": "Adult",
            "age": 18,
            "fare": adult_base_fare,
            "label": "Adult Fare (100%)"
        })

    child_subtotal = 0.0
    for child_age in child_ages:
        band_applied = None
        for band in age_bands:
            if band["min_age"] <= child_age <= band["max_age"]:
                band_applied = band
                break

        if band_applied:
            pct = band_applied["fare_percentage"]
            fare = round(adult_base_fare * (pct / 100.0), 2)
            label = f"Child Age {child_age} ({band_applied['label']})"
        else:
            pct = 100.0
            fare = adult_base_fare
            label = f"Child Age {child_age} (Standard)"

        child_subtotal += fare
        passengers_breakdown.append({
            "type": "Child",
            "age": child_age,
            "fare": fare,
            "label": label
        })

    child_subtotal = round(child_subtotal, 2)
    cruise_fare_subtotal = round(adult_subtotal + child_subtotal, 2)

    # 5. Group Discount Calculation (Cruise Fare only)
    cursor.execute("SELECT * FROM group_discounts ORDER BY min_passengers ASC")
    group_tiers = [dict(r) for r in cursor.fetchall()]

    group_discount_pct = 0.0
    for tier in group_tiers:
        if tier["min_passengers"] <= total_passengers <= tier["max_passengers"]:
            group_discount_pct = float(tier["discount_percentage"])
            break

    group_discount_amount = round(cruise_fare_subtotal * (group_discount_pct / 100.0), 2)
    discounted_cruise_subtotal = round(cruise_fare_subtotal - group_discount_amount, 2)

    # 6. Optional Services Calculation
    cursor.execute("SELECT * FROM optional_services")
    all_services = {r["code"]: dict(r) for r in cursor.fetchall()}

    services_breakdown = []
    services_total_amount = 0.0

    for s_code in services_selected:
        s_code_upper = s_code.upper()
        if s_code_upper in all_services:
            svc = all_services[s_code_upper]
            if svc["price_type"] == "PerPassengerPerNight":
                unit_price = float(svc["price"])
                total_svc = round(unit_price * total_passengers * cruise["nights"], 2)
                detail = f"${unit_price:,.2f} x {total_passengers} pax x {cruise['nights']} nights"
            else: # PerPassenger
                unit_price = float(svc["price"])
                total_svc = round(unit_price * total_passengers, 2)
                detail = f"${unit_price:,.2f} x {total_passengers} pax"

            services_total_amount += total_svc
            services_breakdown.append({
                "code": svc["code"],
                "name": svc["name"],
                "unit_price": unit_price,
                "price_type": svc["price_type"],
                "detail": detail,
                "total_amount": total_svc
            })

    services_total_amount = round(services_total_amount, 2)

    # 7. Pre-Promo Subtotal
    pre_promo_subtotal = round(discounted_cruise_subtotal + services_total_amount, 2)

    # 8. Promotional Code Validation & Discount
    promo_result = validate_promo_code(
        code_str=promo_code_str,
        pre_promo_subtotal=pre_promo_subtotal,
        customer_email=customer_email,
        db_conn=db_conn,
        current_dt=current_dt
    )

    promo_discount_amount = promo_result["discount_amount"]
    net_taxable_subtotal = round(max(0.0, pre_promo_subtotal - promo_discount_amount), 2)

    # 9. Tax Calculation (12% of net taxable subtotal)
    cursor.execute("SELECT value FROM system_config WHERE key = 'tax_rate'")
    tax_row = cursor.fetchone()
    tax_rate = float(tax_row["value"]) if tax_row else 0.12

    tax_amount = round(net_taxable_subtotal * tax_rate, 2)
    total_price = round(net_taxable_subtotal + tax_amount, 2)

    # 10. Construct Line Item Breakdown Response
    return {
        "cruise": {
            "id": cruise["id"],
            "ship_name": cruise["ship_name"],
            "cruise_line": cruise["cruise_line"],
            "departure_port": cruise["departure_port"] if "departure_port" in cruise.keys() else "PortMiami, FL",
            "destination": cruise["destination"],
            "nights": cruise["nights"],
            "adult_base_fare": adult_base_fare
        },
        "passengers_summary": {
            "adult_count": adult_count,
            "child_count": len(child_ages),
            "total_passengers": total_passengers,
            "passengers": passengers_breakdown
        },
        "pricing_summary": {
            "adult_subtotal": adult_subtotal,
            "child_subtotal": child_subtotal,
            "gross_cruise_subtotal": cruise_fare_subtotal,
            "group_discount": {
                "percentage": group_discount_pct,
                "amount": group_discount_amount
            },
            "discounted_cruise_subtotal": discounted_cruise_subtotal,
            "services": services_breakdown,
            "services_total_amount": services_total_amount,
            "pre_promo_subtotal": pre_promo_subtotal,
            "promo_code": {
                "applied_code": promo_code_str.upper() if (promo_code_str and promo_result["is_valid"]) else None,
                "is_valid": promo_result["is_valid"],
                "error_code": promo_result["error_code"],
                "error_message": promo_result["error_message"],
                "discount_amount": promo_discount_amount
            },
            "net_taxable_subtotal": net_taxable_subtotal,
            "tax": {
                "rate": tax_rate,
                "percentage_label": f"{int(tax_rate * 100)}%",
                "amount": tax_amount
            },
            "total_price": total_price
        }
    }
