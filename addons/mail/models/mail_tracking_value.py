# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models


class MailTracking(models.Model):
    _name = 'mail.tracking.value'
    _description = 'Mail Tracking Value'
    _rec_name = 'field'
    _order = 'tracking_sequence asc'

    field = fields.Many2one('ir.model.fields', required=True, readonly=True, index=True, ondelete='cascade')
    field_desc = fields.Char('Field Description', required=True, readonly=True)
    field_type = fields.Char('Field Type')
    field_groups = fields.Char(compute='_compute_field_groups')

    old_value_integer = fields.Integer('Old Value Integer', readonly=True)
    old_value_float = fields.Float('Old Value Float', readonly=True)
    old_value_monetary = fields.Float('Old Value Monetary', readonly=True)
    old_value_char = fields.Char('Old Value Char', readonly=True)
    old_value_text = fields.Text('Old Value Text', readonly=True)
    old_value_datetime = fields.Datetime('Old Value DateTime', readonly=True)

    new_value_integer = fields.Integer('New Value Integer', readonly=True)
    new_value_float = fields.Float('New Value Float', readonly=True)
    new_value_monetary = fields.Float('New Value Monetary', readonly=True)
    new_value_char = fields.Char('New Value Char', readonly=True)
    new_value_text = fields.Text('New Value Text', readonly=True)
    new_value_datetime = fields.Datetime('New Value Datetime', readonly=True)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, ondelete='set null',
        help="Used to display the currency when tracking monetary values")

    mail_message_id = fields.Many2one('mail.message', 'Message ID', required=True, index=True, ondelete='cascade')

    tracking_sequence = fields.Integer('Tracking field sequence', readonly=True, default=100)

    @api.depends('mail_message_id', 'field')
    def _compute_field_groups(self):
        for tracking in self:
            model = self.env[tracking.mail_message_id.model]
            field = model._fields.get(tracking.field.name)
            tracking.field_groups = field.groups if field else 'base.group_system'

    @api.model
    def _create_tracking_values(self, initial_value, new_value, col_name, col_info, tracking_sequence, record):
        """ Prepare values to create a mail.tracking.value. It prepares old and
        new value according to the field type.

        :param initial_value: field value before the change, could be text, int,
          date, datetime, ...;
        :param new_value: field value after the change, could be text, int,
          date, datetime, ...;
        :param str col_name: technical field name, column name (e.g. 'user_id);
        :param dict col_info: result of fields_get(col_name);
        :param int tracking_sequence: sequence used for ordering tracking
          value display;
        :param <record> record: record on which tracking is performed, used for
          related computation e.g. finding currency of monetary fields;

        :return: a dict values valid for 'mail.tracking.value' creation;
        """
        tracked = True

        field = self.env['ir.model.fields']._get(record._name, col_name)
        if not field:
            return

        values = {'field': field.id, 'field_desc': col_info['string'], 'field_type': col_info['type'], 'tracking_sequence': tracking_sequence}

        if col_info['type'] in {'integer', 'float', 'char', 'text', 'datetime', 'monetary'}:
            values.update({
                f'old_value_{col_info["type"]}': initial_value,
                f'new_value_{col_info["type"]}': new_value
            })
            if col_info['type'] == 'monetary':
                values['currency_id'] = record[col_info['currency_field']].id
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
            values.update({
                'old_value_integer': initial_value.id if initial_value else 0,
                'new_value_integer': new_value.id if new_value else 0,
                'old_value_char': initial_value.display_name if initial_value else '',
                'new_value_char': new_value.display_name if new_value else ''
            })
        elif col_info['type'] in {'one2many', 'many2many'}:
            values.update({
                'old_value_char': ', '.join(initial_value.mapped('display_name')) if initial_value else '',
                'new_value_char': ', '.join(new_value.mapped('display_name')) if new_value else '',
            })
        else:
            tracked = False

        if tracked:
            return values
        return {}

    def _tracking_value_format(self):
        """ Return structure and formatted data structure to be used by chatter
        to display tracking values.

        :return list: for each tracking value in self, their formatted display
          values given as a dict;
        """
        formatted = []
        for tracking in self:
            formatted.append({
                'changedField': tracking.field_desc,
                'id': tracking.id,
                'fieldName': tracking.field.name,
                'fieldType': tracking.field_type,
                'newValue': {
                    'currencyId': tracking.currency_id.id,
                    'value': tracking._format_display_value(new=True)[0],
                },
                'oldValue': {
                    'currencyId': tracking.currency_id.id,
                    'value': tracking._format_display_value(new=False)[0],
                },
            })
        return formatted

    def _format_display_value(self, new=True):
        """ Format value of 'mail.tracking.value', according to the field type.

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
            'monetary': ('old_value_monetary', 'new_value_monetary'),
            'text': ('old_value_text', 'new_value_text'),
        }

        result = []
        for record in self:
            ftype = record.field_type
            value_fname = field_mapping.get(
                ftype, ('old_value_char', 'new_value_char')
            )[bool(new)]
            value = record[value_fname]

            if ftype in {'integer', 'float', 'char', 'text', 'monetary'}:
                result.append(value)
            elif ftype in {'date', 'datetime'}:
                if not record[value_fname]:
                    result.append(value)
                elif ftype == 'date':
                    result.append(fields.Date.to_string(value))
                else:
                    result.append(f'{value}Z')
            elif ftype == 'boolean':
                result.append(bool(value))
            else:
                result.append(value)
        return result
