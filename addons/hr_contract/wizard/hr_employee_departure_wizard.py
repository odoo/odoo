# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDepartureWizard(models.TransientModel):
    _inherit = 'hr.employee.departure.wizard'

    first_contract_date = fields.Date(related="employee_id.first_contract_date", string="Start Date")
    do_set_date_end = fields.Boolean(
        string="Set Contract End Date",
        default=lambda self: self.env.user.has_group('hr_contract.group_hr_contract_manager'),
        help="Limit contracts date to End of Contract and cancel future ones.")
