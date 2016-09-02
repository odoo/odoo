# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'CRM',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 5,
    'summary': 'Leads, Opportunities, Activities',
    'description': """
The generic Odoo Customer Relationship Management
====================================================

This application enables a group of people to intelligently and efficiently manage leads, opportunities, meetings and activities.

It manages key tasks such as communication, identification, prioritization, assignment, resolution and notification.

Odoo ensures that all cases are successfully tracked by users, customers and vendors. It can automatically send reminders, trigger specific methods and many other actions based on your own enterprise rules.

The greatest thing about this system is that users don't need to do anything special. The CRM module has an email gateway for the synchronization interface between mails and Odoo. That way, users can just send emails to the request tracker.

Odoo will take care of thanking them for their message, automatically routing it to the appropriate staff and make sure all future correspondence gets to the right place.


Dashboard for CRM will include:
-------------------------------
* Planned Revenue by Stage and User (graph)
* Opportunities by Stage (graph)
""",
    'website': 'https://www.odoo.com/page/crm',
    'depends': [
        'base_action_rule',
        'base_setup',
        'sales_team',
        'mail',
        'calendar',
        'resource',
        'fetchmail',
        'utm',
        'web_planner',
        'web_tour',
    ],
    'data': [
        'data/crm_activity_data.xml',
        'data/crm_data.xml',
        'data/crm_stage_data.xml',
        'data/sales_config_settings_data.xml',
        'data/crm_lead_data.xml',
        'data/web_planner_data.xml',
        'data/mail_template_data.xml',

        'security/crm_security.xml',
        'security/ir.model.access.csv',

        'wizard/base_partner_merge_views.xml',
        'wizard/crm_activity_log_views.xml',
        'wizard/crm_lead_lost_views.xml',
        'wizard/crm_lead_to_opportunity_views.xml',
        'wizard/crm_merge_opportunities_views.xml',
        'wizard/base_partner_merge_views.xml',

        'report/crm_activity_report_views.xml',
        'report/crm_opportunity_report_views.xml',

        'views/crm_templates.xml',
        'views/crm_views.xml',
        'views/crm_activity_views.xml',
        'views/crm_stage_views.xml',
        'views/crm_lead_views.xml',
        'views/calendar_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_views.xml',
        'views/crm_team_views.xml',
    ],
    'demo': [
        'data/crm_demo.xml',
        'data/crm_lead_demo.xml',
        'data/crm_activity_demo.xml',
        'data/base_action_rule_demo.xml',
    ],
    'css': ['static/src/css/crm.css'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
