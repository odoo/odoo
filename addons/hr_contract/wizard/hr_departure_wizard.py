# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def _get_employee_departure_date(self):
        employee = self.env['hr.employee'].browse(self.env.context['active_id'])
        if employee.contract_id.state == "open":
            return False
        expired_contract = self.env['hr.contract'].search([('employee_id', '=', employee.id), ('state', '=', 'close')], limit=1, order='date_end desc')
        if expired_contract:
            return expired_contract.date_end
        return super()._get_employee_departure_date()

    set_date_end = fields.Boolean(string="Set Contract End Date", default=lambda self: self.env.user.user_has_groups('hr_contract.group_hr_contract_manager'),
        help="Set the end date on the current contract.")

    def action_register_departure(self):
        """If set_date_end is checked, set the departure date as the end date to current running contract,
        and cancel all draft contracts"""
        current_contract = self.sudo().employee_id.contract_id
        if current_contract and current_contract.date_start > self.departure_date:
            raise UserError(_("Departure date can't be earlier than the start date of current contract."))

        super(HrDepartureWizard, self).action_register_departure()
        if self.set_date_end:
            self.sudo().employee_id.contract_ids.filtered(lambda c: c.state == 'draft').write({'state': 'cancel'})
            if current_contract and current_contract.state in ['open', 'draft']:
                self.sudo().employee_id.contract_id.write({'date_end': self.departure_date})
            if current_contract.state == 'open':
                current_contract.state = 'close'
