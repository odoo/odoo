{
    "name": "Remote - IoT Device Management",
    "version": "19.0.2.2.0",
    "category": "Supply Chain/IoT",
    "sequence": 10,
    "summary": "Universal Remote device management framework",
    "description": """
Remote - IoT Device Management
==============================

Device management for IoT endpoints, independent of the Odoo IoT Box.

Models
------
* ``device.device`` / ``device.kind`` -- the device registry
* ``device.profile`` -- connection settings, one protocol per config. This
  module ships HTTP/REST and HTTPS/REST; ``device_mqtt``, ``device_modbus``
  and ``device_websocket`` add theirs through ``selection_add``
* ``device.data.log`` / ``mixin.device.data.log`` -- time-series payload storage

Routes
------
* ``POST /remote/device/<identifier>/data`` -- device pushes a payload
* ``POST /remote/device/<identifier>/status`` -- device pushes its status

Devices push to Odoo or Odoo polls them. Bearer token authentication,
company-scoped records, commands and configuration sent back to the device,
events and alerts through ``mail``.

Transports
----------
A protocol contributes one ``comm_protocol`` value and one method per verb in
``TRANSPORT_VERBS`` -- ``<protocol>_connect``, ``<protocol>_disconnect``,
``<protocol>_read_data`` -- plus the ``_protocol_*`` hooks it needs. Nothing
else in ``device.device`` knows the protocol exists, so a transport that costs a
dependency lives in its own module: ``device_mqtt``, ``device_modbus``,
``device_websocket``.

Only HTTP and HTTPS are here, and they cost nothing ``requests`` does not
already cost. This module needs no third-party client and declares no
``external_dependencies``, so a site that polls REST sensors installs neither an
MQTT client nor a PLC library.
""",
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "images": [
        "static/description/icon.png",
    ],
    "license": "LGPL-3",
    "depends": [
        "certificate",
        "integration",
        "mail",
        "mixin_report_sql",
    ],
    "data": [
        "security/security.xml",
        "security/ir.access.csv",
        "data/ir_config_parameter_data.xml",
        "data/device_kind_data.xml",
        "data/ir_cron_data.xml",
        "views/device_profile_views.xml",
        "views/device_kind_views.xml",
        "views/device_data_log_views.xml",
        "views/device_device_views.xml",
        "views/device_dashboard_views.xml",
        "wizards/res_config_settings_views.xml",
        "reports/device_data_log_report_views.xml",
        "views/device_menu.xml",
    ],
    "demo": [
        "demo/ir_cron_demo.xml",
        "demo/device_profile_demo.xml",
        "demo/device_device_demo.xml",
        "demo/device_data_log_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "device/static/src/scss/device_device_kanban.scss",
        ],
    },
    "application": True,
    "uninstall_hook": "uninstall_hook",
}
