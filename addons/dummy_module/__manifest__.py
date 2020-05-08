{
    "name": "Dummy",
    "author": "a",
    "summary": """
    Dummy to tests translations of menus and views from Website
    """,
    "website": "",
    "license": "LGPL-3",
    "category": "",
    "version": "1.0.0.0.0",
    "depends": [
        'website_sale',
    ],
    "data": [
        # Website stuff (A file per page)
        "views/homepage.xml",

        # Main Configuration
        "data/res_config_settings.xml",

        # Data
        'data/website.xml',
    ],
    "demo": [
    ],
    "test": [
    ],
    "qweb": [],
    "auto_install": True,
    "application": True,
    "installable": True,
}

