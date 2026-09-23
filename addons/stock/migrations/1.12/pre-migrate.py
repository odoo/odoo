import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

RENAMES = (
    ("_compute_count_reordering_rules", "_compute_reordering_rules"),
    ("_compute_lead_days", "_compute_lead_time"),
    ("_compute_products_availability", "_compute_availability_status"),
    ("_compute_date_last_movement", "_compute_last_movement"),
    ("_compute_is_partial_package", "_compute_partial_packages"),
    ("_default_lot_sequence", "_default_lot_sequence_id"),
    ("_has_product_selectable_route", "_default_has_available_route_ids"),
    ("_inverse_inventory_quantity", "_inverse_inventory_quantity_auto_apply"),
    ("_compute_action_message", "_compute_rule_message"),
    ("_quantity_search_domain", "_get_domain_quantity_search"),
    ("_get_accessible_location_domain", "_get_domain_accessible_location"),
    ("_get_allocatable_demand_domain", "_get_domain_allocatable_demand"),
    ("_get_resupply_pick_leg_domain", "_get_domain_resupply_pick_leg"),
    ("_get_extra_domain", "_get_domain_extra"),
)

CODE_COLUMNS = (
    ("ir_act_server", "code"),
    ("ir_actions_server_history", "code"),
)


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return
    for table, column in CODE_COLUMNS:
        if not _table_exists(cr, table):
            continue
        for old, new in RENAMES:
            _rewrite(cr, table, column, old, new)


def _table_exists(cr: Cursor, table: str) -> bool:
    cr.execute("SELECT to_regclass(%s) IS NOT NULL", (table,))
    return bool(cr.fetchone()[0])


def _rewrite(cr: Cursor, table: str, column: str, old: str, new: str) -> None:
    pattern = rf"\m{old}\M"
    cr.execute(
        f"UPDATE {table} SET {column} = regexp_replace({column}, %s, %s, 'g')"
        f" WHERE {column} ~ %s",
        (pattern, new, pattern),
    )
    if cr.rowcount:
        _logger.info(
            "stock 1.12: %s.%s %s -> %s (%d row(s))",
            table,
            column,
            old,
            new,
            cr.rowcount,
        )
