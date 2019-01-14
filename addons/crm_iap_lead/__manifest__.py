# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Generation',
    'summary': 'Create Leads/Opportunities based on country, technologies, size, etc.',
    'category': 'CRM',
    'depends': ['iap', 'crm'],
    'data': [
        'data/crm.iap.lead.industry.csv',
        'data/crm.iap.lead.role.csv',
        'data/crm.iap.lead.seniority.csv',
        'data/message_template.xml',
        'data/crm_iap_lead_data.xml',
        'security/ir.model.access.csv',
    ],
}
