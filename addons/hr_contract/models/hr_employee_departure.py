# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrEmployeeDeparture(models.Model):
    _inherit = ['hr.employee.departure']

    first_contract_date = fields.Date(related="employee_id.first_contract_date", string="Start Date")
    do_set_date_end = fields.Boolean(
        string="Set Contract End Date",
        default=lambda self: self.env.user.has_group('hr_contract.group_hr_contract_manager'),
        help="Limit contracts date to End of Contract and cancel future ones.")

    def action_register_departure(self):
        """If do_set_date_end is checked, set the departure date as the end date to current running contract,
        and cancel all draft contracts"""
        active_contract = self.employee_id.contract_id

        if any(c.date_start > self.departure_date for c in active_contract):
            raise UserError(_("Departure date can't be earlier than the start date of current contract."))

        super().action_register_departure()

        if self.do_set_date_end:
            # Write date and update state of current contracts
            if active_contract.state in ['open', 'draft']:
                active_contract.write({'date_end': self.departure_date})
                self.employee_id.message_post(body=self.env._("Contract end date of %s has been set", self.employee_id.name))
                active_contract.filtered(lambda c: c.state == 'open').write({'state': 'close'})
                active_contract.message_post(body=self.env._('Contract end date has been updated due to the end of the collaboration with %s', self.employee_id.name))

            # Cancel draft contracts
            self.employee_id.contract_ids.filtered(lambda c: c.state == 'draft').write({'state': 'cancel'})
