# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class SMSTemplate(models.Model):
    "Templates for sending SMS"
    _name = "sms.template"
    _description = 'SMS Templates'

    name = fields.Char()
    model_id = fields.Many2one('ir.model', 'Applies to', help="The type of document this template can be used with")
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    body = fields.Char('Body', translate=True, required=True)
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                        help="Sidebar action to make this template available on records "
                                             "of the related document model")

    # Fake fields used to implement the placeholder assistant
    model_object_field = fields.Many2one('ir.model.fields', string="Field",
                                         help="Select target field from the related document model.\n"
                                              "If it is a relationship field you will be able to select "
                                              "a target field at the destination of the relationship.")
    sub_object = fields.Many2one('ir.model', 'Sub-model', readonly=True,
                                 help="When a relationship field is selected as first field, "
                                      "this field shows the document model the relationship goes to.")
    sub_model_object_field = fields.Many2one('ir.model.fields', 'Sub-field',
                                             help="When a relationship field is selected as first field, "
                                                  "this field lets you select the target field within the "
                                                  "destination document model (sub-model).")
    null_value = fields.Char('Default Value', help="Optional value to use if the target field is empty")
    copyvalue = fields.Char('Placeholder Expression',
                            help="Final placeholder expression, to be copy-pasted in the desired template field.")

    @api.model
    def _render_template(self, template_txt, model, res_ids):
        """ Render the template using the rendering from mail.template """
        return self.env['mail.template']._render_template(template_txt, model, res_ids)


    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def _onchange_dynamic_placeholder(self):
        """ Generate the dynamic placeholder """
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one', 'one2many', 'many2many']:
                model = self.env['ir.model']._get(self.model_object_field.relation)
                if model:
                    self.sub_object = model.id
                    sub_field_name = self.sub_model_object_field and self.sub_model_object_field.name or False
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

    @api.multi
    def create_action(self):
        """
        Create contextual action on the model 'model_id' to open SMS wizard with
        the template_id.
        """
        for record in self:
            button_name = _('Send SMS Text Message (%s)') % record.name
            action = self.env['ir.actions.act_window'].create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'sms.compose.message',
                'src_model': record.model_id.model,
                'view_type': 'form',
                'context': "{'default_composition_mode': 'mass_sms', 'default_template_id' : %d}" % (record.id),
                'view_mode': 'form',
                'view_id': self.env.ref('sms.send_sms_view_form').id,
                'target': 'new',
                'binding_model_id': record.model_id.id,
            })
            record.write({'ref_ir_act_window': action.id})
        return True

    @api.multi
    def unlink_action(self):
        """
        Delete the contextual action linked to the template.
        """
        for record in self:
            if record.ref_ir_act_window:
                record.ref_ir_act_window.unlink()
        return True
