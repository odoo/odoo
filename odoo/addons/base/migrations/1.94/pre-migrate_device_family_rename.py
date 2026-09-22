from odoo.tools.module_data import rename_module

RENAMES = (
    ("agro_surface_remote_gps_geoengine", "agro_surface_device_gps_geoengine"),
    ("asset_ledger_maintenance_remote", "asset_ledger_maintenance_gps"),
    ("project_task_remote_visit", "project_task_device_visit"),
    ("asset_remote_geoengine", "asset_gps_geoengine"),
    ("remote_access_device", "device_access_control"),
    ("remote_gps_geoengine", "device_gps_geoengine"),
    ("remote_mobile_speech", "device_mobile_speech"),
    ("asset_delivery_remote", "asset_delivery_gps"),
    ("remote_websocket", "device_websocket"),
    ("remote_dav_sync", "device_dav_sync"),
    ("remote_machines", "device_machines"),
    ("asset_remote_hr", "asset_gps_hr"),
    ("remote_modbus", "device_modbus"),
    ("remote_mobile", "device_mobile"),
    ("remote_mqtt", "device_mqtt"),
    ("asset_remote", "asset_gps"),
    ("remote_gps", "device_gps"),
    ("remote_hr", "device_hr"),
    ("remote", "device"),
)


def migrate(cr, version):
    """agromarin's remote family is the device family (transport plan §9.2, B)."""
    if not version:
        return
    for old, new in RENAMES:
        rename_module(cr, old, new)
