#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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

import time
from datetime import date
from datetime import datetime
from datetime import timedelta

import netsvc
from osv import fields, osv
import tools
from tools.translate import _
import decimal_precision as dp



class hr_contract_be(osv.osv):

    _inherit = 'hr.contract'
    _description = 'Add for belgium users'
    _columns = {

    'reim_travel':fields.float('Reimbursement of travel expenses', digits=(16,2)),
    'company_car_emp':fields.float('Company car employer', digits=(16,2)),
    'company_car_wkr':fields.float('Company Car Deduction for Worker', digits=(16,2)),
    'mis_ex_onss':fields.float('Miscellaneous exempt ONSS ', digits=(16,2)),
    'ch_value':fields.float('Check Value Meal ', digits=(16,2)),
    'ch_worker':fields.float('Check Value Meal - by worker ', digits=(16,2)),
    'insurance':fields.float('Insurance Group - by worker ', digits=(16,2)),
    'advantage':fields.float('Benefits of various nature ', digits=(16,2)),
    'suppl_net':fields.float('Net supplements', digits=(16,2)),
    'retained_net':fields.float('Net retained ', digits=(16,2)),
#    'vol_tax':fields.float('Voluntary tax ', digits=(16,2)),
#    'horaire_effectif': fields.many2one('resource.calendar','Actual Work', help="Hours of work means the actual working time elapsing between the beginning and end of the workday, regardless of where it runs, excluding the stop work devoted to meals, breaks and, more generally, any interruptions between 2 sequences of work that are not actually worked since the employee can go freely about his personal affairs"),

    }
hr_contract_be()

class hr_employee_be(osv.osv):

    _inherit = 'hr.employee'
    _description = 'add for all Belgian users'
    _columns = {
    'statut_fiscal':fields.selection([('without income','Without Income'),('with income','With Income')], 'Tax status for spouse'),
    'handicap':fields.boolean('Disabled Spouse', help="if recipient spouse is declared disabled by law"),
        'handicap_child':fields.boolean('Disabled Children', help="if recipient children is/are declared disabled by law"),
    'resident':fields.boolean('Nonresident', help="if recipient lives in a foreign country"),
    'number_handicap':fields.integer('Number of disabled children'),
    }
hr_employee_be()
