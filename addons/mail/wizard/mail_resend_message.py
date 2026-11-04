# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class MailResendMessage(models.TransientModel):
    _name = 'mail.resend.message'
    _description = 'Email resend wizard'

    mail_message_id = fields.Many2one('mail.message', 'Message', readonly=True)
    partner_ids = fields.One2many('mail.resend.partner', 'resend_wizard_id', string='Recipients')
    notification_ids = fields.Many2many('mail.notification', string='Notifications', readonly=True)
    can_cancel = fields.Boolean(compute='_compute_can_cancel')
    can_resend = fields.Boolean(compute='_compute_can_resend')
    partner_readonly = fields.Boolean(compute='_compute_partner_readonly')

    @api.depends("partner_ids")
    def _compute_can_cancel(self):
        self.can_cancel = self.partner_ids.filtered(lambda p: not p.resend)

    @api.depends('partner_ids.resend')
    def _compute_can_resend(self):
        self.can_resend = any([partner.resend for partner in self.partner_ids])

    def _compute_partner_readonly(self):
        self.partner_readonly = not self.env['res.partner'].has_access('write')

    @api.model
    def default_get(self, fields):
        rec = super(MailResendMessage, self).default_get(fields)
        message_id = self._context.get('mail_message_to_resend')
        if message_id:
            mail_message_id = self.env['mail.message'].browse(message_id)
            notification_ids = mail_message_id.notification_ids.filtered(lambda notif: notif.notification_type == 'email' and notif.notification_status in ('exception', 'bounce'))
            partner_values = [({
                "notification_id": notif.id,
                "resend": True,
                "message": notif.format_failure_reason(),
            }) for notif in notification_ids]

            # mail.resend.partner need to exist to be able to execute an action
            partner_ids = self.env['mail.resend.partner'].create(partner_values).ids
            partner_commands = [Command.link(partner_id) for partner_id in partner_ids]

            has_user = any(notif.res_partner_id.user_ids for notif in notification_ids)
            if has_user:
                partner_readonly = not self.env['res.users'].has_access('write')
            else:
                partner_readonly = not self.env['res.partner'].has_access('write')
            rec['partner_readonly'] = partner_readonly
            rec['notification_ids'] = [Command.set(notification_ids.ids)]
            rec['mail_message_id'] = mail_message_id.id
            rec['partner_ids'] = partner_commands
        else:
            raise UserError(_('No message_id found in context'))
        return rec

    def resend_mail_action(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        for wizard in self:
            "If a partner disappeared from partner list, we cancel the notification"
            to_cancel = wizard.partner_ids.filtered(lambda p: not p.resend).mapped("partner_id")
            to_send = wizard.partner_ids.filtered(lambda p: p.resend)
            notif_to_cancel = wizard.notification_ids.filtered(lambda notif: notif.notification_type == 'email' and notif.res_partner_id in to_cancel and notif.notification_status in ('exception', 'bounce'))
            notif_to_cancel.sudo().write({'notification_status': 'canceled'})
            if to_send:
                # this will update the notification already
                to_send.action_resend()
            else:
                self.mail_message_id._notify_message_notification_update()
        return {'type': 'ir.actions.act_window_close'}

    def cancel_mail_action(self):
        for wizard in self:
            for notif in wizard.notification_ids:
                notif.filtered(lambda notif: notif.notification_type == 'email' and notif.notification_status in ('exception', 'bounce')).sudo().write({'notification_status': 'canceled'})
            wizard.mail_message_id._notify_message_notification_update()
        return {'type': 'ir.actions.act_window_close'}


class PartnerResend(models.TransientModel):
    _name = 'mail.resend.partner'
    _description = 'Partner with additional information for mail resend'

    notification_id = fields.Many2one('mail.notification', string='Notification', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', related='notification_id.res_partner_id')
    name = fields.Char(related='partner_id.name', string='Recipient Name', related_sudo=False, readonly=False)
    email = fields.Char(related='partner_id.email', string='Email Address', related_sudo=False, readonly=False)
    failure_reason = fields.Text('Failure Reason', related='notification_id.failure_reason')
    resend = fields.Boolean(string='Try Again', default=True)
    resend_wizard_id = fields.Many2one('mail.resend.message', string="Resend wizard")
    message = fields.Char(string='Error message')
    partner_readonly = fields.Boolean('Partner Readonly', related='resend_wizard_id.partner_readonly')

    def action_open_record(self):
        self.ensure_one()
        message = self.notification_id.mail_message_id
        return {
            'type': 'ir.actions.act_window',
            'res_model': message.model,
            'res_id': message.res_id,
            'view_ids': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_resend_partner(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('mail.mail_resend_partner_action')
        action['res_id'] = self.id
        return action

    def action_resend(self):
        message = self.resend_wizard_id.mail_message_id
        if len(message) != 1:
            raise UserError(_('All partners must belong to the same message'))

        recipients_data = self.env['mail.followers']._get_recipient_data(None, 'comment', False, pids=self.partner_id.ids)
        email_partners_data = [
            pdata
            for pid, pdata in recipients_data[0].items()
            if pid and pdata.get('notif', 'email') == 'email'
        ]

        record = self.env[message.model].browse(message.res_id) if message.is_thread_message() else self.env['mail.thread']
        record._notify_thread_by_email(
            message, email_partners_data,
            resend_existing=True,
            send_after_commit=False
        )

        message._notify_message_notification_update()

        if len(self) == 1:
            return self.action_open_record()
