from odoo import api, models


class ResourceCalendarAttendance(models.Model):
    _name = 'resource.calendar.attendance'
    _inherit = ['resource.calendar.attendance', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        attendance_ids = data['pos.preset'].attendance_ids.ids
        return [('id', 'in', attendance_ids)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'hour_from', 'hour_to', 'dayofweek', 'day_period']
