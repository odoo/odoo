# -*- coding: utf-8 -*-
from __future__ import annotations

import typing

from odoo import fields, models

if typing.TYPE_CHECKING:
    from odoo.api import ValuesType


class MailTrackingValue(models.Model):
    _name = 'mail.tracking.value'
    _description = 'Mail Tracking Value'
    _rec_name = 'field_id'
    _order = 'id DESC'

    field_id = fields.Many2one(
        'ir.model.fields', required=False, readonly=True,
        index=True, ondelete='set null')
    field_info = fields.Json('Removed field information')

    old_value_integer = fields.Integer('Old Value Integer', readonly=True)
    old_value_float = fields.Float('Old Value Float', readonly=True)
    old_value_char = fields.Char('Old Value Char', readonly=True)
    old_value_text = fields.Text('Old Value Text', readonly=True)
    old_value_datetime = fields.Datetime('Old Value DateTime', readonly=True)

    new_value_integer = fields.Integer('New Value Integer', readonly=True)
    new_value_float = fields.Float('New Value Float', readonly=True)
    new_value_char = fields.Char('New Value Char', readonly=True)
    new_value_text = fields.Text('New Value Text', readonly=True)
    new_value_datetime = fields.Datetime('New Value Datetime', readonly=True)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, ondelete='set null',
        help="Used to display the currency when tracking monetary values")

    mail_message_id = fields.Many2one('mail.message', 'Message ID', required=True, index=True, ondelete='cascade')

    def _filter_has_field_access(self, env):
        """ Return the subset of self for which the user in env has access. As
        this model is admin-only, it is generally accessed as sudo and we need
        to distinguish context environment from tracking values environment.

        If tracking is linked to a field, user should have access to the field.
        Otherwise only members of "base.group_system" can access it. """

        def has_field_access(tracking):
            if not tracking.field_id:
                return env.is_system()
            model = env[tracking.field_id.model]
            model_field = model._fields.get(tracking.field_id.name)
            return model.has_field_access(model_field, 'read') if model_field else False

        return self.filtered(has_field_access)

    def _filter_free_field_access(self):
        """ Return the subset of self which is available for all users: trackings
        linked to an existing field without access group. It is used notably
        when sending tracking summary through notifications. """

        def has_free_access(tracking):
            if not tracking.field_id:
                return False
            model_field = self.env[tracking.field_id.model]._fields.get(tracking.field_id.name)
            return model_field and not model_field.groups

        return self.filtered(has_free_access)

    def _tracking_value_format(self) -> list[ValuesType]:
        """ Return structured formatted data to be used by chatter to display
        tracking values. It is organized by model.

        :return: for each tracking value in self, their formatted display
          values given as a dict;
        :rtype: list[ValuesType]
        """
        model_map = {}
        for tracking in self:
            model = tracking.field_id.model or tracking.mail_message_id.model
            model_map.setdefault(model, self.browse())
            model_map[model] += tracking
        formatted = []
        for model, trackings in model_map.items():
            formatted += trackings._tracking_value_format_model(model)
        return formatted

    def _tracking_value_format_model(self, model: str) -> list[ValuesType]:
        """ Return structured formatted data to be used by chatter to display
        tracking values on a single model. Order it based on ascending sequence
        then field name. Property fields are always last.

        :returns: for each tracking value in self, their formatted display
          values given as a dict;
        :rtype: list[ValuesType]
        """
        if not self:
            return []

        # fetch model-based information
        if model:
            TrackedModel = self.env[model]
            tracked_fields = TrackedModel.fields_get(self.field_id.mapped('name'), attributes={'digits', 'string', 'type'})
            model_sequence_info = dict(TrackedModel._mail_track_order_fields(tracked_fields)) if model else {}
        else:
            tracked_fields, model_sequence_info = {}, {}

        # generate sequence of trackings
        fields_sequence_map = dict(
            {
                tracking.field_info['name']: tracking.field_info.get('sequence', 100)
                for tracking in self.filtered('field_info')
            },
            **model_sequence_info,
        )
        # generate dict of field information, if available
        fields_col_info = (
            tracking.field_id.ttype != 'properties'
            and tracked_fields.get(tracking.field_id.name)
            or {
                'string': tracking.field_info['desc'] if tracking.field_info else self.env._('Unknown'),
                'type': tracking.field_info['type'] if tracking.field_info else 'char',
            } for tracking in self
        )

        def sort_tracking_info(tracking_info_tuple):
            tracking = tracking_info_tuple[0]
            field_name = tracking.field_id.name or (tracking.field_info['name'] if tracking.field_info else 'unknown')
            return (
                fields_sequence_map.get(field_name, 100),
                tracking.field_id.ttype == 'properties',
                field_name,
            )

        formatted = [
            {
                'id': tracking.id,
                'fieldInfo': {
                    'changedField': col_info['string'],
                    'currencyId': tracking.currency_id.id,
                    'floatPrecision': col_info.get('digits'),
                    'fieldType': col_info['type'],
                    'isPropertyField': tracking.field_id.ttype == 'properties',
                },
                'newValue': tracking._format_display_value(col_info['type'], new=True)[0],
                'oldValue': tracking._format_display_value(col_info['type'], new=False)[0],
            }
            for tracking, col_info in sorted(zip(self, fields_col_info), key=sort_tracking_info)
        ]
        return formatted

    def _format_display_value(self, field_type: str, new: bool = True) -> str:
        """ Format value of 'mail.tracking.value', according to the field type.

        :param str field_type: Odoo field type;
        :param bool new: if True, display the 'new' value. Otherwise display
          the 'old' one.
        """
        field_mapping = {
            'boolean': ('old_value_integer', 'new_value_integer'),
            'date': ('old_value_datetime', 'new_value_datetime'),
            'datetime': ('old_value_datetime', 'new_value_datetime'),
            'char': ('old_value_char', 'new_value_char'),
            'float': ('old_value_float', 'new_value_float'),
            'integer': ('old_value_integer', 'new_value_integer'),
            'monetary': ('old_value_float', 'new_value_float'),
            'text': ('old_value_text', 'new_value_text'),
        }

        result = []
        for record in self:
            value_fname = field_mapping.get(
                field_type, ('old_value_char', 'new_value_char')
            )[bool(new)]
            value = record[value_fname]

            if field_type in {'integer', 'float', 'char', 'text', 'monetary'}:
                result.append(value)
            elif field_type in {'date', 'datetime'}:
                if not record[value_fname]:
                    result.append(value)
                elif field_type == 'date':
                    result.append(fields.Date.to_string(value))
                else:
                    result.append(f'{value}Z')
            elif field_type == 'boolean':
                result.append(bool(value))
            else:
                result.append(value)
        return result
