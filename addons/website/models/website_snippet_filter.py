# -*- coding: utf-8 -*-

from ast import literal_eval
from collections import OrderedDict
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, MissingError
from odoo.osv import expression
from odoo.tools import html_escape as escape
from lxml import etree as ET
import logging
from random import randint

_logger = logging.getLogger(__name__)


class WebsiteSnippetFilter(models.Model):
    _name = 'website.snippet.filter'
    _inherit = ['website.published.multi.mixin']
    _description = 'Website Snippet Filter'
    _order = 'name ASC'

    name = fields.Char(required=True)
    action_server_id = fields.Many2one('ir.actions.server', 'Server Action', ondelete='cascade')
    field_names = fields.Char(help="A list of comma-separated field names", required=True)
    filter_id = fields.Many2one('ir.filters', 'Filter', ondelete='cascade')
    limit = fields.Integer(help='The limit is the maximum number of records retrieved', required=True)
    website_id = fields.Many2one('website', string='Website', ondelete='cascade')

    @api.model
    def escape_falsy_as_empty(self, s):
        return escape(s) if s else ''

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

    def render(self, template_key, limit, search_domain=None, with_sample=False):
        """Renders the website dynamic snippet items"""
        self.ensure_one()
        assert '.dynamic_filter_template_' in template_key, _("You can only use template prefixed by dynamic_filter_template_ ")
        if search_domain is None:
            search_domain = []

        if self.website_id and self.env['website'].get_current_website() != self.website_id:
            return ''

        records = self._prepare_values(limit, search_domain)
        is_sample = with_sample and not records
        if is_sample:
            records = self._prepare_sample()
        View = self.env['ir.ui.view'].sudo().with_context(inherit_branding=False)
        content = View._render_template(template_key, dict(records=records, is_sample=is_sample)).decode('utf-8')
        return [ET.tostring(el) for el in ET.fromstring('<root>%s</root>' % content).getchildren()]

    def _prepare_values(self, limit=None, search_domain=None):
        """Gets the data and returns it the right format for render."""
        self.ensure_one()
        limit = limit and min(limit, self.limit) or self.limit
        if self.filter_id:
            filter_sudo = self.filter_id.sudo()
            domain = filter_sudo._get_eval_domain()
            if 'is_published' in self.env[filter_sudo.model_id]:
                domain = expression.AND([domain, [('is_published', '=', True)]])
            if search_domain:
                domain = expression.AND([domain, search_domain])
            try:
                records = self.env[filter_sudo.model_id].search(
                    domain,
                    order=','.join(literal_eval(filter_sudo.sort)) or None,
                    limit=limit
                )
                return self._filter_records_to_dict_values(records)
            except MissingError:
                _logger.warning("The provided domain %s in 'ir.filters' generated a MissingError in '%s'", domain, self._name)
                return []
        elif self.action_server_id:
            try:
                return self.action_server_id.with_context(
                    dynamic_filter=self,
                    limit=limit,
                    search_domain=search_domain,
                    get_rendering_data_structure=self._get_rendering_data_structure,
                ).sudo().run()
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
        field = model._fields.get(field_name) if model else None
        if field:
            field_type = field.type
        elif 'image' in field_name:
            field_type = 'image'
        elif 'price' in field_name:
            field_type = 'monetary'
        else:
            field_type = 'text'
        return field_name, field_widget or field_type

    def _prepare_sample(self, length=4):
        """
        Generates sample data and returns it the right format for render.

        @param length: Number of sample records to generate

        @return Array of objets with a value associated to each name in field_names
        """
        if not length:
            return []
        sample = []
        model = self.env[self.filter_id.model_id] if self.filter_id else (
            self.action_server_id.model_id if self.action_server_id else None)
        sample_data = self._get_hardcoded_sample(model)
        for index in range(0, length):
            single_sample_data = sample_data[index % len(sample_data)].copy()
            self._fill_sample(single_sample_data, model, index)
            data = self._get_rendering_data_structure()
            for field_name in self.field_names.split(","):
                field_name, field_widget = self._get_field_name_and_type(model, field_name)
                value = single_sample_data[field_name]
                if field_widget == 'binary':
                    data['image_fields'][field_name] = self.escape_falsy_as_empty(value)
                elif field_widget == 'image':
                    data['image_fields'][field_name] = value
                elif field_widget == 'monetary':
                    FieldMonetary = self.env['ir.qweb.field.monetary']
                    website_currency = self._get_website_currency()
                    data['fields'][field_name] = FieldMonetary.value_to_html(
                        value,
                        {'display_currency': website_currency}
                    )
                elif 'ir.qweb.field.%s' % field_widget in self.env:
                    data['fields'][field_name] = self.env['ir.qweb.field.%s' % field_widget].value_to_html(
                        value, {})
                else:
                    data['fields'][field_name] = self.escape_falsy_as_empty(value)
            data['fields']['call_to_action_url'] = ''
            sample.append(data)
        return sample

    def _fill_sample(self, sample, model, index):
        """
        Fills the sample for the given model

        @param sample: Data structure to fill with values for each name in field_names
        @param model: Model to which the sample belongs
        @param index: Index of the sample within the dataset
        """
        for field_name in self.field_names.split(","):
            field_name, field_widget = self._get_field_name_and_type(model, field_name)
            if field_name not in sample:
                if field_widget == 'binary':
                    sample[field_name] = None
                elif field_widget == 'image':
                    sample[field_name] = '/web/image'
                elif field_widget == 'monetary':
                    sample[field_name] = randint(100, 10000) / 10.0
                elif field_widget in ('integer', 'float'):
                    sample[field_name] = index
                else:
                    sample[field_name] = _('Sample %s', index + 1)

    def _get_hardcoded_sample(self, model):
        """
        Returns a hard-coded sample

        @param model: Model of the currently rendered view

        @return Sample data records with field values
        """
        return [{}]

    @api.model
    def _get_rendering_data_structure(self):
        return {
            'fields': OrderedDict({}),
            'image_fields': OrderedDict({}),
        }

    def _filter_records_to_dict_values(self, records):
        """Extract the fields from the data source and put them into a dictionary of values

            [{
                'fields':
                    OrderedDict([
                        ('name', 'Afghanistan'),
                        ('code', 'AF'),
                    ]),
                'image_fields':
                    OrderedDict([
                        ('image', '/web/image/res.country/3/image?unique=5d9b44e')
                    ]),
             }, ... , ...]

        """

        self.ensure_one()
        values = []
        model = self.env[self.filter_id.model_id]
        Website = self.env['website']
        for record in records:
            data = self._get_rendering_data_structure()
            for field_name in self.field_names.split(","):
                field_name, _, field_widget = field_name.partition(":")
                field = model._fields.get(field_name)
                field_widget = field_widget or field.type
                if field.type == 'binary':
                    data['image_fields'][field_name] = self.escape_falsy_as_empty(Website.image_url(record, field_name))
                elif field_widget == 'image':
                    data['image_fields'][field_name] = self.escape_falsy_as_empty(record[field_name])
                elif field_widget == 'monetary':
                    FieldMonetary = self.env['ir.qweb.field.monetary']
                    model_currency = None
                    if field.type == 'monetary':
                        model_currency = record[record[field_name].currency_field]
                    elif 'currency_id' in model._fields:
                        model_currency = record['currency_id']
                    if model_currency:
                        website_currency = self._get_website_currency()
                        data['fields'][field_name] = FieldMonetary.value_to_html(
                            model_currency._convert(
                                record[field_name],
                                website_currency,
                                Website.get_current_website().company_id,
                                fields.Date.today()
                            ),
                            {'display_currency': website_currency}
                        )
                    else:
                        data['fields'][field_name] = self.escape_falsy_as_empty(record[field_name])
                elif ('ir.qweb.field.%s' % field_widget) in self.env:
                    data['fields'][field_name] = self.env[('ir.qweb.field.%s' % field_widget)].record_to_html(record, field_name, {})
                else:
                    data['fields'][field_name] = self.escape_falsy_as_empty(record[field_name])

            data['fields']['call_to_action_url'] = 'website_url' in record and record['website_url']
            values.append(data)
        return values

    @api.model
    def _get_website_currency(self):
        company = self.env['website'].get_current_website().company_id
        return company.currency_id
