import datetime
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.tools.date_utils import all_timezones

_timezones = [(tz, tz) for tz in sorted(all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]


class TestCorePartner(models.Model):
    _name = 'test_core.partner'
    _description = 'Test Core Partner'

    name = fields.Char()
    tz = fields.Selection(_timezones, default=lambda self: self.env.context.get('tz'))
    tz_offset = fields.Char(compute='_compute_tz_offset')

    @api.depends('tz')
    def _compute_tz_offset(self):
        for partner in self:
            partner.tz_offset = datetime.datetime.now(ZoneInfo(partner.tz or 'UTC')).strftime('%z')
