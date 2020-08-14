# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, tools, _
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    notification_type = fields.Selection(selection_add=[
        ('sms', 'SMS')
    ], ondelete={'sms': 'set default'})
    sms_id = fields.Many2one('sms.sms', string='SMS', index=True, ondelete='set null')
    sms_number = fields.Char('SMS Number')
    failure_type = fields.Selection(selection_add=[
        ('sms_number_missing', 'Missing Number'),
        ('sms_number_format', 'Wrong Number Format'),
        ('sms_credit', 'Insufficient Credit'),
        ('sms_server', 'Server Error'),
        ('sms_acc', 'Unregistered Account')
    ])

    @api.model
    def _cron_notify_admins(self):
        super()._cron_notify_admins()
        cron = self.env.ref('mail.ir_cron_mail_notify_administrators')
        previous_date = fields.Datetime.now() - relativedelta(**{cron.interval_type: cron.interval_number})
        # Count failed SMS
        failed_sms_counter = self.env['sms.sms'].sudo().search_count([
            ('create_date', '>=', previous_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
            ('state', '=', 'error')])
        # Send notifications about failed SMS (_notify_admins methods in daily cron job should set a repeat_delay of 1 day)
        if failed_sms_counter:
            sms_messages = {
                "sms__failure": lambda failed_sms_counter, mail_sms_notifications_window_action: (
                    _('Odoo has been unable to send SMS'),
                    _(
                        "%(failed_sms_counter)d SMS(s) could not be sent due to technical issues.\n"
                        "Please check whether recipient's phone number exists and if your have enaugh IAP credits.\n"
                        "To recharge your IAP credits please go to your 'IAP Portal' [Settings app > Odoo IAP > View my Services].\n"
                        "From there, you can view your current balance, recharge your credits, review your consumption and "
                        "set another reminder (by email) to when credits are low.\n"
                        "You can check SMS notifications for more details about failed SMS messages (an error message should help you diagnose the issue.)"
                    ) % {
                        'failed_sms_counter': failed_sms_counter,
                    },
                    {
                        "related_doc": 'https://www.odoo.com/documentation/user/online/general/in_app_purchase/in_app_purchase.html',
                        "related_view_url": "/web#action=%(mail_sms_notifications_window_action)s&amp;view_type=list" % {
                            'mail_sms_notifications_window_action': mail_sms_notifications_window_action
                        },
                        "related_view_text": "go to sms notifications"
                    }
                )
            }
            self._notify_admins(
                *self._get_admin_notification('sms__failure', sms_messages)(
                    failed_sms_counter,
                    self.env.ref('mail.mail_notification_action').id
                ),
                repeat_delay=timedelta(days=1)
            )
