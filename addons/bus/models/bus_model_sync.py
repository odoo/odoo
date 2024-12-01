# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, api
from odoo.models import BaseModel

_logger = logging.getLogger(__name__)
_original_create = BaseModel.create


@api.model_create_multi
def create(self, vals_list):
    """
    Extended method for creating multiple records.
    Notifies bus events when records are created.
    """
    try:
        records = _original_create(self, vals_list)

        if 'bus.model.sync' in self.env:
            view_ids = self.env['ir.ui.view'].sudo().search([
                ('active', '=', True),
                ('model', '=', self._name)
            ])
            for view in view_ids:
                self.env['bus.model.sync']._bus_model_notify_event(self._name, view.id)

        return records

    except Exception as e:
        _logger.exception("Error creating records: %s", e)
        raise e


BaseModel.create = create


class BusModelSync(models.AbstractModel):
    _name = 'bus.model.sync'
    _description = 'Model for synchronizing updates in real-time across user sessions using Odoo\'s Bus system.'

    def _bus_model_notify_event(self, model_name, view_id):
        merged_view = f'realtime_sync_{model_name}_{view_id}'
        self.env['bus.bus']._sendone(merged_view, 'NOTIFICATION_FROM_NEW_RECORD', {
            'mergedView': merged_view
        })
