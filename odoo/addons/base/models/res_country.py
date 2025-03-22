# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import logging
from odoo import api, fields, models, tools
from odoo.osv import expression
from odoo.exceptions import UserError
from psycopg2 import IntegrityError
from odoo.tools.translate import _
_logger = logging.getLogger(__name__)


FLAG_MAPPING = {
    "GF": "fr",
    "BV": "no",
    "BQ": "nl",
    "GP": "fr",
    "HM": "au",
    "YT": "fr",
    "RE": "fr",
    "MF": "fr",
    "UM": "us",
}

NO_FLAG_COUNTRIES = [
    "AQ", #Antarctica
    "SJ", #Svalbard + Jan Mayen : separate jurisdictions : no dedicated flag
]


class Country(models.Model):
    _name = 'res.country'
    _description = 'Country'
    _order = 'name'

    name = fields.Char(
        string='Country Name', required=True, translate=True)
    code = fields.Char(
        string='Country Code', size=2,
        help='The ISO country code in two chars. \nYou can use this field for quick search.')
    address_format = fields.Text(string="Layout in Reports",
        help="Display format to use for addresses belonging to this country.\n\n"
             "You can use python-style string pattern with all the fields of the address "
             "(for example, use '%(street)s' to display the field 'street') plus"
             "\n%(state_name)s: the name of the state"
             "\n%(state_code)s: the code of the state"
             "\n%(country_name)s: the name of the country"
             "\n%(country_code)s: the code of the country",
        default='%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s')
    address_view_id = fields.Many2one(
        comodel_name='ir.ui.view', string="Input View",
        domain=[('model', '=', 'res.partner'), ('type', '=', 'form')],
        help="Use this field if you want to replace the usual way to encode a complete address. "
             "Note that the address_format field is used to modify the way to display addresses "
             "(in reports for example), while this field is used to modify the input form for "
             "addresses.")
    currency_id = fields.Many2one('res.currency', string='Currency')
    image_url = fields.Char(
        compute="_compute_image_url", string="Flag",
        help="Url of static flag image",
    )
    phone_code = fields.Integer(string='Country Calling Code')
    country_group_ids = fields.Many2many('res.country.group', 'res_country_res_country_group_rel',
                         'res_country_id', 'res_country_group_id', string='Country Groups')
    state_ids = fields.One2many('res.country.state', 'country_id', string='States')
    name_position = fields.Selection([
            ('before', 'Before Address'),
            ('after', 'After Address'),
        ], string="Customer Name Position", default="before",
        help="Determines where the customer/company name should be placed, i.e. after or before the address.")
    vat_label = fields.Char(string='Vat Label', translate=True, prefetch=True, help="Use this field if you want to change vat label.")

    state_required = fields.Boolean(default=False)
    zip_required = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)',
            'The name of the country must be unique !'),
        ('code_uniq', 'unique (code)',
            'The code of the country must be unique !')
    ]

    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []

        ids = []
        if len(name) == 2:
            ids = list(self._search([('code', 'ilike', name)] + args, limit=limit))

        search_domain = [('name', operator, name)]
        if ids:
            search_domain.append(('id', 'not in', ids))
        ids += list(self._search(search_domain + args, limit=limit))

        return ids

    @api.model
    @tools.ormcache('code')
    def _phone_code_for(self, code):
        return self.search([('code', '=', code)]).phone_code

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code'):
                vals['code'] = vals['code'].upper()
        return super(Country, self).create(vals_list)

    def write(self, vals):
        if vals.get('code'):
            vals['code'] = vals['code'].upper()
        res = super().write(vals)
        if ('code' in vals or 'phone_code' in vals):
            # Intentionally simplified by not clearing the cache in create and unlink.
            self.clear_caches()
        if 'address_view_id' in vals:
            # Changing the address view of the company must invalidate the view cached for res.partner
            # because of _view_get_address
            self.env['res.partner'].clear_caches()
        return res

    def get_address_fields(self):
        self.ensure_one()
        return re.findall(r'\((.+?)\)', self.address_format)

    @api.depends('code')
    def _compute_image_url(self):
        for country in self:
            if not country.code or country.code in NO_FLAG_COUNTRIES:
                country.image_url = False
            else:
                code = FLAG_MAPPING.get(country.code, country.code.lower())
                country.image_url = "/base/static/img/country_flags/%s.png" % code

    @api.constrains('address_format')
    def _check_address_format(self):
        for record in self:
            if record.address_format:
                address_fields = self.env['res.partner']._formatting_address_fields() + ['state_code', 'state_name', 'country_code', 'country_name', 'company_name']
                try:
                    record.address_format % {i: 1 for i in address_fields}
                except (ValueError, KeyError):
                    raise UserError(_('The layout contains an invalid format key'))

    @api.constrains('code')
    def _check_country_code(self):
        for record in self:
            if not record.code:
                raise UserError(_('Country code cannot be empty'))

class CountryGroup(models.Model):
    _description = "Country Group"
    _name = 'res.country.group'

    name = fields.Char(required=True, translate=True)
    country_ids = fields.Many2many('res.country', 'res_country_res_country_group_rel',
                                   'res_country_group_id', 'res_country_id', string='Countries')


class CountryState(models.Model):
    _description = "Country state"
    _name = 'res.country.state'
    _order = 'code'

    country_id = fields.Many2one('res.country', string='Country', required=True)
    name = fields.Char(string='State Name', required=True,
               help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton')
    code = fields.Char(string='State Code', help='The state code.', required=True)

    _sql_constraints = [
        ('name_code_uniq', 'unique(country_id, code)', 'The code of the state must be unique by country !')
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if self.env.context.get('country_id'):
            args = expression.AND([args, [('country_id', '=', self.env.context.get('country_id'))]])

        if operator == 'ilike' and not (name or '').strip():
            first_domain = []
            domain = []
        else:
            first_domain = [('code', '=ilike', name)]
            domain = [('name', operator, name)]

        fallback_domain = None
        if name and operator in ['ilike', '=']:
            fallback_domain = self._get_name_search_domain(name, operator)

        if name and operator in ['in', 'any']:
            fallback_domain = expression.OR([self._get_name_search_domain(n, '=') for n in name])

        first_state_ids = self._search(expression.AND([first_domain, args]), limit=limit, access_rights_uid=name_get_uid) if first_domain else []
        return list(first_state_ids) + [
            state_id
            for state_id in self._search(expression.AND([domain, args]),
                                         limit=limit, access_rights_uid=name_get_uid)
            if state_id not in first_state_ids
        ] or (
            list(self._search(expression.AND([fallback_domain, args]), limit=limit))
            if fallback_domain
            else []
        )

    def _get_name_search_domain(self, name, operator):
        m = re.fullmatch(r"(?P<name>.+)\((?P<country>.+)\)", name)
        if m:
            return [
                ('name', operator, m['name'].strip()),
                '|', ('country_id.name', 'ilike', m['country'].strip()),
                ('country_id.code', '=', m['country'].strip()),
            ]
        return None


    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} ({})".format(record.name, record.country_id.code)))
        return result
