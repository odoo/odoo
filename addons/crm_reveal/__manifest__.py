# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Generation',
    'summary': 'Create Leads/Opportunities from your website\'s traffic',
    'category': 'CRM',
    'depends': ['iap', 'crm', 'website_form'],
    'data': [
        'data/crm.reveal.industry.csv',
        'data/crm.reveal.role.csv',
        'data/crm.reveal.seniority.csv',
        'data/message_template.xml',
        'data/reveal_data.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
        'views/crm_reveal_views.xml',
        'views/res_config_settings_views.xml',
    ]
}
