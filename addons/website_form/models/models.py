from openerp import tools
from openerp import models, fields, api


class website_form_config(models.Model):
    _inherit = 'website'
    website_form_enable_metadata = fields.Boolean('Write metadata',help="Enable writing metadata on form submit.")


class website_form_model(models.Model):
    _name = 'ir.model'
    _inherit = 'ir.model'

    website_form_access = fields.Boolean('Allowed to use in forms', help='Enable the form builder feature for this model.')
    website_form_default_field_id = fields.Many2one('ir.model.fields', 'Field for custom form data', domain="[('model', '=', model), ('ttype', '=', 'text')]", help="Specify the field wich will contain meta and custom form fields datas.")
    website_form_label = fields.Char("Label for form action", help="Form action label. Ex: crm.lead could be 'Send an e-mail' and project.issue could be 'Create an Issue'.")


    def all_inherited_model_ids(self):
        return [self.id] + [m.all_inherited_model_ids() for m in self.inherited_model_ids]

    @api.multi
    def get_authorized_fields(self):
        model = self.env[self.model]
        fields_get = model.fields_get()
        domain = [('model_id', 'in', self.all_inherited_model_ids()), ('website_form_blacklisted', '=', False)]

        for elem in self.env['ir.model.fields'].search(domain):
            if elem.website_form_blacklisted:
                fields_get.pop(elem.name, None)
        for key, val in model._inherits.iteritems():
            fields_get.pop(val,None)

        # Unrequire fields with default values
        default_values = model.default_get(fields_get.keys())
        for field in [f for f in fields_get if f in default_values]:
            fields_get[field]['required'] = False

        return fields_get


class website_form_model_fields(models.Model):
    """ fields configuration for form builder """
    _name = 'ir.model.fields'
    _inherit = 'ir.model.fields'

    website_form_blacklisted = fields.Boolean('Blacklisted in web forms', help='Blacklist this field for web forms')
