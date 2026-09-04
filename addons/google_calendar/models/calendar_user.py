from odoo import api, fields, models


class CalendarUser(models.Model):
    _inherit = 'calendar.user'

    # What if google_calendar is uninstalled? If the reader is defined here, the calendars will be deleted which might not be the expected behavior
    access_role = fields.Selection(selection_add=[
        ('reader', 'Reader'),  # can read events but cannot write or delete them
        ('freeBusyReader', 'Free Busy Reader'),  # can only see event timeslots marked as Busy, without any event details
    ], ondelete={'reader': 'cascade', 'freeBusyReader': 'cascade'})

    google_sync_enabled = fields.Boolean(default=True)
    google_sync_token = fields.Char('Sync Token')

    is_filter_active = fields.Boolean(string="Filter Active", compute='_compute_filters', store=True, readonly=False)
    is_filter_checked = fields.Boolean(string="Filter Checked", compute='_compute_filters', store=True, readonly=False)

    def write(self, vals):
        res = super().write(vals)
        # Calendars imported via Google sync are hidden by default (is_import_pending=True)
        # and should only be imported after the user chooses to sync them.
        if vals.get('google_sync_enabled'):
            self.filtered(lambda r: r.calendar_id.is_import_pending).calendar_id.is_import_pending = False

        return res

    def _get_writeable_fields(self):
        return super()._get_writeable_fields() | {'google_sync_enabled'}

    @api.depends('google_sync_enabled')
    def _compute_filters(self):
        """When the user chooses to start syncing a calendar/import it from google
        we should immediately show it in the filters"""
        for record in self:
            if record.google_sync_enabled:
                record.is_filter_active = True
                record.is_filter_checked = True
