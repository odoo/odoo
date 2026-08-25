{
    "name": "Web Serial IoT devices",
    "category": "Administration/IoT",
    "sequence": 300,
    "summary": "Interface with serial devices directly via the browser using Web Serial.",
    "description": """
This module provides support for interfacing with serial devices locally via the Web Serial API.
Since the browser is used directly no IoT box is required.
""",
    "depends": ["web"],
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "assets": {
        "web.assets_backend": [
            "iot_webserial/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "iot_webserial/static/tests/**/*",
        ],
    },
}
