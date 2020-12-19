# -*- coding: utf-8 -*-
{
    'name' : 'Discuss Media Repository',
    'version': '1.0',
    'sequence': 1000,
    'summary': 'Chat with remote media files',
    'category': 'Productivity/Discuss',
    'complexity': 'easy',
    'website': 'https://www.odoo.com/glovebx/odoo/discuss',
    'description':
        """
Attachment Files Support
==========================

Allow to pick media files into chat window.

        """,
    'data': [
        "views/mail_media_repository_templates.xml",
    ],
    'demo': [
    ],
    'depends': ["mail"],
    'qweb': [
        'static/src/components/composer/composer.xml',
        'static/src/components/media_select_button/media_select_button.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
