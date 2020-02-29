# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class MailRenderMixin(models.AbstractModel):

    _name = 'mail.render.mixin'
    _description = 'Mail Render Mixin'

    model_object_field = fields.Many2one(
        'ir.model.fields', string="Field", store=False,
        help="Select target field from the related document model.\n"
            "If it is a relationship field you will be able to select "
            "a target field at the destination of the relationship.")
    sub_object = fields.Many2one(
        'ir.model', 'Sub-model', readonly=True, store=False,
        help="When a relationship field is selected as first field, "
            "this field shows the document model the relationship goes to.")
    sub_model_object_field = fields.Many2one(
        'ir.model.fields', 'Sub-field', store=False,
        help="When a relationship field is selected as first field, "
            "this field lets you select the target field within the "
            "destination document model (sub-model).")
    null_value = fields.Char('Default Value', store=False, help="Optional value to use if the target field is empty")
    copyvalue = fields.Char(
        'Placeholder Expression',store=False,
        help="Final placeholder expression, to be copy-pasted in the desired template field.")

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def _onchange_dynamic_placeholder(self):
        """ Generate the dynamic placeholder """
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one', 'one2many', 'many2many']:
                model = self.env['ir.model']._get(self.model_object_field.relation)
                if model:
                    self.sub_object = model.id
                    sub_field_name = self.sub_model_object_field.name
                    self.copyvalue = self._build_expression(self.model_object_field.name,
                                                            sub_field_name, self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self._build_expression(self.model_object_field.name, False, self.null_value or False)
        else:
            self.sub_object = False
            self.copyvalue = False
            self.sub_model_object_field = False
            self.null_value = False

    @api.model
    def _build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.

        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :param null_value: default value if the target value is empty
        :return: final placeholder expression """
        expression = ''
        if field_name:
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression        
