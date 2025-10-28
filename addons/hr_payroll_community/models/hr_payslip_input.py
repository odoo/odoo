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


class HrPayslipInput(models.Model):
    """Create new model for adding fields"""
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    name = fields.Char(string='Description', required=True, help='Name of the input')
    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip',
                                 required=True, help='Payslip related to the input',
                                 ondelete='cascade',  index=True)
    sequence = fields.Integer(required=True, index=True, default=10,
                              string="Sequence", help='Sequence to identify the record')
    code = fields.Char(required=True, string='Code',
                       help="The code that can be used in the salary rules")
    date_from = fields.Date(string='Date From',
                            help="Starting Date for Payslip Lines",
                            required=True,
                            default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To',
                          help="Ending Date for Payslip Lines", required=True,
                          default=str(
                              datetime.now() + relativedelta.relativedelta(
                                  months=+1, day=1, days=-1))[:10])
    amount = fields.Float(string="Amount",
                          help="It is used in computation." 
                               "For e.g. A rule for sales having "
                               "1% commission of basic salary for" 
                               "per product can defined in "
                               "expression like result = "
                               "inputs.SALEURO.amount * contract.wage*0.01.")
    contract_id = fields.Many2one('hr.version', string='Contract',
                                  required=True,
                                  help="The contract for which applied"
                                       " this input")
