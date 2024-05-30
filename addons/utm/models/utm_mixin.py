# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import defaultdict
import itertools

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.http import request


class UtmMixin(models.AbstractModel):
    """ Mixin class for objects which can be tracked by marketing. """
    _name = 'utm.mixin'
    _description = 'UTM Mixin'

    @api.model
    def _selection_target_model(self):
        return [
            (model.model, model.name)
            for model
            in self.env['ir.model'].sudo().search([])
            if not model.is_transient()
        ]

    campaign_id = fields.Many2one('utm.campaign', 'Campaign', index='btree_not_null',
                                  help="This is a name that helps you keep track of your different campaign efforts, e.g. Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', 'Source', index='btree_not_null',
                                help="This is the source of the link, e.g. Search Engine, another domain, or name of email list")
    medium_id = fields.Many2one('utm.medium', 'Medium', index='btree_not_null',
                                help="This is the method of delivery, e.g. Postcard, Email, or Banner Ad")
    # This is the (optional) reference to the originating record (e.g: the social post, the mailing)
    utm_reference = fields.Reference(string='UTM Reference',
                                     selection='_selection_target_model',
                                     index=True)  # will be used extensively for statistics (e.g: how many leads did this mailing generate)

    @api.model
    def default_get(self, fields):
        values = super(UtmMixin, self).default_get(fields)

        # We ignore UTM for salesmen, except some requests that could be done as superuser_id to bypass access rights.
        if not self.env.is_superuser() and self.env.user.has_group('sales_team.group_sale_salesman'):
            return values

        for _url_param, field_name, cookie_name in self.env['utm.mixin'].tracking_fields():
            if field_name in fields:
                field = self._fields[field_name]
                value = False
                if request:
                    # ir_http dispatch saves the url params in a cookie
                    value = request.cookies.get(cookie_name)
                if field.type == 'many2one' and isinstance(value, str) and value:
                    # if we receive a string for a many2one, we search/create the id
                    record = self._find_or_create_record(field.comodel_name, value)
                    value = record.id
                elif field.type == 'reference' and isinstance(value, str) and value:
                    # sanitize the value first, the ORM will crash if ill-formatted
                    # we prefer to just void the field if so, as UTMs are optional
                    # see 'fields_reference#convert_to_cache'
                    try:
                        res_model, res_id = value.split(',')
                    except ValueError:
                        value = False
                    else:
                        if not res_model in self.env or not self.env[res_model].browse(int(res_id)).exists():
                            value = False
                if value:
                    values[field_name] = value
        return values

    def tracking_fields(self):
        # This function cannot be overridden in a model which inherit utm.mixin
        # Limitation by the heritage on AbstractModel
        # record_crm_lead.tracking_fields() will call tracking_fields() from module utm.mixin (if not overridden on crm.lead)
        # instead of the overridden method from utm.mixin.
        # To force the call of overridden method, we use self.env['utm.mixin'].tracking_fields() which respects overridden
        # methods of utm.mixin, but will ignore overridden method on crm.lead
        return [
            # ("URL_PARAMETER", "FIELD_NAME_MIXIN", "NAME_IN_COOKIES")
            ('utm_campaign', 'campaign_id', 'odoo_utm_campaign'),
            ('utm_source', 'source_id', 'odoo_utm_source'),
            ('utm_medium', 'medium_id', 'odoo_utm_medium'),
            ('utm_reference', 'utm_reference', 'odoo_utm_reference'),
        ]

    def _tracking_models(self):
        fnames = {fname for _, fname, _ in self.tracking_fields()}
        return {
            self._fields[fname].comodel_name
            for fname in fnames
            if fname in self._fields and self._fields[fname].type == "many2one"
        }

    @api.model
    def find_or_create_record(self, model_name, name):
        """ Version of ``_find_or_create_record`` used in frontend notably in
        website_links. For UTM models it calls _find_or_create_record. For other
        models (as through inheritance custom models could be used notably in
        website links) it simply calls a create. In the end it relies on
        standard ACLs, and is mainly a wrapper for UTM models.

        :return: id of newly created or found record. As the magic of call_kw
            for create is not called anymore we have to manually return an id
            instead of a recordset.
        """
        if model_name in self._tracking_models():
            record = self._find_or_create_record(model_name, name)
        else:
            record = self.env[model_name].create({self.env[model_name]._rec_name: name})
        return {'id': record.id, 'name': record.display_name}

    def _find_or_create_record(self, model_name, name):
        """Based on the model name and on the name of the record, retrieve the corresponding record or create it."""
        Model = self.env[model_name]

        cleaned_name = name.strip()
        if cleaned_name:
            record = Model.with_context(active_test=False).search([('name', '=ilike', cleaned_name)], limit=1)

        if not record:
            # No record found, create a new one
            record_values = {'name': cleaned_name}
            if 'is_auto_campaign' in record._fields:
                record_values['is_auto_campaign'] = True
            record = Model.create(record_values)

        return record

    @api.model
    def _get_unique_names(self, model_name, names):
        """Generate unique names for the given model.

        Take a list of names and return for each names, the new names to set
        in the same order (with a counter added if needed).

        E.G.
            The name "test" already exists in database
            Input: ['test', 'test [3]', 'bob', 'test', 'test']
            Output: ['test [2]', 'test [3]', 'bob', 'test [4]', 'test [5]']

        :param model_name: name of the model for which we will generate unique names
        :param names: list of names, we will ensure that each name will be unique
        :return: a list of new values for each name, in the same order
        """
        # Avoid conflicting with itself, otherwise each check at update automatically
        # increments counters
        skip_record_ids = self.env.context.get("utm_check_skip_record_ids") or []
        # Remove potential counter part in each names
        names_without_counter = {self._split_name_and_count(name)[0] for name in names}

        # Retrieve existing similar names
        search_domain = Domain.OR(Domain('name', 'ilike', name) for name in names_without_counter)
        if skip_record_ids:
            search_domain &= Domain('id', 'not in', skip_record_ids)
        existing_names = {vals['name'] for vals in self.env[model_name].search_read(search_domain, ['name'])}

        # Counter for each names, based on the names list given in argument
        # and the record names in database
        used_counters_per_name = {
            name: {
                self._split_name_and_count(existing_name)[1]
                for existing_name in existing_names
                if existing_name == name or existing_name.startswith(f'{name} [')
            } for name in names_without_counter
        }
        # Automatically incrementing counters for each name, will be used
        # to fill holes in used_counters_per_name
        current_counter_per_name = defaultdict(lambda: itertools.count(1))

        result = []
        for name in names:
            if not name:
                result.append(False)
                continue

            name_without_counter, asked_counter = self._split_name_and_count(name)
            existing = used_counters_per_name.get(name_without_counter, set())
            if asked_counter and asked_counter not in existing:
                count = asked_counter
            else:
                # keep going until the count is not already used
                for count in current_counter_per_name[name_without_counter]:
                    if count not in existing:
                        break
            existing.add(count)
            result.append(f'{name_without_counter} [{count}]' if count > 1 else name_without_counter)

        return result

    @staticmethod
    def _split_name_and_count(name):
        """
        Return the name part and the counter based on the given name.

        e.g.
            "Medium" -> "Medium", 1
            "Medium [1234]" -> "Medium", 1234
        """
        name = name or ''
        name_counter_re = r'(.*)\s+\[([0-9]+)\]'
        match = re.match(name_counter_re, name)
        if match:
            return match.group(1), int(match.group(2) or '1')
        return name, 1

    def _utm_ref(self, xml_id):
        """" Special "ref" implementation for utm records (utm.source/utm.medium).
        For xml_ids in 'SELF_REQUIRED_UTM_REF', we create them if they don't exist.

        This allows functional flows to use static UTM data records and keep clean
        statistics/reporting. """
        utm_record = self.env.ref(xml_id, raise_if_not_found=False)

        if not utm_record and xml_id in self.SELF_REQUIRED_UTM_REF:
            try:
                module, xml_name = xml_id.split('.')
            except ValueError:
                raise ValueError(f'Malformed xml_id: {xml_id}. Should be "module.name".')

            label, model = self.SELF_REQUIRED_UTM_REF[xml_id]
            utm_record = self.sudo().env[model].create({
                self.env[model]._rec_name: label
            })

            # create matching data record
            self.sudo().env['ir.model.data'].create({
                'name': xml_name,
                'module': module,
                'res_id': utm_record.id,
                'model': model,
            })

        return utm_record

    @property
    def SELF_REQUIRED_UTM_REF(self):
        return {
            'utm.utm_medium_direct': ('Direct', 'utm.medium'),
            'utm.utm_medium_email': ('Email', 'utm.medium'),
            'utm.utm_medium_social_media': ('Social Media', 'utm.medium'),
            'utm.utm_medium_website': ('Website', 'utm.medium'),
            'utm.utm_source_facebook': ('Facebook', 'utm.source'),
            'utm.utm_source_instagram': ('Instagram', 'utm.source'),
            'utm.utm_source_linkedin': ('LinkedIn', 'utm.source'),
            'utm.utm_source_mailing': ('Mass Mailing', 'utm.source'),
            'utm.utm_source_referral': ('Referral', 'utm.source'),
            'utm.utm_source_survey': ('Survey', 'utm.source'),
            'utm.utm_source_twitter': ('X', 'utm.source'),
            'utm.utm_source_youtube': ('YouTube', 'utm.source'),
        }
