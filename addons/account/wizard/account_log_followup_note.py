# -*- coding: utf-8 -*-
from openerp import models, fields, api, _


class AccountLogFollowupNote(models.TransientModel):

    """Logs a note"""

    _name = "account.log.followup.note"
    _description = "Log A Followup Note"

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, default=lambda s: dict(s._context or {}).get('active_id', False))
    note = fields.Text(required=True)

    @api.multi
    def log_note(self):
        self.partner_id.write({'payment_next_action': self.note})
        self.partner_id.message_post(body=self.note, subtype='account.followup_logged_action')
        return True
