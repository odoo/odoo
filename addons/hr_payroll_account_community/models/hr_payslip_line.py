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
from odoo import models


class HrPayslipLine(models.Model):
    """Extends the standard 'hr.payslip.line' model to provide additional
    functionality for accounting.
    Methods:
        - _get_partner_id: Get partner_id of the slip line to use in
        account_move_line."""
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self, credit_account):
        """Get partner_id of slip line to use in account_move_line."""
        # use partner of salary rule or fallback on employee's address
        register_partner_id = self.salary_rule_id.register_id.partner_id
        if credit_account:
            if (register_partner_id or
                    self.salary_rule_id.account_credit_id.account_type in (
                    'asset_receivable', 'liability_payable')):
                return register_partner_id.id
        else:
            if (register_partner_id or
                    self.salary_rule_id.account_debit_id.account_type in (
                    'asset_receivable', 'liability_payable')):
                return register_partner_id.id
        return False
