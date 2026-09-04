from odoo import api, fields, models


class CalendarCalendar(models.Model):
    _name = 'calendar.calendar'
    _inherit = ['calendar.calendar']

    microsoft_sync_enabled = fields.Boolean('Sync with Outlook', compute='_compute_sync_microsoft', search='_search_sync_microsoft',
        help='In the current version of Odoo, only the primary calendar can be synchronized with Outlook.')

    @api.depends('calendar_user_ids.is_primary')
    def _compute_sync_microsoft(self):
        for calendar in self:
            calendar.microsoft_sync_enabled = calendar.calendar_user_ids.is_primary

    def _search_sync_microsoft(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented

        # = True -> in [True] -> True
        # != True -> not in [True] -> False
        want_sync = (operator == 'in')
        return [('calendar_user_ids', 'any' if want_sync else 'not any', [('is_primary', '=', True)])]
