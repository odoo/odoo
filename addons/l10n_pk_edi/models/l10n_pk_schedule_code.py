# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class L10nPkScheduleCode(models.Model):
    _name = "l10n.pk.schedule.code"
    _description = 'Product Schedule Code'
    _rec_name = 'display_name'

    name = fields.Char('Schedule Code Description', required=True)
    schedule_code = fields.Char('Schedule Code', required=True)

    @api.depends('name', 'schedule_code')
    def _compute_display_name(self):
        for line in self:
            line.display_name = f"[{line.schedule_code}] {line.name}"
