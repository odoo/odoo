# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import collections
import datetime
import logging
import re
import typing
from collections import defaultdict
from random import randint
import stdnum
from stdnum import luhn
from stdnum.exceptions import InvalidChecksum, InvalidFormat
from stdnum.eu import vat as eu_vat
from stdnum.util import clean
from zoneinfo import ZoneInfo
from werkzeug import urls

from odoo import api, fields, models, tools, _, Command
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import LazyTranslate
from odoo.tools.business_data import street_split, split_vat
from odoo.tools.date_utils import all_timezones
from odoo.tools.translate import LazyGettext
from odoo.tools.partner_identifiers import (
    ADDITIONAL_IDENTIFIERS_METADATA,
    TIN_METADATA,
    get_deduced_identifiers,
    get_tin_metadata_of_country,
    is_identifier_void,
    normalize_identifier,
    validation_error_message,
)

_logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    from .res_users import ResUsers
    from .res_partner_bank import ResPartnerBank
    from .res_country import ResCountry, ResCountryState
    from .res_company import ResCompany


ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')


EU_EXTRA_VAT_CODES = {
    'GR': 'EL',
    'GB': 'XI',
}
EU_EXTRA_VAT_CODES_INV = {v: k for k, v in EU_EXTRA_VAT_CODES.items()}


_lt = LazyTranslate(__name__)
_ref_vat = {
    'al': 'ALJ91402501L',
    'ar': '20055361682',
    'at': 'ATU12345675',
    'au': '83 914 571 673',
    'be': 'BE0477472701',
    'bg': 'BG1234567892',
    'br': _lt('either 11 digits for CPF or 14 characters for CNPJ'),
    'ca': _lt('123456782 or 123456782RT0001'),
    'cr': '3101012009',
    'ch': _lt('CHE-123.456.788 TVA or CHE-123.456.788 MWST or CHE-123.456.788 IVA'),  # Swiss by Yannick Vaucher @ Camptocamp
    'cl': '76086428-5',
    'co': '213123432-1',
    'cy': 'CY10259033P',
    'cz': 'CZ12345679',
    'de': _lt('DE123456788 or 12/345/67890'),
    'dk': 'DK12345674',
    'do': _lt('1-01-85004-3 or 101850043'),
    'ec': _lt('1792060346001 or 1792060346'),
    'ee': 'EE123456780',
    'es': 'ESA12345674',
    'fi': 'FI12345671',
    'fr': 'FR23334175221',
    'gb': _lt('GB123456782 or XI123456782'),
    'gr': 'EL123456783',
    'hu': _lt('HU12345676 or 12345678-1-11 or 8071592153'),
    'hr': 'HR01234567896',  # Croatia, contributed by Milan Tribuson
    'id': '1234567890123456',
    'ie': 'IE1234567FA',
    'il': _lt('XXXXXXXXX [9 digits] and it should respect the Luhn algorithm checksum'),
    'in': "12AAAAA1234AAZA",
    'is': 'IS062199',
    'it': 'IT12345670017',
    'jp': 'T7000012050002',
    'kr': '123-45-67890 or 1234567890',
    'lt': 'LT123456715',
    'lu': 'LU12345613',
    'lv': 'LV41234567891',
    'ma': '12345678',
    'mc': 'FR53000004605',
    'mt': 'MT12345634',
    'mx': _lt('GODE561231GR8'),
    'nl': 'NL123456782B90',
    'no': 'NO123456785',
    'nz': _lt('49-098-576 or 49098576'),
    'pe': _lt('10XXXXXXXXY or 20XXXXXXXXY or 15XXXXXXXXY or 16XXXXXXXXY or 17XXXXXXXXY'),
    'ph': '123-456-789-123',
    'pk': _lt('1234567 or 1234567-8 or 12345-1234567-8'),
    'pl': 'PL1234567883',
    'pt': 'PT123456789',
    'ro': 'RO1234567897 or 8001011234567 or 9000123456789',
    'rs': 'RS101134702',
    'ru': '123456789047',
    'se': 'SE123456789701',
    'si': 'SI12345679',
    'sk': 'SK2022749619',
    'sm': 'SM24165',
    'th': _lt('0123456789016 or 1234545678781 [13 digits]'),
    'tr': _lt('11111111111 (NIN) or 2222222222 (VKN)'),
    'ua': _lt('12345678 or UA12345678 (EDRPOU), 1234567890 (RNOPP) or 123456789012 (IPN)'),
    'uy': _lt("Example: '219999830019' (format: 12 digits, all numbers, valid check digit)"),
    'uz': _lt('123456789 (TIN) or 12345678901234 (PINFL)'),
    've': 'V-12345678-1, V123456781, V-12.345.678-1',
    'xi': 'XI123456782',
    'sa': _lt('310175397400003 [Fifteen digits, first and last digits should be "3"]'),
}


@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs


class FormatVatLabelMixin(models.AbstractModel):
    _name = 'format.vat.label.mixin'
    _description = "Country Specific VAT Label"

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if attributes and 'string' in attributes and 'vat' in res:
            res['vat']['string'] = self.env.company.country_id.vat_label or _("Tax ID")
        return res


class FormatAddressMixin(models.AbstractModel):
    _name = 'format.address.mixin'
    _description = 'Address Format'

    def _extract_fields_from_address(self, address_line):
        """
        Extract keys from the address line.
        For example, if the address line is "zip: %(zip)s, city: %(city)s.",
        this method will return ['zip', 'city'].
        """
        address_fields = ['%(' + field + ')s' for field in ADDRESS_FIELDS + ('state_code', 'state_name')]
        return sorted([field[2:-2] for field in address_fields if field in address_line], key=address_line.index)

    def _view_get_address(self, arch):
        # consider the country of the user, not the country of the partner we want to display
        address_view_id = self.env.company.country_id.address_view_id.sudo()
        address_format = self.env.company.country_id.address_format
        if address_view_id and not self.env.context.get('no_address_format') and (not address_view_id.model or address_view_id.model == self._name):
            #render the partner address accordingly to address_view_id
            for address_node in arch.xpath("//div[hasclass('o_address_format')]"):
                Partner = self.env['res.partner'].with_context(no_address_format=True)
                sub_arch, _sub_view = Partner._get_view(address_view_id.id, 'form')
                #if the model is different than res.partner, there are chances that the view won't work
                #(e.g fields not present on the model). In that case we just return arch
                if self._name != 'res.partner':
                    try:
                        self.env['ir.ui.view'].postprocess_and_fields(sub_arch, model=self._name)
                    except ValueError:
                        return arch
                new_address_node = sub_arch.find('.//div[@class="o_address_format"]')
                if new_address_node is not None:
                    sub_arch = new_address_node
                address_node.getparent().replace(address_node, sub_arch)
        elif address_format and not self.env.context.get('no_address_format'):
            # For the zip, city and state fields we need to move them around in order to follow the country address format.
            # The purpose of this is to help the user by following a format he is used to.
            city_line = [self._extract_fields_from_address(line) for line in address_format.split('\n') if 'city' in line]
            if city_line:
                field_order = city_line[0]
                for address_node in arch.xpath("//div[hasclass('o_address_format')]"):
                    first_field = field_order[0] if field_order[0] not in ('state_code', 'state_name') else 'state_id'
                    concerned_fields = {'zip', 'city', 'state_id'} - {first_field}
                    current_field = address_node.find(f".//field[@name='{first_field}']")
                    # First loop into the fields displayed in the address_format, and order them.
                    for field in field_order[1:]:
                        if field in ('state_code', 'state_name'):
                            field = 'state_id'
                        previous_field = current_field
                        current_field = address_node.find(f".//field[@name='{field}']")
                        if previous_field is not None and current_field is not None:
                            previous_field.addnext(current_field)
                        concerned_fields -= {field}
                    # Add the remaining fields in 'concerned_fields' at the end, after the others
                    for field in concerned_fields:
                        previous_field = current_field
                        current_field = address_node.find(f".//field[@name='{field}']")
                        if previous_field is not None and current_field is not None:
                            previous_field.addnext(current_field)

        return arch

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view, using _view_get_address,
        changing the architecture according to the address view of the company,
        makes the view cache dependent on the company.
        Different companies could use each a different address view"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.company, self.env.context.get('no_address_format'))

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view.type == 'form':
            arch = self._view_get_address(arch)
        return arch, view


class ResPartnerCategory(models.Model):
    _name = 'res.partner.category'
    _description = 'Partner Tag'
    _order = 'name, id'
    _parent_store = True

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color, aggregator=False)
    parent_id: ResPartnerCategory = fields.Many2one('res.partner.category', string='Category', index=True, ondelete='cascade')
    child_ids: ResPartnerCategory = fields.One2many('res.partner.category', 'parent_id', string='Child Tags')
    active = fields.Boolean(default=True, help="The active field allows you to hide the category without removing it.")
    parent_path = fields.Char(index=True)
    partner_ids: ResPartner = fields.Many2many('res.partner', column1='category_id', column2='partner_id', string='Partners', copy=False)

    @api.depends('parent_id')
    def _compute_display_name(self):
        """ Return the categories' display name, including their direct
            parent by default.
        """
        for category in self:
            names = []
            current = category
            while current:
                names.append(current.name or "")
                current = current.parent_id
            category.display_name = ' / '.join(reversed(names))

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if operator.endswith('like'):
            if operator.startswith('not'):
                return NotImplemented
            return [('id', 'child_of', tuple(self._search(domain)))]
        return domain


class ResPartner(models.Model):
    _name = 'res.partner'
    _description = 'Contact'
    _explanation = "Foundational model for all people and companies (customers, vendors, employees, etc.). Used for identifying individuals or organizations."
    _inherit = ['format.address.mixin', 'format.vat.label.mixin', 'avatar.mixin', 'properties.base.definition.mixin']
    _order = "complete_name ASC, id DESC"
    _rec_names_search = ('complete_name', 'email', 'ref', 'vat')  # TODO vat must be sanitized the same way for storing/searching
    _allow_sudo_commands = False
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    # the partner types that must be added to a partner's complete name, like "Delivery"
    _complete_name_displayed_types = ('invoice', 'delivery', 'other')

    def _default_category(self):
        return self.env['res.partner.category'].browse(self.env.context.get('category_id'))

    @api.model
    def default_get(self, fields):
        """Add the company of the parent as default if we are creating a child partner. """
        values = super().default_get(fields)
        if 'parent_id' in fields and values.get('parent_id'):
            parent = self.browse(values.get('parent_id'))
            values['company_id'] = parent.company_id.id
        # protection for `default_type` values leaking from menu action context (e.g. for crm's email)
        if 'type' in fields and values.get('type'):
            if values['type'] not in self._fields['type'].get_values(self.env):
                values['type'] = None
        return values

    name = fields.Char(index=True, default_export_compatible=True)
    complete_name = fields.Char(compute='_compute_complete_name', store=True, index=True)
    parent_id: ResPartner = fields.Many2one('res.partner', string='Related Company', index=True)
    # It's Stored intentionally and will act in place of `company_name`
    parent_name = fields.Char(related='parent_id.name', readonly=True, store=False, string='Parent name')
    child_ids: ResPartner = fields.One2many('res.partner', 'parent_id', string='Related Contacts', domain=[('active', '=', True)], context={'active_test': False})
    ref = fields.Char(string='Reference', index=True)
    lang = fields.Selection(_lang_get, string='Language',
                            compute='_compute_lang', readonly=False, store=True,
                            help="All the emails and documents sent to this contact will be translated in this language.")
    active_lang_count = fields.Integer(compute='_compute_active_lang_count')
    tz = fields.Selection(_tzs, string='Timezone', default=lambda self: self.env.context.get('tz'),
                          help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
                               "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
                               "Anywhere else, time values are computed according to the time offset of your web client.")

    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset')
    # Warning: user_id is a Salesperson, not the inverse of partner_id in res.users.
    # For the latter, see user_ids and main_user_id.
    user_id: ResUsers = fields.Many2one(
        'res.users', string='Salesperson',
        compute='_compute_user_id',
        precompute=True,  # avoid queries post-create
        readonly=False, store=True,
        help='The internal user in charge of this contact.')
    vat = fields.Char(string='Tax ID', index=True, inverse='_inverse_vat', help="You can use '/' to indicate that the customer has no Tax ID.")
    additional_identifiers = fields.Json(string="Additional Identifiers", copy=False)
    available_additional_identifiers_metadata = fields.Json(compute='_compute_available_additional_identifiers_metadata')
    vat_label = fields.Char(string='Tax ID Label', compute='_compute_vat_label')
    same_vat_partner_id: ResPartner = fields.Many2one('res.partner', string='Partner with same Tax ID', compute='_compute_same_vat_partner_id', store=False)
    bank_ids: ResPartnerBank = fields.One2many('res.partner.bank', 'partner_id', string='Banks')
    website = fields.Char('Website Link')
    comment = fields.Html(string='Notes')

    category_id: ResPartnerCategory = fields.Many2many('res.partner.category', column1='partner_id',
                                    column2='category_id', string='Tags', default=_default_category)
    active = fields.Boolean(default=True)
    employee = fields.Boolean(help="Check this box if this contact is an Employee.")
    function = fields.Char(string='Job Position')
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice'),
         ('delivery', 'Delivery'),
         ('other', 'Other'),
        ], string='Address Type',
        default='contact')
    type_address_label = fields.Char('Address Type Description', compute='_compute_type_address_label')
    # address fields
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id: ResCountryState = fields.Many2one("res.country.state", string='State', ondelete='restrict', index='btree_not_null', domain="[('country_id', '=?', country_id)]")
    country_id: ResCountry = fields.Many2one('res.country', string='Country', ondelete='restrict', index='btree_not_null', inverse='_inverse_vat')
    country_code = fields.Char(related='country_id.code', string="Country Code")
    partner_latitude = fields.Float(string='Latitude', digits=(10, 7))
    partner_longitude = fields.Float(string='Longitude', digits=(10, 7))
    email = fields.Char()
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    phone = fields.Char()
    is_company = fields.Boolean(string='Is a Company', default=False, compute="_compute_is_company", store=True,
        help="Check if the contact is a company, otherwise it is a person")
    is_public = fields.Boolean(compute='_compute_is_public', compute_sudo=True)
    industry_id: ResPartnerIndustry = fields.Many2one('res.partner.industry', 'Industry')
    company_id: ResCompany = fields.Many2one('res.company', 'Company', index=True)
    color = fields.Integer(string='Color Index', default=0)
    user_ids: ResUsers = fields.One2many('res.users', 'partner_id', string='Users', bypass_search_access=True)
    main_user_id: ResUsers = fields.Many2one(
        "res.users",
        string="Main User",
        compute="_compute_main_user_id",
        help="There can be several users related to the same partner. "
        "When a single user is needed, this field attempts to find the most appropriate one.",
    )
    partner_share = fields.Boolean(
        'Share Partner', compute='_compute_partner_share', store=True,
        help="Either customer (not a user), either shared user. Indicated the current partner is a customer without "
             "access or with a limited access created for sharing data.")
    contact_address = fields.Char(compute='_compute_address', string="Complete Address")
    address = fields.Char(compute='_compute_address', string="Address (without name)")
    contact_address_inline = fields.Char(compute='_compute_address', string="Complete Address inline")
    address_inline = fields.Char(compute='_compute_address', string="Address inline (without name)")

    # technical field used for managing commercial fields
    commercial_partner_id: ResPartner = fields.Many2one(
        'res.partner', string='Commercial Entity',
        compute='_compute_commercial_partner', store=True,
        recursive=True, index=True)
    commercial_company_name = fields.Char('Company Name Entity', related='commercial_partner_id.name',
                                          store=True)
    barcode = fields.Char(help="Use a barcode to identify this contact.", copy=False, company_dependent=True)

    # hack to allow using plain browse record in qweb views, and used in ir.qweb.field.contact
    self: ResPartner = fields.Many2one(comodel_name='res.partner', compute='_compute_get_ids')
    application_statistics = fields.Json(string="Stats", compute="_compute_application_statistics")

    @property
    def country_name(self):
        return self.country_id.name or ''

    def _compute_application_statistics(self):
        result = self._compute_application_statistics_hook()
        for p in self:
            p.application_statistics = result.get(p.id, [])

    def _compute_application_statistics_hook(self):
        """ Hook for override, as overriding compute method does not update
        cache accordingly. All overrides receive False instead of previously
        assigned value. """
        return defaultdict(list)

    _check_name = models.Constraint(
        "CHECK( (type='contact' AND name IS NOT NULL) or (type!='contact') )",
        "Contacts require a name",
    )

    def _get_street_split(self):
        return street_split(self.street or '')

    @api.depends('name', 'user_ids.share', 'image_1920', 'is_company', 'type')
    def _compute_avatar_1920(self):
        super()._compute_avatar_1920()

    @api.depends('name', 'user_ids.share', 'image_1024', 'is_company', 'type')
    def _compute_avatar_1024(self):
        super()._compute_avatar_1024()

    @api.depends('name', 'user_ids.share', 'image_512', 'is_company', 'type')
    def _compute_avatar_512(self):
        super()._compute_avatar_512()

    @api.depends('name', 'user_ids.share', 'image_256', 'is_company', 'type')
    def _compute_avatar_256(self):
        super()._compute_avatar_256()

    @api.depends('name', 'user_ids.share', 'image_128', 'is_company', 'type')
    def _compute_avatar_128(self):
        super()._compute_avatar_128()

    def _compute_avatar(self, avatar_field, image_field):
        partners_with_internal_user = self.filtered(
            lambda partner: partner.type == 'contact' or any(not u.share for u in partner.user_ids))
        super(ResPartner, partners_with_internal_user)._compute_avatar(avatar_field, image_field)
        partners_without_image = (self - partners_with_internal_user).filtered(lambda p: not p[image_field])
        for _, group in tools.groupby(partners_without_image, key=lambda p: p._avatar_get_placeholder_path()):
            group_partners = self.env['res.partner'].concat(group)
            group_partners[avatar_field] = group_partners[0]._avatar_get_placeholder()

        for partner in self - partners_with_internal_user - partners_without_image:
            partner[avatar_field] = partner[image_field]

    def _avatar_get_placeholder_path(self):
        if self.is_company:
            return "base/static/img/avatar_placeholder_company.png"
        if self.type == 'delivery':
            return "base/static/img/avatar_placeholder_delivery.png"
        if self.type == 'invoice':
            return "base/static/img/avatar_placeholder_invoice.png"
        if self.type == 'other':
            return "base/static/img/avatar_placeholder_other.png"
        return super()._avatar_get_placeholder_path()

    def _get_complete_name(self):
        self.ensure_one()

        displayed_types = self._complete_name_displayed_types
        type_description = dict(self._fields['type']._description_selection(self.env))

        name = self.name or ''
        if self.parent_id:
            if not name and self.type in displayed_types:
                name = type_description[self.type]
            if not self.is_company and not self.env.context.get('partner_display_name_hide_company'):
                name = f"{self.commercial_company_name or self.sudo().parent_id.name}, {name}"
        return name.strip()

    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'commercial_company_name')
    def _compute_complete_name(self):
        for partner in self:
            partner.complete_name = partner.with_context({})._get_complete_name()

    @api.depends('parent_id')
    def _compute_lang(self):
        """ While creating / updating child contact, take the parent lang by
        default if any. 0therwise, fallback to default context / DB lang """
        for partner in self:
            if partner.parent_id:
                partner.lang = partner.parent_id.lang or partner.default_get(['lang']).get('lang') or partner.env.lang
            elif not partner.lang:
                partner.lang = partner.default_get(['lang']).get('lang') or partner.env.lang

    @api.depends('lang')
    def _compute_active_lang_count(self):
        lang_count = len(self.env['res.lang'].get_installed())
        for partner in self:
            partner.active_lang_count = lang_count

    @api.depends('tz')
    def _compute_tz_offset(self):
        for partner in self:
            partner.tz_offset = datetime.datetime.now(ZoneInfo(partner.tz or 'UTC')).strftime('%z')

    @api.depends('parent_id')
    def _compute_user_id(self):
        """ Synchronize sales rep with parent if partner is a person """
        for partner in self.filtered(lambda partner: not partner.user_id and not partner.is_company and partner.parent_id.user_id):
            partner.user_id = partner.parent_id.user_id

    @api.depends_context("uid")
    @api.depends("user_ids.active", "user_ids.share")
    def _compute_main_user_id(self):
        partners = self
        if partner := partners & self.env.user.partner_id:
            partner.main_user_id = self.env.user
            partners -= partner
        active_users = partners.user_ids.filtered('active')
        for partner in partners:
            users = partner.user_ids & active_users
            # Special case for OdooBot as its user might be archived.
            if not users and partner.id == self.env["ir.model.data"]._xmlid_to_res_id("base.partner_root"):
                partner.main_user_id = self.env["ir.model.data"]._xmlid_to_res_id("base.user_root")
                continue
            partner.main_user_id = users.sorted(
                lambda u: (not u.share, -u.id), reverse=True,
            )[:1]

    @api.depends('user_ids.share', 'user_ids.active')
    def _compute_partner_share(self):
        super_partner = self.env['res.users'].browse(api.SUPERUSER_ID).partner_id
        if super_partner in self:
            super_partner.partner_share = False
        for partner in self - super_partner:
            partner.partner_share = not partner.user_ids or not any(not user.share for user in partner.user_ids)

    @api.depends('vat', 'company_id', 'country_id')
    def _compute_same_vat_partner_id(self):
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            # active_test = False because if a partner has been deactivated you still want to raise the error,
            # so that you can reactivate it instead of creating a new one, which would lose its history.
            Partner = self.with_context(active_test=False).sudo()
            vats = [partner.vat]
            should_check_vat = not self._is_vat_void(partner.vat)

            if should_check_vat and partner.country_id and 'EU_PREFIX' in partner.country_id.country_group_codes:
                if partner.vat[:2].isalpha():
                    vats.append(partner.vat[2:])
                else:
                    vats.append(partner.country_id.code + partner.vat)
                    if new_code := EU_EXTRA_VAT_CODES.get(partner.country_id.code):
                        vats.append(new_code + partner.vat)
            domain = [
                ('vat', 'in', vats),
            ]
            if partner.country_id:
                domain += [('country_id', 'in', [partner.country_id.id, False])]
            if partner.company_id:
                domain += [('company_id', 'in', [False, partner.company_id.id])]
            if partner_id:
                domain += [('id', '!=', partner_id), '!', ('id', 'child_of', partner_id)]
            # For VAT number being only one character, we will skip the check just like the regular check_vat

            partner.same_vat_partner_id = should_check_vat and not partner.parent_id and Partner.search(domain, limit=1)

    @api.depends_context('company')
    def _compute_vat_label(self):
        self.vat_label = self.env.company.country_id.vat_label or _("Tax ID")

    @api.depends('parent_id', 'type')
    def _compute_type_address_label(self):
        for partner in self:
            if partner.type == 'invoice':
                partner.type_address_label = _('Invoice Address')
            elif partner.type == 'delivery':
                partner.type_address_label = _('Delivery Address')
            else:
                partner.type_address_label = _('Address')

    @api.depends_context('lang')
    @api.depends(lambda self: self._display_address_depends())
    def _compute_address(self):
        for partner in self:
            partner.contact_address = partner._display_address()
            partner.address = partner._display_address(without_name=True)
            partner.contact_address_inline = partner._display_address(separator=', ')
            partner.address_inline = partner._display_address(without_name=True, separator=', ')

    def _compute_get_ids(self):
        for partner in self:
            partner.self = partner.id

    @api.depends('parent_id.commercial_partner_id', 'parent_id')
    def _compute_commercial_partner(self):
        for partner in self:
            if not partner.parent_id:
                partner.commercial_partner_id = partner
            else:
                partner.commercial_partner_id = partner.parent_id.commercial_partner_id

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive Partner hierarchies.'))

    @api.constrains('company_id')
    def _check_partner_company(self):
        """
        Check that for every partner which has a company,
        if there exists a company linked to that partner,
        the company_id set on the partner is that company
        """
        partners = self.filtered(lambda p: p.is_company and p.company_id)
        companies = self.env['res.company'].search_fetch([('partner_id', 'in', partners.ids)], ['partner_id'])
        for company in companies:
            if company != company.partner_id.company_id:
                raise ValidationError(_('The company assigned to this partner does not match the company this partner represents.'))

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        # return values in result, as this method is used by _fields_sync()
        if not self.parent_id:
            return
        result = {}
        partner = self._origin
        parent_address = self.parent_id._get_address_values()
        if (partner.type or self.type) == 'contact' and bool(parent_address):
            # for contacts: copy the parent address, if set (aka, at least one
            # value is set in the address: otherwise, keep the one from the
            # contact)
            result['value'] = parent_address
        return result

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('parent_id', 'company_id')
    def _onchange_company_id(self):
        if self.parent_id:
            self.company_id = self.parent_id.company_id.id

    @api.depends('name', 'email')
    def _compute_email_formatted(self):
        """ Compute formatted email for partner, using formataddr. Be defensive
        in computation, notably

          * double format: if email already holds a formatted email like
            'Name' <email@domain.com> we should not use it as it to compute
            email formatted like "Name <'Name' <email@domain.com>>";
          * multi emails: sometimes this field is used to hold several addresses
            like email1@domain.com, email2@domain.com. We currently let this value
            untouched, but remove any formatting from multi emails;
          * invalid email: if something is wrong, keep it in email_formatted as
            this eases management and understanding of failures at mail.mail,
            mail.notification and mailing.trace level;
          * void email: email_formatted is False, as we cannot do anything with
            it;
        """
        self.email_formatted = False
        for partner in self:
            emails_normalized = tools.email_normalize_all(partner.email)
            if emails_normalized:
                # note: multi-email input leads to invalid email like "Name" <email1, email2>
                # but this is current behavior in Odoo 14+ and some servers allow it
                partner.email_formatted = tools.formataddr((
                    partner.name or u"False",
                    ','.join(emails_normalized)
                ))
            elif partner.email:
                partner.email_formatted = tools.formataddr((
                    partner.name or u"False",
                    partner.email
                ))

    @api.constrains('barcode')
    def _check_barcode_unicity(self):
        for partner in self:
            if partner.barcode and self.env['res.partner'].search_count([('barcode', '=', partner.barcode)]) > 1:
                raise ValidationError(_('Another partner already has this barcode'))

    def _convert_fields_to_values(self, field_names):
        """ Returns dict of write() values for synchronizing ``field_names`` """
        if any(self._fields[fname].type == 'one2many' for fname in field_names):
            raise AssertionError(_('One2Many fields cannot be synchronized as part of `commercial_fields` or `address fields`'))
        return self._convert_to_write({fname: self[fname] for fname in field_names})

    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        return list(ADDRESS_FIELDS)

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return self._address_fields()

    def _get_address_values(self):
        """ Get address values from record if at least one value is set. Otherwise
        it is considered empty and nothing is returned. """
        address_fields = self._address_fields()
        if any(self[key] for key in address_fields):
            return self._convert_fields_to_values(address_fields)
        return {}

    def _update_address(self, vals):
        """ Filter values from vals that are liked to address definition, and
        update recordset using super().write to avoid loops and side effects
        due to synchronization of address fields through partner hierarchy. """
        addr_vals = {key: vals[key] for key in self._address_fields() if key in vals}
        if addr_vals:
            super().write(addr_vals)

    @api.model
    def _commercial_fields(self):
        """ Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. These fields are meant to be hidden on
        partners that aren't `commercial entities` themselves, or synchronized
        at update (if present in _synced_commercial_fields), and will be
        delegated to the parent `commercial entity`. The list is meant to be
        extended by inheriting classes. """
        return self._synced_commercial_fields() + ['industry_id']

    @api.model
    def _synced_commercial_fields(self):
        """ Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. When modified on a children, update is
        propagated until the commercial entity. """
        return ['vat', 'additional_identifiers']

    def _get_commercial_values(self):
        """ Get commercial values from record. Return only set values, as they
        are considered individually, and only set values should be taken into
        account. """
        set_commercial_fields = [fname for fname in self._commercial_fields() if self[fname]]
        if set_commercial_fields:
            return self._convert_fields_to_values(set_commercial_fields)
        return {}

    def _get_synced_commercial_values(self):
        """ Get synchronized commercial values from ercord. Return only set values
        as for other commercial values. """
        set_synced_fields = [fname for fname in self._synced_commercial_fields() if self[fname]]
        if set_synced_fields:
            return self._convert_fields_to_values(set_synced_fields)
        return {}

    def _apply_synced_identifiers(self, source_identifiers):
        """ Mirror the *synced* identifiers of ``source_identifiers`` onto every record
        in ``self``, while keeping per-contact identifiers untouched.
        Per-contact identifiers are those flagged ``synced=False`` in their metadata
        """
        all_metadata = self._get_all_identifiers_metadata()
        synced = {
            key: value
            for key, value in (source_identifiers or {}).items()
            if all_metadata.get(key, {}).get('synced', True)
        }
        for record in self:
            existing = record.additional_identifiers or {}
            merged = {
                key: value
                for key, value in existing.items()
                if not all_metadata.get(key, {}).get('synced', True)
            } | synced
            if merged != existing:
                record.write({'additional_identifiers': merged})

    def _write_commercial_sync(self, sync_vals):
        """ Apply commercial-fields ``sync_vals`` to ``self``.
        ``additional_identifiers`` is special-cased so only its flagged synced keys
        are propagated; the remaining fields are written as-is.
        """
        if 'additional_identifiers' in sync_vals:
            sync_vals = dict(sync_vals)
            self._apply_synced_identifiers(sync_vals.pop('additional_identifiers'))
        self.write(sync_vals)

    @api.model
    def _company_dependent_commercial_fields(self):
        return [
            fname for fname in self._commercial_fields()
            if self._fields[fname].company_dependent
        ]

    def _commercial_sync_from_company(self):
        """ Handle sync of commercial fields when a new parent commercial entity is set,
        as if they were related fields """
        commercial_partner = self.commercial_partner_id
        if commercial_partner != self:
            sync_vals = commercial_partner._get_commercial_values()
            if sync_vals:
                self._write_commercial_sync(sync_vals)
                self._commercial_sync_to_descendants()
            self._company_dependent_commercial_sync()

    def _company_dependent_commercial_sync(self):
        """ Propagate sync of company dependant commercial fields to other
        commpanies. """
        if not (fields_to_sync := self._company_dependent_commercial_fields()):
            return

        for company_sudo in self.env['res.company'].sudo().search([]):
            if company_sudo == self.env.company:
                continue  # already handled by _commercial_sync_from_company
            self_in_company = self.with_company(company_sudo)
            self_in_company.write(
                self_in_company.commercial_partner_id._convert_fields_to_values(fields_to_sync)
            )

    def _commercial_sync_to_descendants(self, fields_to_sync=None):
        """ Handle sync of commercial fields to descendants """
        commercial_partner = self.commercial_partner_id
        if fields_to_sync is None:
            fields_to_sync = self._commercial_fields()
        sync_vals = commercial_partner._convert_fields_to_values(fields_to_sync)
        sync_children = self.child_ids.filtered(lambda c: not c.is_company)
        children_ids_to_sync = tools.OrderedSet()
        for child in sync_children:
            if any(
                self.env['res.partner']._fields[fname].convert_to_write(child[fname], self) != sync_vals[fname]
                for fname in fields_to_sync
            ):
                children_ids_to_sync.add(child.id)
            child._commercial_sync_to_descendants(fields_to_sync)
        if children_ids_to_sync:
            children_to_sync = self.env['res.partner'].browse(children_ids_to_sync)
            children_to_sync._write_commercial_sync(sync_vals)

    def _fields_sync(self, values):
        """ Sync commercial fields and address fields from company and to children.
        Also synchronize address to parent. This somehow mimics related fields
        to the parent, with more control. This method should be called after
        updating values in cache e.g. self should contain new values.

        :param dict values: updated values, triggering sync
        """
        self.fetch(['parent_id', 'type', 'commercial_partner_id'])
        # 1. From UPSTREAM: sync from parent
        if values.get('parent_id') or values.get('type') == 'contact':
            # 1a. Commercial fields: sync if parent changed
            if values.get('parent_id'):
                address = self._get_address_values()
                parent_address = self.parent_id._get_address_values()
                if self.type == 'contact' and bool(address) and bool(parent_address) and address != parent_address:
                    # If current partner has a different address set, change it's type so we don't lost it
                    self.type = 'other'
                self.sudo()._commercial_sync_from_company()
            # 1b. Address fields: sync if parent or use_parent changed *and* both are now set
            if self.parent_id and self.type == 'contact':
                if address_values := self.parent_id._get_address_values():
                    self._update_address(address_values)

        # 2. To UPSTREAM: sync parent address, as well as editable synchronized commercial fields
        address_to_upstream = (
            # parent is set, potential address update as contact address = parent address
            bool(self.parent_id) and bool(self.type == 'contact') and
            # address updated, or parent updated
            (any(field in values for field in self._address_fields()) or 'parent_id' in values) and
            # something is actually updated
            any(self[fname] != self.parent_id[fname] for fname in self._address_fields())
        )
        if address_to_upstream:
            new_address = self._get_address_values()
            self.parent_id.write(new_address)  # is going to trigger _fields_sync again
        commercial_to_upstream = (
            # has a parent and is not a commercial entity itself
            bool(self.parent_id) and (self.commercial_partner_id != self) and
            # actually updated, or parent updated
            (any(field in values for field in self._synced_commercial_fields()) or 'parent_id' in values) and
            # something is actually updated
            any(self[fname] != self.parent_id[fname] for fname in self._synced_commercial_fields())
        )
        if commercial_to_upstream:
            new_synced_commercials = self._get_synced_commercial_values()
            self.parent_id._write_commercial_sync(new_synced_commercials)

        # 3. To DOWNSTREAM: sync children
        self._children_sync(values)

    def _children_sync(self, values):
        if not self.child_ids:
            return
        # 2a. Commercial Fields: sync if commercial entity
        if self.commercial_partner_id == self:
            fields_to_sync = values.keys() & self._commercial_fields()
            self.sudo()._commercial_sync_to_descendants(fields_to_sync)
        # 2b. Address fields: sync if address changed
        address_fields = self._address_fields()
        if any(field in values for field in address_fields):
            contacts = self.child_ids.filtered(lambda c: c.type == 'contact')
            contacts._update_address(values)

    def _handle_first_contact_creation(self):
        """ On creation of first contact for a company (or root) that has no address, assume contact address
        was meant to be company address """
        parent = self.parent_id
        address_fields = self._address_fields()
        if (
            (parent.is_company or not parent.parent_id)
            and any(self[f] for f in address_fields)
            and not any(parent[f] for f in address_fields)
            and len(parent.child_ids) == 1
        ):
            addr_vals = self._convert_fields_to_values(address_fields)
            parent._update_address(addr_vals)

    def _clean_website(self, website):
        url = urls.url_parse(website)
        if not url.scheme:
            if not url.netloc:
                url = url.replace(netloc=url.path, path='')
            website = url.replace(scheme='http').to_url()
        return website

    @api.depends('vat', 'commercial_partner_id')
    def _compute_is_company(self):
        """ By default, a partner is considered as a company if they are their own
        commercial entity (see computed field), and if their VAT is considered as being
        valid, based on a default heuristic (not void, '/', 'na' or 'NA').

        Each localization can then further refine this definition according to legal
        definition of what is a company (e.g. more strict VAT, specific field usage,
        ...) """
        for partner in self:
            partner.is_company = partner.commercial_partner_id == partner and not partner._is_vat_void(partner.vat)

    def _compute_is_public(self):
        for partner in self.with_context(active_test=False):
            users = partner.user_ids
            partner.is_public = users and any(user._is_public() for user in users)

    def write(self, vals):
        self._clean_additional_identifiers(vals)
        if vals.get('active') is False:
            # DLE: It should not be necessary to modify this to make work the ORM. The problem was just the recompute
            # of partner.user_ids when you create a new user for this partner, see test test_70_archive_internal_partners
            # You modified it in a previous commit, see original commit of this:
            # https://github.com/odoo/odoo/commit/9d7226371730e73c296bcc68eb1f856f82b0b4ed
            #
            # RCO: when creating a user for partner, the user is automatically added in partner.user_ids.
            # This is wrong if the user is not active, as partner.user_ids only returns active users.
            # Hence this temporary hack until the ORM updates inverse fields correctly.
            self.invalidate_recordset(['user_ids'])
            users = self.env['res.users'].sudo().search([('partner_id', 'in', self.ids), ('active', '=', True)])
            if users:
                if users.sudo(False).has_access('write'):
                    error_msg = _('You cannot archive contacts linked to an active user.\n'
                                  'You first need to archive their associated user.\n\n'
                                  'Linked active users : %(names)s', names=", ".join([u.display_name for u in users]))
                    action_error = users._action_show()
                    raise RedirectWarning(error_msg, action_error, _('Go to users'))
                else:
                    raise ValidationError(_('You cannot archive contacts linked to an active user.\n'
                                            'Ask an administrator to archive their associated user first.\n\n'
                                            'Linked active users :\n%(names)s', names=", ".join([u.display_name for u in users])))
        if vals.get('website'):
            vals['website'] = self._clean_website(vals['website'])
        if vals.get('name'):
            for partner in self:
                for bank in partner.bank_ids:
                    if bank.holder_name == partner.name:
                        bank.holder_name = vals['name']

        # filter to keep only really updated values -> field synchronize goes through
        # partner tree and we should avoid infinite loops in case same value is
        # updated due to cycles. Use case: updating a property field, which updated
        # a computed field, which has an inverse writing the same value on property
        # field. Yay.
        pre_values_list = [{fname: partner[fname] for fname in vals} for partner in self]

        # res.partner must only allow to set the company_id of a partner if it
        # is the same as the company of all users that inherit from this partner
        # (this is to allow the code from res_users to write to the partner!) or
        # if setting the company_id to False (this is compatible with any user
        # company)
        if 'company_id' in vals:
            company_id = vals['company_id']
            for partner in self:
                if company_id and partner.user_ids:
                    company = self.env['res.company'].browse(company_id)
                    companies = set(user.company_id for user in partner.user_ids)
                    if len(companies) > 1 or company not in companies:
                        raise UserError(
                            self.env._("The selected company is not compatible with the companies of the related user(s)"))
                if partner.child_ids:
                    partner.child_ids.write({'company_id': company_id})
        result = super().write(vals)
        for partner, pre_values in zip(self, pre_values_list, strict=True):
            if internal_users := partner.user_ids.filtered(lambda u: u._is_internal() and u != self.env.user):
                internal_users.check_access('write')
            updated = {fname: fvalue for fname, fvalue in vals.items() if partner[fname] != pre_values.get(fname)}
            if updated:
                partner._fields_sync(updated)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('import_file'):
            self._check_import_consistency(vals_list)
        for vals in vals_list:
            self._clean_additional_identifiers(vals)
            if vals.get('website'):
                vals['website'] = self._clean_website(vals['website'])
        partners = super().create(vals_list)
        # due to ir.default, compute is not called as there is a default value
        # hence calling the compute manually
        for partner, values in zip(partners, vals_list):
            if 'lang' not in values:
                partner._compute_lang()
            if values.get('parent_name') and not partner.parent_id:
                # Create parent company if we got 'parent_name'
                partner._create_parent_from_name(
                    values.get('parent_name'),
                    values.get('parent_additional_values'),
                )

        if self.env.context.get('_partners_skip_fields_sync'):
            return partners

        for partner, vals in zip(partners, vals_list):
            vals = self.env['res.partner']._add_missing_default_values(vals)
            partner._fields_sync(vals)
        return partners

    def _is_vat_void(self, vat):
        if not vat:
            return True
        return vat in ['/', 'na', 'NA']

    @api.ondelete(at_uninstall=False)
    def _unlink_except_user(self):
        users = self.env['res.users'].sudo().search([('partner_id', 'in', self.ids)])
        if not users:
            return  # no linked user, operation is allowed
        if self.env['res.users'].sudo(False).has_access('write'):
            error_msg = _('You cannot delete contacts linked to an active user.\n'
                          'You should rather archive them after archiving their associated user.\n\n'
                          'Linked active users : %(names)s', names=", ".join([u.display_name for u in users]))
            action_error = users._action_show()
            raise RedirectWarning(error_msg, action_error, _('Go to users'))
        else:
            raise ValidationError(_('You cannot delete contacts linked to an active user.\n'
                                    'Ask an administrator to archive their associated user first.\n\n'
                                    'Linked active users :\n%(names)s', names=", ".join([u.display_name for u in users])))

    def _load_records_create(self, vals_list):
        partners = super(ResPartner, self.with_context(_partners_skip_fields_sync=True))._load_records_create(vals_list)

        # batch up first part of _fields_sync
        # group partners by commercial_partner_id (if not self) and parent_id (if type == contact)
        groups = collections.defaultdict(list)
        for partner, vals in zip(partners, vals_list):
            cp_id = None
            if vals.get('parent_id') and partner.commercial_partner_id != partner:
                cp_id = partner.commercial_partner_id.id

            add_id = None
            if partner.parent_id and partner.type == 'contact':
                add_id = partner.parent_id.id
            groups[(cp_id, add_id)].append(partner.id)

        for (cp_id, add_id), children in groups.items():
            # values from parents (commercial, regular) written to their common children
            to_write = {}
            # commercial fields from commercial partner
            if cp_id:
                to_write = self.sudo().browse(cp_id)._convert_fields_to_values(self._commercial_fields())
            # address fields from parent
            if add_id:
                parent = self.browse(add_id)
                for f in self._address_fields():
                    v = parent[f]
                    if v:
                        to_write[f] = v.id if isinstance(v, models.BaseModel) else v
            if to_write:
                self.sudo().browse(children).write(to_write)

        # do the second half of _fields_sync the "normal" way
        for partner, vals in zip(partners, vals_list):
            partner._children_sync(vals)
            partner._handle_first_contact_creation()
        return partners

    def _create_parent_from_name(self, parent_name, additional_values=None):
        """ Creates a parent form a name, used mainly when creating new partners with
        a parent (often a company) consisting in a name only, not yet a record. """
        self.ensure_one()
        if not parent_name:
            raise ValueError(_('Parent Name is required at this point'))
        parent_values = dict(name=parent_name, vat=self.vat, lang=self.lang)
        parent_values.update(self._convert_fields_to_values(self._address_fields()))
        if additional_values:
            parent_values.update(**additional_values)
        parent_company = self._create_contact_parent_company(parent_values)
        # Set new company as parent
        self.write({
            'parent_id': parent_company.id,
            'child_ids': [
                Command.update(partner_id, dict(parent_id=parent_company.id))
                for partner_id in self.child_ids.ids
            ],
        })
        return parent_company

    def _create_contact_parent_company(self, values):
        """ Need to avoid recomputation of vies_valid """
        self.ensure_one()
        return self.create(values)

    def open_commercial_entity(self):
        """ Utility method used to add an "Open Company" button in partner views """
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': self.commercial_partner_id.id,
                'target': 'current',
                }

    @api.depends('complete_name', 'email', 'vat', 'state_id', 'country_id')
    @api.depends_context(
        'show_address', 'partner_show_db_id',
        'show_email', 'show_vat', 'lang', 'formatted_display_name'
    )
    def _compute_display_name(self):
        type_description = dict(self._fields['type']._description_selection(self.env))
        for partner in self:
            if partner.env.context.get("formatted_display_name"):
                name = partner.name or ''
                if partner.parent_id:
                    name = (f"{partner.parent_id.name} \t "
                            f"--{partner.name or type_description.get(partner.type, '')}--")

                if partner.env.context.get('show_email') and partner.email:
                    name = f"{name} \t --{partner.email}--"
                elif partner.env.context.get('partner_show_db_id'):
                    name = f"{name} \t --{partner.id}--"

            else:
                name = partner.with_context(lang=self.env.lang)._get_complete_name()
                if partner.env.context.get('partner_show_db_id'):
                    name = f"{name} ({partner.id})"
                if partner.env.context.get('show_email') and partner.email:
                    name = f"{name} <{partner.email}>"
                if partner.env.context.get('show_address'):
                    name = name + "\n" + partner.address

                if partner.env.context.get('show_vat') and partner.vat:
                    if partner.env.context.get('show_address'):
                        name = f"{name} \n {partner.vat}"
                    else:
                        name = f"{name} - {partner.vat}"

            # Remove extra empty lines
            name = re.sub(r'\s+\n', '\n', name)
            partner.display_name = name.strip()

    @api.model
    def name_create(self, name):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            If only an email address is received and that the regex cannot find
            a name, the name will have the email value.
            If 'force_email' key in context: must find the email address. """
        default_type = self.env.context.get('default_type')
        if default_type and default_type not in self._fields['type'].get_values(self.env):
            context = dict(self.env.context)
            context.pop('default_type')
            self = self.with_context(context)
        name, email_normalized = tools.parse_contact_from_email(name)
        if self.env.context.get('force_email') and not email_normalized:
            raise ValidationError(_("Couldn't create contact without email address!"))

        create_values = {self._rec_name: name or email_normalized}
        if email_normalized:  # keep default_email in context
            create_values['email'] = email_normalized
        partner = self.create(create_values)
        return partner.id, partner.display_name

    @api.model
    def find_or_create(self, email, assert_valid_email=False):
        """ Find a partner with the given ``email`` or use :meth:`name_create`
        to create a new one.

        :param str email: email-like string, which should contain at least one email,
            e.g. ``"Raoul Grosbedon <r.g@grosbedon.fr>"``
        :param bool assert_valid_email: raise if no valid email is found
        :return: newly created record
        """
        if not email:
            raise ValueError(_('An email is required for find_or_create to work'))

        parsed_name, parsed_email_normalized = tools.parse_contact_from_email(email)
        if not parsed_email_normalized and assert_valid_email:
            raise ValueError(_('A valid email is required for find_or_create to work properly.'))

        if parsed_email_normalized:
            partners = self.search([('email', '=ilike', parsed_email_normalized)], limit=1)
            if partners:
                return partners

        create_values = {self._rec_name: parsed_name or parsed_email_normalized}
        if parsed_email_normalized:  # keep default_email in context
            create_values['email'] = parsed_email_normalized
        return self.create(create_values)

    def address_get(self, adr_pref=None):
        """ Find contacts/addresses of the right type(s) by doing a depth-first-search
        through descendants within company boundaries (stop at entities flagged ``is_company``)
        then continuing the search at the ancestors that are within the same company boundaries.
        Defaults to partners of type ``'default'`` when the exact type is not found, or to the
        provided partner itself if no type ``'default'`` is found either. """
        adr_pref = set(adr_pref or [])
        if 'contact' not in adr_pref:
            adr_pref.add('contact')
        result = {}
        visited = set()
        for partner in self:
            current_partner = partner
            while current_partner:
                to_scan = [current_partner]
                # Scan descendants, DFS
                while to_scan:
                    record = to_scan.pop(0)
                    visited.add(record)
                    if record.type in adr_pref and not result.get(record.type):
                        result[record.type] = record.id
                    if len(result) == len(adr_pref):
                        return result
                    record.child_ids.fetch(['type', 'child_ids', 'is_company', 'parent_id'])
                    to_scan = [c for c in record.child_ids
                                 if c not in visited
                                 if not c.is_company] + to_scan

                # Continue scanning at ancestor if current_partner is not a commercial entity
                if current_partner.is_company or not current_partner.parent_id:
                    break
                current_partner = current_partner.parent_id

        # default to type 'contact' or the partner itself
        default = result.get('contact', self.id or False)
        for adr_type in adr_pref:
            result[adr_type] = result.get(adr_type) or default
        return result

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get('category_id'):
            return  _(
                'Partners: %(category)s',
                category=self.env['res.partner.category'].browse(self.env.context['category_id']).name,
            )
        return super().view_header_get(view_id, view_type)

    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"

    def _get_address_format(self):
        return self.country_id.address_format or self._get_default_address_format()

    def _prepare_display_address(self, without_name=False):
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = defaultdict(str, {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self.country_name,
            'parent_name': self.commercial_company_name or '',
        })
        for field in self._formatting_address_fields():
            args[field] = self[field] or ''
        if without_name:
            args['parent_name'] = ''
        elif self.parent_id:
            address_format = '%(parent_name)s\n' + address_format
        return address_format, args

    def _display_address(self, without_name=False, separator='\n'):
        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param without_name: if address contains name
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        address_format, args = self._prepare_display_address(without_name)
        address = address_format % args
        address = re.sub(r' {2,}', ' ', address)  # Remove extra space
        return separator.join(val for line in address.splitlines() if (val := line.strip()))

    def _display_address_depends(self):
        # field dependencies of method _display_address()
        return self._formatting_address_fields() + [
            'country_id', 'parent_id', 'state_id',
        ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Template for Contacts'),
            'template': '/base/static/xls/contacts_import_template.xlsx',
        }]

    @api.model
    def _check_import_consistency(self, vals_list):
        """
        The values created by an import are generated by a name search, field by field.
        As a result there is no check that the field values are consistent with each others.
        We check that if the state is given a value, it does belong to the given country, or we remove it.
        """
        States = self.env['res.country.state']
        states_ids = {vals['state_id'] for vals in vals_list if vals.get('state_id')}
        state_to_country = States.search_read([('id', 'in', list(states_ids))], ['country_id'])
        for vals in vals_list:
            if vals.get('state_id'):
                country_id = next(c['country_id'][0] for c in state_to_country if c['id'] == vals.get('state_id'))
                state = States.browse(vals['state_id'])
                if state.country_id.id != country_id:
                    state_domain = [('code', '=', state.code),
                                    ('country_id', '=', country_id)]
                    state = States.search(state_domain, limit=1)
                    vals['state_id'] = state.id  # replace state or remove it if not found

    def _get_all_addr(self):
        self.ensure_one()
        return [{
            'contact_type': self.street,
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'state': self.state_id.code,
            'country': self.country_id.code,
        }]

    @api.model
    def _get_res_city_by_name(self, name, country_id):
        pass

    # -------------------------------------------------------------------------
    # PARTNER IDENTIFIERS (VAT + additional identifiers)
    # -------------------------------------------------------------------------

    @api.constrains('additional_identifiers')
    def _check_additional_identifiers(self):
        """Safety guard for paths that bypass `_clean_additional_identifiers`, so malformed values
        never reach the JSON.
        """
        for partner in self:
            for key, value in (partner.additional_identifiers or {}).items():
                self.env['res.partner']._validate_identifier(key, value, validation='error')  # will raise ValidationError if invalid

    @api.onchange('vat', 'country_id')
    def _onchange_vat(self):
        self._check_vat(validation=False)

    def _inverse_vat(self):
        self._check_vat()
        self._deduce_additional_identifiers_from_vat()

    def _check_vat(self, validation="error"):
        for partner in self:
            vat, _country_code = self._run_vat_checks(partner.commercial_partner_id.country_id, partner.vat,
                                               partner_name=partner.name, validation=validation)
            if vat != partner.vat:  # To avoid unnecessary queries (perf tested)
                partner.vat = vat

    @api.model
    def _run_vat_checks(self, country, vat, partner_name='', validation='error'):
        """Checks a VAT number syntactically to ensure its validity upon saving.

        :param country: a country to check for
        :param vat: a string with the VAT number to check.
        :param partner_name: to put into the error message
        :param validation: if False, it will only return the formatted vat without checking if it valid.
            if 'error', an incorrect number will raise and if 'setnull' it will just return an empty vat

        :return: A two-elements tuple with:

            1. The vat number
            2. The country code of the country the VAT number was validated for, if it was validated.
               False if it could not be validated against the provided or guessed country.
        """
        if not country or not vat:
            return vat, False
        if 1 <= len(vat) <= 2:
            if self._is_vat_void(vat) or not validation:
                return vat, False
            if validation == 'setnull':
                return '', False
            if validation == 'error':
                raise ValidationError(_("To explicitly indicate no (valid) VAT, use '/', 'na' or 'NA' instead. "))
        vat_prefix, vat_number = split_vat(vat)

        if vat_prefix == 'EU' and country not in self.env.ref('base.europe').country_ids:
            # Foreign companies that trade with non-enterprises in the EU
            # may have a VATIN starting with "EU" instead of a country code.
            return vat, False

        do_eu_check = False
        prefixed_country = ''
        eu_prefix_country_group = self.env['res.country.group'].search([('code', '=', 'EU_PREFIX')], limit=1)
        country_code = EU_EXTRA_VAT_CODES_INV.get(vat_prefix, vat_prefix)
        if country_code in eu_prefix_country_group.country_ids.mapped('code'):
            if 'EU_PREFIX' in country.country_group_codes and vat_prefix:
                vat = vat_number
                prefixed_country = vat_prefix
            else:
                do_eu_check = True

        code_to_check = prefixed_country or country.code
        vat = self._format_vat_number(code_to_check, vat)

        if prefixed_country == 'GR':
            prefixed_country = 'EL'

        vat_to_return = prefixed_country + vat

        # The context key 'no_vat_validation' allows you to store/set a VAT number without doing validations.
        # This is for API pushes from external platforms where you have no control over VAT numbers.
        if not validation or self.env.context.get('no_vat_validation'):
            return vat_to_return, code_to_check

        # Avoid validating double prefix like BEBE0477472701
        double_prefix = prefixed_country and vat_to_return.startswith(prefixed_country + prefixed_country)
        if not self._check_vat_number(code_to_check, vat) or double_prefix:
            partner_label = _("partner%s", f' [{partner_name}]' if partner_name else '')
            if do_eu_check:
                try:
                    return self._run_vat_checks(self.env['res.country'].search([('code', '=', country_code)], limit=1), vat_prefix + vat_number, partner_name, validation)
                except ValidationError:
                    msg = self._build_vat_error_message(code_to_check, vat_to_return, partner_label)
                    raise ValidationError(msg + "\n\n" + self.env._('If you are trying to input a European number, this is the expected format: ') + _ref_vat[country_code.lower()])
            if validation == 'error':
                msg = self._build_vat_error_message(code_to_check, vat_to_return, partner_label)
                raise ValidationError(msg)
            else:
                return '', code_to_check
        return vat_to_return, code_to_check

    @api.model
    def _check_vat_number(self, country_code, vat_number):
        ''' Low-level method directly calling stdnum or our own specific method. '''
        check_func_name = 'check_vat_' + country_code.lower()
        check_func = getattr(self, check_func_name, None) or getattr(stdnum.util.get_cc_module(country_code, 'vat'), 'is_valid', None)
        return check_func(vat_number) if check_func else True

    @api.model
    def _build_vat_error_message(self, country_code, wrong_vat, record_label):
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(self.env.context['company_id'])
        else:
            company = self.env.company

        vat_label = _("VAT")
        if country_code and company.country_id and country_code == company.country_id.code and company.country_id.vat_label:
            vat_label = company.country_id.vat_label

        expected_format = _ref_vat.get(country_code.lower())
        expected_note = ""
        if expected_format:
            expected_note = ' \n' + self.env._(
                'Note: the expected format is %(expected_format)s',
                 expected_format=expected_format
            )

        # Catch use case where the record label is about the public user (name: False)
        if 'False' not in record_label:
            return '\n' + self.env._(
                'The %(vat_label)s number [%(wrong_vat)s] for %(record_label)s does not seem to be valid. %(expected_note)s',
                vat_label=vat_label,
                wrong_vat=wrong_vat,
                record_label=record_label,
                expected_note=expected_note
            )
        else:
            return '\n' + self.env._(
                'The %(vat_label)s number [%(wrong_vat)s] does not seem to be valid. %(expected_note)s',
                vat_label=vat_label,
                wrong_vat=wrong_vat,
                expected_note=expected_note,
            )

    @api.model
    def _get_country_specific_vat_variants(self, normalized_vat, country_prefix):
        """
        Return additional formatted VAT values to consider during EDI partner matching.
        Should stay consistent with `_check_customer_vat_match` to ensure
        correct partner matching when importing EDI documents.
        """
        vat_variants = []
        if country_prefix.upper() == 'CH':
            normalized_vat = normalized_vat.replace('-', '')
            if (vat_formatted := self._run_vat_checks(self.env.ref('base.ch'), normalized_vat, validation='setnull')[0]):
                vat_base = re.sub(r"\s*(TVA|IVA|MWST)?$", "", vat_formatted.upper())
                vat_variants.extend([f'{vat_base} {suffix}' for suffix in ('TVA', 'IVA', 'MWST')])
        return vat_variants

    @api.model
    def _format_vat_number(self, country_code, vat):
        """ Low-level method directly calling stdnum or our own specific method returning the formatted VAT. """
        stdnum_vat_fix_func = getattr(stdnum.util.get_cc_module(country_code, 'vat'), 'compact', None)
        # If any localization module needs to define vat fix method for its country then we give first priority to it.
        format_func_name = 'format_vat_' + country_code.lower()
        format_func = getattr(self, format_func_name, None) or stdnum_vat_fix_func
        if format_func:
            vat = format_func(vat)
        return vat

    @api.model
    def _validate_identifier(self, key, value, validation=False):
        """ Run the per-identifier-type validator (if any) and return a uniform
        `{valid, value, example}` dict.
        """
        assert validation in (False, 'error', 'setnull')
        value = normalize_identifier(value)
        if not value or self.env.context.get('no_vat_validation'):
            return {'valid': True, 'value': value, 'example': None}

        if (tin_meta := TIN_METADATA.get(key)) and (country_code := tin_meta.get('countries')[:1]):
            country = self.env['res.country'].search([('code', '=', country_code[0])], limit=1)
            tin, _country_code = self._run_vat_checks(country, value, validation=validation)
            example = tin_meta.get('examples') or tin_meta.get('placeholder')
            return {'valid': bool(tin), 'value': tin, 'example': example}

        metadata = self._get_all_identifiers_metadata().get(key) or {}
        example = metadata.get('examples') or metadata.get('placeholder')
        validation_vals = {'valid': True, 'value': value, 'example': example}
        validation_function = metadata.get('validation_function')

        # For VAT-like identifiers (that are not in `vat` field) without a dedicated validator,
        # fallback to eu_vat.validate only when the value looks like a prefixed EU VAT (starts with a 2-letter code).
        supported_countries = eu_vat.MEMBER_STATES
        if not validation_function and metadata.get('category') == 'VAT' and value[:2].lower() in supported_countries:
            validation_function = eu_vat.validate

        if validation_function:
            try:
                value_normalized = validation_function(value)
            except Exception:  # noqa: BLE001
                validation_vals['valid'] = False
            else:
                validation_vals['value'] = value_normalized

        if not validation_vals['valid'] and validation == 'error':
            identifier_label = self._get_identifier_label(key)
            raise ValidationError(validation_error_message(self.env, identifier_label, validation_vals['value'], example=validation_vals['example']))
        if not validation_vals['valid'] and validation == 'setnull':
            _logger.warning("Invalid identifier %s for key %s. Returning None.", value, key)
            validation_vals['value'] = None
        return validation_vals

    @api.model
    def _validate_identifier_by_scheme(self, scheme, value, validation=False):
        assert validation in (False, 'error', 'setnull')
        ResPartner = self.env['res.partner']
        meta = ResPartner._get_all_identifiers_metadata_by_scheme().get(scheme)
        if not meta:
            # Needs to return True to handle `odemo` scheme
            return {'valid': True, 'scheme': scheme, 'value': value, 'key': None, 'example': None}
        validation = ResPartner._validate_identifier(meta['key'], value, validation=validation)
        return {'scheme': scheme, 'key': meta['key'], **validation}

    @api.model
    def _format_identifier(self, identifier_type, value):
        value = normalize_identifier(value)
        if not value:
            return None
        if format_function := self._get_all_identifiers_metadata().get(identifier_type, {}).get('format'):
            return format_function(value)
        return value

    @api.model
    def _pick_preferred_identifier(self, identifiers, filter_func=None, sort_key=None):
        """ Pick the best identifier from a candidates dict.

        :param identifiers: dict {identifier_type: value} as from `_get_all_identifiers()`
        :param filter_func: optional (key, value, metadata) -> bool
        :param sort_key: optional (key, value, metadata) -> comparable
        :return: dict `{'key': ..., 'value': ..., **metadata}` of the winner, or empty dict if no candidate.
        """
        candidates = []
        for key, value in identifiers.items():
            meta = self._get_all_identifiers_metadata().get(key) or {}
            if filter_func and not filter_func(key, value, meta):
                continue
            candidates.append((key, value, meta))
        if not candidates:
            return {}
        if sort_key:
            candidates.sort(key=lambda c: sort_key(*c))
        winner_key, winner_value, winner_meta = candidates[0]
        return {'key': winner_key, 'value': winner_value, **winner_meta}

    @api.depends('country_id')
    def _compute_available_additional_identifiers_metadata(self):
        for partner in self:
            vals = {
                key: {
                    # Resolve lazy translations now: JSON would otherwise stringify them in a frame where
                    # no language can be detected.
                    k: self.env._(v) if isinstance(v, LazyGettext) else v  # pylint: disable=gettext-variable
                    for k, v in metadata.items()
                }
                for key, metadata in self._get_all_additional_identifiers_metadata().items()
                if not metadata.get('countries') or partner.country_code in metadata['countries']  # includes international
            }
            if {key: metadata for key, metadata in vals.items() if metadata.get('category') == 'EN' and key != 'OTHER'}:
                # Pops out the default 'OTHER' only if another 'EN' identifier is available
                vals.pop('OTHER', None)
            partner.available_additional_identifiers_metadata = vals

    def _get_additional_identifier(self, identifier_type):
        """Convenience getter for an entry of the JSON."""
        if not self:
            return None
        self.ensure_one()
        return (self.additional_identifiers or {}).get(identifier_type)

    def _set_additional_identifier(self, identifier_type, value):
        """ Write helper for adding identifier in the JSON.
        It validates, normalizes, deduce siblings and inserts the value.
        """
        self.ensure_one()
        if not identifier_type:
            return
        identifiers = self.additional_identifiers or {}
        if not value:
            identifiers.pop(identifier_type, None)
            self.additional_identifiers = identifiers
            return
        validation = self.env['res.partner']._validate_identifier(identifier_type, value, validation='error')  # possibly raises ValidationError
        normalized_value = validation['value']
        identifiers[identifier_type] = normalized_value  # set the normalized value
        deduced_identifiers = get_deduced_identifiers(identifier_type, normalized_value)
        self.additional_identifiers = {**identifiers, **deduced_identifiers}  # json needs to be fully reassigned each time

    def _get_all_identifiers(self, enrich=False):
        """Combined VAT + additional identifiers of the commercial partner.
        With `enrich`, also include identifiers derivable from the stored ones (e.g. FR_SIRET => FR_SIREN).
        """
        self.ensure_one()
        partner = self.commercial_partner_id
        identifiers = partner.additional_identifiers or {}
        if not is_identifier_void(partner.vat):
            key = get_tin_metadata_of_country(partner.country_code).get('key', 'TIN')
            identifiers = {key: partner.vat, **identifiers}
        enriched_identifiers = {}
        if enrich:
            for identifier_type, value in identifiers.items():
                enriched_identifiers.update(get_deduced_identifiers(identifier_type, value))
        return {**enriched_identifiers, **identifiers}

    @api.model
    def _get_all_identifiers_metadata(self):
        """ Returns a dict with the metadata of every known identifier: the TIN ones, which
        describe the generic `vat` field, plus the additional ones.
        Only override this to register an identifier that must NOT be added in
        `additional_identifiers` (e.g. a corner case scheme); in any other case override
        `_get_all_additional_identifiers_metadata` instead.
        """
        return {**TIN_METADATA, **self._get_all_additional_identifiers_metadata()}

    @api.model
    def _get_all_identifiers_metadata_by_scheme(self):
        return {
            metadata.get('scheme'): {'key': key, **metadata}
            for key, metadata in self._get_all_identifiers_metadata().items()
            if metadata.get('scheme')
        }

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        """ Returns a dict with the metadata of the identifiers available in `additional_identifiers`.
        TO BE OVERRIDDEN by modules that want to add or modify the default
        metadata. Entries added here are automatically picked up by
        `_get_all_identifiers_metadata`, hence used for validation, labels, etc.
        """
        return {**ADDITIONAL_IDENTIFIERS_METADATA}

    @api.model
    def _get_legal_entity_category_priority(self):
        return {'EN': 0, 'VAT': 1, 'TIN': 1, 'GST': 1, 'CN': 2}

    @api.model
    def _get_tax_category_priority(self):
        return {'VAT': 0, 'TIN': 0, 'GST': 0}

    @api.model
    def _get_identifier_label(self, identifier_key):
        """Return the label of an identifier given its key."""
        return self._get_all_identifiers_metadata().get(identifier_key, {}).get('label', '')

    def _get_preferred_legal_entity_identifier_vals(self):
        """Return a dict {'scheme': scheme, 'value': value, ...metadata} of the preferred legal entity identifier for the given partner.
        The selection is based on the following rules:
        1. It must be a legal entity identifier (e.g. company number, Tax ID, citizen card number).
        2. Among those, it picks the one with the lowest sequence, THEN the "best" category (see _get_legal_entity_category_priority).
        3. If no such identifier is found, an empty dict is returned.
        """
        self.ensure_one()
        partner = self.commercial_partner_id
        priorities = self._get_legal_entity_category_priority()
        identifier_vals = self._pick_preferred_identifier(
            partner._get_all_identifiers(enrich=True),
            filter_func=lambda k, v, m: m.get('category') in priorities or k == 'TIN',
            sort_key=lambda k, v, m: (m.get('sequence', 100), priorities.get(m.get('category'), 100)),
        )
        return identifier_vals or {}

    def _get_preferred_tax_identifier_vals(self):
        """Return a dict {'scheme': scheme, 'value': value, ...metadata} of the preferred tax identifier for the given partner.
        The selection is based on the following rules:
        1. It must be a valid tax identifier (e.g. company number, Tax ID).
        2. Among those, it picks the one with the "best" category (see _get_tax_category_priority), THEN ties with the sequence.
        3. If no such identifier is found, an empty dict is returned.
        """
        self.ensure_one()
        partner = self.commercial_partner_id
        priorities = self._get_tax_category_priority()
        identifier_vals = self._pick_preferred_identifier(
            partner._get_all_identifiers(enrich=True),
            filter_func=lambda k, v, m: m.get('category') in priorities or k == 'TIN',
            sort_key=lambda k, v, m: (priorities.get(m.get('category'), 100), m.get('sequence', 100)),
        )
        return identifier_vals or {}

    def _deduce_additional_identifiers_from_vat(self):
        """Populate companion identifiers freely derivable from the VAT (e.g. BE_VAT → BE_EN,
        AT_VAT → AT_EN) so users only enter the VAT and don't have to retype the same digits.
        Pre-existing entries are kept as-is and tracking is muted to avoid recomputing
        VAT-tracked computed fields mid-inverse."""
        for partner in self:
            if not partner.vat or not partner.country_code:
                continue
            vat_key = get_tin_metadata_of_country(partner.country_code).get('key')
            if not vat_key:
                continue
            deduced_identifiers = get_deduced_identifiers(vat_key, partner.vat)
            identifiers = partner.additional_identifiers or {}
            # Only keep deduced identifiers that are actually valid: a VAT does not always map to a
            # well-formed companion id (e.g. a 13-digit RO fiscal code is not a valid 10-digit CUI).
            new_identifiers = {
                k: v for k, v in deduced_identifiers.items()
                if k not in identifiers and self.env['res.partner']._validate_identifier(k, v)['valid']
            }
            if not new_identifiers:
                continue
            try:
                # Use mail_notrack to avoid triggering mail tracking, which would
                # recompute tracked computed fields (e.g. vies_valid) mid-inverse.
                partner.with_context(mail_notrack=True).additional_identifiers = {**identifiers, **new_identifiers}
            except ValidationError:
                _logger.info("Skipped %s: deduced identifier from %s could not be validated.", deduced_identifiers, vat_key)
                continue

    def _clean_additional_identifiers(self, vals):
        """ Pre-write filter on a `vals` dict:
        - drop unknown keys (with a warning log)
        - reject malformed values (raises ValidationError)
        - normalize
        - add deduced identifiers.
        Mutates `vals` in place.
        """
        if 'additional_identifiers' not in vals or not isinstance(vals['additional_identifiers'], dict):
            return vals
        cleaned = {}
        for key, value in vals['additional_identifiers'].items():
            if not self._get_all_additional_identifiers_metadata().get(key):
                _logger.warning(" Skipped %s: identifier %s is not in supported identifiers.", value, key)
                continue
            if not value:
                continue
            result = self.env['res.partner']._validate_identifier(key, value, validation='error')  # possibly raises ValidationError
            cleaned[key] = result['value']
        # Compute deduced identifiers (e.g. FR_SIRET => FR_SIREN). Only keep the well-formed ones.
        for key, value in list(cleaned.items()):
            for deduced_key, deduced_value in get_deduced_identifiers(key, value).items():
                if deduced_key not in cleaned and self.env['res.partner']._validate_identifier(deduced_key, deduced_value)['valid']:
                    cleaned[deduced_key] = deduced_value
        vals['additional_identifiers'] = cleaned

    def _deduce_country_code(self):
        """ deduce the country code based on the information available.
        we have three cases:
        - country_code is BE but the VAT number starts with FR, the country code is FR, not BE
        - if a country-specific field is set (e.g. the codice_fiscale), that country is used for the country code
        - if the VAT number has no ISO country code, use the country_code in that case.
        """
        self.ensure_one()
        _vat, country_code = self._run_vat_checks(self.country_id, self.vat, validation=False)
        return country_code or self.country_code

    # ============
    # VAT HELPERS
    # ============
    @api.model
    def _convert_hu_local_to_eu_vat(self, local_vat):
        if self._check_tin_hu_companies_re.match(local_vat) or self._check_tin_hu_european_re.match(local_vat):
            return f'HU{local_vat[:8]}'
        return False

    def _ie_check_char(self, vat):
        vat = vat.zfill(8)
        extra = 0
        if vat[7] not in ' W':
            if vat[7].isalpha():
                extra = 9 * (ord(vat[7]) - 64)
            else:
                # invalid
                return -1
        checksum = extra + sum((8 - i) * int(x) for i, x in enumerate(vat[:7]))
        return 'WABCDEFGHIJKLMNOPQRSTUV'[checksum % 23]

    _check_vat_al_re = re.compile(r'^[JKLM][0-9]{8}[A-Z]$')

    def check_vat_al(self, vat):
        """Check Albania VAT number"""
        number = split_vat(vat, default_country_code='al')[1]
        return len(number) == 10 and self._check_vat_al_re.match(number)

    # Minimal regex matching similar to stdnum
    # Derived from https://github.com/arthurdejong/python-stdnum/commit/d3ec3bd7fefe0d0a708b6594a66de28777eb9b8d
    __check_vat_br_re = re.compile(r'^[\dA-Z]+$')

    def check_vat_br(self, vat):
        def is_cnpj_valid(vat):
            vat = clean(vat, ' -./').strip().upper()
            if vat.startswith('000000000000') or len(vat) != 14:
                return False
            if self.__check_vat_br_re.match(vat):
                values = [ord(n) - 48 for n in vat[:12]]
                weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
                d1 = (11 - sum(w * v for w, v in zip(weights, values))) % 11 % 10
                values.append(d1)
                weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
                d2 = (11 - sum(w * v for w, v in zip(weights, values))) % 11 % 10
                return vat[-2:] == f'{d1}{d2}'
            return False

        is_cpf_valid = stdnum.get_cc_module('br', 'cpf').is_valid
        return is_cpf_valid(vat) or is_cnpj_valid(vat)

    _check_vat_ch_re = re.compile(r'E([0-9]{9}|-[0-9]{3}\.[0-9]{3}\.[0-9]{3})( )?(MWST|TVA|IVA)$')

    def check_vat_ch(self, vat):
        '''
        Check Switzerland VAT number.
        '''
        # A new VAT number format in Switzerland has been introduced between 2011 and 2013
        # https://www.estv.admin.ch/estv/fr/home/mehrwertsteuer/fachinformationen/steuerpflicht/unternehmens-identifikationsnummer--uid-.html
        # The old format "TVA 123456" is not valid since 2014
        # Accepted format are: (spaces are ignored)
        #     CHE#########MWST
        #     CHE#########TVA
        #     CHE#########IVA
        #     CHE-###.###.### MWST
        #     CHE-###.###.### TVA
        #     CHE-###.###.### IVA
        #
        # /!\ The english abbreviation VAT is not valid /!\

        match = self._check_vat_ch_re.match(vat)
        if match:
            # For new TVA numbers, the last digit is a MOD11 checksum digit build with weighting pattern: 5,4,3,2,7,6,5,4
            num = [s for s in match.group(1) if s.isdigit()]        # get the digits only
            factor = (5, 4, 3, 2, 7, 6, 5, 4)
            csum = sum(int(num[i]) * factor[i] for i in range(8))
            check = (11 - (csum % 11)) % 11
            return check == int(num[8])
        return False

    _check_vat_cr_re = re.compile(r'^(?:[1-9]\d{8}|\d{10}|[1-9]\d{10,11})$')

    def check_vat_cr(self, vat):
        # CÉDULA FÍSICA: 9 digits
        # CÉDULA JURÍDICA: 10 digits
        # CÉDULA DIMEX: 11 or 12 digits
        # CÉDULA NITE: 10 digits

        return self._check_vat_cr_re.match(vat) or False

    def check_vat_de(self, vat):
        is_valid_vat = stdnum.util.get_cc_module("de", "vat").is_valid
        is_valid_stnr = stdnum.util.get_cc_module("de", "stnr").is_valid
        return is_valid_vat(vat) or is_valid_stnr(vat)

    def check_vat_do(self, vat):
        is_valid_vat = stdnum.util.get_cc_module("do", "vat").is_valid
        is_valid_cedula = stdnum.util.get_cc_module("do", "cedula").is_valid
        return is_valid_vat(vat) or is_valid_cedula(vat)

    def check_vat_ec(self, vat):
        vat = clean(vat, ' -.').upper().strip()
        return self.is_valid_ruc_ec(vat)

    def check_vat_gr(self, vat):
        """ Allows some custom test VAT number to be valid to allow testing Greece EDI. """
        gr_vat = stdnum.util.get_cc_module('gr', 'vat')
        vat = gr_vat.compact(vat)
        greece_test_vats = ('047747270', '047747210', '047747220', '117747270', '127747270')
        if vat in greece_test_vats:
            return True
        return gr_vat.is_valid(vat)

    # Our EDI provider Infile has designated this range of testing VATs for our customers.
    __check_vat_gt_testing_infile = re.compile(r'98[0-9]{10}K')

    def check_vat_gt(self, vat):
        """
        Allow some custom Guatemala NIT numbers to pass the test to be used for testing the Guatemalan EDI.
        """
        guatemalan_test_vats = ('11201220K', '11201350K')
        if vat in guatemalan_test_vats or self.__check_vat_gt_testing_infile.match(vat):
            return True
        return stdnum.util.get_cc_module('gt', 'vat').is_valid(vat)

    _check_tin_hu_individual_re = re.compile(r'^8\d{9}$')
    _check_tin_hu_companies_re = re.compile(r'^\d{8}-?[1-5]-?\d{2}$')
    _check_tin_hu_european_re = re.compile(r'^\d{8}$')

    def check_vat_hu(self, vat):
        """
            Check Hungary VAT number that can be for example 'HU12345676 or 'xxxxxxxx-y-zz' or '8xxxxxxxxy'

            - For xxxxxxxx-y-zz, 'x' can be any number, 'y' is a number between 1 and 5 depending on the person and the 'zz'
              is used for region code.
            - 8xxxxxxxxy, Tin number for individual, it has to start with an 8 and finish with the check digit
            - In case of EU format it will be the first 8 digits of the full VAT
        """
        companies = self._check_tin_hu_companies_re.match(vat)
        if companies:
            return True
        individual = self._check_tin_hu_individual_re.match(vat)
        if individual:
            return True
        european = self._check_tin_hu_european_re.match(vat)
        if european:
            return True
        # Check the vat number
        return stdnum.util.get_cc_module('hu', 'vat').is_valid(vat)

    def check_vat_id(self, vat):
        """ Temporary Indonesian VAT validation to support the new format
        introduced in January 2024."""
        vat = clean(vat, ' -.').strip()

        if len(vat) not in (15, 16) or not vat.isdecimal():
            return False

        # VAT could be 15 (old numbers) or 16 digits. If there are 15 digits long, the 10th digit is a luhn checksum
        # In some cases, the 15 digits can be transformed in a 16-digit by adding a 0 in front. In such case, we
        # we can verify the luhn checksum like for the 15 digits by removing the 0.
        # However, for newly created VAT 16-digits VAT number, there is no checksum.
        if (len(vat) == 16 and vat[0] != '0'):
            return True

        try:
            luhn.validate(vat[0:9] if len(vat) == 15 else vat[1:10])
        except (InvalidFormat, InvalidChecksum):
            return False

        return True

    # TODO: remove in master
    def check_vat_ie(self, vat):
        return stdnum.util.get_cc_module('ie', 'vat').is_valid(vat)

    def check_vat_il(self, vat):
        check_func = stdnum.util.get_cc_module('il', 'idnr').is_valid
        return check_func(vat)

    def check_vat_in(self, vat):
        # reference from https://www.gstzen.in/a/format-of-a-gst-number-gstin.html
        if vat and len(vat) == 15:
            all_gstin_re = [
                r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[Z1-9A-J]{1}[0-9A-Z]{1}',  # Normal, Composite, Casual GSTIN
                r'[0-9]{4}[A-Z]{3}[0-9]{5}[UO]{1}[N][A-Z0-9]{1}',  # UN/ON Body GSTIN
                r'[0-9]{4}[A-Z]{3}[0-9]{5}[A-Z]{3}',  # Revised NRI GSTIN
                r'[0-9]{4}[A-Z]{3}[0-9]{5}[N][R][0-9A-Z]{1}',  # NRI GSTIN
                r'[0-9]{2}[A-Z]{4}[A-Z0-9]{1}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[DK]{1}[0-9A-Z]{1}',  # TDS GSTIN
                r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}[C]{1}[0-9A-Z]{1}'  # TCS GSTIN
            ]
            return any(re.compile(rx).match(vat) for rx in all_gstin_re)
        return False

    def check_vat_jp(self, vat):
        if vat and vat[0] == 'T':
            vat = vat[1:]
        return stdnum.util.get_cc_module('jp', 'vat').is_valid(vat)

    def check_vat_ma(self, vat):
        return vat.isdigit() and len(vat) == 8

    # Mexican VAT verification, contributed by Vauxoo
    # and Panos Christeas <p_christ@hol.gr>
    _check_vat_mx_re = re.compile(r"(?P<primeras>[A-Za-z\xd1\xf1&]{3,4})"
                                   r"[ \-_]?"
                                   r"(?P<ano>[0-9]{2})(?P<mes>[01][0-9])(?P<dia>[0-3][0-9])"
                                   r"[ \-_]?"
                                   r"(?P<code>[A-Za-z0-9&\xd1\xf1]{3})")

    def check_vat_mx(self, vat):
        ''' Mexican VAT verification

        Verificar RFC México
        '''
        m = self._check_vat_mx_re.fullmatch(vat)
        if not m:
            # No valid format
            return False
        ano = int(m['ano'])
        if ano > 30:
            ano = 1900 + ano
        else:
            ano = 2000 + ano
        try:
            datetime.date(ano, int(m['mes']), int(m['dia']))
        except ValueError:
            return False

        # Valid format and valid date
        return True

    # Norway VAT validation, contributed by Rolv Råen (adEgo) <rora@adego.no>
    # Support for MVA suffix contributed by Bringsvor Consulting AS (bringsvor@bringsvor.com)
    def check_vat_no(self, vat):
        """
        Check Norway VAT number.See http://www.brreg.no/english/coordination/number.html
        """
        if len(vat) == 12 and vat.upper().endswith('MVA'):
            vat = vat[:-3]  # Strictly speaking we should enforce the suffix MVA but...

        if len(vat) != 9:
            return False
        try:
            int(vat)
        except ValueError:
            return False

        sum = (3 * int(vat[0])) + (2 * int(vat[1])) + \
            (7 * int(vat[2])) + (6 * int(vat[3])) + \
            (5 * int(vat[4])) + (4 * int(vat[5])) + \
            (3 * int(vat[6])) + (2 * int(vat[7]))

        check = 11 - (sum % 11)
        if check == 11:
            check = 0
        if check == 10:
            # 10 is not a valid check digit for an organization number
            return False
        return check == int(vat[8])

    # Peruvian VAT validation, contributed by Vauxoo
    def check_vat_pe(self, vat):
        if len(vat) != 11 or not vat.isdigit():
            return False
        dig_check = 11 - (sum(int('5432765432'[f]) * int(vat[f]) for f in range(0, 10)) % 11)
        if dig_check == 10:
            dig_check = 0
        elif dig_check == 11:
            dig_check = 1
        return int(vat[10]) == dig_check

    # Philippines TIN (+ branch code) validation
    _check_vat_ph_re = re.compile(r"\d{3}-\d{3}-\d{3}(-\d{3,5})?$")

    def check_vat_ph(self, vat):
        return len(vat) >= 11 and len(vat) <= 17 and self._check_vat_ph_re.match(vat)

    def check_vat_pk(self, vat):
        # NTN (7 digits, or 7 + 1 check digit) or CNIC (13 digits): 1234567, 1234567-8, 12345-1234567-8.
        return bool(re.fullmatch(r'\d{7}|\d{8}|\d{13}', (vat or '').replace('-', '').replace(' ', '')))

    _check_tin1_ro_natural_persons = re.compile(r'[1-9]\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{6}')
    _check_tin2_ro_natural_persons = re.compile(r'9000\d{9}')

    def check_vat_ro(self, vat):
        """
            Check Romanian VAT number that can be for example 'RO1234567897 or 'xyyzzaabbxxxx' or '9000xxxxxxxx'.

            - For xyyzzaabbxxxx, 'x' can be any number, 'y' is the two last digit of a year (in the range 00…99),
              'a' is a month, b is a day of the month, the number 8 and 9 are Country or district code
              (For those twos digits, we decided to let some flexibility  to avoid complexifying the regex and also
              for maintainability)
            - 9000xxxxxxxx, start with 9000 and then is filled by number In the range 0...9

            Also stdum also checks the CUI or CIF (Romanian company identifier). So a number like '123456897' will pass.
        """
        tin1 = self._check_tin1_ro_natural_persons.match(vat)
        if tin1:
            return True
        tin2 = self._check_tin2_ro_natural_persons.match(vat)
        if tin2:
            return True
        # Check the vat number
        return stdnum.util.get_cc_module('ro', 'vat').is_valid(vat)

    # VAT validation in Serbia
    def check_vat_rs(self, vat):
        vat = vat.removeprefix('RS')
        return stdnum.util.get_cc_module('rs', 'vat').is_valid(vat)

    _check_vat_sa_re = re.compile(r"^3[0-9]{13}3$")

    # Saudi Arabia TIN validation
    def check_vat_sa(self, vat):
        """
            Check company VAT TIN according to ZATCA specifications: The VAT number should start and begin with a '3'
            and be 15 digits long
        """
        return self._check_vat_sa_re.match(vat) or False

    def check_vat_th(self, vat):
        check_func = stdnum.util.get_cc_module('th', 'tin').is_valid
        return check_func(vat)

    # VAT validation in Turkey
    def check_vat_tr(self, vat):
        return stdnum.util.get_cc_module('tr', 'tckimlik').is_valid(vat) or stdnum.util.get_cc_module('tr', 'vkn').is_valid(vat)

    def check_vat_tw(self, vat):
        """
        Since Feb. 2025, due to the imminent exhaustion of the UBN numbers, the validation logic was changed from using
        a division by 10 for the final check to using a division by 5, making numbers that were previously invalid now
        valid.

        The stdnum implementation of the VAT validation is not up to date with this latest update, so we implement our
        own validation to support these new valid UBNs.
        """
        vat = stdnum.util.get_cc_module("tw", "vat").compact(vat)
        if len(vat) != 8 or not vat.isdigit():
            return False  # The length is fixed, and we will expect it to be 8 in the following checks.

        logic_multiplier = [1, 2, 1, 2, 1, 2, 4, 1]  # This multiplier is set by the official validation logic.
        # Multiply each of the 8 digits of the VAT number by the corresponding digit of the logic multiplier.
        # For the next steps, we will need to sum the results.
        # For a two-digit product like 20, you would add its digits (2 + 0) to the total sum, so we convert the sums here
        # to strings in order to make it easier later on.
        products = [str(a * int(b)) for a, b in zip(logic_multiplier, vat)]
        if vat[6] != '7':
            # If the 7th number is not 7, we simply sum everything and check that the result is divisible by 5.
            checksum = sum(int(d) for d in ''.join(products))
            return checksum % 5 == 0
        else:
            # If the 7th number is 7, we calculate two sums:
            # z1: Calculate the total sum where the 7th position's contribution is taken as 1.
            # z2: Calculate the total sum where the 7th position's contribution is taken as 0.
            # The VAT number is valid if either Z1 or Z2 (or both) is evenly divisible by 5.
            base_checksum = sum(int(d) for d in "".join(products[0:6] + products[7:]))
            return (base_checksum + 1) % 5 == 0 or base_checksum % 5 == 0

    def check_vat_ua(self, vat):
        return len(vat[2:] if vat.startswith('UA') else vat) in {8, 10, 12}

    def check_vat_uy(self, vat):
        """ Taken from python-stdnum's master branch, as the release doesn't handle RUT numbers starting with 22.
        origin https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/uy/rut.py
        FIXME Can be removed when python-stdnum does a new release. """

        def calc_check_digit(number):
            """Calculate the check digit."""
            weights = (4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
            total = sum(int(n) * w for w, n in zip(weights, number))
            return str(-total % 11)

        vat = split_vat(vat, default_country_code='UY')[1]

        return (
            vat.isdigit()  # InvalidFormat
            and len(vat) == 12  # InvalidLength
            and '01' <= vat[:2] <= '22'  # InvalidComponent
            and vat[2:8] != '000000'
            and vat[8:11] == '001'
            and vat[-1] == calc_check_digit(vat)  # Invalid Check Digit
        )

    def check_vat_uz(self, vat):
        return vat.isdigit() and len(vat) in (9, 14)

    def check_vat_ve(self, vat):
        # https://tin-check.com/en/venezuela/
        # https://techdocs.broadcom.com/us/en/symantec-security-software/information-security/data-loss-prevention/15-7/About-content-packs/What-s-included-in-Content-Pack-2021-02/Updated-data-identifiers-in-Content-Pack-2021-02/venezuela-national-identification-number-v115451096-d327e108002-CP2021-02.html
        # Sources last visited on 2022-12-09

        # VAT format: (kind - 1 letter)(identifier number - 8-digit number)(check digit - 1 digit)
        vat_regex = re.compile(r"""
            ([vecjpg])                          # group 1 - kind
            (
                (?P<optional_1>-)?                      # optional '-' (1)
                [0-9]{2}
                (?(optional_1)(?P<optional_2>[.])?)     # optional '.' (2) only if (1)
                [0-9]{3}
                (?(optional_2)[.])                      # mandatory '.' if (2)
                [0-9]{3}
                (?(optional_1)-)                        # mandatory '-' if (1)
            )                                   # group 2 - identifier number
            ([0-9]{1})                          # group X - check digit
        """, re.VERBOSE | re.IGNORECASE)

        matches = re.fullmatch(vat_regex, vat)
        if not matches:
            return False

        kind, identifier_number, *_, check_digit = matches.groups()
        kind = kind.lower()
        identifier_number = identifier_number.replace("-", "").replace(".", "")
        check_digit = int(check_digit)

        if kind == 'v':                   # Venezuela citizenship
            kind_digit = 1
        elif kind == 'e':                 # Foreigner
            kind_digit = 2
        elif kind == 'c' or kind == 'j':  # Township/Communal Council or Legal entity
            kind_digit = 3
        elif kind == 'p':                 # Passport
            kind_digit = 4
        else:                             # Government ('g')
            kind_digit = 5

        # === Checksum validation ===
        multipliers = [3, 2, 7, 6, 5, 4, 3, 2]
        checksum = kind_digit * 4
        checksum += sum(map(lambda n, m: int(n) * m, identifier_number, multipliers))

        checksum_digit = 11 - checksum % 11
        if checksum_digit > 9:
            checksum_digit = 0

        return check_digit == checksum_digit

    __check_vat_vn_re = re.compile(r'^\d{10}(?:-?\d{3})?$|^\d{12}$')
    __check_vat_vn_companies_re = re.compile(r'^\d{10}(?:-?\d{3})?$')

    def check_vat_vn(self, vat):
        """
        VAT format validator for Vietnam.
        Supported formats:
        - 10-digit format (Enterprise tax ID): e.g., 0101243150
        - 13-digit format with branch suffix: e.g., 0101243150-001
        - 12-digit format (Personal ID / Citizen ID - CCCD): e.g., 079123456789
        (used as tax ID for individuals from July 1st, 2025)

        Note:
        - stdnum.vn.mst.validate() currently only supports 10- and 13-digit VAT numbers
        - and does not accept the 12-digit personal tax ID (CCCD) format introduced from 01/07/2025.
        - This helper provides a lightweight format-level validator for use in the meantime.
        - Can be removed once stdnum.vn.mst adds CCCD support.
        """
        vat = vat.strip()
        return bool(self.__check_vat_vn_re.match(vat))

    def format_vat_al(self, vat):
        vat_prefix, vat_number = split_vat(vat)
        stdnum_vat_format = stdnum.util.get_cc_module('al', 'nipt').compact
        vat_number = stdnum_vat_format(vat_number)
        return f'{vat_prefix}{vat_number}'

    def format_vat_ca(self, vat):
        """Normalize the case of a Canadian Business Number (BN).

        Two forms are accepted:
          9 digits, the business number itself, for example 123456782
          9 digits followed by a 2 letter program identifier and a 4 digit
          reference number, for example 123456782RT0001

        The program identifier tells which account the number refers to.
        RT is goods and services tax, RP is payroll, RC is corporate income
        tax and RM is import and export. It is always written in upper case,
        but stdnum keeps the case as it was typed and then rejects a lower
        case identifier, so upper case the number before compacting it.
        """
        return stdnum.get_cc_module('ca', 'bn').compact(vat.upper())

    def format_vat_ch(self, vat):
        stdnum_vat_format = stdnum.util.get_cc_module('ch', 'vat').format
        return stdnum_vat_format('CH' + vat)[2:]

    def format_vat_cl(self, vat):
        """ It is better to always have the -"""
        vat = vat.replace('.', '').replace('CL', '').replace(' ', '').replace('-', '').upper()
        if len(vat) > 2:
            return vat[:-1] + '-' + vat[-1]
        return vat

    def format_vat_co(self, vat):
        """ It is better to always have the -"""
        stdnum_vat_format = stdnum.util.get_cc_module('co', 'vat').format
        vat = stdnum_vat_format(vat).replace('.', '').replace('-', '')
        if len(vat) > 2:
            return vat[:-1] + '-' + vat[-1]
        return vat

    def format_vat_eu(self, vat):
        # Foreign companies that trade with non-enterprises in the EU
        # may have a VATIN starting with "EU" instead of a country code.
        return vat

    def format_vat_hu(self, vat):
        """ We put the - back as we require it for the EDI and the different parts will make it clear to the user"""
        vat = split_vat(vat, default_country_code='hu')[1]
        if self._check_tin_hu_companies_re.match(vat):
            vat = vat[:8] + '-' + vat[8] + '-' + vat[9] + vat[10]
        return vat

    def format_vat_is(self, vat):
        vat_prefix, vat_number = split_vat(vat)
        stdnum_vat_format = stdnum.util.get_cc_module('is_', 'vsk').compact
        vat_number = stdnum_vat_format(vat_number)
        return f'{vat_prefix}{vat_number}'

    def format_vat_pk(self, vat):
        vat = (vat or '').replace('-', '').replace(' ', '')
        if len(vat) == 8:
            return f'{vat[:-1]}-{vat[-1]}'
        if len(vat) == 13:
            return f'{vat[:5]}-{vat[5:12]}-{vat[12]}'
        return vat

    def format_vat_sm(self, vat):
        stdnum_vat_format = stdnum.util.get_cc_module('sm', 'vat').compact
        return stdnum_vat_format('SM' + vat)[2:]

    def format_vat_vn(self, vat):
        """ It is better to always have the -"""
        stdnum_vat_format = stdnum.util.get_cc_module('vn', 'vat').format
        if self.__check_vat_vn_companies_re.match(vat):
            return stdnum_vat_format(vat)
        else:
            return vat

    def is_valid_ruc_ec(self, vat):
        return len(vat) in (10, 13) and vat.isdecimal()


class ResPartnerIndustry(models.Model):
    _name = 'res.partner.industry'
    _description = 'Industry'
    _order = "name, id"

    name = fields.Char('Name', translate=True)
    full_name = fields.Char('Full Name', translate=True)
    active = fields.Boolean('Active', default=True)
