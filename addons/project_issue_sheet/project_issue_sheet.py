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

import base64
import os
import re
import time
import mx.DateTime
from datetime import datetime, timedelta

import tools
from crm import crm
from osv import fields,osv,orm
from osv.orm import except_orm
from tools.translate import _

class project_issue(osv.osv):
    _inherit = 'project.issue'

    _columns = {
        'timesheet_ids' : fields.one2many('hr.analytic.timesheet', 'issue_id', 'Timesheets'),
        'analytic_account_id' : fields.many2one('account.analytic.account', 'Analytic Account',
                                                domain="[('partner_id', '=', partner_id)]",
                                                required=True),
    }

class account_analytic_line(osv.osv):
    _inherit = 'account.analytic.line'

    _columns = {
        'create_date' : fields.datetime('Create Date', readonly=True),
    }

account_analytic_line()

class hr_analytic_issue(osv.osv):
    _inherit = 'hr.analytic.timesheet'

    _columns = {
        'issue_id' : fields.many2one('project.issue', 'Issue'),
    }

hr_analytic_issue()

