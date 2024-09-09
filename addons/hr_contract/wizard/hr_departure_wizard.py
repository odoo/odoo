# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    set_date_end = fields.Boolean(string="Set Contract End Date", default=lambda self: self.env.user.has_group('hr_contract.group_hr_contract_manager'),
        help="Set the end date on the current contract.")

    def action_register_departure(self):
        """If set_date_end is checked, set the departure date as the end date to current running contract,
        and cancel all draft contracts"""
        active_contracts = self.employee_ids.contract_id

        if any(c.date_start > self.departure_date for c in active_contracts):
            raise UserError(_("Departure date can't be earlier than the start date of current contract."))

        super().action_register_departure()

        if self.set_date_end:
            # Write date and update state of current contracts
            current_contracts = active_contracts.filtered(lambda c: c.state in ['open', 'draft'])
            current_contracts.write({'date_end': self.departure_date})
            current_contracts.filtered(lambda c: c.state == 'open').write({'state': 'close'})

            # Cancel draft contracts
            self.employee_ids.contract_ids.filtered(lambda c: c.state == 'draft').write({'state': 'cancel'})
