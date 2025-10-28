# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from datetime import datetime
from dateutil import relativedelta

from odoo import fields, models


class PayslipLinesContributionRegister(models.TransientModel):
    """Create new model Payslip Lines by Contribution Registers"""
    _name = 'payslip.lines.contribution.register'
    _description = 'Payslip Lines by Contribution Registers'

    date_from = fields.Date(string='Date From',
                            help="Starting Date for Payslip Lines",
                            required=True,
                            default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To',
                          help="Ending Date for Payslip Lines", required=True,
                          default=str(
                              datetime.now() + relativedelta.relativedelta(
                                  months=+1, day=1, days=-1))[:10])

    def action_print_report(self):
        """Function for Print Report"""
        active_ids = self.env.context.get('active_ids', [])
        datas = {
            'ids': active_ids,
            'model': 'hr.contribution.register',
            'form': self.read()[0]
        }
        return (self.env.ref(
            'hr_payroll_community.contribution_register_action')
                .report_action([], data=datas))
