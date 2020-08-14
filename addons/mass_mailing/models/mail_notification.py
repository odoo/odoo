from odoo import fields, models, api, tools, _
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class MailNotification(models.Model):
    _inherit = 'mail.notification'

    @api.model
    def _cron_notify_admins(self):
        super()._cron_notify_admins()
        cron = self.env.ref('mail.ir_cron_mail_notify_administrators')
        previous_date = fields.Datetime.now() - relativedelta(**{cron.interval_type: cron.interval_number})
        ignored_mailing_counter = self.env['mailing.trace'].sudo().search_count([
            ('create_date', '>=', previous_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
            ('state', '=', 'ignored')])
        mass_mailing_message = {
            "mass_mailing__ignored": lambda failed_ignored_mailing_counter, mailing_traces_window_action: (
                _('Email marketing : ignored emails'),
                _(
                    "%(failed_ignored_mailing_counter)d email(s) have been ignored and will not be sent.\n"
                    "Please make sure that recipient's email address really exists and if it's actually valid.\n"
                    "You can check your mailing traces for more details."
                ) % {
                    'failed_ignored_mailing_counter': failed_ignored_mailing_counter,
                },
                {
                    "related_view_url": "/web#action=%(mailing_traces_window_action)s&amp;view_type=list" % {
                        'mailing_traces_window_action': mailing_traces_window_action
                    },
                    "related_view_text": "go to mailing traces"
                }
            )
        }
        if ignored_mailing_counter:
            self._notify_admins(
                *self._get_admin_notification('mass_mailing__ignored', mass_mailing_message)(
                    ignored_mailing_counter,
                    self.env.ref('mass_mailing.mailing_trace_action').id
                ),
                repeat_delay=timedelta(days=1)
            )
