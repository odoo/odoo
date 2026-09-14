{
    "name": "Internet of Things",
    "category": "Supply Chain/IoT",
    "sequence": 250,
    "summary": "Connect and manage IoT Boxes and the devices attached to them.",
    "description": """
This module provides management of your IoT Boxes inside Odoo.

It owns the box and device registry, the routes an IoT Box calls home on, and
the browser-side transport stack used to reach a device. Device drivers ship in
their own ``iot_*`` modules, so installing one never drags an application in.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "integration",
        "mail",
    ],
    "data": [
        "wizards/add_iot_box_views.xml",
        "wizards/select_printers_views.xml",
        "security/iot_security.xml",
        "security/ir.model.access.csv",
        "views/iot_views.xml",
        "views/iot_menus.xml",
    ],
    "demo": [
        "demo/iot_demo.xml",
    ],
    "assets": {
        "iot.assets_client": [
            "iot/static/src/network_utils/**/*",
            "iot/static/src/device_controller.js",
            "iot/static/src/device_messages.js",
        ],
        "iot.assets_report": [
            "iot/static/src/iot_report_action.js",
            "iot/static/src/select_printer_wizard.js",
            "iot/static/src/client_action/delete_local_storage.js",
        ],
        "web.assets_backend": [
            (
                "include",
                "iot.assets_client",
            ),
            (
                "include",
                "iot.assets_report",
            ),
            "iot/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "iot/static/tests/unit/**/*",
        ],
        "web.assets_tests": [
            (
                "include",
                "iot.assets_tests",
            ),
        ],
        "iot.assets_tests": [
            "iot/static/tests/tours/**/*",
        ],
    },
    "application": True,
}
