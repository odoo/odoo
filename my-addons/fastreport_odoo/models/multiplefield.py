from odoo import models, fields,api

class Multiplefield(models.Model):
    _name='multiple.field'


    select_field=fields.Many2many('ir.model.fields',string='关联字段',domain="[('model_id','=',field_model_id)]")

    field_model_id=fields.Integer()

    def select_fields(self):
        field_option_id=self.env.context.get('field_option_id',False)
        parent_id=self.env.context.get('parent_id',False)
        for field in self.select_field:
            if field.ttype == 'one2many' or field.ttype == 'many2one' or field.ttype == 'many2many':
                model_id=self.env['ir.model'].search([('model', '=', field['relation'])]).id
            else:
                model_id=False
            if self.env['field.option'].search(['&','|',('field_option_id','=',field_option_id),('parent_id','=',parent_id),('name_id','=',field.id)]):
                continue
            self.env['field.option'].create({
                'name': field.name,
                'name_id': field.id,
                'ttype': field.ttype,
                'relevance_model': model_id,
                'parent_id': parent_id,
                'field_option_id': field_option_id,
            })
        pass

