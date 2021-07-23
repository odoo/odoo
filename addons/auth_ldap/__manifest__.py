# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Authentication via LDAP',
    'depends': ['base', 'base_setup'],
    #'description': < auto-loaded from README file
    'category': 'Tools',
    'data': [
        'views/ldap_installer_views.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
<<<<<<< HEAD
    'external_dependencies': {
        'python': ['ldap'],
    }
=======
    'external_dependencies' : {
        'python' : ['ldap'],
    },
    'license': 'LGPL-3',
>>>>>>> 2daf1153937... temp
}
