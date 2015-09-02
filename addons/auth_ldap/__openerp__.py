# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Authentication via LDAP',
    'depends' : ['base'],
    #'description': < auto-loaded from README file
    'category' : 'Extra Tools',
    'data' : [
        'views/res_company_views.xml',
        'views/ldap_installer_views.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': False,
    'external_dependencies' : {
        'python' : ['ldap'],
    }
}
