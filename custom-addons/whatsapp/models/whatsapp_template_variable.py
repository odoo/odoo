# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_join

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError


class WhatsAppTemplateVariable(models.Model):
    _name = 'whatsapp.template.variable'
    _description = 'WhatsApp Template Variable'
    _order = 'line_type desc, name, id'

    name = fields.Char(string="Placeholder", required=True)
    button_id = fields.Many2one('whatsapp.template.button', ondelete='cascade')
    wa_template_id = fields.Many2one(comodel_name='whatsapp.template', required=True, ondelete='cascade')
    model = fields.Char(string="Model Name", related='wa_template_id.model')

    line_type = fields.Selection([
        ('button', 'Button'),
        ('header', 'Header'),
        ('location', 'Location'),
        ('body', 'Body')], string="Variable location", required=True)
    field_type = fields.Selection([
        ('user_name', 'User Name'),
        ('user_mobile', 'User Mobile'),
        ('free_text', 'Free Text'),
        ('portal_url', 'Portal Link'),
        ('field', 'Field of Model')], string="Type", default='free_text', required=True)
    field_name = fields.Char(string="Field")
    demo_value = fields.Char(string="Sample Value", default="Sample Value", required=True)

    _sql_constraints = [
        (
            'name_type_template_unique',
            'UNIQUE(name, line_type, wa_template_id, button_id)',
            'Variable names must be unique for a given template'
        ),
    ]

    @api.constrains("field_type", "demo_value", "button_id")
    def _check_demo_values(self):
        if self.filtered(lambda var: var.field_type == 'free_text' and not var.demo_value):
            raise ValidationError(_('Free Text template variables must have a demo value.'))
        for var in self.filtered('button_id'):
            if not var.demo_value.startswith(var.button_id.website_url):
                raise ValidationError(_('Demo value of a dynamic url must start with the non-dynamic part'
                                        'of the url such as "https://www.example.com/menu?id=20"'))

    @api.constrains("field_type", "field_name")
    def _check_field_name(self):
        is_system = self.user_has_groups('base.group_system')
        failing = self.browse()
        to_check = self.filtered(lambda v: v.field_type == "field")
        missing = to_check.filtered(lambda v: not v.field_name)
        if missing:
            raise ValidationError(
                _("Field template variables %(var_names)s must be associated with a field.",
                  var_names=", ".join(missing.mapped("name")),
                )
            )
        for variable in to_check:
            model = self.env[variable.model]
            if not is_system:
                if not model.check_access_rights('read', raise_exception=False):
                    model_description = self.env['ir.model']._get(variable.model).display_name
                    raise ValidationError(
                        _("You can not select field of %(model)s.", model=model_description)
                    )
                safe_fields = model._get_whatsapp_safe_fields() if hasattr(model, '_get_whatsapp_safe_fields') else []
                if variable.field_name not in safe_fields:
                    raise ValidationError(
                        _("You are not allowed to use field %(field)s, contact your administrator.",
                          field=variable.field_name)
                    )
            try:
                model._find_value_from_field_path(variable.field_name)
            except UserError:
                failing += variable
        if failing:
            model_description = self.env['ir.model']._get(failing.mapped('model')[0]).display_name
            raise ValidationError(
                _("Variables %(field_names)s do not seem to be valid field path for model %(model_name)s.",
                  field_names=", ".join(failing.mapped("field_name")),
                  model_name=model_description,
                )
            )

    @api.constrains('name')
    def _check_name(self):
        for variable in self:
            if variable.line_type == 'location' and variable.name not in {'name', 'address', 'latitude', 'longitude'}:
                raise ValidationError(
                    _("Location variable should be 'name', 'address', 'latitude' or 'longitude'. Cannot parse '%(placeholder)s'",
                      placeholder=variable.name))
            elif variable.line_type == 'button' and variable.name != variable.button_id.name:
                raise ValidationError(_("Dynamic button variable name must be the same as its respective button's name"))
            elif variable.line_type in ('header', 'body') and not variable._extract_variable_index():
                raise ValidationError(
                    _('Template variable should be in format {{number}}. Cannot parse "%(placeholder)s"',
                      placeholder=variable.name))

    @api.constrains('button_id', 'line_type')
    def _check_button_id(self):
        for variable in self:
            if variable.line_type == 'button' and not variable.button_id:
                raise ValidationError(_('Button variables must be linked to a button.'))

    @api.depends('line_type', 'name')
    def _compute_display_name(self):
        type_names = dict(self._fields["line_type"]._description_selection(self.env))
        for variable in self:
            type_name = type_names[variable.line_type or 'body']
            variable.display_name = type_name if variable.line_type == 'header' else f'{type_name} - {variable.name}'

    @api.onchange('model')
    def _onchange_model_id(self):
        self.field_name = False

    @api.onchange('field_type')
    def _onchange_field_type(self):
        if self.field_type != 'field':
            self.field_name = False

    def _get_variables_value(self, record):
        value_by_name = {}
        user = self.env.user
        for variable in self:
            if variable.field_type == 'user_name':
                value = user.name
            elif variable.field_type == 'user_mobile':
                value = user.mobile
            elif variable.field_type == 'field':
                value = variable._find_value_from_field_chain(record)
            elif variable.field_type == 'portal_url':
                portal_url = record._whatsapp_get_portal_url()
                value = url_join(variable.get_base_url(), (portal_url or ''))
            else:
                value = variable.demo_value

            value_str = value and str(value) or ''
            if variable.button_id:
                value_by_name[f"button-{variable.button_id.name}"] = value_str
            else:
                value_by_name[f"{variable.line_type}-{variable.name}"] = value_str

        return value_by_name

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    def _find_value_from_field_chain(self, record):
        """Get the value of field, returning display_name(s) if the field is a model."""
        self.ensure_one()
        return record.sudo(False)._find_value_from_field_path(self.field_name)

    def _extract_variable_index(self):
        """ Extract variable index, located between '{{}}' markers. """
        self.ensure_one()
        try:
            return int(self.name.lstrip('{{').rstrip('}}'))
        except ValueError:
            return None
