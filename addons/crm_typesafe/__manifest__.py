# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lead Qualification (TypeSafe)',
    'summary': 'Qualify leads with TypeSafe System One models (Jev)',
    'description': """
Ask TypeSafe's System One model (Jev) a few typed questions about each new
lead: which priority it deserves, how ready the contact is to buy and whether
the lead looks like spam. Answers come back as calibrated probabilities, so
the priority is only set when the model is confident enough.
""",
    'category': 'Sales/CRM',
    'depends': ['crm'],
    'data': [
        'data/ir_cron.xml',
        'data/ir_action.xml',
        'views/crm_lead_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
