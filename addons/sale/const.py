# Mapping of config parameters to the crons they toggle.
PARAM_CRON_MAPPING = {
    "sale.async_emails": "sale.send_pending_emails_cron",
    "sale.automatic_invoice": "sale.send_invoice_cron",
}

# Maximum number of products to list individually in chatter messages.
# Above this threshold, messages will summarize instead of listing each product.
CHATTER_PRODUCT_LIST_THRESHOLD = 50

# Seconds in one day (24 hours)
ONE_DAY_SECONDS = 86400

# Default tolerance for date matching in merge operations (24 hours)
DATE_MATCH_THRESHOLD_SECONDS = ONE_DAY_SECONDS

ORDER_STATE = [
    ("draft", "Quotation"),
    ("done", "Sales Order"),
    ("cancel", "Cancelled"),
]

INVOICE_STATE = [
    ("no", "Nothing to invoice"),
    ("to do", "To invoice"),
    ("partial", "Partially invoiced"),
    ("done", "Fully invoiced"),
    ("over done", "Over-invoiced"),
]
