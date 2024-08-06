# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Generation',
    'summary': 'Generate Leads/Opportunities based on country, industries, size, etc.',
    'version': '1.1',
    'category': 'Sales/CRM',
    'version': '1.1',
    'depends': [
        'iap_crm',
        'iap_mail',
    ],
    'data': [
        'data/crm.iap.lead.industry.csv',
        'data/crm.iap.lead.role.csv',
        'data/crm.iap.lead.seniority.csv',
        'data/crm_iap_lead_data.xml',
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/crm_lead_view.xml',
        'views/crm_iap_lead_views.xml',
        'views/res_config_settings_views.xml',
        'views/mail_templates.xml',
    ],
    'qweb': [
        'static/src/xml/leads_tree_generate_leads_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
