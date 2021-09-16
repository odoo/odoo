# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class HrHolidaysCancelLeave(models.TransientModel):
    _name = 'hr.holidays.cancel.leave'
    _description = 'Cancel Leave Wizard'

    leave_id = fields.Many2one('hr.leave', required=True)
    reason = fields.Text(required=True)

    def action_cancel_leave(self):
        self.ensure_one()

        if not self.leave_id.can_cancel:
            raise ValidationError(_('This time off cannot be canceled.'))

        self.leave_id.message_post(
            body=_('The time off has been canceled: %s', self.reason)
        )

        leave_sudo = self.leave_id.sudo()
        leave_sudo.with_context(from_cancel_wizard=True).active = False
        leave_sudo._remove_resource_leave()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Your time off has been canceled."),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
