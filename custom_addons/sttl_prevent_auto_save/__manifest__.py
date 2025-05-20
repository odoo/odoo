{
    'name': "Prevent AutoSave",
    'summary': """
            This module allows the user to disable the auto save feature of Odoo.
        """,
    "description": """

    """,
    "author": "Silver Touch Technologies Limited",
    "website": "https://www.silvertouch.com",
    'category': 'Technical',
    'version': '18.0.1.0',
    'license': 'LGPL-3',
    'depends': ["base", "web"],
    'demo': [],
    'data': [
        "security/ir.model.access.csv",
        "data/prevent_model_demo.xml",
        "views/prevent_autosave_views.xml",
    ],
    'installable': True,
    'auto_install': False,
    'assets': {
        "web.assets_backend": [
            "sttl_prevent_auto_save/static/src/js/prevent_autosave_formcontroller.js",
            "sttl_prevent_auto_save/static/src/js/prevent_autosave_listcontroller.js",
        ],
    },
    'images': ['static/description/banner.png'],
}
