{
    "name": "Custom IBM Flex Arabic Font",
    "version": "1.0",
    "summary": "Apply IBM Flex Sans Arabic font across Odoo 19 backend & website",
    "category": "Theme/Backend",
    "depends": ["web", "website"],
    "assets": {
        "web.assets_backend": [
            "/custom_ibm_flex_font/static/src/scss/custom_font.scss"
        ],
        "web.assets_frontend": [
            "/custom_ibm_flex_font/static/src/scss/custom_font.scss"
        ],
        "website.assets_editor": [
            "/custom_ibm_flex_font/static/src/scss/custom_font.scss"
        ]
    },
    "installable": true,
    "application": false
}
