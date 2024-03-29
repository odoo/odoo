# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.http import request
from odoo.osv import expression


class UtmMixin(models.AbstractModel):
    """ Mixin class for objects which can be tracked by marketing. """
    _name = 'utm.mixin'
    _description = 'UTM Mixin'

    campaign_id = fields.Many2one('utm.campaign', 'Campaign',
                                  help="This is a name that helps you keep track of your different campaign efforts, e.g. Fall_Drive, Christmas_Special")
    source_id = fields.Many2one('utm.source', 'Source',
                                help="This is the source of the link, e.g. Search Engine, another domain, or name of email list")
    medium_id = fields.Many2one('utm.medium', 'Medium',
                                help="This is the method of delivery, e.g. Postcard, Email, or Banner Ad")

    @api.model
    def default_get(self, fields):
        values = super(UtmMixin, self).default_get(fields)

        # We ignore UTM for salesmen, except some requests that could be done as superuser_id to bypass access rights.
        if not self.env.is_superuser() and self.env.user.has_group('sales_team.group_sale_salesman'):
            return values

        for url_param, field_name, cookie_name in self.env['utm.mixin'].tracking_fields():
            if field_name in fields:
                field = self._fields[field_name]
                value = False
                if request:
                    # ir_http dispatch saves the url params in a cookie
                    value = request.httprequest.cookies.get(cookie_name)
                # if we receive a string for a many2one, we search/create the id
                if field.type == 'many2one' and isinstance(value, str) and value:
                    record = self._find_or_create_record(field.comodel_name, value)
                    value = record.id
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
        ]

    def _find_or_create_record(self, model_name, name):
        """Based on the model name and on the name of the record, retrieve the corresponding record or create it."""
        Model = self.env[model_name]

        record = Model.with_context(active_test=False).search([('name', '=', name)], limit=1)

        if not record:
            # No record found, create a new one
            record_values = {'name': name}
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

        # Remove potential counter part in each names
        names_without_counter = {_split_name_and_count(name)[0] for name in names}

        # Retrieve existing similar names
        seach_domain = expression.OR([[('name', 'ilike', name)] for name in names_without_counter])
        existing_names = {vals['name'] for vals in self.env[model_name].search_read(seach_domain, ['name'])}

        # Count for each names, based on the names list given in argument
        # and the record names in database
        count_per_names = defaultdict(lambda: 0)
        count_per_names.update({
            name: max((
                _split_name_and_count(existing_name)[1] + 1
                for existing_name in existing_names
                if existing_name == name or existing_name.startswith(f'{name} [')
            ), default=1)
            for name in names_without_counter
        })

        result = []
        for name in names:
            if not name:
                result.append(False)
                continue

            name_without_counter = _split_name_and_count(name)[0]
            counter = count_per_names[name_without_counter]
            result.append(f'{name_without_counter} [{counter}]' if counter > 1 else name)
            count_per_names[name_without_counter] += 1

        return result
