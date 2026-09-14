{
    "name": "Portal Account Security",
    "category": "Hidden/Tools",
    "summary": "Two-factor authentication and passkeys on the portal account page",
    "description": """
Portal Account Security
=======================
Exposes the credential management that ``auth_totp`` and ``auth_passkey``
provide in the backend on the portal's ``/my/security`` page: enabling and
disabling two-factor authentication, revoking trusted devices, and adding,
renaming and deleting passkeys.

Merged from the former ``auth_totp_portal`` and ``auth_passkey_portal``. Both
were ``auto_install`` on ``portal`` plus an always-installed parent, so neither
could ever exist without the other; they extended the same view and shipped the
same kind of frontend interaction.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "portal",
        "auth_totp",
        "auth_totp_mail",
        "auth_passkey",
    ],
    "data": [
        "security/security.xml",
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "auth_portal/static/src/**/*",
        ],
        "web.assets_tests": [
            "auth_portal/static/tests/tours/**/*",
        ],
        "web.assets_unit_tests_setup": [
            "auth_passkey/static/lib/simplewebauthn.js",
            "auth_passkey/static/src/passkey_lib.js",
            "auth_portal/static/src/interactions/**/*",
            "auth_portal/static/src/xml/**/*",
        ],
        "web.assets_unit_tests": [
            "auth_portal/static/tests/**/*.test.js",
        ],
    },
    "auto_install": True,
    "pre_init_hook": "pre_init_hook",
}
