# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'CRM',
    'version': '1.0',
    'category': 'Customer Relationship Management',
    'sequence': 2,
    'summary': 'Leads, Opportunities, Phone Calls',
    'description': """
The generic Odoo Customer Relationship Management
====================================================

This application enables a group of people to intelligently and efficiently manage leads, opportunities, meetings and phone calls.

It manages key tasks such as communication, identification, prioritization, assignment, resolution and notification.

Odoo ensures that all cases are successfully tracked by users, customers and suppliers. It can automatically send reminders, escalate the request, trigger specific methods and many other actions based on your own enterprise rules.

The greatest thing about this system is that users don't need to do anything special. The CRM module has an email gateway for the synchronization interface between mails and Odoo. That way, users can just send emails to the request tracker.

Odoo will take care of thanking them for their message, automatically routing it to the appropriate staff and make sure all future correspondence gets to the right place.


Dashboard for CRM will include:
-------------------------------
* Planned Revenue by Stage and User (graph)
* Opportunities by Stage (graph)
""",
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com/page/crm',
    'depends': [
        'base_action_rule',
        'base_setup',
        'sales_team',
        'mail',
        'calendar',
        'resource',
        'board',
        'fetchmail',
        'utm',
        'web_tip',
        'web_planner',
    ],
    'data': [
        'data/crm_data.xml',
        'data/crm_lead_data.xml',
        'data/crm_phonecall_data.xml',
        'data/crm_tip_data.xml',

        'security/crm_security.xml',
        'security/ir.model.access.csv',

        'wizard/crm_lead_to_opportunity_view.xml',

        'wizard/crm_phonecall_to_phonecall_view.xml',

        'wizard/crm_merge_opportunities_view.xml',

        'views/crm_view.xml',

        'views/crm_phonecall_view.xml',
        'views/crm_phonecall_menu.xml',

        'views/crm_lead_view.xml',
        'views/crm_lead_menu.xml',

        'views/calendar_event_menu.xml',

        'report/crm_lead_report_view.xml',
        'report/crm_opportunity_report_view.xml',
        'report/crm_phonecall_report_view.xml',

        'views/res_partner_view.xml',

        'views/res_config_view.xml',
        'wizard/base_partner_merge_view.xml',

        'views/sales_team_view.xml',
        'views/crm.xml',
        'data/web_planner_data.xml',
        'views/sales_team_dashboard.xml',
    ],
    'demo': [
        'data/crm_demo.xml',
        'data/crm_lead_demo.xml',
        'data/crm_phonecall_demo.xml',
        'data/crm_action_rule_demo.xml',
    ],
    'css': ['static/src/css/crm.css'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
