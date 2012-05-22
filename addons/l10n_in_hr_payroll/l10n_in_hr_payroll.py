#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP SA (<http://openerp.com>). All Rights Reserved
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

from osv import fields, osv
import decimal_precision as dp

import time
from datetime import datetime
from datetime import timedelta
from datetime import date
from calendar import isleap
from dateutil.relativedelta import relativedelta

class hr_contract_in(osv.osv):
    _inherit = 'hr.contract'
    
    def _compute_year(self, cr, uid, ids, fields, args, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: No. of years of experience.
        @param context: A standard dictionary for contextual values
        """
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            c_date = time.strftime('%Y-%m-%d')
            DATETIME_FORMAT = "%Y-%m-%d"
            date_start = datetime.strptime(contract.date_start, DATETIME_FORMAT)
            current_date = datetime.strptime(c_date,DATETIME_FORMAT)
            diffyears = current_date.year - date_start.year
            difference  = current_date - date_start.replace(current_date.year)
            days_in_year = isleap(current_date.year) and 366 or 365
            difference_in_years = diffyears + (difference.days + difference.seconds/86400.0)/days_in_year
            years = relativedelta(current_date, date_start).years
            months = relativedelta(current_date, date_start).months
            mnth = months * 0.01
            if months < 10:
                year_month= float(mnth) + float(years)
                res[contract.id] = year_month
            else:
                year_months = float(mnth) + float(years)
                res[contract.id] = year_months
        return res

    _columns = {
        'tds': fields.float('TDS', digits_compute=dp.get_precision('Payroll')),
        'house_rent_income': fields.float('House Rent Income ', digits_compute=dp.get_precision('Payroll')),
        'saving_bank_account': fields.float('Saving Bank Account Income ', digits_compute=dp.get_precision('Payroll')),
        'other_income': fields.float('Other Income ', digits_compute=dp.get_precision('Payroll')),
        'short_term_gain':fields.float('Short Term Gain from Share Trading/Equity MFs ', digits_compute=dp.get_precision('Payroll')),
        'long_term_gain':fields.float('Long Term Gain from Share Trading/Equity MFs', digits_compute=dp.get_precision('Payroll')),
        'food_coupon_amount': fields.float('Food Coupons ', digits_compute=dp.get_precision('Payroll')),
        'driver_salay': fields.boolean('Driver salary '),
        'professional_tax': fields.float('Professional Tax ', digits_compute=dp.get_precision('Payroll')),
        'leave_avail_dedution': fields.float('leave Avail deduction ', digits_compute=dp.get_precision('Payroll')),
        'No_of_year':fields.function(_compute_year, string='No. of Years of service',type="float",readonly=True),
        'medical_insurance': fields.float('Medical Insurance', digits_compute=dp.get_precision('Payroll')), 
        'voluntarily_provident_fund': fields.float('Voluntarily Provident Fund', digits_compute=dp.get_precision('Payroll'),help="it is computed as percentage.(%)"), 
        'company_transport': fields.float('Company provided transport', digits_compute=dp.get_precision('Payroll')), 
    }

hr_contract_in()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: