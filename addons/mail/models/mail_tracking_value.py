# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models


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
            return model._has_field_access(model_field, 'read') if model_field else False

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

    @api.model
    def _create_tracking_values(self, initial_value, new_value, col_name, col_info, record):
        """ Prepare values to create a mail.tracking.value. It prepares old and
        new value according to the field type.

        :param initial_value: field value before the change, could be text, int,
          date, datetime, ...;
        :param new_value: field value after the change, could be text, int,
          date, datetime, ...;
        :param str col_name: technical field name, column name (e.g. 'user_id);
        :param dict col_info: result of fields_get(col_name);
        :param <record> record: record on which tracking is performed, used for
          related computation e.g. finding currency of monetary fields;

        :return: a dict values valid for 'mail.tracking.value' creation;
        """
        field = self.env['ir.model.fields']._get(record._name, col_name)
        if not field:
            raise ValueError(f'Unknown field {col_name} on model {record._name}')

        values = {
            'field_id': field.id,
            'field_name': col_info['string'],
            'field_type': col_info['type'],
        }

        if col_info['type'] in {'integer', 'float', 'char', 'text', 'datetime'}:
            values.update({
                f'old_value_{col_info["type"]}': initial_value,
                f'new_value_{col_info["type"]}': new_value,
                'old_value': initial_value,
                'new_value': new_value,
            })
        elif col_info['type'] == 'monetary':
            values.update({
                'currency_id': record[col_info['currency_field']].id,
                'old_value_float': initial_value,
                'new_value_float': new_value,
                'old_value': initial_value,
                'new_value': new_value,
            })
        elif col_info['type'] == 'date':
            old_value = (initial_value and fields.Datetime.to_string(datetime.combine(fields.Date.from_string(initial_value), datetime.min.time()))) or False
            new_value = (new_value and fields.Datetime.to_string(datetime.combine(fields.Date.from_string(new_value), datetime.min.time()))) or False
            values.update({
                'old_value_datetime': old_value,
                'new_value_datetime': new_value,
                'old_value': initial_value,
                'new_value': new_value,
            })
        elif col_info['type'] == 'boolean':
            values.update({
                'old_value_integer': initial_value,
                'new_value_integer': new_value,
                'old_value': initial_value,
                'new_value': new_value,
            })
        elif col_info['type'] == 'selection':
            old_value = (initial_value and dict(col_info['selection']).get(initial_value, initial_value)) or ''
            new_value = (new_value and dict(col_info['selection'])[new_value]) or ''
            values.update({
                'old_value_char': old_value,
                'new_value_char': new_value,
            })
        elif col_info['type'] == 'many2one':
            # Can be:
            # - False value
            # - recordset, in case of standard field
            # - (id, display name), in case of properties (read format)
            if not initial_value:
                initial_value = (0, '')
            elif isinstance(initial_value, models.BaseModel):
                initial_value = (initial_value.id, initial_value.display_name)

            if not new_value:
                new_value = (0, '')
            elif isinstance(new_value, models.BaseModel):
                new_value = (new_value.id, new_value.display_name)

            values.update({
                'old_value_integer': initial_value[0],
                'new_value_integer': new_value[0],
                'old_value_char': initial_value[1],
                'new_value_char': new_value[1],
            })
        elif col_info['type'] in {'one2many', 'many2many', 'tags'}:
            # Can be:
            # - False value
            # - recordset, in case of standard field
            # - [(id, display name), ...], in case of properties (read format)
            model_name = self.env['ir.model']._get(field.relation).display_name
            if not initial_value:
                old_value_char = ''
            elif isinstance(initial_value, models.BaseModel):
                old_value_char = ', '.join(
                    value.display_name or self.env._(
                        'Unnamed %(record_model_name)s (%(record_id)s)',
                        record_model_name=model_name, record_id=value.id
                    )
                    for value in initial_value
                )
            else:
                old_value_char = ', '.join(value[1] for value in initial_value)
            if not new_value:
                new_value_char = ''
            elif isinstance(new_value, models.BaseModel):
                new_value_char = ', '.join(
                    value.display_name or self.env._(
                        'Unnamed %(record_model_name)s (%(record_id)s)',
                        record_model_name=model_name, record_id=value.id
                    )
                    for value in new_value
                )
            else:
                new_value_char = ', '.join(value[1] for value in new_value)

            values.update({
                'old_value_char': old_value_char,
                'new_value_char': new_value_char,
            })
        else:
            raise NotImplementedError(f'Unsupported tracking on field {field.name} (type {col_info["type"]}')

        return values

    @api.model
    def _create_tracking_values_property(self, initial_value, col_name, col_info, record):
        """Generate the values for the <mail.tracking.values> corresponding to a property."""
        property_col_info = col_info | {'type': initial_value['type'], 'selection': initial_value.get('selection')}

        field_info = {
            'desc': f"{col_info['string']}: {initial_value['string']}",
            'name': col_name,
            'property_string': initial_value['string'],
            'property_type': initial_value['type'],
            'type': property_col_info['type'],
        }
        value = initial_value.get('value', False)
        if value and initial_value['type'] == 'tags':
            value = [t for t in initial_value.get('tags', []) if t[0] in value]

        tracking_values = self.env['mail.tracking.value']._create_tracking_values(
            value, False, col_name, property_col_info, record)
        return {**tracking_values, 'field_type': col_info['type'], 'field_info': field_info}
