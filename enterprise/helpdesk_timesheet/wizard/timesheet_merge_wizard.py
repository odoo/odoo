# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import ValidationError


class MergeTimesheets(models.TransientModel):
    _inherit = 'hr_timesheet.merge.wizard'

    @api.constrains('timesheet_ids')
    def _check_timesheet_ids_helpdesk_ticket_id(self):
        for wizard in self:
            if any(t.helpdesk_ticket_id != wizard.timesheet_ids.helpdesk_ticket_id for t in wizard.timesheet_ids):
                raise ValidationError(self.env._("All timesheets must be linked to the same helpdesk ticket."))

    def _prepare_merged_timesheet_values(self):
        res = super()._prepare_merged_timesheet_values()
        if ticket := self.timesheet_ids.helpdesk_ticket_id:
            res['helpdesk_ticket_id'] = ticket.id
        return res
