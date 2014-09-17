# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Survey',
    'version': '2.0',
    'category': 'Marketing',
    'description': """
Create beautiful web surveys and visualize answers
==================================================

It depends on the answers or reviews of some questions by different users. A
survey may have multiple pages. Each page may contain multiple questions and
each question may have multiple answers. Different users may give different
answers of question and according to that survey is done. Partners are also
sent mails with personal token for the invitation of the survey.
    """,
    'summary': 'Create surveys, collect answers and print statistics',
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/survey',
    'depends': ['email_template', 'mail', 'website', 'marketing'],
    'data': [
        'security/survey_security.xml',
        'security/ir.model.access.csv',
        'views/survey_views.xml',
        'views/survey_templates.xml',
        'views/survey_result.xml',
        'wizard/survey_email_compose_message.xml',
        'data/survey_stages.xml',
        'data/survey_cron.xml'
    ],
    'demo': ['data/survey_demo_user.xml',
             'data/survey_demo_feedback.xml',
             'data/survey.user_input.csv',
             'data/survey.user_input_line.csv'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
    'images': [],
}
