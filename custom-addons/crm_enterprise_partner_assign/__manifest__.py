# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Enterprise Resellers',
    'version': '1.0',
    'summary': 'Enterprise counterpart for Resellers',
    'description': 'Enterprise counterpart for Resellers',
    'category': 'Website/Website',
    'depends': [
        'crm_enterprise',
        'website_crm_partner_assign',
    ],
    'data': [
        'views/crm_lead_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
