# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _get_notify_alert_extra_conditions(self):
        res = super()._get_notify_alert_extra_conditions()
        return f'{res} AND "event"."google_id" IS NULL'
