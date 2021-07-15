# -*- coding: utf-8 -*-

from ast import literal_eval
from collections import OrderedDict
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, MissingError
from odoo.osv import expression
from odoo.tools import html_escape as escape
from lxml import etree as ET
import logging

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
    website_id = fields.Many2one('website', string='Website', ondelete='cascade', required=True)

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

    def render(self, template_key, limit, search_domain=[]):
        """Renders the website dynamic snippet items"""
        self.ensure_one()
        assert '.dynamic_filter_template_' in template_key, _("You can only use template prefixed by dynamic_filter_template_ ")

        if self.env['website'].get_current_website() != self.website_id:
            return ''

        records = self._prepare_values(limit, search_domain)
        View = self.env['ir.ui.view'].sudo().with_context(inherit_branding=False)
        content = View._render_template(template_key, dict(records=records)).decode('utf-8')
        return [ET.tostring(el, encoding='utf-8') for el in ET.fromstring('<root>%s</root>' % content).getchildren()]

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
