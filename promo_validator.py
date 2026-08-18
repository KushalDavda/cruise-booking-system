"""
Promotional Code Validation Engine for Odysseus Cruise Booking System.
Provides explicit failure reasons per Functional Requirement FR-04.
"""
from datetime import datetime, date

def validate_promo_code(code_str, pre_promo_subtotal, customer_email, db_conn, current_dt=None):
    """
    Validates a promotional code against database rules and customer redemption history.
    
    Returns:
        dict: {
            "is_valid": bool,
            "error_code": str or None,
            "error_message": str or None,
            "promo": dict or None,
            "discount_amount": float
        }
    """
    if not code_str or not code_str.strip():
        return {
            "is_valid": True,
            "error_code": None,
            "error_message": None,
            "promo": None,
            "discount_amount": 0.0
        }

    code_str = code_str.strip().upper()
    if current_dt is None:
        current_dt = date.today()
    elif isinstance(current_dt, datetime):
        current_dt = current_dt.date()

    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM promotional_codes WHERE code = ?", (code_str,))
    promo = cursor.fetchone()

    # 1. Existence check
    if not promo or promo["is_active"] != 1:
        return {
            "is_valid": False,
            "error_code": "INVALID_CODE",
            "error_message": f"Promotional code '{code_str}' does not exist or is inactive.",
            "promo": None,
            "discount_amount": 0.0
        }

    # Convert row to dict
    promo_dict = dict(promo)

    # 2. Date validity check
    valid_from = datetime.strptime(promo_dict["valid_from"], "%Y-%m-%d").date()
    valid_to = datetime.strptime(promo_dict["valid_to"], "%Y-%m-%d").date()
    if not (valid_from <= current_dt <= valid_to):
        return {
            "is_valid": False,
            "error_code": "EXPIRED_CODE",
            "error_message": f"Promotional code '{code_str}' expired on {valid_to.strftime('%b %d, %Y')} or is not yet active.",
            "promo": promo_dict,
            "discount_amount": 0.0
        }

    # 3. Total uses check
    if promo_dict["current_total_uses"] >= promo_dict["max_total_uses"]:
        return {
            "is_valid": False,
            "error_code": "TOTAL_LIMIT_REACHED",
            "error_message": f"Promotional code '{code_str}' has reached its maximum global usage limit ({promo_dict['max_total_uses']} uses).",
            "promo": promo_dict,
            "discount_amount": 0.0
        }

    # 4. Customer limit check
    if customer_email:
        cursor.execute(
            """SELECT COUNT(*) FROM promo_redemptions 
               WHERE promo_code_id = ? AND customer_email = ?""",
            (promo_dict["id"], customer_email.lower().strip())
        )
        user_redemptions = cursor.fetchone()[0]
        if user_redemptions >= promo_dict["max_uses_per_customer"]:
            return {
                "is_valid": False,
                "error_code": "CUSTOMER_LIMIT_REACHED",
                "error_message": f"You have already redeemed promotional code '{code_str}' the maximum allowed times ({promo_dict['max_uses_per_customer']} time(s)).",
                "promo": promo_dict,
                "discount_amount": 0.0
            }

    # 5. Minimum spend check
    min_spend = promo_dict["min_spend"]
    if pre_promo_subtotal < min_spend:
        return {
            "is_valid": False,
            "error_code": "MINIMUM_SPEND_NOT_MET",
            "error_message": f"Promotional code '{code_str}' requires a minimum spend of ${min_spend:,.2f}. Your subtotal is ${pre_promo_subtotal:,.2f}.",
            "promo": promo_dict,
            "discount_amount": 0.0
        }

    # Calculate discount
    if promo_dict["type"] == "Percentage":
        discount = round(pre_promo_subtotal * (promo_dict["value"] / 100.0), 2)
    elif promo_dict["type"] == "Fixed":
        discount = round(min(promo_dict["value"], pre_promo_subtotal), 2)
    else:
        discount = 0.0

    return {
        "is_valid": True,
        "error_code": None,
        "error_message": None,
        "promo": promo_dict,
        "discount_amount": discount
    }
