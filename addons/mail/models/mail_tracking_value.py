# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, tools


class MailTracking(models.Model):
    _name = 'mail.tracking.value'
    _description = 'Mail Tracking Value'

    # TDE CLEANME: why not a m2o to ir model field ?
    field = fields.Char('Changed Field', required=True, readonly=1)
    field_desc = fields.Char('Field Description', required=True, readonly=1)
    field_type = fields.Char('Field Type')

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

    mail_message_id = fields.Many2one('mail.message', 'Message ID', required=True, index=True, ondelete='cascade')

    def _create_multi_from_message(self, msg_id, values):
        def _format_value(vals, name, type):
            value = vals.get(name)
            if type == 'float':
                return value if value else 0.0
            elif type == 'timestamp':
                return value if value else None
            elif type == 'integer':
                if value is True:
                    return 1
                return value if value else 0
            return value

        def _prepare_insert_values(vals):
            return (vals['field'], vals['field_desc'], vals["field_type"], msg_id,
                    # old value
                    _format_value(vals, 'old_value_integer', 'integer'), _format_value(vals, 'old_value_float', 'float'),
                    _format_value(vals, 'old_value_monetary', 'float'), _format_value(vals, 'old_value_char', 'char'),
                    _format_value(vals, 'old_value_text', 'char'), _format_value(vals, 'old_value_datetime', 'timestamp'),
                    # new value
                    _format_value(vals, 'new_value_integer', 'integer'), _format_value(vals, 'new_value_float', 'float'),
                    _format_value(vals, 'new_value_monetary', 'float'), _format_value(vals, 'new_value_char', 'char'),
                    _format_value(vals, 'new_value_text', 'char'), _format_value(vals, 'new_value_datetime', 'timestamp'),
                    )
        sql_vals = [_prepare_insert_values(cmd[2]) for cmd in values if len(cmd) == 3 and cmd[0] == 0]
        field_names = ['field', 'field_desc', 'field_type', 'mail_message_id',
                       'old_value_integer', 'old_value_float', 'old_value_monetary', 'old_value_char', 'old_value_text', 'old_value_datetime',
                       'new_value_integer', 'new_value_float', 'new_value_monetary', 'new_value_char', 'new_value_text', 'new_value_datetime']
        query = """INSERT INTO mail_tracking_value ({}) VALUES {}""".format(
            ", ".join('"%s"' % name for name in field_names),
            ", ".join(["(%s)" % ", ".join("%s" for name in field_names)] * len(sql_vals))
        )
        # print('query', query)
        params = [val for vals in sql_vals for val in vals]
        # print('params', params)
        self.env.cr.execute(query, params)

    @api.model
    def create_tracking_values(self, initial_value, new_value, col_name, col_info):
        tracked = True
        values = {'field': col_name, 'field_desc': col_info['string'], 'field_type': col_info['type']}

        if col_info['type'] in ['integer', 'float', 'char', 'text', 'datetime', 'monetary']:
            values.update({
                'old_value_%s' % col_info['type']: initial_value,
                'new_value_%s' % col_info['type']: new_value
            })
        elif col_info['type'] == 'date':
            values.update({
                'old_value_datetime': initial_value and datetime.strftime(datetime.combine(datetime.strptime(initial_value, tools.DEFAULT_SERVER_DATE_FORMAT), datetime.min.time()), tools.DEFAULT_SERVER_DATETIME_FORMAT) or False,
                'new_value_datetime': new_value and datetime.strftime(datetime.combine(datetime.strptime(new_value, tools.DEFAULT_SERVER_DATE_FORMAT), datetime.min.time()), tools.DEFAULT_SERVER_DATETIME_FORMAT) or False,
            })
        elif col_info['type'] == 'boolean':
            values.update({
                'old_value_integer': initial_value,
                'new_value_integer': new_value
            })
        elif col_info['type'] == 'selection':
            values.update({
                'old_value_char': initial_value and dict(col_info['selection'])[initial_value] or '',
                'new_value_char': new_value and dict(col_info['selection'])[new_value] or ''
            })
        elif col_info['type'] == 'many2one':
            values.update({
                'old_value_integer': initial_value and initial_value.id or 0,
                'new_value_integer': new_value and new_value.id or 0,
                'old_value_char': initial_value and initial_value.name_get()[0][1] or '',
                'new_value_char': new_value and new_value.name_get()[0][1] or ''
            })
        else:
            tracked = False

        if tracked:
            return values
        return {}

    @api.multi
    def get_display_value(self, type):
        assert type in ('new', 'old')
        result = []
        for record in self:
            if record.field_type in ['integer', 'float', 'char', 'text', 'monetary']:
                result.append(getattr(record, '%s_value_%s' % (type, record.field_type)))
            elif record.field_type == 'datetime':
                if record['%s_value_datetime' % type]:
                    new_datetime = getattr(record, '%s_value_datetime' % type)
                    result.append('%sZ' % new_datetime)
                else:
                    result.append(record['%s_value_datetime' % type])
            elif record.field_type == 'date':
                if record['%s_value_datetime' % type]:
                    new_date = datetime.strptime(record['%s_value_datetime' % type], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
                    result.append(new_date.strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
                else:
                    result.append(record['%s_value_datetime' % type])
            elif record.field_type == 'boolean':
                result.append(bool(record['%s_value_integer' % type]))
            else:
                result.append(record['%s_value_char' % type])
        return result

    @api.multi
    def get_old_display_value(self):
        # grep : # old_value_integer | old_value_datetime | old_value_char
        return self.get_display_value('old')

    @api.multi
    def get_new_display_value(self):
        # grep : # new_value_integer | new_value_datetime | new_value_char
        return self.get_display_value('new')
