from odoo import models


class SmsTracker(models.Model):
    _inherit = "sms.tracker"

    def _update_sms_traces(self, trace_status, failure_type=False, failure_reason=False):
        # when setting a sms trace as bounced, also trigger the bounce status
        # on matching marketing trace to trigger activities
        traces = super()._update_sms_traces(trace_status, failure_type=failure_type, failure_reason=failure_reason)
        if traces and trace_status == 'bounce':
            # TDE FIXME: 'set_bounce' is too much mail oriented, should be cleaned somehow
            for marketing_trace in traces.marketing_trace_id:
                marketing_trace.process_event('sms_bounce')
        return traces
