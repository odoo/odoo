from odoo import api, models


class RecurrenceRule(models.Model):
    _inherit = 'calendar.recurrence'

    @api.model
    def _odoo_values(self, google_recurrence, default_reminders=()):
        values = super()._odoo_values(google_recurrence, default_reminders)
        if google_recurrence.iCalUID:
            values['ms_universal_event_id'] = google_recurrence.iCalUID
        return values

    def _get_post_sync_values(self, request_values, google_values):
        values = super()._get_post_sync_values(request_values, google_values)
        if google_values.get('iCalUID'):
            values['ms_universal_event_id'] = google_values.get('iCalUID')
        return values

    @api.model
    def _sync_google2odoo(self, google_events, write_dates=None, default_reminders=()):
        uids = [e.iCalUID for e in google_events if e.iCalUID]
        if uids:
            existing_by_uids = self.with_context(active_test=False).search([
                ('ms_universal_event_id', 'in', uids),
                ('google_id', '=', False)
            ])
            if existing_by_uids:
                mapping = {e.ms_universal_event_id: e for e in existing_by_uids}
                for gevent in google_events:
                    if gevent.iCalUID in mapping:
                        mapping[gevent.iCalUID].google_id = gevent.id

        return super()._sync_google2odoo(google_events, write_dates, default_reminders)
