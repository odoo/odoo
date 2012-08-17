# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
    'name': 'Timesheet on Issues',
    'version': '1.0',
    'category': 'Project Management',
    'description': """
This module adds the Timesheet support for the Issues/Bugs Management in Project.
=================================================================================

Worklogs can be maintained to signify number of hours spent by users to handle an issue.
                """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/project_issue_sheet_worklog.jpeg'],
    'depends': [
        'project_issue',
        'hr_timesheet_sheet',
    ],
    'data': [],
    'data': [
        'project_issue_sheet_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '00856032058128997037',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
