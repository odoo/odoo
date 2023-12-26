# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Generation From Website Visits',
    'summary': 'Generate Leads/Opportunities from your website\'s traffic',
    'version': '1.1',
    'category': 'Sales/CRM',
    'depends': [
        'iap_crm',
        'iap_mail',
        'crm_iap_lead',
        'website_form'
    ],
    'data': [
        'data/reveal_data.xml',
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
        'views/crm_reveal_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}
