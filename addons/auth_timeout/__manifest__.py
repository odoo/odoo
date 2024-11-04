{
    "name": "Auth Timeout",
    "summary": "Ask for authentication after user inactivity",
    "category": "Hidden/Tools",
    "depends": ["auth_totp", "auth_totp_mail", "auth_passkey", "bus"],
    "data": [
        "views/login_templates.xml",
        "views/res_groups_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "auth_timeout/static/src/services/check_identity/*",
        ],
        "web.assets_frontend": [
            "auth_timeout/static/src/services/check_identity/*",
            "auth_timeout/static/src/scss/auth_timeout.scss",
        ],
        "web.assets_tests": [
            "auth_timeout/static/tests/tours/**/*",
        ],
    },
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
