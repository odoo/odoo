# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "SMS Marketing in Marketing Automation",
    'version': "1.0",
    'summary': "Integrate SMS Marketing in marketing campaigns",
    'category': "Marketing/Marketing Automation",
    'depends': [
        'marketing_automation',
        'mass_mailing_sms'
    ],
    'data': [
        'views/mailing_mailing_views.xml',
        'views/mailing_trace_views.xml',
        'views/marketing_activity_views.xml',
        'views/marketing_campaign_views.xml',
        'views/marketing_participant_views.xml',
        'security/ir.model.access.csv',
        'security/sms_security.xml',
    ],
    'uninstall_hook': '_uninstall_hook',
    'auto_install': True,
    'license': 'OEEL-1',
}
