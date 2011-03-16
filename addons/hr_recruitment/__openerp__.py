# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'HR - Recruitement',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Manages job positions and the recruitement process. It's integrated with the
survey module to allow you to define interview for different jobs.

This module is integrated with the mail gateway to automatically tracks email
sent to jobs@YOURCOMPANY.com. It's also integrated with the document management
system to store and search in your CV base.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['decimal_precision', 'hr', 'survey', 'crm'],
    'update_xml': [
        'wizard/hr_recruitment_phonecall_view.xml',
        'wizard/hr_recruitment_employee_hired.xml',
        'wizard/hr_recruitment_create_partner_job_view.xml',
        'hr_recruitment_view.xml',
        'hr_recruitment_menu.xml',
        'security/hr_recruitment_security.xml',
        'security/ir.model.access.csv',
        'report/hr_recruitment_report_view.xml',
        'board_hr_recruitment_statistical_view.xml',
     ],
    'init_xml': [
        'hr_recruitment_data.xml'
    ],
    'demo_xml': [
        'hr_recruitment_demo.xml',
    ],
    'test':['test/test_hr_recruitment.yml'],
    'installable': True,
    'active': False,
    'certificate' : '001073437025460275621',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
