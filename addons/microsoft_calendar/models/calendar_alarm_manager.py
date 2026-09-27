# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import SQL


class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _get_notify_alert_extra_conditions(self, alarm_type=None):
        base = super()._get_notify_alert_extra_conditions(alarm_type)
        if alarm_type == 'email':
            return SQL("%s AND event.microsoft_id IS NULL", base)
        return base
