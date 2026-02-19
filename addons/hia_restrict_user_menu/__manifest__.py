{
    'name': 'Restrict User Menu',
    'version': '16.0.1.0.0',
    'summary': 'Restrict menu access for specific users',
    'description': 'Hide Menu, Restrict Menu, hide, restrict, restrict menus, hide menu odoo,Hide Any Menu Item User Wise, Hide Menu Items, Hide Menu',
    'category': 'Extra Tools',
    'author': 'Himanjali Intelligent Automation Private Limited',
    'company': 'Himanjali Intelligent Automation Private Limited',
    'maintainer': 'Himanjali Intelligent Automation Private Limited',
    'website': "https://www.himanjali.com/",
    'depends': ['base'],
    'data': [
        'views/res_users.xml',
        'security/security.xml'
    ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
