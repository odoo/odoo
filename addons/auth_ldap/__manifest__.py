# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Authentication via LDAP',
    'depends': ['base', 'base_setup'],
    #'description': < auto-loaded from README file
    'category': 'Hidden/Tools',
    'data': [
        'views/ldap_installer_views.xml',
        'views/res_config_settings_views.xml',
        'security/ir.access.csv',
    ],
    'external_dependencies': {
        'python': ['python-ldap'],
        'apt': {
            'python-ldap': 'python3-ldap',
        },
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
