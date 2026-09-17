from odoo.db.schema import column_exists, table_exists

RELIABILITY_COLUMNS = {
    "maintenance_team_id": "maintenance_team_id",
    "technician_user_id": "technician_user_id",
    "expected_mtbf": "expected_mtbf",
    "date_effective": "date_in_service",
}


def migrate(cr, version):
    if not version:
        return
    _link_resources(cr, "maintenance_order", "order_id", "block_asset")
    _link_resources(cr, "maintenance_plan", "plan_id", "block_asset")
    _move_reliability(cr, "resource_asset", "resource_id")
    if column_exists(cr, "resource_reservation", "booking_key"):
        cr.execute(
            """
            UPDATE resource_reservation
               SET booking_key = NULL
             WHERE res_model = 'maintenance.order' AND booking_key = 'asset'
            """
        )
    for table in ("maintenance_order", "maintenance_plan"):
        for column in ("asset_id", "block_asset"):
            if column_exists(cr, table, column):
                cr.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')
    for column in RELIABILITY_COLUMNS:
        if column_exists(cr, "resource_asset", column):
            cr.execute(f'ALTER TABLE resource_asset DROP COLUMN "{column}"')


def _link_resources(cr, table, column, block_column):
    if not column_exists(cr, table, "asset_id"):
        return
    cr.execute(
        f"""
        INSERT INTO {table}_resource_rel ({column}, resource_id)
        SELECT record.id, asset.resource_id
          FROM "{table}" record
          JOIN resource_asset asset ON asset.id = record.asset_id
        ON CONFLICT DO NOTHING
        """
    )
    if column_exists(cr, table, block_column):
        cr.execute(
            f"""
            UPDATE "{table}"
               SET block_resource = COALESCE({block_column}, FALSE)
             WHERE asset_id IS NOT NULL
            """
        )


def _move_reliability(cr, table, resource_column):
    if not table_exists(cr, table):
        return
    columns = [c for c in RELIABILITY_COLUMNS if column_exists(cr, table, c)]
    if not columns:
        return
    assignments = ", ".join(
        f"{RELIABILITY_COLUMNS[c]} = COALESCE(source.{c}, resource.{RELIABILITY_COLUMNS[c]})"
        for c in columns
    )
    cr.execute(
        f"""
        UPDATE resource_resource resource
           SET {assignments}
          FROM "{table}" source
         WHERE source.{resource_column} = resource.id
        """
    )
