# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SmsTracker(models.Model):
    _inherit = "sms.tracker"

    SMS_STATE_TO_TRACE_STATUS = {
        'error': 'error',
        'process': 'process',
        'outgoing': 'outgoing',
        'canceled': 'cancel',
        'pending': 'pending',
        'sent': 'sent',
    }

    mailing_trace_id = fields.Many2one('mailing.trace', ondelete='cascade', index='btree_not_null')

    def _action_update_from_provider_error(self, provider_error):
        error_status, failure_type, failure_reason = super()._action_update_from_provider_error(provider_error)
        self._update_sms_traces(error_status or 'error', failure_type=failure_type, failure_reason=failure_reason)
        return error_status, failure_type, failure_reason

    def _action_update_from_sms_state(self, sms_state, failure_type=False, failure_reason=False):
        super()._action_update_from_sms_state(sms_state, failure_type=failure_type, failure_reason=failure_reason)
        trace_status = self.SMS_STATE_TO_TRACE_STATUS[sms_state]
        traces = self._update_sms_traces(trace_status, failure_type=failure_type, failure_reason=failure_reason)
        self._update_sms_mailings(trace_status, traces)

    def _update_sms_traces(self, trace_status, failure_type=False, failure_reason=False):
        if not self.mailing_trace_id:  # avoid a search below
            return self.env['mailing.trace']
        # See _update_sms_notifications
        statuses_to_ignore = {
            'cancel': ['cancel', 'process', 'pending', 'sent'],
            'outgoing': ['outgoing', 'process', 'pending', 'sent'],
            'process': ['process', 'pending', 'sent'],
            'pending': ['pending', 'sent'],
            'bounce': ['bounce'],
            'sent': ['sent'],
            'error': ['error'],
        }[trace_status]
        traces = self.mailing_trace_id.filtered(lambda t: t.trace_status not in statuses_to_ignore)
        if traces:
            # TDE note: check to use set_sent / ... tools updating marketing automation bits
            traces_values = {
                'trace_status': trace_status,
                'failure_type': failure_type,
                'failure_reason': failure_reason,
            }
            traces.write(traces_values)
            traces.filtered(
                lambda t: t.trace_status not in ['outgoing', 'process', 'error', 'cancel'] and not t.sent_datetime
            ).sent_datetime = self.env.cr.now()
        return traces

    def _update_sms_mailings(self, trace_status, traces):
        traces.flush_recordset(['trace_status'])

        if trace_status == 'process':
            traces.mass_mailing_id.write({'state': 'sending'})
            return

        mailings_to_mark_done = self.env['mailing.mailing'].search([
            ('id', 'in', traces.mass_mailing_id.ids),
            '!', ('mailing_trace_ids.trace_status', '=', 'process'),  # = not any trace with 'process' status
            ('state', '!=', 'done'),
        ])

        if mailings_to_mark_done:
            if self.env.user.is_public:  # From webhook event
                mailings_to_mark_done._track_set_author(self.env.ref('base.partner_root'))
            for mailing in mailings_to_mark_done:
                mailing.write({
                    'state': 'done',
                    'sent_date': fields.Datetime.now(),
                    'kpi_mail_required': not mailing.sent_date
                })
