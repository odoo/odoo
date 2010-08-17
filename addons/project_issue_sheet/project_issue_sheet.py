 #-*- coding: utf-8 -*-
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

from osv import fields,osv,orm
from tools.translate import _

class project_issue(osv.osv):
    _inherit = 'project.issue'
    _description = 'project issue'
    _columns = {
        'timesheet_ids': fields.one2many('hr.analytic.timesheet', 'issue_id', 'Timesheets'),
        'analytic_account_id': fields.related('project_id', 'analytic_account_id', type='many2one', relation='account.analytic.account',string='Analytic Account')
    }

project_issue()

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'
    _description = 'account analytic line'
    _columns = {
        'create_date' : fields.datetime('Create Date', readonly=True),
    }

account_analytic_line()

class hr_analytic_issue(osv.osv):

    _inherit = 'hr.analytic.timesheet'
    _description = 'hr analytic timesheet'
    _columns = {
        'issue_id' : fields.many2one('project.issue', 'Issue'),
    }

hr_analytic_issue()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
