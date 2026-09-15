"""Pre-migration: `sale` owns the sales groups and absorbs `sale_management`,
and `sales_team` moves above `sale`, taking the team half of `sale` with it.

It runs in `base` because the `sale_management` module row has to go before the
graph is assembled, and because every row below has to change hands before
`sale` and `sales_team` load their data files: `sale` now loads first, and a
group left under `sales_team` would be created a second time by `sale`.

Field xml ids are repointed rather than left behind, because `_process_end`
deletes the record behind an orphaned `ir.model.fields` xml id, and for a field
that drops the column.
"""

import logging

from odoo.tools import SQL
from odoo.tools.module_data import adopt_xmlids

_logger = logging.getLogger(__name__)

DISSOLVED = "sale_management"
SALE = "sale"
SALES_TEAM = "sales_team"

DISSOLVED_RENAMED = {
    "digest_tip_sale1_management_0": "digest_tip_sale_configurable_products",
    "digest_tip_sale_management_1": "digest_tip_sale_product_grid",
}

DISSOLVED_SUPERSEDED_VIEWS = (
    "res_config_settings_view_form",
    "sale_order_form_quote",
    "sale_order_portal_content_inherit_sale_management",
)

GROUPS = (
    "res_groups_privilege_sales",
    "group_sale_readonly",
    "group_sale_salesman",
    "group_sale_salesman_team",
    "group_sale_salesman_all_leads",
    "group_sale_manager",
)

TEAM_RECORDS = (
    "action_quotations_salesteams",
    "action_quotation_form",
    "action_orders_salesteams",
    "action_orders_to_invoice_salesteams",
    "crm_team_salesteams_view_form",
    "crm_team_view_kanban_dashboard",
    "account_invoice_groupby_inherit",
    "account_invoice_view_tree",
    "action_invoice_salesteams",
    "action_invoice_salesteams_view_tree",
    "action_invoice_salesteams_view_form",
    "view_account_invoice_report_search_inherit",
    "account_invoice_report_view_tree",
    "action_account_invoice_report_salesteam",
    "action_sale_report_quotation_salesteam",
    "action_sale_report_so_salesteam",
    "sale_order_team_rule",
    "sale_order_line_team_rule",
    "sale_order_report_team_rule",
    "account_invoice_report_rule_see_team",
    "account_invoice_rule_see_team",
    "account_invoice_line_rule_see_team",
    "account_invoice_send_single_rule_see_team",
    "account_invoice_send_batch_rule_see_team",
    "mt_salesteam_order_sent",
    "mt_salesteam_order_viewed",
    "mt_salesteam_order_confirmed",
    "mt_salesteam_invoice_paid",
    "mt_salesteam_invoice_posted",
    "report_sales_team",
    "sales_team_config",
    "menu_tag_config",
    "field_sale_order__team_id",
    "field_sale_order__tag_ids",
    "field_account_move__team_id",
    "field_sale_report__team_id",
    "field_account_invoice_report__team_id",
    "field_team_team__invoiced",
    "field_team_team__invoiced_target",
    "field_team_team__sale_order_ids",
    "field_team_team__sale_order_count",
)

TEAM_CONSTRAINTS = (
    "account_move_team_id_fkey",
    "sale_order_team_id_fkey",
    "sale_order_tag_rel_order_id_fkey",
    "sale_order_tag_rel_tag_id_fkey",
)

TEAM_RELATIONS = ("sale_order_tag_rel",)

APP_MENU_MARKER = "sale.migration_app_menu_visible"


def migrate(cr, version):
    module_ids = _module_ids(cr, (DISSOLVED, SALE, SALES_TEAM))
    if DISSOLVED in module_ids and SALE in module_ids:
        _dissolve_sale_management(cr, module_ids[DISSOLVED], module_ids[SALE])
    if SALES_TEAM in module_ids and SALE in module_ids:
        adopt_xmlids(cr, SALES_TEAM, SALE, GROUPS)
        _drop_views_inline_in(cr, SALE, SALES_TEAM, TEAM_RECORDS)
        adopt_xmlids(cr, SALE, SALES_TEAM, TEAM_RECORDS)
        _move_schema_rows(
            cr,
            module_ids[SALE],
            module_ids[SALES_TEAM],
            constraints=TEAM_CONSTRAINTS,
            relations=TEAM_RELATIONS,
        )
        cr.execute(
            """
            DELETE FROM ir_module_module_dependency
             WHERE module_id = %s AND name = %s
            """,
            (module_ids[SALE], SALES_TEAM),
        )


def _module_ids(cr, names):
    cr.execute(
        "SELECT name, id FROM ir_module_module WHERE name = ANY(%s)",
        (list(names),),
    )
    return dict(cr.fetchall())


def _dissolve_sale_management(cr, module_id, sale_id):
    cr.execute("SELECT state FROM ir_module_module WHERE id = %s", (module_id,))
    (state,) = cr.fetchone()
    if state in ("installed", "to upgrade"):
        cr.execute(
            """
            INSERT INTO ir_config_parameter (key, value)
            VALUES (%s, 'True')
            ON CONFLICT (key) DO NOTHING
            """,
            (APP_MENU_MARKER,),
        )

    _drop_superseded_views(cr)
    for old_name, new_name in DISSOLVED_RENAMED.items():
        cr.execute(
            "UPDATE ir_model_data SET name = %s WHERE module = %s AND name = %s",
            (new_name, DISSOLVED, old_name),
        )
    cr.execute(
        """
        DELETE FROM ir_model_data d
              WHERE d.module = %s
                AND EXISTS (SELECT 1
                              FROM ir_model_data o
                             WHERE o.module = %s
                               AND o.name = d.name
                               AND o.model = d.model
                               AND o.res_id = d.res_id)
        """,
        (DISSOLVED, SALE),
    )
    _refuse_collisions(cr, DISSOLVED, SALE)
    cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s", (SALE, DISSOLVED)
    )
    _logger.info("repointed %s xml id(s) from %s to %s", cr.rowcount, DISSOLVED, SALE)
    _move_schema_rows(cr, module_id, sale_id)

    cr.execute(
        """
        DELETE FROM ir_module_module_dependency d
              WHERE d.name = %s
                AND EXISTS (SELECT 1
                              FROM ir_module_module_dependency o
                             WHERE o.module_id = d.module_id AND o.name = %s)
        """,
        (DISSOLVED, SALE),
    )
    cr.execute(
        "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
        (SALE, DISSOLVED),
    )
    cr.execute(
        "DELETE FROM ir_module_module_dependency WHERE module_id = %s", (module_id,)
    )
    cr.execute("DELETE FROM ir_module_module_exclusion WHERE name = %s", (DISSOLVED,))
    cr.execute(
        "DELETE FROM ir_model_data "
        "WHERE module = 'base' AND model = 'ir.module.module' AND res_id = %s",
        (module_id,),
    )
    cr.execute("DELETE FROM ir_module_module WHERE id = %s", (module_id,))
    _logger.info("dropped the %s module row, which was %s", DISSOLVED, state)


def _drop_superseded_views(cr):
    # The three views are inline in the sale views they patched. A view that
    # inherited one of them now inherits that sale view directly, since
    # ir_ui_view_inherit_id_fkey is RESTRICT and would refuse the delete.
    names = list(DISSOLVED_SUPERSEDED_VIEWS)
    cr.execute(
        """
        UPDATE ir_ui_view child
           SET inherit_id = superseded.inherit_id
          FROM ir_ui_view superseded
          JOIN ir_model_data d ON d.res_id = superseded.id
         WHERE d.module = %s AND d.model = 'ir.ui.view' AND d.name = ANY(%s)
           AND child.inherit_id = superseded.id
        """,
        (DISSOLVED, names),
    )
    _logger.info("repointed %s view(s) inheriting a superseded view", cr.rowcount)
    cr.execute(
        """
        DELETE FROM ir_ui_view
              WHERE id IN (SELECT res_id
                             FROM ir_model_data
                            WHERE module = %s AND model = 'ir.ui.view'
                              AND name = ANY(%s))
        """,
        (DISSOLVED, names),
    )
    deleted = cr.rowcount
    cr.execute(
        "DELETE FROM ir_model_data "
        "WHERE module = %s AND model = 'ir.ui.view' AND name = ANY(%s)",
        (DISSOLVED, names),
    )
    _logger.info("dropped %s superseded view(s), now inline in %s", deleted, SALE)


def _drop_views_inline_in(cr, from_module, to_module, names):
    # Upstream sale patched sales_team's views under the same xml id; that patch is
    # inline in the view sales_team now owns, so the two ids would collide.
    cr.execute(
        """
        SELECT patch.id, patched.id, d.name
          FROM ir_model_data d
          JOIN ir_ui_view patch ON patch.id = d.res_id
          JOIN ir_model_data o ON o.module = %s AND o.name = d.name
                              AND o.model = 'ir.ui.view'
          JOIN ir_ui_view patched ON patched.id = o.res_id
         WHERE d.module = %s AND d.model = 'ir.ui.view' AND d.name = ANY(%s)
           AND patch.inherit_id = patched.id
        """,
        (to_module, from_module, list(names)),
    )
    inlined = cr.fetchall()
    for patch_id, patched_id, name in inlined:
        cr.execute(
            "UPDATE ir_ui_view SET inherit_id = %s WHERE inherit_id = %s",
            (patched_id, patch_id),
        )
        cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (patch_id,))
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = %s AND name = %s",
            (from_module, name),
        )
    _logger.info(
        "dropped %s %s view(s) now inline in %s: %s",
        len(inlined),
        from_module,
        to_module,
        [name for _patch, _patched, name in inlined],
    )


def _refuse_collisions(cr, from_module, to_module):
    cr.execute(
        """
        SELECT d.name FROM ir_model_data d
         WHERE d.module = %s
           AND EXISTS (SELECT 1 FROM ir_model_data o
                        WHERE o.module = %s AND o.name = d.name)
         ORDER BY d.name
        """,
        (from_module, to_module),
    )
    clashing = [name for (name,) in cr.fetchall()]
    if clashing:
        raise ValueError(
            f"{from_module} and {to_module} both own {clashing}, naming different "
            f"records; rename them before repointing"
        )


def _move_schema_rows(cr, from_id, to_id, constraints=None, relations=None):
    # Constraints and many2many relations are owned by module id, not by xml
    # id; uninstalling their recorded owner drops them from the database.
    for table, names in (
        ("ir_model_constraint", constraints),
        ("ir_model_relation", relations),
    ):
        name_filter = SQL("AND d.name = ANY(%s)", list(names)) if names else SQL()
        cr.execute(
            SQL(
                """
                DELETE FROM %(table)s d
                      WHERE d.module = %(from_id)s
                        AND EXISTS (SELECT 1 FROM %(table)s o
                                     WHERE o.module = %(to_id)s AND o.name = d.name)
                        %(name_filter)s
                """,
                table=SQL.identifier(table),
                from_id=from_id,
                to_id=to_id,
                name_filter=name_filter,
            )
        )
        cr.execute(
            SQL(
                "UPDATE %(table)s d SET module = %(to_id)s "
                "WHERE d.module = %(from_id)s %(name_filter)s",
                table=SQL.identifier(table),
                from_id=from_id,
                to_id=to_id,
                name_filter=name_filter,
            )
        )
