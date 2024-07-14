# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Slides Forum Helpdesk',
    'category': 'Services/Helpdesk',
    'depends': [
        'website_helpdesk',
        'website_slides_forum',
    ],
    'data': [
        'views/helpdesk_templates.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
