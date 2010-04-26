# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'HR - Recruitement',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Manages job positions and the recruitement process. It's integrated with the
survey module to allows you to define interview for different jobs.

This module is integrated with the mail gateway to automatically tracks email
sent to jobs@YOURCOMPANY.com. It's also integrated with the document management
system to store and search in your CV base.
    """,
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['hr','survey','crm'],
    'init_xml': [
        'hr_recruitment_data.xml'
    ],
    'update_xml': [
        'wizard/hr_recruitment_phonecall_view.xml',
        'hr_recruitment_view.xml',
        'hr_recruitment_menu.xml',
#        'report_hr_recruitment_view.xml',
        'security/hr_recruitment_security.xml',
        'security/ir.model.access.csv',
        'board_hr_recruitment_statistical_view.xml',
        'report/hr_recruitment_report_view.xml',
        'wizard/hr_recruitment_create_partner_job_view.xml',
     ],
    'demo_xml': [
        'hr_recruitment_demo.xml'
    ],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
