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

        values = {'field_id': field.id}

        if col_info['type'] in {'integer', 'float', 'char', 'text', 'datetime'}:
            values.update({
                f'old_value_{col_info["type"]}': initial_value,
                f'new_value_{col_info["type"]}': new_value
            })
        elif col_info['type'] == 'monetary':
            values.update({
                'currency_id': record[col_info['currency_field']].id,
                'old_value_float': initial_value,
                'new_value_float': new_value
            })
        elif col_info['type'] == 'date':
            values.update({
                'old_value_datetime': initial_value and fields.Datetime.to_string(datetime.combine(fields.Date.from_string(initial_value), datetime.min.time())) or False,
                'new_value_datetime': new_value and fields.Datetime.to_string(datetime.combine(fields.Date.from_string(new_value), datetime.min.time())) or False,
            })
        elif col_info['type'] == 'boolean':
            values.update({
                'old_value_integer': initial_value,
                'new_value_integer': new_value
            })
        elif col_info['type'] == 'selection':
            values.update({
                'old_value_char': initial_value and dict(col_info['selection']).get(initial_value, initial_value) or '',
                'new_value_char': new_value and dict(col_info['selection'])[new_value] or ''
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
                'new_value_char': new_value[1]
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
