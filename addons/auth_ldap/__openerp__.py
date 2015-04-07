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
        'views/res_company_views.xml',
        'views/res_company_ldap_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'external_dependencies' : {
        'python' : ['ldap'],
    }
}
