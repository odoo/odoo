# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class MailResendCancel(models.TransientModel):
    _name = 'mail.resend.cancel'
    _description = 'Dismiss notification for resend by model'

    model = fields.Char(string='Model')
    help_message = fields.Char(string='Help message', compute='_compute_help_message')

    @api.depends('model')
    def _compute_help_message(self):
        for wizard in self:
            wizard.help_message = _("Are you sure you want to discard %s mail delivery failures. You won't be able to re-send these mails later!") % (wizard._context.get('unread_counter'))

    def cancel_resend_action(self):
        author_id = self.env.user.partner_id.id
        for wizard in self:
            self._cr.execute("""
                                SELECT notif.id, mes.id
                                FROM mail_message_res_partner_needaction_rel notif
                                JOIN mail_message mes
                                    ON notif.mail_message_id = mes.id
                                WHERE notif.notification_type = 'email' AND notif.notification_status IN ('bounce', 'exception')
                                    AND mes.model = %s
                                    AND mes.author_id = %s
                            """, (wizard.model, author_id))
            res = self._cr.fetchall()
            notif_ids = [row[0] for row in res]
            messages_ids = list(set([row[1] for row in res]))
            if notif_ids:
                self.env["mail.notification"].browse(notif_ids).sudo().write({'notification_status': 'canceled'})
                self.env["mail.message"].browse(messages_ids)._notify_message_notification_update()
        return {'type': 'ir.actions.act_window_close'}
