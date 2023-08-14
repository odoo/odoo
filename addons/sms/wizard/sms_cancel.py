# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class SMSCancel(models.TransientModel):
    _name = 'sms.cancel'
    _description = 'Dismiss notification for resend by model'

    model = fields.Char(string='Model', required=True)
    help_message = fields.Char(string='Help message', compute='_compute_help_message')

    @api.depends('model')
    def _compute_help_message(self):
        for wizard in self:
            wizard.help_message = _("Are you sure you want to discard %s SMS delivery failures? You won't be able to re-send these SMS later!") % (wizard._context.get('unread_counter'))

    def action_cancel(self):
        # TDE CHECK: delete pending SMS
        author_id = self.env.user.partner_id.id
        for wizard in self:
            self._cr.execute("""
SELECT notif.id, msg.id
FROM mail_message_res_partner_needaction_rel notif
JOIN mail_message msg
    ON notif.mail_message_id = msg.id
WHERE notif.notification_type = 'sms' IS TRUE AND notif.notification_status IN ('bounce', 'exception')
    AND msg.model = %s
    AND msg.author_id = %s """, (wizard.model, author_id))
            res = self._cr.fetchall()
            notif_ids = [row[0] for row in res]
            message_ids = list(set([row[1] for row in res]))
            if notif_ids:
                self.env['mail.notification'].browse(notif_ids).sudo().write({'notification_status': 'canceled'})
            if message_ids:
                self.env['mail.message'].browse(message_ids)._notify_message_notification_update()
        return {'type': 'ir.actions.act_window_close'}
