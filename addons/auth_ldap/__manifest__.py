# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Authentication via LDAP',
    'depends' : ['base', 'base_setup'],
    #'description': < auto-loaded from README file
    'category' : 'Extra Tools',
    'data' : [
        'views/ldap_installer_views.xml',
        'security/ir.model.access.csv',
        'views/auth_ldap_config_settings_views.xml',
    ],
    'external_dependencies' : {
        'python' : ['ldap'],
    }
}
