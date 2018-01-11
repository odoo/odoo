{
    'name': 'Website Builder',
    'category': 'Website',
    'summary': 'Build Your Enterprise Website',
    'website': 'https://www.odoo.com/page/website-builder',
    'version': '1.0',
    'description': """
OpenERP Website CMS
===================

        """,
    'author': 'OpenERP SA',
    'depends': ['web', 'share', 'mail'],
    'installable': True,
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'security/ir_ui_view.xml',
        'views/website_templates.xml',
        'views/website_views.xml',
        'views/snippets.xml',
        'views/themes.xml',
        'views/res_config.xml',
        'views/ir_actions.xml',
        'views/website_backend_navbar.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'qweb': ['static/src/xml/website.backend.xml'],
    'application': True,
}
