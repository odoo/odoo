{
    "name": "Base - Module Install Request",
    "version": "1.2",
    "category": "Hidden",
    "description": """
Allow internal users requesting a module installation
=====================================================
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/ir.access.csv",
        "wizards/base_module_install_request_views.xml",
        "data/mail_template_data.xml",
        "data/mail_templates_module_install.xml",
        "views/ir_module_module_views.xml",
    ],
    "auto_install": True,
    "post_init_hook": "_auto_install_apps",
}
