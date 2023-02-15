# -*- coding: utf-8 -*-

from ast import literal_eval
from collections import OrderedDict
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, MissingError
from odoo.osv import expression
from lxml import etree, html
import logging
from random import randint

_logger = logging.getLogger(__name__)


class WebsiteSnippetFilter(models.Model):
    _name = 'website.snippet.filter'
    _inherit = ['website.published.multi.mixin']
    _description = 'Website Snippet Filter'
    _order = 'name ASC'

    name = fields.Char(required=True, translate=True)
    action_server_id = fields.Many2one('ir.actions.server', 'Server Action', ondelete='cascade')
    field_names = fields.Char(help="A list of comma-separated field names", required=True)
    filter_id = fields.Many2one('ir.filters', 'Filter', ondelete='cascade')
    limit = fields.Integer(help='The limit is the maximum number of records retrieved', required=True)
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')
    model_name = fields.Char(string='Model name', compute='_compute_model_name')

    @api.depends('filter_id', 'action_server_id')
    def _compute_model_name(self):
        for snippet_filter in self:
            if snippet_filter.filter_id:
                snippet_filter.model_name = snippet_filter.filter_id.model_id
            else:  # self.action_server_id
                snippet_filter.model_name = snippet_filter.action_server_id.model_id.model

    @api.constrains('action_server_id', 'filter_id')
    def _check_data_source_is_provided(self):
        for record in self:
            if bool(record.action_server_id) == bool(record.filter_id):
                raise ValidationError(_("Either action_server_id or filter_id must be provided."))

    @api.constrains('limit')
    def _check_limit(self):
        """Limit must be between 1 and 16."""
        for record in self:
            if not 0 < record.limit <= 16:
                raise ValidationError(_("The limit must be between 1 and 16."))

    @api.constrains('field_names')
    def _check_field_names(self):
        for record in self:
            for field_name in record.field_names.split(","):
                if not field_name.strip():
                    raise ValidationError(_("Empty field name in %r") % (record.field_names))

    def _render(self, template_key, limit, search_domain=None, with_sample=False):
        """Renders the website dynamic snippet items"""
        self.ensure_one()
        assert '.dynamic_filter_template_' in template_key, _("You can only use template prefixed by dynamic_filter_template_ ")
        if search_domain is None:
            search_domain = []

        if self.website_id and self.env['website'].get_current_website() != self.website_id:
            return ''

        if self.model_name.replace('.', '_') not in template_key:
            return ''

        records = self._prepare_values(limit, search_domain)
        is_sample = with_sample and not records
        if is_sample:
            records = self._prepare_sample(limit)
        content = self.env['ir.qweb'].with_context(inherit_branding=False)._render(template_key, dict(
            records=records,
            is_sample=is_sample,
        ))
        return [etree.tostring(el, encoding='unicode') for el in html.fromstring('<root>%s</root>' % str(content)).getchildren()]

    def _prepare_values(self, limit=None, search_domain=None):
        """Gets the data and returns it the right format for render."""
        self.ensure_one()

        # The "limit" field is there to prevent loading an arbitrary number of
        # records asked by the client side. This here makes sure you can always
        # load at least 16 records as it is what the editor allows.
        max_limit = max(self.limit, 16)
        limit = limit and min(limit, max_limit) or max_limit

        if self.filter_id:
            filter_sudo = self.filter_id.sudo()
            domain = filter_sudo._get_eval_domain()
            if 'website_id' in self.env[filter_sudo.model_id]:
                domain = expression.AND([domain, self.env['website'].get_current_website().website_domain()])
            if 'company_id' in self.env[filter_sudo.model_id]:
                website = self.env['website'].get_current_website()
                domain = expression.AND([domain, [('company_id', 'in', [False, website.company_id.id])]])
            if 'is_published' in self.env[filter_sudo.model_id]:
                domain = expression.AND([domain, [('is_published', '=', True)]])
            if search_domain:
                domain = expression.AND([domain, search_domain])
            try:
                records = self.env[filter_sudo.model_id].with_context(**literal_eval(filter_sudo.context)).search(
                    domain,
                    order=','.join(literal_eval(filter_sudo.sort)) or None,
                    limit=limit
                )
                return self._filter_records_to_values(records)
            except MissingError:
                _logger.warning("The provided domain %s in 'ir.filters' generated a MissingError in '%s'", domain, self._name)
                return []
        elif self.action_server_id:
            try:
                return self.action_server_id.with_context(
                    dynamic_filter=self,
                    limit=limit,
                    search_domain=search_domain,
                ).sudo().run() or []
            except MissingError:
                _logger.warning("The provided domain %s in 'ir.actions.server' generated a MissingError in '%s'", search_domain, self._name)
                return []

    def _get_field_name_and_type(self, model, field_name):
        """
        Separates the name and the widget type

        @param model: Model to which the field belongs, without it type is deduced from field_name
        @param field_name: Name of the field possibly followed by a colon and a forced field type

        @return Tuple containing the field name and the field type
        """
        field_name, _, field_widget = field_name.partition(":")
        if not field_widget:
            field = model._fields.get(field_name)
            if field:
                field_type = field.type
            elif 'image' in field_name:
                field_type = 'image'
            elif 'price' in field_name:
                field_type = 'monetary'
            else:
                field_type = 'text'
        return field_name, field_widget or field_type

    def _get_filter_meta_data(self):
        """
        Extracts the meta data of each field

        @return OrderedDict containing the widget type for each field name
        """
        model = self.env[self.model_name]
        meta_data = OrderedDict({})
        for field_name in self.field_names.split(","):
            field_name, field_widget = self._get_field_name_and_type(model, field_name)
            meta_data[field_name] = field_widget
        return meta_data

    def _prepare_sample(self, length=6):
        """
        Generates sample data and returns it the right format for render.

        @param length: Number of sample records to generate

        @return Array of objets with a value associated to each name in field_names
        """
        if not length:
            return []
        records = self._prepare_sample_records(length)
        return self._filter_records_to_values(records, is_sample=True)

    def _prepare_sample_records(self, length):
        """
        Generates sample records.

        @param length: Number of sample records to generate

        @return List of of sample records
        """
        if not length:
            return []

        sample = []
        model = self.env[self.model_name]
        sample_data = self._get_hardcoded_sample(model)
        if sample_data:
            for index in range(0, length):
                single_sample_data = sample_data[index % len(sample_data)].copy()
                self._fill_sample(single_sample_data, index)
                sample.append(model.new(single_sample_data))
        return sample

    def _fill_sample(self, sample, index):
        """
        Fills the missing fields of a sample

        @param sample: Data structure to fill with values for each name in field_names
        @param index: Index of the sample within the dataset
        """
        meta_data = self._get_filter_meta_data()
        model = self.env[self.model_name]
        for field_name, field_widget in meta_data.items():
            if field_name not in sample and field_name in model:
                if field_widget in ('image', 'binary'):
                    sample[field_name] = None
                elif field_widget == 'monetary':
                    sample[field_name] = randint(100, 10000) / 10.0
                elif field_widget in ('integer', 'float'):
                    sample[field_name] = index
                else:
                    sample[field_name] = _('Sample %s', index + 1)
        return sample

    def _get_hardcoded_sample(self, model):
        """
        Returns a hard-coded sample

        @param model: Model of the currently rendered view

        @return Sample data records with field values
        """
        return [{}]

    def _filter_records_to_values(self, records, is_sample=False):
        """
        Extract the fields from the data source 'records' and put them into a dictionary of values

        @param records: Model records returned by the filter
        @param is_sample: True if conversion if for sample records

        @return List of dict associating the field value to each field name
        """
        self.ensure_one()
        meta_data = self._get_filter_meta_data()

        values = []
        model = self.env[self.model_name]
        Website = self.env['website']
        for record in records:
            data = {}
            for field_name, field_widget in meta_data.items():
                field = model._fields.get(field_name)
                if field and field.type in ('binary', 'image'):
                    if is_sample:
                        data[field_name] = record[field_name].decode('utf8') if field_name in record else '/web/image'
                    else:
                        data[field_name] = Website.image_url(record, field_name)
                elif field_widget == 'monetary':
                    model_currency = None
                    if field and field.type == 'monetary':
                        model_currency = record[field.get_currency_field(record)]
                    elif 'currency_id' in model._fields:
                        model_currency = record['currency_id']
                    if model_currency:
                        website_currency = self._get_website_currency()
                        data[field_name] = model_currency._convert(
                            record[field_name],
                            website_currency,
                            Website.get_current_website().company_id,
                            fields.Date.today()
                        )
                    else:
                        data[field_name] = record[field_name]
                else:
                    data[field_name] = record[field_name]

            data['call_to_action_url'] = 'website_url' in record and record['website_url']
            data['_record'] = record
            values.append(data)
        return values

    @api.model
    def _get_website_currency(self):
        company = self.env['website'].get_current_website().company_id
        return company.currency_id
