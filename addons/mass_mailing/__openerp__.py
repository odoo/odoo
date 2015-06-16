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
    'author': 'OpenERP',
    'website': 'https://www.odoo.com/page/mailing',
    'category': 'Marketing',
    'depends': [
        'mail',
        'marketing',
        'web_kanban_gauge',
        'website_mail',
        'website_links',
        'utm',
    ],
    'data': [
        'data/mail_data.xml',
        'data/mass_mailing_data.xml',
        'wizard/mail_compose_message_view.xml',
        'wizard/test_mailing.xml',
        'views/mass_mailing_report.xml',
        'views/mass_mailing.xml',
        'views/res_config.xml',
        'views/email_template.xml',
        'views/website_mass_mailing.xml',
        'views/snippets.xml',
        'security/ir.model.access.csv',
        'views/mass_mailing.xml',
        'views/unsubscribe.xml',
    ],
    'qweb': [],
    'demo': [
        'data/mass_mailing_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
