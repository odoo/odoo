# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models


class MailTracking(models.Model):
    _name = 'mail.tracking.value'
    _description = 'Mail Tracking Value'
    _rec_name = 'field'
    _order = 'tracking_sequence asc'

    field = fields.Many2one('ir.model.fields', required=True, readonly=1, index=True, ondelete='cascade')
    field_desc = fields.Char('Field Description', required=True, readonly=1)
    field_type = fields.Char('Field Type')
    field_groups = fields.Char(compute='_compute_field_groups')

    old_value_integer = fields.Integer('Old Value Integer', readonly=1)
    old_value_float = fields.Float('Old Value Float', readonly=1)
    old_value_monetary = fields.Float('Old Value Monetary', readonly=1)
    old_value_char = fields.Char('Old Value Char', readonly=1)
    old_value_text = fields.Text('Old Value Text', readonly=1)
    old_value_datetime = fields.Datetime('Old Value DateTime', readonly=1)

    new_value_integer = fields.Integer('New Value Integer', readonly=1)
    new_value_float = fields.Float('New Value Float', readonly=1)
    new_value_monetary = fields.Float('New Value Monetary', readonly=1)
    new_value_char = fields.Char('New Value Char', readonly=1)
    new_value_text = fields.Text('New Value Text', readonly=1)
    new_value_datetime = fields.Datetime('New Value Datetime', readonly=1)

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, ondelete='set null',
        help="Used to display the currency when tracking monetary values")

    mail_message_id = fields.Many2one('mail.message', 'Message ID', required=True, index=True, ondelete='cascade')

    tracking_sequence = fields.Integer('Tracking field sequence', readonly=1, default=100)

    def _compute_field_groups(self):
        for tracking in self:
            model = self.env[tracking.mail_message_id.model]
            field = model._fields.get(tracking.field.name)
            tracking.field_groups = field.groups if field else 'base.group_system'

    @api.model
    def create_tracking_values(self, initial_value, new_value, col_name, col_info, tracking_sequence, model_name):
        tracked = True

        field = self.env['ir.model.fields']._get(model_name, col_name)
        if not field:
            return

        values = {'field': field.id, 'field_desc': col_info['string'], 'field_type': col_info['type'], 'tracking_sequence': tracking_sequence}

        if col_info['type'] in ['integer', 'float', 'char', 'text', 'datetime', 'monetary']:
            values.update({
                'old_value_%s' % col_info['type']: initial_value,
                'new_value_%s' % col_info['type']: new_value
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
            values.update({
                'old_value_integer': initial_value and initial_value.id or 0,
                'new_value_integer': new_value and new_value.id or 0,
                'old_value_char': initial_value and initial_value.sudo().name_get()[0][1] or '',
                'new_value_char': new_value and new_value.sudo().name_get()[0][1] or ''
            })
        else:
            tracked = False

        if tracked:
            return values
        return {}

    def _tracking_value_format(self):
        tracking_values = [{
            'changedField': tracking.field_desc,
            'id': tracking.id,
            'newValue': {
                'currencyId': tracking.currency_id.id,
                'fieldType': tracking.field_type,
                'value': tracking._get_new_display_value()[0],
            },
            'oldValue': {
                'currencyId': tracking.currency_id.id,
                'fieldType': tracking.field_type,
                'value': tracking._get_old_display_value()[0],
            },
        } for tracking in self]
        return tracking_values

    def _get_display_value(self, prefix):
        assert prefix in ('new', 'old')
        result = []
        for record in self:
            if record.field_type in ['integer', 'float', 'char', 'text', 'monetary']:
                result.append(record[f'{prefix}_value_{record.field_type}'])
            elif record.field_type == 'datetime':
                if record[f'{prefix}_value_datetime']:
                    new_datetime = record[f'{prefix}_value_datetime']
                    result.append(f'{new_datetime}Z')
                else:
                    result.append(record[f'{prefix}_value_datetime'])
            elif record.field_type == 'date':
                if record[f'{prefix}_value_datetime']:
                    new_date = record[f'{prefix}_value_datetime']
                    result.append(fields.Date.to_string(new_date))
                else:
                    result.append(record[f'{prefix}_value_datetime'])
            elif record.field_type == 'boolean':
                result.append(bool(record[f'{prefix}_value_integer']))
            else:
                result.append(record[f'{prefix}_value_char'])
        return result

    def _get_old_display_value(self):
        # grep : # old_value_integer | old_value_datetime | old_value_char
        return self._get_display_value('old')

    def _get_new_display_value(self):
        # grep : # new_value_integer | new_value_datetime | new_value_char
        return self._get_display_value('new')
