# -*- coding: utf-8 -*-

{
    'name': 'Mass Mailing with CRM',
    'version': '1.0',
    'depends': ['mass_mailing', 'crm'],
    'author': 'OpenERP SA',
    'category': 'Hidden/Dependency',
    'description': """
Bridge module between Mass Mailing and CRM
    """,
    'website': 'http://www.openerp.com',
    'data': [
        'views/crm_lead.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
}
