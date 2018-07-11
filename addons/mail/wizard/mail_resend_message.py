# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from ast import literal_eval
from odoo.exceptions import UserError

class MailResendMessage(models.TransientModel):
    _name = 'mail.resend.message'
    _description = 'Email resend wizard'

    mail_message_id = fields.Many2one('mail.message', 'Message', readonly=True)
    partner_ids = fields.One2many('mail.resend.partner', 'resend_wizard_id', string='Recipients')
    notification_ids = fields.Many2many('mail.notification', string='Notifications', readonly=True)
    has_cancel = fields.Boolean(compute='_compute_has_cancel')
    partner_readonly = fields.Boolean(compute='_compute_partner_readonly')

    @api.depends("partner_ids")
    def _compute_has_cancel(self):
        self.has_cancel = self.partner_ids.filtered(lambda p: not p.resend)

    def _compute_partner_readonly(self):
        self.partner_readonly = not self.env['res.partner'].check_access_rights('write', raise_exception=False)

    @api.model
    def default_get(self, fields):
        rec = super(MailResendMessage, self).default_get(fields)
        message_id = self._context.get('mail_message_to_resend')
        if message_id:
            mail_message_id = self.env['mail.message'].browse(message_id)
            notification_ids = mail_message_id.notification_ids.filtered(lambda notif: notif.email_status in ('exception', 'bounce'))
            partner_readonly = not self.env['res.partner'].check_access_rights('write', raise_exception=False)
            partner_ids = [(0, 0,
                {
                    "partner_id": notif.res_partner_id.id,
                    "name": notif.res_partner_id.name,
                    "email": notif.res_partner_id.email,
                    "resend": True,
                    "message": notif.format_failure_reason(),
                }
                ) for notif in notification_ids]
            rec['partner_readonly'] = partner_readonly
            rec['notification_ids'] = [(6, 0, notification_ids.ids)]
            rec['mail_message_id'] = mail_message_id.id
            rec['partner_ids'] = partner_ids
        else:
            raise UserError('No message_id found in context')
        return rec

    @api.multi
    def resend_mail_action(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        for wizard in self:
            "If a partner disappeared from partner list, we cancel the notification"
            to_cancel = wizard.partner_ids.filtered(lambda p: not p.resend).mapped("partner_id")
            to_send = wizard.partner_ids.filtered(lambda p: p.resend).mapped("partner_id")
            notif_to_cancel = wizard.notification_ids.filtered(lambda notif: notif.res_partner_id in to_cancel and notif.email_status in ('exception', 'bounce'))
            notif_to_cancel.sudo().write({'email_status': 'canceled'})
            to_send.sudo()._notify(self.mail_message_id, force_send=True, send_after_commit=False)
            self.mail_message_id._notify_failure_update()
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def cancel_mail_action(self):
        for wizard in self:
            for notif in wizard.notification_ids:
                notif.filtered(lambda notif: notif.email_status in ('exception', 'bounce')).sudo().write({'email_status': 'canceled'})
            wizard.mail_message_id._notify_failure_update()
        return {'type': 'ir.actions.act_window_close'}


class PartnerResend(models.TransientModel):
    _name = 'mail.resend.partner'
    _description = 'Partner with additionnal information for mail resend'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    name = fields.Char(related="partner_id.name", related_sudo=False)
    email = fields.Char(related="partner_id.email", related_sudo=False)
    resend = fields.Boolean(string="Send Again", default=True)
    resend_wizard_id = fields.Many2one('mail.resend.message', string="Resend wizard")
    message = fields.Char(string="Help message")


class MailCancelResend(models.TransientModel):
    _name = 'mail.resend.cancel'
    _description = 'Dismiss notification for resend by model'

    model = fields.Char(string='Model')
    help_message = fields.Char(string='Help message', compute='_compute_help_message')

    @api.multi
    @api.depends('model')
    def _compute_help_message(self):
        for wizard in self:
            wizard.help_message = _("Are you sure you want to discard %s mail delivery failures. You won't be able to re-send these mails later!") % (wizard._context.get('unread_counter'))

    @api.multi
    def cancel_resend_action(self):
        author_id = self.env.user.partner_id.id
        for wizard in self:
            self._cr.execute("""
                                SELECT notif.id, mes.id
                                FROM mail_message_res_partner_needaction_rel notif
                                JOIN mail_message mes
                                    ON notif.mail_message_id = mes.id
                                WHERE notif.email_status IN ('bounce', 'exception')
                                    AND mes.model = %s
                                    AND mes.author_id = %s
                            """, (wizard.model, author_id))
            res = self._cr.fetchall()
            notif_ids = [row[0] for row in res]
            messages_ids = list(set([row[1] for row in res]))
            if notif_ids:
                self.env["mail.notification"].browse(notif_ids).sudo().write({'email_status': 'canceled'})
                self.env["mail.message"].browse(messages_ids)._notify_failure_update()
        return {'type': 'ir.actions.act_window_close'}
