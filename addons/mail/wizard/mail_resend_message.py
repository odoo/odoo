# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import AccessError, UserError
from odoo.tools.mail import email_normalize


class MailResendMessage(models.TransientModel):
    _name = 'mail.resend.message'
    _description = 'Email resend wizard'

    mail_message_id = fields.Many2one('mail.message', 'Message', readonly=True)
    contact_ids = fields.One2many('mail.resend.contact', 'resend_wizard_id', string='Recipients')
    notification_ids = fields.Many2many('mail.notification', string='Notifications', readonly=True)
    can_cancel = fields.Boolean(compute='_compute_can_cancel')
    can_resend = fields.Boolean(compute='_compute_can_resend')
    partner_readonly = fields.Boolean(compute='_compute_partner_readonly')

    @api.depends('contact_ids')
    def _compute_can_cancel(self):
        self.can_cancel = self.contact_ids.filtered(lambda p: not p.resend)

    @api.depends('contact_ids.resend')
    def _compute_can_resend(self):
        self.can_resend = any(contact.resend for contact in self.contact_ids)

    def _compute_partner_readonly(self):
        self.partner_readonly = not self.env['res.partner'].check_access_rights('write', raise_exception=False)

    @api.model
    def default_get(self, fields):
        rec = super(MailResendMessage, self).default_get(fields)
        message_id = self._context.get('mail_message_to_resend')
        if message_id:
            mail_message_id = self.env['mail.message'].browse(message_id)
            notification_ids = mail_message_id.notification_ids.filtered(lambda notif: notif.notification_type == 'email' and notif.notification_status in ('exception', 'bounce'))
            contact_ids = [Command.create({
                'notification_id': notif.id,
                'resend': True,
                'failure_reason': notif.format_failure_reason(),
            }) for notif in notification_ids]

            has_user = any(notif.res_partner_id.user_ids for notif in notification_ids)
            if has_user:
                partner_readonly = not self.env['res.users'].check_access_rights('write', raise_exception=False)
            else:
                partner_readonly = not self.env['res.partner'].check_access_rights('write', raise_exception=False)
            rec['partner_readonly'] = partner_readonly
            rec['notification_ids'] = [Command.set(notification_ids.ids)]
            rec['mail_message_id'] = mail_message_id.id
            rec['contact_ids'] = contact_ids
        else:
            raise UserError(_('No message_id found in context'))
        return rec

    def resend_mail_action(self):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        for wizard in self:
            "If a partner disappeared from partner list, we cancel the notification"
            to_send = wizard.contact_ids.filtered(lambda c: c.resend)
            notif_to_cancel = wizard.contact_ids.filtered(lambda c: not c.resend).notification_id.\
                filtered(lambda notif: notif.notification_type == 'email' and notif.notification_status in ('exception', 'bounce'))
            notif_to_cancel.sudo().write({'notification_status': 'canceled'})
            if to_send:
                message = wizard.mail_message_id
                record = self.env[message.model].browse(message.res_id) if message.is_thread_message() else self.env['mail.thread']

                email_partners_data = []
                recipients_data = self.env['mail.followers']._get_recipient_data(None, 'comment', False, pids=to_send.partner_id.ids)[0]
                for pid, pdata in recipients_data.items():
                    if pid and pdata.get('notif', 'email') == 'email':
                        email_partners_data.append(pdata)

                unpartnered_emails = to_send.filtered(lambda contact: not contact.partner_id).mapped('email')
                email_partners_data += [{'active': True,
                                         'name': self.mail_message_id.record_name,
                                         'notif': 'email',
                                         'share': True,
                                         'type': 'customer',
                                         'unpartnered_email': email, } for email in unpartnered_emails]

                record._notify_thread_by_email(
                    message, email_partners_data,
                    resend_existing=True,
                    send_after_commit=False
                )
            self.mail_message_id._notify_message_notification_update()
        return {'type': 'ir.actions.act_window_close'}

    def cancel_mail_action(self):
        self.notification_ids.filtered(
            lambda notif: notif.notification_type == 'email'
            and notif.notification_status in ('exception', 'bounce')).sudo().write({'notification_status': 'canceled'})
        self.mail_message_id._notify_message_notification_update()
        return {'type': 'ir.actions.act_window_close'}


class ContactResend(models.TransientModel):
    _name = 'mail.resend.contact'
    _description = 'Contact information for mail resend'

    notification_id = fields.Many2one('mail.notification', string='Notification', ondelete='cascade', readonly=True)
    partner_id = fields.Many2one('res.partner', related='notification_id.res_partner_id', string='Partner', ondelete='cascade')
    name = fields.Char(related='partner_id.name', string='Recipient Name')
    email = fields.Char(compute='_compute_email', inverse="_inverse_email", string='Email Address')
    resend = fields.Boolean(string='Try Again', default=True)
    resend_wizard_id = fields.Many2one('mail.resend.message', string="Resend wizard")
    failure_reason = fields.Char(string='Error message')
    partner_readonly = fields.Boolean('Partner Readonly', related='resend_wizard_id.partner_readonly')

    @api.depends('partner_id', 'notification_id')
    def _compute_email(self):
        for contact in self:
            contact.email = contact.notification_id.unpartnered_email or contact.partner_id.email

    def _inverse_email(self):
        for contact in self:
            if contact.partner_id:
                contact.partner_id.email = email_normalize(contact.email)

            # do not update unless there actually is a change (important for 'No Email Found' default email to be cancelable)
            elif contact.notification_id.unpartnered_email and contact.notification_id.unpartnered_email != contact.email:
                if contact.notification_id.notification_status in ('bounce', 'exception'):
                    # This is fine because the mail has not been sent yet, so it will not be falsified
                    contact.notification_id.sudo().unpartnered_email = email_normalize(contact.email)
                else:
                    raise AccessError(_("You may not modify the email of a notification that is not waiting to be re-sent"))

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
