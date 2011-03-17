# -*- coding: utf-8 -*-
{
    'name': 'Enhanced support for (Ether)Pad attachments',
    'version': '1.0.3',
    'category': 'Tools',
    'description': """
Adds enhanced support for (Ether)Pad attachments in the web client, lets the
company customize which Pad installation should be used to link to new pads
(by default, pad.openerp.com)
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'data': [
        'company_pad.xml'
    ],
    'installable': True,
    'active': False,
    'web': True,
    'certificate' : '001183545978470526509',
}
