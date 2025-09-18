"""Constants for the Purchase module."""

# ------------------------------------------------------------
# STATE DEFINITIONS
# ------------------------------------------------------------

ORDER_STATE = [
    ("draft", "RFQ"),
    ("done", "Purchase Order"),
    ("cancel", "Cancelled"),
]

INVOICE_STATE = [
    ("no", "Nothing to invoice"),
    ("to do", "To invoice"),
    ("partial", "Partially invoiced"),
    ("done", "Fully invoiced"),
    ("over done", "Over-invoiced"),
]

# Invoice state priority for determining order-level state
# Higher priority states take precedence when aggregating line states
INVOICE_STATE_PRIORITY = ["over done", "to do", "partial", "done", "no"]

# ------------------------------------------------------------
# TIME CONSTANTS
# ------------------------------------------------------------

# Seconds in one day (24 hours)
ONE_DAY_SECONDS = 86400

# Default tolerance for date matching in merge operations (24 hours)
DATE_MATCH_THRESHOLD_SECONDS = ONE_DAY_SECONDS

# ------------------------------------------------------------
# DISPLAY LIMITS
# ------------------------------------------------------------

# Maximum number of products to show in change messages
MAX_PRODUCTS_IN_MESSAGE = 50

# Maximum number of suppliers to display per product in views
MAX_SUPPLIERS_PER_PRODUCT = 10

# ------------------------------------------------------------
# TOLERANCE VALUES
# ------------------------------------------------------------

# Tolerance for float comparisons in billing matching (2%)
BILLING_MATCH_TOLERANCE = 0.02
