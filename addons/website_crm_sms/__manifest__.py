# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Send SMS to Visitor with leads',
    'category': 'Website/Website',
    'sequence': 54,
    'summary': 'Allows to send sms to website visitor that have lead',
    'version': '1.0',
    'description': """Allows to send sms to website visitor if the visitor is linked to a lead.""",
    'depends': ['website_sms', 'crm'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
