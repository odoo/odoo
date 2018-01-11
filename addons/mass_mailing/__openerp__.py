# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

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
        'email_template',
        'marketing',
        'web_kanban_gauge',
        'web_kanban_sparkline',
        'website_mail',
    ],
    'data': [
        'data/mail_data.xml',
        'data/mass_mailing_data.xml',
        'wizard/mail_compose_message_view.xml',
        'wizard/test_mailing.xml',
        'views/mass_mailing_report.xml',
        'views/mass_mailing.xml',
        'views/res_config.xml',
        'views/res_partner.xml',
        'views/email_template.xml',
        'views/website_mass_mailing.xml',
        'views/snippets.xml',
        'security/ir.model.access.csv',
        'views/mass_mailing.xml',
    ],
    'qweb': [],
    'demo': [
        'data/mass_mailing_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
