# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SMSTemplate(models.Model):
    "Templates for sending SMS"
    _name = "sms.template"
    _description = 'SMS Templates'

    @api.model
    def default_get(self, fields):
        res = super(SMSTemplate, self).default_get(fields)
        if not fields or 'model_id' in fields and not res.get('model_id') and res.get('model'):
            res['model_id'] = self.env['ir.model']._get(res['model']).id
        return res

    name = fields.Char('Name', translate=True)
    model_id = fields.Many2one(
        'ir.model', string='Applies to', required=True,
        domain=['&', ('is_mail_thread_sms', '=', True), ('transient', '=', False)],
        help="The type of document this template can be used with")
    model = fields.Char('Related Document Model', related='model_id.model', index=True, store=True, readonly=True)
    body = fields.Char('Body', translate=True, required=True)
    lang = fields.Char('Language', help="Use this field to either force a specific language (ISO code) or dynamically "
                                        "detect the language of your recipient by a placeholder expression "
                                        "(e.g. ${object.partner_id.lang})")
    # Use to create contextual action (same as for email template)
    sidebar_action_id = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                        help="Sidebar action to make this template available on records "
                                        "of the related document model")
    # Fake fields used to implement the placeholder assistant
    model_object_field = fields.Many2one('ir.model.fields', string="Field", store=False,
                                         help="Select target field from the related document model.\n"
                                              "If it is a relationship field you will be able to select "
                                              "a target field at the destination of the relationship.")
    sub_object = fields.Many2one('ir.model', 'Sub-model', readonly=True, store=False,
                                 help="When a relationship field is selected as first field, "
                                      "this field shows the document model the relationship goes to.")
    sub_model_object_field = fields.Many2one('ir.model.fields', 'Sub-field', store=False,
                                             help="When a relationship field is selected as first field, "
                                                  "this field lets you select the target field within the "
                                                  "destination document model (sub-model).")
    null_value = fields.Char('Default Value',  store=False, help="Optional value to use if the target field is empty")
    copyvalue = fields.Char('Placeholder Expression', store=False,
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

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {},
                       name=_("%s (copy)") % self.name)
        return super(SMSTemplate, self).copy(default=default)

    def action_create_sidebar_action(self):
        ActWindow = self.env['ir.actions.act_window']
        view = self.env.ref('sms.sms_composer_view_form')

        for template in self:
            button_name = _('Send SMS (%s)') % template.name
            action = ActWindow.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'sms.composer',
                # Add default_composition_mode to guess to determine if need to use mass or comment composer
                'context': "{'default_template_id' : %d, 'default_composition_mode': 'guess', 'default_res_ids': active_ids, 'default_res_id': active_id}" % (template.id),
                'view_mode': 'form',
                'view_id': view.id,
                'target': 'new',
                'binding_model_id': template.model_id.id,
            })
            template.write({'sidebar_action_id': action.id})
        return True

    def action_unlink_sidebar_action(self):
        for template in self:
            if template.sidebar_action_id:
                template.sidebar_action_id.unlink()
        return True

    def _get_context_lang_per_id(self, res_ids):
        self.ensure_one()
        if res_ids is None:
            return {None: self}

        if self.env.context.get('template_preview_lang'):
            lang = self.env.context.get('template_preview_lang')
            results = dict((res_id, self.with_context(lang=lang)) for res_id in res_ids)
        else:
            rendered_langs = self._render_template(self.lang, self.model, res_ids)
            results = dict((res_id, self.with_context(lang=lang) if lang else self)
                for res_id, lang in rendered_langs.items())

        return results

    def _get_ids_per_lang(self, res_ids):
        self.ensure_one()

        rids_to_tpl = self._get_context_lang_per_id(res_ids)
        tpl_to_rids = {}
        for res_id, template in rids_to_tpl.items():
            tpl_to_rids.setdefault(template._context.get('lang', self.env.user.lang), []).append(res_id)

        return tpl_to_rids

    def _get_translated_bodies(self, res_ids):
        """ return sms translated bodies into a dict {'res_id':'body'} """
        self.ensure_one()
        lang_to_rids = self._get_ids_per_lang(res_ids)
        all_bodies = {}
        for lang, rids in lang_to_rids.items():
            template = self.with_context(lang=lang)
            all_bodies.update(template._render_template(template.body, self.model, rids))
        return all_bodies

    @api.model
    def _render_template(self, template_txt, model, res_ids):
        """ Render the jinja template """
        return self.env['mail.template']._render_template(template_txt, model, res_ids)
