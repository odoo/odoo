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


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def action_compute_sheet(self):
        """Calculate and generate payroll slips for the selected employees.
        This method calculates and generates payroll slips for the employees
        associated with the current wizard instance. It sets the journal_id
        based on the active_id from the context, and then calls the parent
        class's compute_sheet method."""
        journal_id = False
        if self.env.context.get('active_id'):
            journal_id = self.env['hr.payslip.run'].browse(
                self.env.context.get('active_id')).journal_id.id
        return super(HrPayslipEmployees,
                     self.with_context(journal_id=journal_id)).action_compute_sheet()
