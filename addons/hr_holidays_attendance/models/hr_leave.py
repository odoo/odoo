# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _compute_display_name(self):
        super()._compute_display_name()
        for leave in self.filtered('is_time_rule_output'):
            if not (leave.date_from and leave.date_to):
                continue
            total_seconds = (leave.date_to - leave.date_from).total_seconds()
            h, rem = divmod(int(total_seconds), 3600)
            m = rem // 60
            duration = f'{h}h{m:02d}' if m else f'{h}h'
            leave.display_name = f'{leave.work_entry_type_id.name} {duration}'.strip()
