# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.models import BaseModel

_original_create = BaseModel.create


def global_create(self, vals):
    """
   Extended global `create` method.
    """
    records = _original_create(self, vals)

    view_ids = self.env['ir.ui.view'].search([('active', '=', True), ('model', '=', self._name)])
    for view in view_ids:
        self.env['bus.model.sync']._bus_model_notify_event(self._name, view.id)

    return records


BaseModel.create = global_create


class BusModelSync(models.AbstractModel):
    _name = 'bus.model.sync'
    _description = 'Model for synchronizing updates in real-time across user sessions using Odoo\'s Bus system.'

    def _bus_model_notify_event(self, model_name, view_id):
        merged_view = f'realtime_sync_{model_name}_{view_id}'
        self.env['bus.bus']._sendone(merged_view, 'NOTIFICATION_FROM_NEW_RECORD', {
            'mergedView': merged_view
        })
