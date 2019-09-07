# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
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
            notification_ids = mail_message_id.notification_ids.filtered(lambda notif: notif.notification_type == 'email' and notif.notification_status in ('exception', 'bounce'))
            partner_ids = [(0, 0, {
                "partner_id": notif.res_partner_id.id,
                "name": notif.res_partner_id.name,
                "email": notif.res_partner_id.email,
                "resend": True,
                "message": notif.format_failure_reason(),
            }) for notif in notification_ids]
            has_user = any([notif.res_partner_id.user_ids for notif in notification_ids])
            if has_user:
                partner_readonly = not self.env['res.users'].check_access_rights('write', raise_exception=False)
            else:
                partner_readonly = not self.env['res.partner'].check_access_rights('write', raise_exception=False)
            rec['partner_readonly'] = partner_readonly
            rec['notification_ids'] = [(6, 0, notification_ids.ids)]
            rec['mail_message_id'] = mail_message_id.id
            rec['partner_ids'] = partner_ids
        else:
            raise UserError(_('No message_id found in context'))
        return rec

    def resend_mail_action(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        for wizard in self:
            "If a partner disappeared from partner list, we cancel the notification"
            to_cancel = wizard.partner_ids.filtered(lambda p: not p.resend).mapped("partner_id")
            to_send = wizard.partner_ids.filtered(lambda p: p.resend).mapped("partner_id")
            notif_to_cancel = wizard.notification_ids.filtered(lambda notif: notif.notification_type == 'email' and notif.res_partner_id in to_cancel and notif.notification_status in ('exception', 'bounce'))
            notif_to_cancel.sudo().write({'notification_status': 'canceled'})
            if to_send:
                message = wizard.mail_message_id
                record = self.env[message.model].browse(message.res_id) if message.is_thread_message() else self.env['mail.thread']

                email_partners_data = []
                for pid, cid, active, pshare, ctype, notif, groups in self.env['mail.followers']._get_recipient_data(None, 'comment', False, pids=to_send.ids):
                    if pid and notif == 'email' or not notif:
                        pdata = {'id': pid, 'share': pshare, 'active': active, 'notif': 'email', 'groups': groups or []}
                        if not pshare and notif:  # has an user and is not shared, is therefore user
                            email_partners_data.append(dict(pdata, type='user'))
                        elif pshare and notif:  # has an user and is shared, is therefore portal
                            email_partners_data.append(dict(pdata, type='portal'))
                        else:  # has no user, is therefore customer
                            email_partners_data.append(dict(pdata, type='customer'))

                record._notify_record_by_email(message, {'partners': email_partners_data}, check_existing=True, send_after_commit=False)

            self.mail_message_id._notify_mail_failure_update()
        return {'type': 'ir.actions.act_window_close'}

    def cancel_mail_action(self):
        for wizard in self:
            for notif in wizard.notification_ids:
                notif.filtered(lambda notif: notif.notification_type == 'email' and notif.notification_status in ('exception', 'bounce')).sudo().write({'notification_status': 'canceled'})
            wizard.mail_message_id._notify_mail_failure_update()
        return {'type': 'ir.actions.act_window_close'}


class PartnerResend(models.TransientModel):
    _name = 'mail.resend.partner'
    _description = 'Partner with additionnal information for mail resend'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    name = fields.Char(related="partner_id.name", related_sudo=False, readonly=False)
    email = fields.Char(related="partner_id.email", related_sudo=False, readonly=False)
    resend = fields.Boolean(string="Send Again", default=True)
    resend_wizard_id = fields.Many2one('mail.resend.message', string="Resend wizard")
    message = fields.Char(string="Help message")
