from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists


def migrate(cr, version):
    if not version:
        return
    if table_exists(cr, "maintenance_order_migrated_stage"):
        cr.execute(
            """
            SELECT order_id, COALESCE(stage_name->>'en_US', stage_name::text)
              FROM maintenance_order_migrated_stage
            """
        )
        rows = cr.fetchall()
        env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True})
        orders = env["maintenance.order"].browse([order_id for order_id, _name in rows])
        stage_by_order = dict(rows)
        for order in orders.exists():
            order.message_post(
                body=env._(
                    "This order was in the stage %(stage)s when stages were replaced by its status.",
                    stage=stage_by_order[order.id],
                ),
                message_type="notification",
            )
        cr.execute("DROP TABLE maintenance_order_migrated_stage")
    for column in ("stage_id", "archive"):
        if column_exists(cr, "maintenance_order", column):
            cr.execute(f"ALTER TABLE maintenance_order DROP COLUMN {column}")
