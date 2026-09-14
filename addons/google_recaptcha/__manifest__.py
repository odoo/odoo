{
    "name": "Google reCAPTCHA integration",
    "version": "1.1",
    "category": "Hidden",
    "description": """
This module implements reCaptchaV3 so that you can prevent bot spam on your public modules.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "web",
    ],
    "data": [
        "views/res_config_settings_view.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "google_recaptcha/static/src/scss/recaptcha.scss",
            "google_recaptcha/static/src/js/recaptcha.js",
            "google_recaptcha/static/src/interactions/**/*",
        ],
        "web.assets_backend": [
            "google_recaptcha/static/src/xml/recaptcha.xml",
        ],
    },
}
