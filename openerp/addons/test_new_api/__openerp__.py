# -*- coding: utf-8 -*-
{
    'name': 'Test New API',
    'version': '1.0',
    'category': 'Tests',
    'description': """A module to test the new API.""",
    'author': 'OpenERP SA',
    'maintainer': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'installable': True,
    'auto_install': False,
    'data': [
        'ir.model.access.csv',
        'views.xml',
        'demo_data.xml',
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
