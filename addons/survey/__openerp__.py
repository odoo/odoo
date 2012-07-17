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
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module is used for surveying.
==================================

It depends on the answers or reviews of some questions by different users.
A survey may have multiple pages. Each page may contain multiple questions and each question may have multiple answers.
Different users may give different answers of question and according to that survey is done.
Partners are also sent mails with user name and password for the invitation of the survey
    """,
    'author': 'OpenERP SA',
    'depends': ['base_tools', 'mail'],
    'update_xml': ['survey_report.xml',
                   'survey_data.xml',
                   'wizard/survey_selection.xml',
                   'wizard/survey_answer.xml',
                   'security/survey_security.xml',
                   'security/ir.model.access.csv',
                   'survey_view.xml',
                   'wizard/survey_print_statistics.xml',
                   'wizard/survey_print_answer.xml',
                   'wizard/survey_browse_answer.xml',
                   'wizard/survey_print.xml',
                   'wizard/survey_send_invitation.xml'],
    'demo_xml': ['survey_demo.xml'],
    'test': [
        'test/draft2open2close_survey.yml',
        'test/draft2open2close_request.yml',
        'test/survey_question_type.yml',
        'test/survey_report.yml',
    ],
    'css': ['static/src/css/survey.css'],
    'installable': True,
    'auto_install': False,
    'certificate' : '001131639736864143245',
    'images': ['images/survey_answers.jpeg','images/survey_pages.jpeg','images/surveys.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
