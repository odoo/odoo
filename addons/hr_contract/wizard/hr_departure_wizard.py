# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    set_date_end = fields.Boolean(string="Set Contract End Date", default=True)

    def action_register_departure(self):
        """If set_date_end is checked, set the departure date as the end date to current running contract,
        and cancel all draft contracts"""
        current_contract = self.employee_id.contract_id
        if current_contract and current_contract.date_start > self.departure_date:
            raise UserError(_("Departure date can't be earlier than the start date of current contract."))

        super(HrDepartureWizard, self).action_register_departure()
        if self.set_date_end:
            self.employee_id.contract_ids.filtered(lambda c: c.state == 'draft').write({'state': 'cancel'})
            if current_contract:
                self.employee_id.contract_id.write({'date_end': self.departure_date})
