# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import babel
from datetime import datetime, time
from odoo import fields, models, tools


class HrPayslipAcc(models.Model):
    """" Calculate the date and make payslip done """
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        """Calculate the dates and mark loan lines as paid"""
        for line in self.input_line_ids:
            date_from = self.date_from
            tym = datetime.combine(fields.Date.from_string(date_from), time.min)
            locale = self.env.context.get('lang') or 'en_US'
            month = str(babel.dates.format_date(date=tym, format='MMMM-y', locale=locale))
            if line.loan_line_id:
                line.loan_line_id.action_paid_amount(month)
        return super(HrPayslipAcc, self).action_payslip_done()