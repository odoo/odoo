# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class BusModelSync(models.Model):
    _name = 'bus.model.sync'
    _description = 'Model for synchronizing updates in real-time across user sessions using Odoo\'s Bus system.'

    def _bus_model_notify_event(self, model_name, view_id):
        merged_view = f'realtime_sync_{model_name}_{view_id}'
        self.env['bus.bus']._sendone('NOTIFICATION_FROM_NEW_RECORD', 'NOTIFICATION_FROM_NEW_RECORD', {
            'mergedView': merged_view
        })
