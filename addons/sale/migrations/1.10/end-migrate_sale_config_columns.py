from odoo.db.schema import column_exists

COLUMNS = (
    "order_lock_so",
    "portal_confirmation_sign",
    "portal_confirmation_pay",
    "prepayment_percent",
    "quotation_validity_days",
    "sale_discount_product_id",
    "sale_onboarding_payment_method",
    "sale_order_template_id",
    "downpayment_account_id",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if column_exists(cr, "res_company", column):
            cr.execute(f"ALTER TABLE res_company DROP COLUMN {column} CASCADE")
