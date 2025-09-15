# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SmsTracker(models.Model):
    """Relationship between a sent SMS and tracking records such as notifications and traces.

    This model acts as an extension of a `mail.notification` or a `mailing.trace` and allows to
    update those based on the SMS provider responses both at sending and when later receiving
    sent/delivery reports (see `SmsController`).
    SMS trackers are supposed to be created manually when necessary, and tied to their related
    SMS through the SMS UUID field. (They are not tied to the SMS records directly as those can
    be deleted when sent).

    Note: Only admins/system user should need to access (a fortiori modify) these technical
      records so no "sudo" is used nor should be required here.
    """
    _name = 'sms.tracker'
    _description = "Link SMS to mailing/sms tracking models"

    SMS_STATE_TO_NOTIFICATION_STATUS = {
        'canceled': 'canceled',
        'process': 'process',
        'error': 'exception',
        'outgoing': 'ready',
        'sent': 'sent',
        'pending': 'pending',
    }

    sms_uuid = fields.Char('SMS uuid', required=True)
    mail_notification_id = fields.Many2one('mail.notification', ondelete='cascade')

    _sql_constraints = [
        ('sms_uuid_unique', 'unique(sms_uuid)', 'A record for this UUID already exists'),
    ]

    def _action_update_from_provider_error(self, provider_error):
        """
        :param str provider_error: value returned by SMS service provider (IAP) or any string.
            If provided, notification values will be derived from it.
            (see ``_get_tracker_values_from_provider_error``)
        """
        failure_reason = self.env.context.get("sms_known_failure_reason")  # TODO RIGR in master: pass as param instead of context
        failure_type = f'sms_{provider_error}'
        error_status = None
        if failure_type not in self.env['sms.sms'].DELIVERY_ERRORS:
            failure_type = 'unknown'
            failure_reason = failure_reason or provider_error
        elif failure_type in self.env['sms.sms'].BOUNCE_DELIVERY_ERRORS:
            error_status = "bounce"

        self._update_sms_notifications(error_status or 'exception', failure_type=failure_type, failure_reason=failure_reason)
        return error_status, failure_type, failure_reason

    def _action_update_from_sms_state(self, sms_state, failure_type=False, failure_reason=False):
        notification_status = self.SMS_STATE_TO_NOTIFICATION_STATUS[sms_state]
        self._update_sms_notifications(notification_status, failure_type=failure_type, failure_reason=failure_reason)

    def _update_sms_notifications(self, notification_status, failure_type=False, failure_reason=False):
        # canceled is a state which means that the SMS sending order should not be sent to the SMS service.
        # `process`, `pending` are sent to IAP which is not revertible (as `sent` which means "delivered").
        notifications_statuses_to_ignore = {
            'canceled': ['canceled', 'process', 'pending', 'sent'],
            'ready': ['ready', 'process', 'pending', 'sent'],
            'process': ['process', 'pending', 'sent'],
            'pending': ['pending', 'sent'],
            'bounce': ['bounce', 'sent'],
            'sent': ['sent'],
            'exception': ['exception'],
        }[notification_status]
        notifications = self.mail_notification_id.filtered(
            lambda n: n.notification_status not in notifications_statuses_to_ignore
        )
        if notifications:
            notifications.write({
                'notification_status': notification_status,
                'failure_type': failure_type,
                'failure_reason': failure_reason,
            })
            if not self.env.context.get('sms_skip_msg_notification'):
                notifications.mail_message_id._notify_message_notification_update()
