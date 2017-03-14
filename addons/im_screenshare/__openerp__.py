# -*- coding: utf-8 -*-
{
    'name': 'IM Screensharing',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Record or share your screen',
    'author': 'OpenERP SA',
    'description': """
IM Screensharing allow you to record your screen, or share it with others.
===========================================================================

* Recording : click on 'record', do stuffs and your web browser will be recorded. Then, you can replay it !

* Sharing : you are chatting with people thanks to Instant Messaging, then you can click on 'share my screen', and your
interlocutors will be able to see your screen, without installing anything !
    """,
    'website': 'https://www.odoo.com/',
    'depends': ['base', 'mail', 'im_chat'],
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