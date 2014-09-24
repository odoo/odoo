# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Customer Profiling',
    'version': '1.3',
    'category': 'Marketing',
    'description': """
This module allows users to perform segmentation within partners.
=================================================================

It uses the profiles criteria from the earlier segmentation module and improve it. 
Thanks to the new concept of questionnaire. You can now regroup questions into a 
questionnaire and directly use it on a partner.

It also has been merged with the earlier CRM & SRM segmentation tool because they 
were overlapping.

    **Note:** this module is not compatible with the module segmentation, since it's the same which has been renamed.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['base', 'crm'],
    'data': ['security/ir.model.access.csv', 'wizard/open_questionnaire_view.xml', 'crm_profiling_view.xml'],
    'demo': ['crm_profiling_demo.xml'],
    'test': [
        #'test/process/profiling.yml', #TODO:It's not debuging because problem to write data for open.questionnaire from partner section.
    ],
    'installable': True,
    'auto_install': False,
    'images': ['images/profiling_questionnaires.jpeg','images/profiling_questions.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
