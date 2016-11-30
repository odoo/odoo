# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass Mailing Campaigns',
    'summary': 'Design, send and track emails',
    'description': """
Easily send mass mailing to your leads, opportunities or customers. Track
marketing campaigns performance to improve conversion rates. Design
professional emails and reuse templates in a few clicks.
    """,
    'version': '2.0',
    'sequence': 110,
    'website': 'https://www.odoo.com/page/mailing',
    'category': 'Marketing',
    'depends': [
        'mail',
        'utm',
        'link_tracker',
        'web_editor',
        'web_kanban_gauge',
    ],
    'data': [
        'security/mass_mailing_security.xml',
        'data/mass_mailing_data.xml',
        'wizard/mail_compose_message_views.xml',
        'wizard/test_mailing_views.xml',
        'views/mass_mailing_report_views.xml',
        'views/mass_mailing_stats_views.xml',
        'views/link_tracker_views.xml',
        'views/mass_mailing_template.xml',
        'views/mass_mailing_views.xml',
        'views/res_config_views.xml',
        'security/ir.model.access.csv',
        'views/editor_field_html.xml',
        'views/themes_templates.xml',
        'views/snippets_themes.xml',
        'views/snippets_themes_options.xml',
    ],
    'demo': [
        'data/mass_mailing_demo.xml',
    ],
    'application': True,
}
