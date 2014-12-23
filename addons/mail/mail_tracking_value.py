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

    mail_message_id = fields.Many2one('mail.message', 'Message ID')
        
    @api.model
    def create_tracking_values(self, initial_value, new_value, col_name, col_info):
        record = self.browse()
    
        if col_info['type'] == 'boolean':
            record = super(mail_tracking_value, self).create(
                           {'field': col_name,
                            'field_desc': col_info['string'],
                            'old_value_boolean': initial_value,
                            'new_value_boolean': new_value})
         
        elif col_info['type'] == 'integer':
            record = super(mail_tracking_value, self).create(
                        {'field': col_name,
                         'field_desc': col_info['string'],
                         'old_value_integer': initial_value,
                         'new_value_integer': new_value})

        elif col_info['type'] == 'float':
            record = super(mail_tracking_value, self).create(
                           {'field': col_name,
                            'field_desc': col_info['string'],
                            'old_value_float': initial_value,
                            'new_value_float': new_value})

        elif col_info['type'] == 'char':
            record = super(mail_tracking_value, self).create(
                           {'field': col_name,
                            'field_desc': col_info['string'],
                            'old_value_char': initial_value,
                            'new_value_char': new_value})

        elif col_info['type'] == 'text':
            record = super(mail_tracking_value, self).create(
                           {'field': col_name,
                            'field_desc': col_info['string'],
                            'old_value_text': initial_value,
                            'new_value_text': new_value})

        elif col_info['type'] == 'datetime':
            record = super(mail_tracking_value, self).create(
                           {'field': col_name,
                            'field_desc': col_info['string'],
                            'old_value_datetime': initial_value,
                            'new_value_datetime': new_value})

        elif col_info['type'] == 'date':
            record = super(mail_tracking_value, self).create(
                           {'field': col_name,
                            'field_desc': col_info['string'],
                            'old_value_date': initial_value,
                            'new_value_date': new_value})

        elif col_info['type'] == 'selection':
            if not initial_value:
                record = super(mail_tracking_value, self).create(
                               {'field': col_name,
                                'field_desc': col_info['string'],
                                'old_value_char': '',
                                'new_value_char': dict(col_info['selection'])[new_value]})
            elif not new_value:
                record = super(mail_tracking_value, self).create(
                               {'field': col_name,
                                'field_desc': col_info['string'],
                                'old_value_char': dict(col_info['selection'])[initial_value],
                                'new_value_char': ''})
            else:
                record = super(mail_tracking_value, self).create(
                               {'field': col_name,
                                'field_desc': col_info['string'],
                                'old_value_char': dict(col_info['selection'])[initial_value],
                                'new_value_char': dict(col_info['selection'])[new_value]})

        elif col_info['type'] == 'many2one':
            if not initial_value:
                record = super(mail_tracking_value, self).create(
                               {'field': col_name,
                                'field_desc': col_info['string'],
                                'old_value_char': '',
                                'new_value_char': new_value.name_get()[0][1]})
            elif not new_value:
                record = super(mail_tracking_value, self).create(
                               {'field': col_name,
                                'field_desc': col_info['string'],
                                'old_value_char': initial_value.name_get()[0][1],
                                'new_value_char': ''})
            else:
                record = super(mail_tracking_value, self).create(
                               {'field': col_name,
                                'field_desc': col_info['string'],
                                'old_value_char': initial_value.name_get()[0][1],
                                'new_value_char': new_value.name_get()[0][1]})

        elif col_info['type'] == 'function':
            print "type function"
            # ??
            # ??
            # ??

        return record.ids

        
    @api.model
    def update_message_id(self, msg_id):
        return self.write({'mail_message_id': msg_id})




