# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo import models, fields, api
from odoo.http import request


class website_form_config(models.Model):
    _inherit = 'website'

    website_form_enable_metadata = fields.Boolean('Write metadata', help="Enable writing metadata on form submit.")

    def _website_form_last_record(self):
        if request and request.session.form_builder_model_model:
            return request.env[request.session.form_builder_model_model].browse(request.session.form_builder_id)
        return False


class website_form_model(models.Model):
    _name = 'ir.model'
    _inherit = 'ir.model'

    website_form_access = fields.Boolean('Allowed to use in forms', help='Enable the form builder feature for this model.')
    website_form_default_field_id = fields.Many2one('ir.model.fields', 'Field for custom form data', domain="[('model', '=', model), ('ttype', '=', 'text')]", help="Specify the field which will contain meta and custom form fields datas.")
    website_form_label = fields.Char("Label for form action", help="Form action label. Ex: crm.lead could be 'Send an e-mail' and project.issue could be 'Create an Issue'.")

    def _all_inherited_model_ids(self):
        return list(itertools.chain(
            [self.id],
            *(m._all_inherited_model_ids() for m in self.inherited_model_ids)
        ))

    def _get_form_writable_fields(self):
        """
        Restriction of "authorized fields" (fields which can be used in the
        form builders) to fields which have actually been opted into form
        builders and are writable. By default no field is writable by the
        form builder.
        """
        excluded = {
            field.name
            for field in self.env['ir.model.fields'].sudo().search([
                ('model_id', 'in', self._all_inherited_model_ids()),
                ('website_form_blacklisted', '=', True)
            ])
        }
        return {
            k: v for k, v in self.get_authorized_fields(self.model).iteritems()
            if k not in excluded
        }

    @api.model
    def get_authorized_fields(self, model_name):
        """ Return the fields of the given model name as a mapping like method `fields_get`. """
        model = self.env[model_name]
        fields_get = model.fields_get()

        for key, val in model._inherits.iteritems():
            fields_get.pop(val, None)

        # Unrequire fields with default values
        default_values = model.default_get(fields_get.keys())
        for field in [f for f in fields_get if f in default_values]:
            fields_get[field]['required'] = False

        # Remove readonly and magic fields
        MAGIC_FIELDS = models.MAGIC_COLUMNS + [model.CONCURRENCY_CHECK_FIELD]
        for field in fields_get.keys():
            if fields_get[field]['readonly'] or field in MAGIC_FIELDS:
                del fields_get[field]

        return fields_get


class website_form_model_fields(models.Model):
    """ fields configuration for form builder """
    _name = 'ir.model.fields'
    _inherit = 'ir.model.fields'

    @api.model_cr
    def init(self):
        # set all existing unset website_form_blacklisted fields to ``true``
        #  (so that we can use it as a whitelist rather than a blacklist)
        self._cr.execute('UPDATE ir_model_fields'
                         ' SET website_form_blacklisted=true'
                         ' WHERE website_form_blacklisted IS NULL')
        # add an SQL-level default value on website_form_blacklisted to that
        # pure-SQL ir.model.field creations (e.g. in _reflect) generate
        # the right default value for a whitelist (aka fields should be
        # blacklisted by default)
        self._cr.execute('ALTER TABLE ir_model_fields '
                         ' ALTER COLUMN website_form_blacklisted SET DEFAULT true')

    @api.model
    def formbuilder_whitelist(self, model, fields):
        """
        :param str model: name of the model on which to whitelist fields
        :param list(str) fields: list of fields to whitelist on the model
        :return: nothing of import
        """
        # postgres does *not* like ``in [EMPTY TUPLE]`` queries
        if not fields: return False

        # only allow users who can change the website structure
        if not self.env['res.users'].has_group('website.group_website_designer'):
            return False

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
        'Blacklisted in web forms', default=True, index=True, # required=True,
        help='Blacklist this field for web forms'
    )
