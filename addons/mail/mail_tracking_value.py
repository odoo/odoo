from openerp import models, fields, api
from openerp.osv import orm
        
class mail_tracking_value(models.Model):	
    _name = 'mail.tracking.value'
    _description = 'Mail Tracking Value'

    field = fields.Char('Changed Field', required=True, readonly=1)
    field_desc = fields.Char('Field Description', required=True, readonly=1)

    old_value_boolean = fields.Boolean('Old Value Boolean', readonly=1)
    old_value_integer = fields.Integer('Old Value Integer', readonly=1)
    old_value_float = fields.Float('Old Value Float', readonly=1)
    old_value_char = fields.Char('Old Value Char', readonly=1)
    old_value_text = fields.Text('Old Value Text', readonly=1)   
    old_value_datetime = fields.Datetime('Old Value DateTime', readonly=1)
    old_value_date = fields.Date('Old Value Date', readonly=1)

    new_value_boolean = fields.Boolean('New Value Boolean', readonly=1)
    new_value_integer = fields.Integer('New Value Integer', readonly=1)
    new_value_float = fields.Float('New Value Float', readonly=1)
    new_value_char = fields.Char('New Value Char', readonly=1)
    new_value_text = fields.Text('New Value Text', readonly=1) 
    new_value_datetime = fields.Datetime('New Value Datetime', readonly=1)
    new_value_date = fields.Date('New Value Date', readonly=1)

    mail_message_ids = fields.Many2many('mail.message')
        
    @api.model
    def create_tracking_values(self, record, initial_values, tracked_fields):

        initial = initial_values[record.id]
        records = self.browse()

        for col_name, col_info in tracked_fields.items():
            initial_value = initial[col_name]
            new_value = getattr(record, col_name)

            if new_value != initial_value and (new_value or initial_value): 
               
                if col_info['type'] == 'boolean':
                    rec = super(mail_tracking_value, self).create(
                                {'field': col_name,
                                 'field_desc': col_info['string'],
                                 'old_value_boolean': initial_value,
                                 'new_value_boolean': new_value})
                 
                elif col_info['type'] == 'integer':
                    rec = super(mail_tracking_value, self).create(
                                {'field': col_name,
                                 'field_desc': col_info['string'],
                                 'old_value_integer': initial_value,
                                 'new_value_integer': new_value})

                elif col_info['type'] == 'float':
                    rec = super(mail_tracking_value, self).create(
                                {'field': col_name,
                                 'field_desc': col_info['string'],
                                 'old_value_float': initial_value,
                                 'new_value_float': new_value})

                elif col_info['type'] == 'char':
                    rec = super(mail_tracking_value, self).create(
                                {'field': col_name,
                                 'field_desc': col_info['string'],
                                 'old_value_char': initial_value,
                                 'new_value_char': new_value})

                elif col_info['type'] == 'text':
                    rec = super(mail_tracking_value, self).create(
                                {'field': col_name,
                                 'field_desc': col_info['string'],
                                 'old_value_text': initial_value,
                                 'new_value_text': new_value})

                elif col_info['type'] == 'datetime':
                    rec = super(mail_tracking_value, self).create(
                                {'field': col_name,
                                 'field_desc': col_info['string'],
                                 'old_value_datetime': initial_value,
                                 'new_value_datetime': new_value})

                elif col_info['type'] == 'date':
                    rec = super(mail_tracking_value, self).create(
                                {'field': col_name,
                                 'field_desc': col_info['string'],
                                 'old_value_date': initial_value,
                                 'new_value_date': new_value})

                elif col_info['type'] == 'selection':
                    if not initial_value:
                        rec = super(mail_tracking_value, self).create(
                                    {'field': col_name,
                                     'field_desc': col_info['string'],
                                     'old_value_char': '',
                                     'new_value_char': dict(col_info['selection'])[new_value]})
                    elif not new_value:
                        rec = super(mail_tracking_value, self).create(
                                    {'field': col_name,
                                     'field_desc': col_info['string'],
                                     'old_value_char': dict(col_info['selection'])[initial_value],
                                     'new_value_char': ''})
                    else:
                        rec = super(mail_tracking_value, self).create(
                                    {'field': col_name,
                                     'field_desc': col_info['string'],
                                     'old_value_char': dict(col_info['selection'])[initial_value],
                                     'new_value_char': dict(col_info['selection'])[new_value]})

                elif col_info['type'] == 'many2one':
                    if not initial_value:
                        rec = super(mail_tracking_value, self).create(
                                    {'field': col_name,
                                     'field_desc': col_info['string'],
                                     'old_value_char': '',
                                     'new_value_char': new_value.name_get()[0][1]})
                    elif not new_value:
                        rec = super(mail_tracking_value, self).create(
                                    {'field': col_name,
                                     'field_desc': col_info['string'],
                                     'old_value_char': initial_value.name_get()[0][1],
                                     'new_value_char': ''})
                    else:
                        rec = super(mail_tracking_value, self).create(
                                    {'field': col_name,
                                     'field_desc': col_info['string'],
                                     'old_value_char': initial_value.name_get()[0][1],
                                     'new_value_char': new_value.name_get()[0][1]})

                elif col_info['type'] == 'function':
                    print "type function"
                    # ??
                    # ??
                    # ??

                records = records + rec

        return records.ids
        
    @api.model
    def update_message_ids(self, msg_ids):
        return self.write({'mail_message_ids': [(4, mid) for mid in msg_ids]})




