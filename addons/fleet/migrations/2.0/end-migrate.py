from odoo.db.schema import table_exists

RETIRED_TABLES = (
    "fleet_vehicle_vehicle_tag_rel",
    "fleet_vehicle_model_vendors",
    "fleet_service_type_fleet_vehicle_log_contract_rel",
    "fleet_vehicle_fleet_vehicle_send_mail_rel",
    "fleet_vehicle_log_services",
    "fleet_vehicle_log_contract",
    "fleet_vehicle_assignation_log",
    "fleet_vehicle_odometer",
    "fleet_vehicle_model",
    "fleet_vehicle_model_brand",
    "fleet_vehicle_model_category",
    "fleet_vehicle_state",
    "fleet_service_type",
)


def migrate(cr, version):
    if not version:
        return
    for view in ("fleet_vehicle_cost_report", "fleet_vehicle_odometer_report"):
        cr.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
    for table in RETIRED_TABLES:
        if table_exists(cr, table):
            cr.execute(f"DROP TABLE {table} CASCADE")
