QUANTITY_FIELDS = (
    "qty_available",
    "qty_free",
    "qty_incoming",
    "qty_outgoing",
    "qty_available_virtual",
)

TEMPLATE_QUANTITY_FIELDS = tuple(f for f in QUANTITY_FIELDS if f != "qty_free")

INVENTORY_REFERENCE_CONFIRMED = "Product Quantity Confirmed"
INVENTORY_REFERENCE_UPDATED = "Product Quantity Updated"
INVENTORY_REFERENCE_RELOCATED = "Quantity Relocated"
INVENTORY_REFERENCE_PACKAGE_RELOCATED = "Package manually relocated"
INVENTORY_REFERENCE_REVERTED = "%s [reverted]"

ADVANCED_STOCK_OPTION_GROUPS = (
    "stock.group_stock_multi_locations",
    "stock.group_tracking_owner",
    "stock.group_tracking_lot",
)

TEMPLATE_STOCK_FLAGS = ("type", "is_storable", "tracking")

BLOCK_TYPE_SELECTION = [
    ("none", "No Blocking"),
    ("soft_in", "Soft Block Incoming"),
    ("soft_out", "Soft Block Outgoing"),
    ("soft_both", "Soft Block Both Directions"),
    ("hard", "Hard Block (Freeze All)"),
]

INCOMING_BLOCK_TYPES = ("soft_in", "soft_both", "hard")
OUTGOING_BLOCK_TYPES = ("soft_out", "soft_both", "hard")

PARTNER_LOCATION_USAGES = ("supplier", "customer")
PARTNER_USAGE_BY_PICKING_CODE = {"incoming": "supplier", "outgoing": "customer"}

BLOCKABLE_USAGES = ("internal",)

DISPOSAL_DEST_USAGES = ("inventory", "production")

BLOCK_GOVERNED_FIELDS = frozenset({"block_type", "location_id", "active"})

BLOCK_REASON_COMPLETING = "completing"
BLOCK_REASON_DISPOSAL = "disposal"
BLOCK_REASON_OVERRIDE_HARD = "override_hard"
BLOCK_REASON_OVERRIDE_SOFT = "override_soft"

CONTEXT_ACTIVE_CASCADE = "stock_location_active_cascade"
CONTEXT_PUTAWAY_SCAN = "stock_putaway_scan"

CONTEXT_BLOCK_COMPLETING = "stock_blocked_completing"
CONTEXT_BLOCK_IS_INVENTORY = "stock_blocked_is_inventory"
CONTEXT_BLOCK_EXCLUDED_TYPES = "stock_blocked_excluded_types"
CONTEXT_BLOCK_SKIP_HOOKS = "stock_blocked_skip_hooks"
CONTEXT_BLOCK_BYPASS = "bypass_blocked_locations"

INTERNAL_CONTEXT_FLAG = object()


def is_internal_flag(context, key):
    return context.get(key) is INTERNAL_CONTEXT_FLAG


def get_internal_payload(value):
    return (INTERNAL_CONTEXT_FLAG, value)


def read_internal_payload(context, key, default=None):
    stored = context.get(key)
    if (
        isinstance(stored, tuple)
        and len(stored) == 2
        and stored[0] is INTERNAL_CONTEXT_FLAG
    ):
        return stored[1]
    return default
