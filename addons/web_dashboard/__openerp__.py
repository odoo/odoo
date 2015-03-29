{
    'name' : 'Odoo Dashboard',
    'version': '1.0',
    'summary': '',
    'category': 'Tools',
    'description':
        """
Odoo dashboard
==============

        """,
    'data': [
        "views/dashboard_menu.xml",
        "views/dashboard_assets.xml",
        "views/dashboard_data.xml",
    ],
    'depends' : ['auth_signup', 'planner'],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
