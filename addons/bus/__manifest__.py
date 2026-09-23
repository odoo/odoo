{
    "name": "IM Bus",
    "version": "1.0",
    "category": "Hidden",
    "description": "Instant Messaging Bus allow you to send messages to users, in live.",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "bus/static/src/*.js",
            "bus/static/src/debug/**/*",
            "bus/static/src/services/**/*.js",
            "bus/static/src/workers/*",
            (
                "remove",
                "bus/static/src/workers/bus_worker_script.js",
            ),
        ],
        "web.assets_frontend": [
            "bus/static/src/*.js",
            "bus/static/src/services/**/*.js",
            (
                "remove",
                "bus/static/src/services/assets_watchdog_service.js",
            ),
            (
                "remove",
                "bus/static/src/simple_notification_service.js",
            ),
            "bus/static/src/workers/*",
            (
                "remove",
                "bus/static/src/workers/bus_worker_script.js",
            ),
        ],
        "web.assets_unit_tests": [
            "bus/static/tests/**/*",
        ],
        "bus.websocket_worker_assets": [
            "bus/static/src/workers/*",
        ],
    },
    "esm": {
        "bundles": [
            "bus.websocket_worker_assets",
        ],
        "standalone_bundles": [
            "bus.websocket_worker_assets",
        ],
    },
    "auto_install": True,
}
