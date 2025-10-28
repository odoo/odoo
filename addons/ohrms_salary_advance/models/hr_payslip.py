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


class HrPayslip(models.Model):
    """Class for the inherited model hr_payslip. Supering get_inputs() method
        inorder to add details of advance salary in the payslip."""
    _inherit = 'hr.payslip'

    def get_inputs(self, contract_ids, date_from, date_to):
        """Supering get_inputs() method inorder to add details of advance
           salary in the payslip."""
        res = super(HrPayslip, self).get_inputs(contract_ids, date_from,
                                                date_to)
        employee_id = self.env['hr.version'].browse(
            contract_ids[0].id).employee_id if contract_ids \
            else self.employee_id
        advance_salary = self.env['salary.advance'].search(
            [('employee_id', '=', employee_id.id)])
        for record in advance_salary:
            current_date = date_from.month
            date = record.date
            existing_date = date.month
            if current_date == existing_date:
                state = record.state
                amount = record.advance
                for result in res:
                    if state == 'approve' and amount != 0 and result.get(
                            'code') == 'SAR':
                        result['amount'] = amount
        return res
