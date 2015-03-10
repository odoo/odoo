# -*- coding: utf-8 -*-

{
    'name' : 'Authentication via LDAP',
    'version' : '1.0',
    'depends' : ['base'],
    'author' : 'Odoo S.A.',
    #'description': < auto-loaded from README file
    'website' : 'https://www.odoo.com',
    'category' : 'Authentication',
    'data' : [
        'views/users_ldap_view.xml',
        'views/user_ldap_installer.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'external_dependencies' : {
        'python' : ['ldap'],
    }
}
