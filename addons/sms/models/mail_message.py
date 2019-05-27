# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from operator import itemgetter

from odoo import api, exceptions, fields, models
from odoo.tools import groupby


class MailMessage(models.Model):
    """ Override MailMessage class in order to add a new type: SMS messages.
    Those messages comes with their own notification method, using SMS
    gateway. """
    _inherit = 'mail.message'

    message_type = fields.Selection(selection_add=[('sms', 'SMS')])

    @api.multi
    def _format_mail_failures(self):
        """ A shorter message to notify a SMS delivery failure update

        TDE FIXME: should be cleaned
        """
        res = super(MailMessage, self)._format_mail_failures()

        # prepare notifications computation in batch
        all_notifications = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', self.ids)
        ])
        msgid_to_notif = defaultdict(lambda: self.env['mail.notification'].sudo())
        for notif in all_notifications:
            msgid_to_notif[notif.mail_message_id.id] += notif

        for message in self:
            notifications = msgid_to_notif[message.id]
            if not any(notification.notification_type == 'sms' for notification in notifications):
                continue
            info = dict(message._get_mail_failure_dict(),
                        failure_type='sms',
                        notifications=dict((notif.res_partner_id.id, (notif.notification_status, notif.res_partner_id.name)) for notif in notifications if notif.notification_type == 'sms'),
                        module_icon='/sms/static/img/sms_failure.png'
                        )
            res.append(info)
        return res

    @api.multi
    def _notify_sms_update(self):
        messages = self.env['mail.message']
        for message in self:
            # Check if user has access to the record before displaying a notification about it.
            # In case the user switches from one company to another, it might happen that he doesn't
            # have access to the record related to the notification. In this case, we skip it.
            if message.model and message.res_id:
                record = self.env[message.model].browse(message.res_id)
                try:
                    record.check_access_rights('read')
                    record.check_access_rule('read')
                except exceptions.AccessError:
                    continue
                else:
                    messages |= message

        """ Notify channels after update of SMS status """
        updates = [[
            (self._cr.dbname, 'res.partner', author.id),
            {'type': 'sms_update', 'elements': self.env['mail.message'].concat(*author_messages)._format_mail_failures()}
        ] for author, author_messages in groupby(messages, itemgetter('author_id'))]
        self.env['bus.bus'].sendmany(updates)

    @api.multi
    def message_format(self):
        """ Override in order to retrieves data about SMS (recipient name and
            SMS status)

        TDE FIXME: clean the overall message_format thingy
        """
        message_values = super(MailMessage, self).message_format()
        all_sms_notifications = self.env['mail.notification'].sudo().search([
            ('mail_message_id', 'in', [r['id'] for r in message_values]),
            ('notification_type', '=', 'sms')
        ])
        msgid_to_notif = defaultdict(lambda: self.env['mail.notification'].sudo())
        for notif in all_sms_notifications:
            msgid_to_notif[notif.mail_message_id.id] += notif

        for message in message_values:
            customer_sms_data = [(notif.id, notif.res_partner_id.display_name, notif.notification_status) for notif in msgid_to_notif.get(message['id'], [])]
            message['sms_ids'] = customer_sms_data
        return message_values
