from random import randint

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class CalendarUser(models.Model):
    _name = 'calendar.user'
    _description = 'Calendar User Manager'

    def _get_default_color(self):
        return randint(1, 11)

    _unique_user_per_calendar = models.UniqueIndex('(user_id, calendar_id)')
    _single_primary_calendar_per_user = models.UniqueIndex('(user_id) WHERE is_primary')

    calendar_id = fields.Many2one('calendar.calendar', string='Calendar', ondelete='cascade', index='btree', required=True, readonly=True)
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', index='btree', required=True, readonly=True)
    is_primary = fields.Boolean('Primary', readonly=True)
    name = fields.Char('Label')

    # Access roles matching those of Google Calendar
    access_role = fields.Selection([
        ('owner', 'Owner'),
        ('writer', 'Write'),
    ], required=True, readonly=True)

    # Filter values
    filter_color = fields.Integer(string='Color', default=_get_default_color)
    is_filter_active = fields.Boolean('Active', default=True)
    is_filter_checked = fields.Boolean('Checked', default=True)

    def write(self, vals):
        blacklisted_fields = [k for k in vals if k not in self._get_writeable_fields()]
        if blacklisted_fields and not self.env.su:
            raise AccessError(_("These fields cannot be modified: %(fields)s", fields=", ".join(blacklisted_fields)))

        return super().write(vals)

    def unlink(self):
        calendars_to_remove = self.calendar_id.filtered(lambda cal: cal.calendar_user_ids <= self)
        result = super().unlink()
        calendars_to_remove.sudo().unlink()
        return result

    @api.model
    def _get_writeable_fields(self):
        return {'is_filter_active', 'is_filter_checked', 'filter_color', 'name'}
