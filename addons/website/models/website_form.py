# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from lxml import etree

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    def _website_form_last_record(self):
        if request and request.session.get('form_builder_model_model'):
            return request.env[request.session['form_builder_model_model']].browse(request.session['form_builder_id'])
        return False


class IrModel(models.Model):
    _name = 'ir.model'
    _description = 'Models'
    _inherit = ['ir.model']

    website_form_access = fields.Boolean('Allowed to use in forms', help='Enable the form builder feature for this model.')
    website_form_default_field_id = fields.Many2one('ir.model.fields', 'Field for custom form data', domain="[('model', '=', model), ('ttype', '=', 'text')]", help="Specify the field which will contain meta and custom form fields datas.")
    website_form_label = fields.Char("Label for form action", help="Form action label. Ex: crm.lead could be 'Send an e-mail' and project.issue could be 'Create an Issue'.", translate=True)
    website_form_key = fields.Char(help='Used in FormBuilder Registry')

    def _get_form_writable_fields(self, property_origins=None):
        """
        Restriction of "authorized fields" (fields which can be used in the
        form builders) to fields which have actually been opted into form
        builders and are writable. By default no field is writable by the
        form builder.
        """
        if self.model == "mail.mail":
            included = {'email_from', 'email_to', 'email_cc', 'email_bcc', 'body', 'reply_to', 'subject'}
        else:
            included = {
                field.name
                for field in self.env['ir.model.fields'].sudo().search([
                    ('model_id', '=', self.id),
                    ('website_form_blacklisted', '=', False)
                ])
            }
        return {
            k: v for k, v in self.get_authorized_fields(self.model, property_origins).items()
            if k in included or '_property' in v and v['_property']['field'] in included
        }

    @api.model
    def get_authorized_fields(self, model_name, property_origins):
        """ Return the fields of the given model name as a mapping like method `fields_get`. """
        model = self.env[model_name]
        fields_get = model.fields_get()

        for val in model._inherits.values():
            fields_get.pop(val, None)

        # Unrequire fields with default values
        default_values = model.with_user(SUPERUSER_ID).default_get(list(fields_get))
        for field in [f for f in fields_get if f in default_values]:
            fields_get[field]['required'] = False

        # Remove readonly, JSON, and magic fields
        # Remove string domains which are supposed to be evaluated
        # (e.g. "[('product_id', '=', product_id)]")
        # Expand properties fields
        for field in list(fields_get):
            if 'domain' in fields_get[field] and isinstance(fields_get[field]['domain'], str):
                del fields_get[field]['domain']
            if fields_get[field].get('readonly') or field in models.MAGIC_COLUMNS or \
                    fields_get[field]['type'] in ('many2one_reference', 'json'):
                del fields_get[field]
            elif fields_get[field]['type'] == 'properties':
                property_field = fields_get[field]
                del fields_get[field]
                if property_origins:
                    # Add property pseudo-fields
                    # The properties of a property field are defined in a
                    # definition record (e.g. properties inside a project.task
                    # are defined inside its related project.project)
                    definition_record = property_field['definition_record']
                    if definition_record in property_origins:
                        definition_record_field = property_field['definition_record_field']
                        relation_field = fields_get[definition_record]
                        definition_model = self.env[relation_field['relation']]
                        if not property_origins[definition_record].isdigit():
                            # Do not fail on malformed forms.
                            continue
                        definition_record = definition_model.browse(int(property_origins[definition_record]))
                        properties_definitions = definition_record[definition_record_field]
                        for property_definition in properties_definitions:
                            if ((
                                property_definition['type'] in ['many2one', 'many2many']
                                and 'comodel' not in property_definition
                            ) or (
                                property_definition['type'] == 'selection'
                                and not property_definition['selection']
                            ) or (
                                property_definition['type'] == 'tags'
                                and not property_definition['tags']
                            ) or (property_definition['type'] == 'separator')):
                                # Ignore non-fully defined properties
                                continue
                            property_definition['_property'] = {
                                'field': field,
                            }
                            property_definition['required'] = False
                            if 'domain' in property_definition and isinstance(property_definition['domain'], str):
                                property_definition['domain'] = literal_eval(property_definition['domain'])
                                try:
                                    property_definition['domain'] = list(Domain(property_definition['domain']))
                                except Exception:
                                    # Ignore non-fully defined properties
                                    continue
                            fields_get[property_definition.get('name')] = property_definition

        return fields_get

    @api.model
    def get_compatible_form_models(self):
        if not self.env.user.has_group('website.group_website_restricted_editor'):
            return []
        return self.sudo().search_read(
            [('website_form_access', '=', True)],
            ['id', 'model', 'name', 'website_form_label', 'website_form_key'],
        )


class IrModelFields(models.Model):
    """ fields configuration for form builder """
    _description = 'Fields'
    _inherit = 'ir.model.fields'

    def init(self):
        # set all existing unset website_form_blacklisted fields to ``true``
        #  (so that we can use it as a whitelist rather than a blacklist)
        self.env.cr.execute('UPDATE ir_model_fields'
                         ' SET website_form_blacklisted=true'
                         ' WHERE website_form_blacklisted IS NULL')
        # add an SQL-level default value on website_form_blacklisted to that
        # pure-SQL ir.model.field creations (e.g. in _reflect) generate
        # the right default value for a whitelist (aka fields should be
        # blacklisted by default)
        self.env.cr.execute('ALTER TABLE ir_model_fields '
                         ' ALTER COLUMN website_form_blacklisted SET DEFAULT true')

    @api.ondelete(at_uninstall=False)
    def _check_if_used_in_website_form(self):
        """Prevent field deletion if used in a website form."""
        for field in self:
            for model_name, field_name in self.env['website']._get_html_fields():
                domain = [(field_name, 'ilike', f'data-model_name="{field.model}"')]
                records = self.env[model_name].with_context(active_test=False).search(domain)
                for record in records:
                    arch_parsed = etree.fromstring(record[field_name])
                    xpath_selector = f'//form[@data-model_name="{field.model}"]//*[@name="{field.name}"]'
                    if arch_parsed.xpath(xpath_selector):
                        raise ValidationError(_(
                            "The field '%(field)s' cannot be deleted because it is referenced in a website view.\n"
                            "Model: %(model)s\n"
                            "View: %(view)s",
                            field=field.name,
                            model=field.model,
                            view=record.display_name,
                        ))

    @api.model
    def formbuilder_whitelist(self, model, fields):
        """
        :param str model: name of the model on which to whitelist fields
        :param list(str) fields: list of fields to whitelist on the model
        :return: nothing of import
        """
        # postgres does *not* like ``in [EMPTY TUPLE]`` queries
        if not fields:
            return False

        # only allow users who can change the website structure
        if not self.env.user.has_group('website.group_website_designer'):
            return False

        unexisting_fields = [field for field in fields if field not in self.env[model]._fields.keys()]
        if unexisting_fields:
            raise ValueError("Unable to whitelist field(s) %r for model %r." % (unexisting_fields, model))

        # the ORM only allows writing on custom fields and will trigger a
        # registry reload once that's happened. We want to be able to
        # whitelist non-custom fields and the registry reload absolutely
        # isn't desirable, so go with a method and raw SQL
        self.env.cr.execute(
            "UPDATE ir_model_fields"
            " SET website_form_blacklisted=false"
            " WHERE model=%s AND name in %s", (model, tuple(fields)))
        return True

    website_form_blacklisted = fields.Boolean(
        'Blacklisted in web forms', default=True, index=True,
        help='Blacklist this field for web forms'
    )
