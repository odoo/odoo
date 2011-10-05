# -*- coding: utf-8 -*-
{
    'name': 'Collaborative Note Pad',
    'version': '1.0.3',
    'category': 'Hidden',
    'complexity': "easy",
    'description': """
Adds enhanced support for (Ether)Pad attachments in the web client.
===================================================================

Lets the company customize which Pad installation should be used to link to new pads
(by default, http://ietherpad.com/).
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
    'images': ['images/pad_link_companies.jpeg'],
}
