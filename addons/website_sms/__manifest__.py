# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Send SMS to Visitor',
    'category': 'Website/Website',
    'sequence': 54,
    'summary': 'Allows to send sms to website visitor',
    'version': '1.0',
    'description': """Allows to send sms to website visitor if the visitor is linked to a partner.""",
    'depends': ['website', 'sms'],
    'data': [
        'views/website_visitor_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
