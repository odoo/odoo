# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools


class MailCCMixin(models.AbstractModel):
    _name = 'mail.thread.cc'
    _inherit = 'mail.thread'
    _description = 'Email CC management'

    email_cc = fields.Char('Email cc')

    def _mail_cc_sanitized_raw_dict(self, cc_string):
        '''return a dict of sanitize_email:raw_email from a string of cc'''
        if not cc_string:
            return {}
        return {
            tools.email_normalize(email): tools.formataddr((name, tools.email_normalize(email)))
            for (name, email) in tools.mail.email_split_tuples(cc_string)
        }

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}
        cc_values = {
            'email_cc': ", ".join(self._mail_cc_sanitized_raw_dict(msg_dict.get('cc')).values()),
        }
        cc_values.update(custom_values)
        return super(MailCCMixin, self).message_new(msg_dict, cc_values)

    def message_update(self, msg_dict, update_vals=None):
        '''Adds cc email to self.email_cc while trying to keep email as raw as possible but unique'''
        if update_vals is None:
            update_vals = {}
        cc_values = {}
        new_cc = self._mail_cc_sanitized_raw_dict(msg_dict.get('cc'))
        if new_cc:
            old_cc = self._mail_cc_sanitized_raw_dict(self.email_cc)
            new_cc.update(old_cc)
            cc_values['email_cc'] = ", ".join(new_cc.values())
        cc_values.update(update_vals)
        return super(MailCCMixin, self).message_update(msg_dict, cc_values)

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        if self.email_cc:
            for email in tools.mail.email_split_and_format(self.email_cc):
                self._message_add_suggested_recipient(recipients, email=email, reason=_('CC Email'))
        return recipients
