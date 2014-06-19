# -*- coding: utf-8 -*-
{
    'name': 'IM Screensharing',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Record your screen, or share it with people thanks to the Instant Messaging',
    'author': 'OpenERP SA',
    'description': """ """,
    'website': 'https://www.openerp.com/',
    'depends': ['base', 'im_chat'],
    'data': [
        'security/ir.model.access.csv',
        'views/im_screenshare_view.xml',
        'views/im_screenshare.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'images': [],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: