# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Authentication via LDAP',
    'version' : '1.0',
    'depends' : ['base'],
    #'description': < auto-loaded from README file
    'category' : 'Extra Tools',
    'data' : [
        'users_ldap_view.xml',
        'user_ldap_installer.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': False,
    'installable': True,
    'external_dependencies' : {
        'python' : ['ldap'],
    }
}
