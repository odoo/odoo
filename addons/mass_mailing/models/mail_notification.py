# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.osv import expression


class MailNotification(models.Model):
    """Extend the mail.notification to add tracking value/method.

    When the mass_mailing_id is set (then related to a mailing.mailing record),
    the notification acts as a mailing trace (save the tracking data). Functionnaly,
    nothing change for the deskop notification (where mass_mailing_id is Falsy).
    """
    _inherit = 'mail.notification'

    # Mail data
    mail_id_int = fields.Integer(
        string='Mail ID (tech)',
        help='ID of the related mail_mail. This field is an integer field because '
             'the related mail_mail can be deleted separately from its statistics. '
             'However the ID is needed for several action and controllers.',
        index=True)
    email = fields.Char('Email')
    message_id = fields.Char('Message-ID', help='Technical field for the email Message-ID (RFC 2392)')
    # Related Document
    model = fields.Char('Document model')
    res_id = fields.Many2oneReference('Document ID', model_field='model')
    # If mass_mailing_id is set, the notification will act as a trace
    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mailing', index=True, ondelete='cascade')
    campaign_id = fields.Many2one('utm.campaign', related='mass_mailing_id.campaign_id',
                                  string='Campaign', index=True, store=True, default=False)
    # Bounce and tracking
    canceled = fields.Datetime(help='Date when the email has been invalidated. '
                                    'Invalid emails are blacklisted, opted-out or invalid email format')
    scheduled = fields.Datetime(help='Date when the email has been created', default=fields.Datetime.now)
    sent = fields.Datetime(help='Date when the email has been sent')
    exception = fields.Datetime(help='Date of technical error leading to the email not being sent')
    opened = fields.Datetime(help='Date when the email has been opened the first time')
    clicked = fields.Datetime(help='Date when customer clicked on at least one tracked link')
    replied = fields.Datetime(help='Date when this email has been replied for the first time.')
    bounced = fields.Datetime(help='Date when this email has bounced.')
    # Link tracking
    links_click_ids = fields.One2many('link.tracker.click', 'mailing_trace_id', string='Links click')
    # Status
    notification_status = fields.Selection(selection_add=[
        ('outgoing', 'Outgoing'),
        ('opened', 'Opened'),
        ('replied', 'Replied')])
    status_update = fields.Datetime('Status Update', help='Last status tracking update', default=fields.Datetime.now)

    def name_get(self):
        return [(notification.id, '%s: %s (%s)' % (
            notification.notification_type,
            notification.mass_mailing_id.name or notification.res_partner_id.display_name or '',
            notification.id
        )) for notification in self]

    @api.model
    def _get_notification_status(self, values):
        """Get the appropriate notification status value depending of the tracking values.

        It is only available for the notifiction acting as trace.

        :param values: dict of written/created values of a notification
        """
        status_whitelist = ['sent', 'opened', 'clicked', 'replied', 'bounced', 'exception', 'canceled']
        if any(key in status_whitelist for key in values.keys()):
            notification_status = next((key for key in values.keys() if key in status_whitelist), False)
            if notification_status == 'clicked':
                notification_status = 'opened'
            return notification_status

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            # Change default values if mass mailing is set
            if values.get('mass_mailing_id'):
                if not values.get('notification_type'):
                    values['notification_type'] = 'email'
                if values.get('mail_id'):
                    values['mail_id_int'] = values['mail_id']
                notification_status = self._get_notification_status(values)
                if notification_status:
                    values['notification_status'] = notification_status
                else:
                    values['notification_status'] = 'outgoing'
        return super(MailNotification, self).create(values_list)

    def write(self, values):
        notification_status = self._get_notification_status(values)
        if notification_status:
            values['notification_status'] = notification_status
            values['status_update'] = fields.Datetime.now()
        return super(MailNotification, self).write(values)

    def _get_records(self, mail_ids=None, mail_message_ids=None, domain=None):
        if not self.ids and mail_ids:
            base_domain = [('mail_id_int', 'in', mail_ids)]
        elif not self.ids and mail_message_ids:
            base_domain = [('message_id', 'in', mail_message_ids)]
        else:
            base_domain = [('id', 'in', self.ids)]
        if domain:
            base_domain = expression.AND([domain, base_domain])
        return self.search(base_domain)

    def set_opened(self, mail_ids=None, mail_message_ids=None):
        notifs = self._get_records(mail_ids, mail_message_ids, [('opened', '=', False)])
        notifs.write({'opened': fields.Datetime.now(), 'bounced': False})
        return notifs

    def set_clicked(self, mail_ids=None, mail_message_ids=None):
        notifs = self._get_records(mail_ids, mail_message_ids, [('clicked', '=', False)])
        notifs.write({'clicked': fields.Datetime.now()})
        return notifs

    def set_replied(self, mail_ids=None, mail_message_ids=None):
        notifs = self._get_records(mail_ids, mail_message_ids, [('replied', '=', False)])
        notifs.write({'replied': fields.Datetime.now()})
        return notifs

    def set_bounced(self, mail_ids=None, mail_message_ids=None):
        notifs = self._get_records(mail_ids, mail_message_ids, [('bounced', '=', False), ('opened', '=', False)])
        notifs.write({'bounced': fields.Datetime.now()})
        return notifs

    @api.model
    def _gc_notifications(self, max_age_days=180):
        domain = [
            ('mass_mailing_id', '=', False),
            ('is_read', '=', True),
            ('read_date', '<', fields.Datetime.now() - relativedelta(days=max_age_days)),
            ('res_partner_id.partner_share', '=', False),
            ('notification_status', 'in', ('sent', 'canceled'))
        ]
        return self.search(domain).unlink()
