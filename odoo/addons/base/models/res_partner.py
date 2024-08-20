# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import collections
import datetime
import hashlib
import pytz
import re

import requests
from collections import defaultdict
from random import randint
from werkzeug import urls

from odoo import api, fields, models, tools, SUPERUSER_ID, _, Command
from odoo.exceptions import RedirectWarning, UserError, ValidationError

# Global variables used for the warning fields declared on the res.partner
# in the following modules : sale, purchase, account, stock
WARNING_MESSAGE = [
                   ('no-message','No Message'),
                   ('warning','Warning'),
                   ('block','Blocking Message')
                   ]
WARNING_HELP = 'Selecting the "Warning" option will notify user with the message, Selecting "Blocking Message" will throw an exception with the message and block the flow. The Message has to be written in the next field.'


ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')
@api.model
def _lang_get(self):
    return self.env['res.lang'].get_installed()


# put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs


class FormatVATLabelMixin(models.AbstractModel):
    _name = "format.vat.label.mixin"
    _description = "Country Specific VAT Label"

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if vat_label := self.env.company.country_id.vat_label:
            for node in arch.iterfind(".//field[@name='vat']"):
                node.set("string", vat_label)
            # In some module vat field is replaced and so above string change is not working
            for node in arch.iterfind(".//label[@for='vat']"):
                node.set("string", vat_label)
        return arch, view

class FormatAddressMixin(models.AbstractModel):
    _name = "format.address.mixin"
    _description = 'Address Format'

    def _view_get_address(self, arch):
        # consider the country of the user, not the country of the partner we want to display
        address_view_id = self.env.company.country_id.address_view_id.sudo()
        address_format = self.env.company.country_id.address_format
        if address_view_id and not self._context.get('no_address_format') and (not address_view_id.model or address_view_id.model == self._name):
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
                address_node.getparent().replace(address_node, sub_arch)
        elif address_format and not self._context.get('no_address_format'):
            # For the zip, city and state fields we need to move them around in order to follow the country address format.
            # The purpose of this is to help the user by following a format he is used to.
            city_line = [line.split(' ') for line in address_format.split('\n') if 'city' in line]
            if city_line:
                field_order = [field.replace('%(', '').replace(')s', '') for field in city_line[0]]
                for address_node in arch.xpath("//div[hasclass('o_address_format')]"):
                    concerned_fields = {'zip', 'city', 'state_id'} - {field_order[0]}
                    current_field = address_node.find(f".//field[@name='{field_order[0]}']")
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
        return key + (self.env.company, self._context.get('no_address_format'),)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view.type == 'form':
            arch = self._view_get_address(arch)
        return arch, view


class PartnerCategory(models.Model):
    _description = 'Partner Tags'
    _name = 'res.partner.category'
    _order = 'name'
    _parent_store = True

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True, translate=True)
    display_name = fields.Char('Display Name', compute='_compute_display_name', search='_search_display_name')
    color = fields.Integer(string='Color', default=_get_default_color, aggregator=False)
    parent_id = fields.Many2one('res.partner.category', string='Category', index=True, ondelete='cascade')
    child_ids = fields.One2many('res.partner.category', 'parent_id', string='Child Tags')
    active = fields.Boolean(default=True, help="The active field allows you to hide the category without removing it.")
    parent_path = fields.Char(index=True)
    partner_ids = fields.Many2many('res.partner', column1='category_id', column2='partner_id', string='Partners', copy=False)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You can not create recursive tags.'))

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
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            # Be sure name_search is symetric to display_name
            name = name.split(' / ')[-1]
            domain = [('name', operator, name)] + domain
        return self._search(domain, limit=limit, order=order)

    @api.model
    def _search_display_name(self, operator, value):
        return [('id', 'child_of', self._search([('name', operator, value)]))]

class PartnerTitle(models.Model):
    _name = 'res.partner.title'
    _order = 'name'
    _description = 'Partner Title'

    name = fields.Char(string='Title', required=True, translate=True)
    shortcut = fields.Char(string='Abbreviation', translate=True)


class Partner(models.Model):
    _description = 'Contact'
    _inherit = ['format.address.mixin', 'format.vat.label.mixin', 'avatar.mixin']
    _name = "res.partner"
    _order = "complete_name ASC, id DESC"
    _rec_names_search = ['complete_name', 'email', 'ref', 'vat', 'company_registry']  # TODO vat must be sanitized the same way for storing/searching
    _allow_sudo_commands = False
    _check_company_domain = models.check_company_domain_parent_of

    # the partner types that must be added to a partner's complete name, like "Delivery"
    _complete_name_displayed_types = ('invoice', 'delivery', 'other')

    def _default_category(self):
        return self.env['res.partner.category'].browse(self._context.get('category_id'))

    @api.model
    def default_get(self, default_fields):
        """Add the company of the parent as default if we are creating a child partner.
        Also take the parent lang by default if any, otherwise, fallback to default DB lang."""
        values = super().default_get(default_fields)
        parent = self.env["res.partner"]
        if 'parent_id' in default_fields and values.get('parent_id'):
            parent = self.browse(values.get('parent_id'))
            values['company_id'] = parent.company_id.id
        if 'lang' in default_fields:
            values['lang'] = values.get('lang') or parent.lang or self.env.lang
        # protection for `default_type` values leaking from menu action context (e.g. for crm's email)
        if 'type' in default_fields and values.get('type'):
            if values['type'] not in self._fields['type'].get_values(self.env):
                values['type'] = None
        return values

    name = fields.Char(index=True, default_export_compatible=True)
    complete_name = fields.Char(compute='_compute_complete_name', store=True, index=True)
    title = fields.Many2one('res.partner.title')
    parent_id = fields.Many2one('res.partner', string='Related Company', index=True)
    parent_name = fields.Char(related='parent_id.name', readonly=True, string='Parent name')
    child_ids = fields.One2many('res.partner', 'parent_id', string='Contact', domain=[('active', '=', True)])
    ref = fields.Char(string='Reference', index=True)
    lang = fields.Selection(_lang_get, string='Language',
                            help="All the emails and documents sent to this contact will be translated in this language.")
    active_lang_count = fields.Integer(compute='_compute_active_lang_count')
    tz = fields.Selection(_tzs, string='Timezone', default=lambda self: self._context.get('tz'),
                          help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
                               "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
                               "Anywhere else, time values are computed according to the time offset of your web client.")

    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset')
    user_id = fields.Many2one(
        'res.users', string='Salesperson',
        compute='_compute_user_id',
        precompute=True,  # avoid queries post-create
        readonly=False, store=True,
        help='The internal user in charge of this contact.')
    vat = fields.Char(string='Tax ID', index=True, help="The Tax Identification Number. Values here will be validated based on the country format. You can use '/' to indicate that the partner is not subject to tax.")
    same_vat_partner_id = fields.Many2one('res.partner', string='Partner with same Tax ID', compute='_compute_same_vat_partner_id', store=False)
    same_company_registry_partner_id = fields.Many2one('res.partner', string='Partner with same Company Registry', compute='_compute_same_vat_partner_id', store=False)
    company_registry = fields.Char(string="Company ID", compute='_compute_company_registry', store=True, readonly=False,
       help="The registry number of the company. Use it if it is different from the Tax ID. It must be unique across all partners of a same country")
    bank_ids = fields.One2many('res.partner.bank', 'partner_id', string='Banks')
    website = fields.Char('Website Link')
    comment = fields.Html(string='Notes')

    category_id = fields.Many2many('res.partner.category', column1='partner_id',
                                    column2='category_id', string='Tags', default=_default_category)
    active = fields.Boolean(default=True)
    employee = fields.Boolean(help="Check this box if this contact is an Employee.")
    function = fields.Char(string='Job Position')
    type = fields.Selection(
        [('contact', 'Contact'),
         ('invoice', 'Invoice Address'),
         ('delivery', 'Delivery Address'),
         ('other', 'Other Address'),
        ], string='Address Type',
        default='contact')
    # address fields
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    country_code = fields.Char(related='country_id.code', string="Country Code")
    partner_latitude = fields.Float(string='Geo Latitude', digits=(10, 7))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(10, 7))
    email = fields.Char()
    email_formatted = fields.Char(
        'Formatted Email', compute='_compute_email_formatted',
        help='Format email address "Name <email@domain>"')
    phone = fields.Char()
    mobile = fields.Char()
    is_company = fields.Boolean(string='Is a Company', default=False,
        help="Check if the contact is a company, otherwise it is a person")
    is_public = fields.Boolean(compute='_compute_is_public')
    industry_id = fields.Many2one('res.partner.industry', 'Industry')
    # company_type is only an interface field, do not use it in business logic
    company_type = fields.Selection(string='Company Type',
        selection=[('person', 'Individual'), ('company', 'Company')],
        compute='_compute_company_type', inverse='_write_company_type')
    company_id = fields.Many2one('res.company', 'Company', index=True)
    color = fields.Integer(string='Color Index', default=0)
    user_ids = fields.One2many('res.users', 'partner_id', string='Users', auto_join=True)
    partner_share = fields.Boolean(
        'Share Partner', compute='_compute_partner_share', store=True,
        help="Either customer (not a user), either shared user. Indicated the current partner is a customer without "
             "access or with a limited access created for sharing data.")
    contact_address = fields.Char(compute='_compute_contact_address', string='Complete Address')

    # technical field used for managing commercial fields
    commercial_partner_id = fields.Many2one(
        'res.partner', string='Commercial Entity',
        compute='_compute_commercial_partner', store=True,
        recursive=True, index=True)
    commercial_company_name = fields.Char('Company Name Entity', compute='_compute_commercial_company_name',
                                          store=True)
    company_name = fields.Char('Company Name')
    barcode = fields.Char(help="Use a barcode to identify this contact.", copy=False, company_dependent=True)

    # hack to allow using plain browse record in qweb views, and used in ir.qweb.field.contact
    self = fields.Many2one(comodel_name=_name, compute='_compute_get_ids')

    _sql_constraints = [
        ('check_name', "CHECK( (type='contact' AND name IS NOT NULL) or (type!='contact') )", 'Contacts require a name'),
    ]

    def _get_street_split(self):
        self.ensure_one()
        return tools.street_split(self.street or '')

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
        partners_with_internal_user = self.filtered(lambda partner: partner.user_ids - partner.user_ids.filtered('share'))
        super(Partner, partners_with_internal_user)._compute_avatar(avatar_field, image_field)
        partners_without_image = (self - partners_with_internal_user).filtered(lambda p: not p[image_field])
        for _, group in tools.groupby(partners_without_image, key=lambda p: p._avatar_get_placeholder_path()):
            group_partners = self.env['res.partner'].concat(*group)
            group_partners[avatar_field] = base64.b64encode(group_partners[0]._avatar_get_placeholder())

        for partner in self - partners_with_internal_user - partners_without_image:
            partner[avatar_field] = partner[image_field]

    def _avatar_get_placeholder_path(self):
        if self.is_company:
            return "base/static/img/company_image.png"
        if self.type == 'delivery':
            return "base/static/img/truck.png"
        if self.type == 'invoice':
            return "base/static/img/money.png"
        return super()._avatar_get_placeholder_path()

    @api.depends('is_company', 'name', 'parent_id.name', 'type', 'company_name', 'commercial_company_name')
    def _compute_complete_name(self):
        displayed_types = self._complete_name_displayed_types
        # determine the labels of partner types to be included
        # as 'displayed_types' (without user lang to avoid context dependency)
        type_description = dict(self._fields['type']._description_selection(self.with_context({}).env))

        for partner in self:
            name = partner.name or ''
            if partner.company_name or partner.parent_id:
                if not name and partner.type in displayed_types:
                    name = type_description[partner.type]
                if not partner.is_company:
                    name = f"{partner.commercial_company_name or partner.sudo().parent_id.name}, {name}"

            partner.complete_name = name.strip()

    @api.depends('lang')
    def _compute_active_lang_count(self):
        lang_count = len(self.env['res.lang'].get_installed())
        for partner in self:
            partner.active_lang_count = lang_count

    @api.depends('tz')
    def _compute_tz_offset(self):
        for partner in self:
            partner.tz_offset = datetime.datetime.now(pytz.timezone(partner.tz or 'GMT')).strftime('%z')

    @api.depends('parent_id')
    def _compute_user_id(self):
        """ Synchronize sales rep with parent if partner is a person """
        for partner in self.filtered(lambda partner: not partner.user_id and partner.company_type == 'person' and partner.parent_id.user_id):
            partner.user_id = partner.parent_id.user_id

    @api.depends('user_ids.share', 'user_ids.active')
    def _compute_partner_share(self):
        super_partner = self.env['res.users'].browse(SUPERUSER_ID).partner_id
        if super_partner in self:
            super_partner.partner_share = False
        for partner in self - super_partner:
            partner.partner_share = not partner.user_ids or not any(not user.share for user in partner.user_ids)

    @api.depends('vat', 'company_id', 'company_registry')
    def _compute_same_vat_partner_id(self):
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            #active_test = False because if a partner has been deactivated you still want to raise the error,
            #so that you can reactivate it instead of creating a new one, which would loose its history.
            Partner = self.with_context(active_test=False).sudo()
            domain = [
                ('vat', '=', partner.vat),
            ]
            if partner.company_id:
                domain += [('company_id', 'in', [False, partner.company_id.id])]
            if partner_id:
                domain += [('id', '!=', partner_id), '!', ('id', 'child_of', partner_id)]
            # For VAT number being only one character, we will skip the check just like the regular check_vat
            should_check_vat = partner.vat and len(partner.vat) != 1
            partner.same_vat_partner_id = should_check_vat and not partner.parent_id and Partner.search(domain, limit=1)
            # check company_registry
            domain = [
                ('company_registry', '=', partner.company_registry),
                ('company_id', 'in', [False, partner.company_id.id]),
            ]
            if partner_id:
                domain += [('id', '!=', partner_id), '!', ('id', 'child_of', partner_id)]
            partner.same_company_registry_partner_id = bool(partner.company_registry) and not partner.parent_id and Partner.search(domain, limit=1)

    @api.depends(lambda self: self._display_address_depends())
    def _compute_contact_address(self):
        for partner in self:
            partner.contact_address = partner._display_address()

    def _compute_get_ids(self):
        for partner in self:
            partner.self = partner.id

    @api.depends('is_company', 'parent_id.commercial_partner_id')
    def _compute_commercial_partner(self):
        for partner in self:
            if partner.is_company or not partner.parent_id:
                partner.commercial_partner_id = partner
            else:
                partner.commercial_partner_id = partner.parent_id.commercial_partner_id

    @api.depends('company_name', 'parent_id.is_company', 'commercial_partner_id.name')
    def _compute_commercial_company_name(self):
        for partner in self:
            p = partner.commercial_partner_id
            partner.commercial_company_name = p.is_company and p.name or partner.company_name

    def _compute_company_registry(self):
        # exists to allow overrides
        for company in self:
            company.company_registry = company.company_registry

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive Partner hierarchies.'))

    @api.constrains('company_id')
    def _check_partner_company(self):
        for partner in self:
            if partner.is_company and partner.company_id:
                related_company = self.env['res.company'].search([
                    ('partner_id', '=', partner.id)
                ], limit=1)

                if related_company and partner.company_id != related_company.id:
                    raise ValidationError(
                        "The company assigned to this partner does not match the company this partner represents."
                    )

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if default.get('name'):
            return vals_list
        return [dict(vals, name=_("%s (copy)", partner.name)) for partner, vals in zip(self, vals_list)]

    @api.onchange('parent_id')
    def onchange_parent_id(self):
        # return values in result, as this method is used by _fields_sync()
        if not self.parent_id:
            return
        result = {}
        partner = self._origin
        if partner.parent_id and partner.parent_id != self.parent_id:
            result['warning'] = {
                'title': _('Warning'),
                'message': _('Changing the company of a contact should only be done if it '
                             'was never correctly set. If an existing contact starts working for a new '
                             'company then a new contact should be created under that new '
                             'company. You can use the "Discard" button to abandon this change.')}
        if partner.type == 'contact' or self.type == 'contact':
            # for contacts: copy the parent address, if set (aka, at least one
            # value is set in the address: otherwise, keep the one from the
            # contact)
            address_fields = self._address_fields()
            if any(self.parent_id[key] for key in address_fields):
                def convert(value):
                    return value.id if isinstance(value, models.BaseModel) else value
                result['value'] = {key: convert(self.parent_id[key]) for key in address_fields}
        return result

    @api.onchange('parent_id')
    def _onchange_parent_id_for_lang(self):
        # While creating / updating child contact, take the parent lang by default if any
        # otherwise, fallback to default context / DB lang
        if self.parent_id:
            self.lang = self.parent_id.lang or self.env.context.get('default_lang') or self.env.lang

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('email')
    def onchange_email(self):
        if not self.image_1920 and self._context.get('gravatar_image') and self.email:
            self.image_1920 = self._get_gravatar_image(self.email)

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

    @api.depends('is_company')
    def _compute_company_type(self):
        for partner in self:
            partner.company_type = 'company' if partner.is_company else 'person'

    def _write_company_type(self):
        for partner in self:
            partner.is_company = partner.company_type == 'company'

    @api.onchange('company_type')
    def onchange_company_type(self):
        self.is_company = (self.company_type == 'company')

    @api.constrains('barcode')
    def _check_barcode_unicity(self):
        for partner in self:
            if partner.barcode and self.env['res.partner'].search_count([('barcode', '=', partner.barcode)]) > 1:
                raise ValidationError(_('Another partner already has this barcode'))

    def _update_fields_values(self, fields):
        """ Returns dict of write() values for synchronizing ``fields`` """
        values = {}
        for fname in fields:
            field = self._fields[fname]
            if field.type == 'many2one':
                values[fname] = self[fname].id
            elif field.type == 'one2many':
                raise AssertionError(_('One2Many fields cannot be synchronized as part of `commercial_fields` or `address fields`'))
            elif field.type == 'many2many':
                values[fname] = [Command.set(self[fname].ids)]
            else:
                values[fname] = self[fname]
        return values

    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        return list(ADDRESS_FIELDS)

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return self._address_fields()

    def update_address(self, vals):
        addr_vals = {key: vals[key] for key in self._address_fields() if key in vals}
        if addr_vals:
            return super(Partner, self).write(addr_vals)

    @api.model
    def _commercial_fields(self):
        """ Returns the list of fields that are managed by the commercial entity
        to which a partner belongs. These fields are meant to be hidden on
        partners that aren't `commercial entities` themselves, and will be
        delegated to the parent `commercial entity`. The list is meant to be
        extended by inheriting classes. """
        return ['vat', 'company_registry', 'industry_id']

    def _commercial_sync_from_company(self):
        """ Handle sync of commercial fields when a new parent commercial entity is set,
        as if they were related fields """
        commercial_partner = self.commercial_partner_id
        if commercial_partner != self:
            sync_vals = commercial_partner._update_fields_values(self._commercial_fields())
            self.write(sync_vals)
            self._commercial_sync_to_children()

    def _commercial_sync_to_children(self):
        """ Handle sync of commercial fields to descendants """
        commercial_partner = self.commercial_partner_id
        sync_vals = commercial_partner._update_fields_values(self._commercial_fields())
        sync_children = self.child_ids.filtered(lambda c: not c.is_company)
        for child in sync_children:
            child._commercial_sync_to_children()
        res = sync_children.write(sync_vals)
        sync_children._compute_commercial_partner()
        return res

    def _fields_sync(self, values):
        """ Sync commercial fields and address fields from company and to children after create/update,
        just as if those were all modeled as fields.related to the parent """
        # 1. From UPSTREAM: sync from parent
        if values.get('parent_id') or values.get('type') == 'contact':
            # 1a. Commercial fields: sync if parent changed
            if values.get('parent_id'):
                self.sudo()._commercial_sync_from_company()
            # 1b. Address fields: sync if parent or use_parent changed *and* both are now set
            if self.parent_id and self.type == 'contact':
                onchange_vals = self.onchange_parent_id().get('value', {})
                self.update_address(onchange_vals)

        # 2. To DOWNSTREAM: sync children
        self._children_sync(values)

    def _children_sync(self, values):
        if not self.child_ids:
            return
        # 2a. Commercial Fields: sync if commercial entity
        if self.commercial_partner_id == self:
            commercial_fields = self._commercial_fields()
            if any(field in values for field in commercial_fields):
                self.sudo()._commercial_sync_to_children()
        for child in self.child_ids.filtered(lambda c: not c.is_company):
            if child.commercial_partner_id != self.commercial_partner_id:
                self.sudo()._commercial_sync_to_children()
                break
        # 2b. Address fields: sync if address changed
        address_fields = self._address_fields()
        if any(field in values for field in address_fields):
            contacts = self.child_ids.filtered(lambda c: c.type == 'contact')
            contacts.update_address(values)

    def _handle_first_contact_creation(self):
        """ On creation of first contact for a company (or root) that has no address, assume contact address
        was meant to be company address """
        parent = self.parent_id
        address_fields = self._address_fields()
        if (parent.is_company or not parent.parent_id) and len(parent.child_ids) == 1 and \
            any(self[f] for f in address_fields) and not any(parent[f] for f in address_fields):
            addr_vals = self._update_fields_values(address_fields)
            parent.update_address(addr_vals)

    def _clean_website(self, website):
        url = urls.url_parse(website)
        if not url.scheme:
            if not url.netloc:
                url = url.replace(netloc=url.path, path='')
            website = url.replace(scheme='http').to_url()
        return website

    def _compute_is_public(self):
        for partner in self.with_context(active_test=False):
            users = partner.user_ids
            partner.is_public = users and any(user._is_public() for user in users)

    def write(self, vals):
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
            users = self.env['res.users'].sudo().search([('partner_id', 'in', self.ids)])
            if users:
                if self.env['res.users'].sudo(False).check_access_rights('write', raise_exception=False):
                    error_msg = _('You cannot archive contacts linked to an active user.\n'
                                  'You first need to archive their associated user.\n\n'
                                  'Linked active users : %(names)s', names=", ".join([u.display_name for u in users]))
                    action_error = users._action_show()
                    raise RedirectWarning(error_msg, action_error, _('Go to users'))
                else:
                    raise ValidationError(_('You cannot archive contacts linked to an active user.\n'
                                            'Ask an administrator to archive their associated user first.\n\n'
                                            'Linked active users :\n%(names)s', names=", ".join([u.display_name for u in users])))
        # res.partner must only allow to set the company_id of a partner if it
        # is the same as the company of all users that inherit from this partner
        # (this is to allow the code from res_users to write to the partner!) or
        # if setting the company_id to False (this is compatible with any user
        # company)
        if vals.get('website'):
            vals['website'] = self._clean_website(vals['website'])
        if vals.get('parent_id'):
            vals['company_name'] = False
        if 'company_id' in vals:
            company_id = vals['company_id']
            for partner in self:
                if company_id and partner.user_ids:
                    company = self.env['res.company'].browse(company_id)
                    companies = set(user.company_id for user in partner.user_ids)
                    if len(companies) > 1 or company not in companies:
                        raise UserError(
                            ("The selected company is not compatible with the companies of the related user(s)"))
                if partner.child_ids:
                    partner.child_ids.write({'company_id': company_id})
        result = True
        # To write in SUPERUSER on field is_company and avoid access rights problems.
        if 'is_company' in vals and not self.env.su and self.env.user.has_group('base.group_partner_manager'):
            result = super(Partner, self.sudo()).write({'is_company': vals.get('is_company')})
            del vals['is_company']
        result = result and super(Partner, self).write(vals)
        for partner in self:
            if any(u._is_internal() for u in partner.user_ids if u != self.env.user):
                self.env['res.users'].check_access_rights('write')
            partner._fields_sync(vals)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('import_file'):
            self._check_import_consistency(vals_list)
        for vals in vals_list:
            if vals.get('website'):
                vals['website'] = self._clean_website(vals['website'])
            if vals.get('parent_id'):
                vals['company_name'] = False
        partners = super(Partner, self).create(vals_list)

        if self.env.context.get('_partners_skip_fields_sync'):
            return partners

        for partner, vals in zip(partners, vals_list):
            partner._fields_sync(vals)
            # Lang: propagate from parent if no value was given
            if 'lang' not in vals and partner.parent_id:
                partner._onchange_parent_id_for_lang()
            partner._handle_first_contact_creation()
        return partners

    @api.ondelete(at_uninstall=False)
    def _unlink_except_user(self):
        users = self.env['res.users'].sudo().search([('partner_id', 'in', self.ids)])
        if not users:
            return  # no linked user, operation is allowed
        if self.env['res.users'].sudo(False).check_access_rights('write', raise_exception=False):
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
        partners = super(Partner, self.with_context(_partners_skip_fields_sync=True))._load_records_create(vals_list)

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
                to_write = self.browse(cp_id)._update_fields_values(self._commercial_fields())
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

    def create_company(self):
        self.ensure_one()
        if self.company_name:
            # Create parent company
            values = dict(name=self.company_name, is_company=True, vat=self.vat)
            values.update(self._update_fields_values(self._address_fields()))
            new_company = self.create(values)
            # Set new company as my parent
            self.write({
                'parent_id': new_company.id,
                'child_ids': [Command.update(partner_id, dict(parent_id=new_company.id)) for partner_id in self.child_ids.ids]
            })
        return True

    def open_commercial_entity(self):
        """ Utility method used to add an "Open Company" button in partner views """
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': self.commercial_partner_id.id,
                'target': 'current',
                }

    @api.depends('complete_name', 'email', 'vat', 'state_id', 'country_id', 'commercial_company_name')
    @api.depends_context('show_address', 'partner_show_db_id', 'address_inline', 'show_email', 'show_vat')
    def _compute_display_name(self):
        for partner in self:
            name = partner.complete_name
            if partner._context.get('show_address'):
                name = name + "\n" + partner._display_address(without_company=True)
            name = re.sub(r'\s+\n', '\n', name)
            if partner._context.get('partner_show_db_id'):
                name = f"{name} ({partner.id})"
            if partner._context.get('address_inline'):
                splitted_names = name.split("\n")
                name = ", ".join([n for n in splitted_names if n.strip()])
            if partner._context.get('show_email') and partner.email:
                name = f"{name} <{partner.email}>"
            if partner._context.get('show_vat') and partner.vat:
                name = f"{name} ‒ {partner.vat}"

            partner.display_name = name.strip()

    @api.model
    def name_create(self, name):
        """ Override of orm's name_create method for partners. The purpose is
            to handle some basic formats to create partners using the
            name_create.
            If only an email address is received and that the regex cannot find
            a name, the name will have the email value.
            If 'force_email' key in context: must find the email address. """
        default_type = self._context.get('default_type')
        if default_type and default_type not in self._fields['type'].get_values(self.env):
            context = dict(self._context)
            context.pop('default_type')
            self = self.with_context(context)
        name, email_normalized = tools.parse_contact_from_email(name)
        if self._context.get('force_email') and not email_normalized:
            raise ValidationError(_("Couldn't create contact without email address!"))

        create_values = {self._rec_name: name or email_normalized}
        if email_normalized:  # keep default_email in context
            create_values['email'] = email_normalized
        partner = self.create(create_values)
        return partner.id, partner.display_name

    @api.model
    @api.returns('self', lambda value: value.id)
    def find_or_create(self, email, assert_valid_email=False):
        """ Find a partner with the given ``email`` or use :py:method:`~.name_create`
        to create a new one.

        :param str email: email-like string, which should contain at least one email,
            e.g. ``"Raoul Grosbedon <r.g@grosbedon.fr>"``
        :param boolean assert_valid_email: raise if no valid email is found
        :return: newly created record
        """
        if not email:
            raise ValueError(_('An email is required for find_or_create to work'))

        parsed_name, parsed_email_normalized = tools.parse_contact_from_email(email)
        if not parsed_email_normalized and assert_valid_email:
            raise ValueError(_('A valid email is required for find_or_create to work properly.'))

        partners = self.search([('email', '=ilike', parsed_email_normalized)], limit=1)
        if partners:
            return partners

        create_values = {self._rec_name: parsed_name or parsed_email_normalized}
        if parsed_email_normalized:  # keep default_email in context
            create_values['email'] = parsed_email_normalized
        return self.create(create_values)

    def _get_gravatar_image(self, email):
        email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
        url = "https://www.gravatar.com/avatar/" + email_hash
        try:
            res = requests.get(url, params={'d': '404', 's': '128'}, timeout=5)
            if res.status_code != requests.codes.ok:
                return False
        except requests.exceptions.ConnectionError as e:
            return False
        except requests.exceptions.Timeout as e:
            return False
        return base64.b64encode(res.content)

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

    @api.model
    def _get_address_format(self):
        return self.country_id.address_format or self._get_default_address_format()

    def _prepare_display_address(self, without_company=False):
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = defaultdict(str, {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            'company_name': self.commercial_company_name or '',
        })
        for field in self._formatting_address_fields():
            args[field] = self[field] or ''
        if without_company:
            args['company_name'] = ''
        elif self.commercial_company_name:
            address_format = '%(company_name)s\n' + address_format
        return address_format, args

    def _display_address(self, without_company=False):
        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param without_company: if address contains company
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        address_format, args = self._prepare_display_address(without_company)
        return address_format % args

    def _display_address_depends(self):
        # field dependencies of method _display_address()
        return self._formatting_address_fields() + [
            'country_id', 'company_name', 'state_id',
        ]

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Customers'),
            'template': '/base/static/xls/res_partner.xlsx'
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

    def _get_country_name(self):
        return self.country_id.name or ''

    def _get_all_addr(self):
        self.ensure_one()
        return [{
            'contact_type': self.street,
            'street': self.street,
            'zip': self.zip,
            'city': self.city,
            'country': self.country_id.code,
        }]


class ResPartnerIndustry(models.Model):
    _description = 'Industry'
    _name = "res.partner.industry"
    _order = "name"

    name = fields.Char('Name', translate=True)
    full_name = fields.Char('Full Name', translate=True)
    active = fields.Boolean('Active', default=True)
