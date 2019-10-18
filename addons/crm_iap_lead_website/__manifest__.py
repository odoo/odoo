# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Generation From Website Visits',
    'summary': 'Create Leads/Opportunities from your website\'s traffic',
    'category': 'Sales/CRM',
    'depends': ['iap', 'crm', 'website_form', 'crm_iap_lead'],
    'data': [
        'data/reveal_data.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
        'views/crm_reveal_views.xml',
        'views/res_config_settings_views.xml',
    ]
}
