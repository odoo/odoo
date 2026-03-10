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
from odoo import fields, models


class HrSalaryRule(models.Model):
    """Extends the standard 'hr.salary.rule' model to include additional
    fields for defining salary rules."""
    _inherit = 'hr.salary.rule'

    analytic_account_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          help="Analytic account associated "
                                               "with the record")
    account_tax_id = fields.Many2one('account.tax', string='Tax',
                                     help="Tax account associated with the "
                                          "record")
    account_debit_id = fields.Many2one('account.account',
                                       string='Debit Account',
                                       help="Debit account associated with the"
                                            " record")
    account_credit_id = fields.Many2one('account.account',
                                        string='Credit Account',
                                        help="Credit account associated with"
                                             " the record")
