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


class HrEmployee(models.Model):
    """Extends the 'hr.employee' model to include loan_count."""
    _inherit = "hr.employee"

    loan_count = fields.Integer(
        string="Loan Count",
        help="Number of loans associated with the employee",
        compute='_compute_loan_count')

    def _compute_loan_count(self):
        """Compute the number of loans associated with the employee."""
        for rec in self:
            rec.loan_count = rec.env['hr.loan'].search_count(
                [('employee_id', '=', rec.id)])

    def action_view_loans(self):
        """Open loans only for this employee."""
        self.ensure_one()
        return {
            'name': 'Loans',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': dict(self.env.context, default_employee_id=self.id),
        }
