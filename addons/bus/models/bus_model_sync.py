# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)
_original_create = models.BaseModel.create


@api.model_create_multi
def create(self, vals_list) -> models.BaseModel:
    """
    Extended method for creating multiple records.
    Notifies bus events when records are created.

    :param vals_list:
        values for the model's fields, as a list of dictionaries::

            [{'field_name': field_value, ...}, ...]

    :return: the created records
    :raise AccessError: if the current user is not allowed to create records of the specified model
    :raise ValidationError: if user tries to enter invalid value for a selection field
    :raise ValueError: if a field name specified in the create values does not exist.
    :raise UserError: if a loop would be created in a hierarchy of objects as a result of the operation
    """

    records = _original_create(self, vals_list)

    if hasattr(self.env.user, '_bus_send'):
        view_ids = self.env['ir.ui.view'].sudo().search([
            ('active', '=', True),
            ('model', '=', self._name),
            ('type', '=', 'list')
        ])
        for view in view_ids:
            merged_view = f'NOTIFICATION_FROM_NEW_RECORD_TO_REALTIME_SYNC_{self._name}_{view.id}'

            self.env.user._bus_send(merged_view, {
                'mergedView': merged_view
            })

        return records


models.BaseModel.create = create
