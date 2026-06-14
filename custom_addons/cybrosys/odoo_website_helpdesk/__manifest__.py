# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Arshad Ali Pottengal (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
{
    'name': "Website Helpdesk Management",
    'version': '19.0.1.0.0',
    'category': 'Website',
    'summary': """The website allows for the creation of tickets, which can 
    then be controlled from the backend.""",
    'description': """Website Helpdesk, Odoo Helpdesk, Helpdesk, Helpdesk Management, Helpdesk Ticket, Odoo18 Helpdesk, Website Ticket, Support Ticket, Odoo18""",
    'author': "Cybrosys Techno Solutions",
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': "https://www.cybrosys.com",
    'depends': ['website', 'project', 'sale_project', 'hr_timesheet',
                'mail', 'contacts'],
    'data': [
        'data/helpdesk_category_data.xml',
        'security/odoo_website_helpdesk_groups.xml',
        'security/odoo_website_helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/helpdesk_replay_template_data.xml',
        'data/helpdesk_type_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'data/ticket_stage_data.xml',
        'views/helpdesk_category_views.xml',
        'views/helpdesk_tag_views.xml',
        'views/helpdesk_type_views.xml',
        'views/merge_ticket_views.xml',
        'views/odoo_website_helpdesk_portal_templates.xml',
        'views/portal_templates.xml',
        'views/rating_form.xml',
        'report/helpdesk_ticket_report_template.xml',
        'views/res_config_settings_views.xml',
        'views/team_helpdesk_views.xml',
        'views/ticket_helpdesk_views.xml',
        'views/ticket_stage_views.xml',
        'views/website_form.xml',
        'views/helpdesk_menu_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            '/odoo_website_helpdesk/static/src/js/ticket_details.js',
            '/odoo_website_helpdesk/static/src/js/portal_search.js',
            '/odoo_website_helpdesk/static/src/js/multiple_product_choose.js',
        ]
    },
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
