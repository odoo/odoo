# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'CRM',
    'version': '1.0',
    'category': 'Sales',
    'sequence': 5,
    'summary': 'Leads, Opportunities, Activities',
    'description': """
The generic OpenERP Customer Relationship Management
====================================================

This application enables a group of people to intelligently and efficiently manage leads, opportunities, meetings and activities.

It manages key tasks such as communication, identification, prioritization, assignment, resolution and notification.

OpenERP ensures that all cases are successfully tracked by users, customers and vendors. It can automatically send reminders, trigger specific methods and many other actions based on your own enterprise rules.

The greatest thing about this system is that users don't need to do anything special. The CRM module has an email gateway for the synchronization interface between mails and OpenERP. That way, users can just send emails to the request tracker.

OpenERP will take care of thanking them for their message, automatically routing it to the appropriate staff and make sure all future correspondence gets to the right place.


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
        'web_tip',
        'web_planner',
    ],
    'data': [
        'data/crm_action_data.xml',
        'crm_data.xml',
        'data/crm_stage_data.xml',
        'data/sales_config_settings_data.xml',
        'crm_lead_data.xml',
        'crm_tip_data.xml',

        'security/crm_security.xml',
        'security/ir.model.access.csv',

        'wizard/crm_lead_lost_view.xml',
        'wizard/crm_lead_to_opportunity_view.xml',
        'wizard/crm_merge_opportunities_view.xml',

        'crm_view.xml',
        'crm_stage_views.xml',
        'crm_lead_view.xml',
        'crm_lead_menu.xml',
        'views/crm_action_views.xml',

        'calendar_event_menu.xml',

        'report/crm_activity_report_view.xml',
        'report/crm_opportunity_report_view.xml',

        'res_partner_view.xml',

        'res_config_view.xml',
        'base_partner_merge_view.xml',

        'sales_team_view.xml',
        'views/crm.xml',
        'web_planner_data.xml',
        'sales_team_dashboard.xml',
    ],
    'demo': [
        'data/crm_stage_demo.xml',
        'crm_demo.xml',
        'crm_lead_demo.xml',
        'data/crm_action_demo.xml',
        'crm_action_rule_demo.xml',
    ],
    'test': [
        'test/crm_access_group_users.yml',
        'test/crm_lead_message.yml',
        'test/lead2opportunity2win.yml',
        'test/lead2opportunity_assign_salesmen.yml',
        'test/crm_lead_merge.yml',
        'test/crm_lead_cancel.yml',
        'test/crm_lead_onchange.yml',
        'test/crm_lead_copy.yml',
        'test/crm_lead_unlink.yml',
        'test/crm_lead_find_stage.yml',
    ],
    'css': ['static/src/css/crm.css'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
