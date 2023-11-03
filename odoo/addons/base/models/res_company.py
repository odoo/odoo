# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import warnings

from odoo import api, fields, models, tools, _, Command, SUPERUSER_ID
from odoo.exceptions import ValidationError, UserError
from odoo.tools import html2plaintext, file_open, ormcache

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _name = "res.company"
    _description = 'Companies'
    _order = 'sequence, name'
    _parent_store = True

    def copy(self, default=None):
        raise UserError(_('Duplicating a company is not allowed. Please create a new company instead.'))

    def _get_logo(self):
        with file_open('base/static/img/res_company_logo.png', 'rb') as file:
            return base64.b64encode(file.read())

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    name = fields.Char(related='partner_id.name', string='Company Name', required=True, store=True, readonly=False)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)
    parent_id = fields.Many2one('res.company', string='Parent Company', index=True)
    child_ids = fields.One2many('res.company', 'parent_id', string='Branches')
    all_child_ids = fields.One2many('res.company', 'parent_id', context={'active_test': False})
    parent_path = fields.Char(index=True, unaccent=False)
    parent_ids = fields.Many2many('res.company', compute='_compute_parent_ids', compute_sudo=True)
    root_id = fields.Many2one('res.company', compute='_compute_parent_ids', compute_sudo=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    report_header = fields.Html(string='Company Tagline', translate=True, help="Company tagline, which is included in a printed document's header or footer (depending on the selected layout).")
    report_footer = fields.Html(string='Report Footer', translate=True, help="Footer text displayed at the bottom of all reports.")
    company_details = fields.Html(string='Company Details', translate=True, help="Header text displayed at the top of all reports.")
    is_company_details_empty = fields.Boolean(compute='_compute_empty_company_details')
    logo = fields.Binary(related='partner_id.image_1920', default=_get_logo, string="Company Logo", readonly=False)
    # logo_web: do not store in attachments, since the image is retrieved in SQL for
    # performance reasons (see addons/web/controllers/main.py, Binary.company_logo)
    logo_web = fields.Binary(compute='_compute_logo_web', store=True, attachment=False)
    uses_default_logo = fields.Boolean(compute='_compute_uses_default_logo', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self._default_currency_id())
    user_ids = fields.Many2many('res.users', 'res_company_users_rel', 'cid', 'user_id', string='Accepted Users')
    street = fields.Char(compute='_compute_address', inverse='_inverse_street')
    street2 = fields.Char(compute='_compute_address', inverse='_inverse_street2')
    zip = fields.Char(compute='_compute_address', inverse='_inverse_zip')
    city = fields.Char(compute='_compute_address', inverse='_inverse_city')
    state_id = fields.Many2one(
        'res.country.state', compute='_compute_address', inverse='_inverse_state',
        string="Fed. State", domain="[('country_id', '=?', country_id)]"
    )
    bank_ids = fields.One2many(related='partner_id.bank_ids', readonly=False)
    country_id = fields.Many2one('res.country', compute='_compute_address', inverse='_inverse_country', string="Country")
    email = fields.Char(related='partner_id.email', store=True, readonly=False)
    phone = fields.Char(related='partner_id.phone', store=True, readonly=False)
    mobile = fields.Char(related='partner_id.mobile', store=True, readonly=False)
    website = fields.Char(related='partner_id.website', readonly=False)
    vat = fields.Char(related='partner_id.vat', string="Tax ID", readonly=False)
    company_registry = fields.Char(related='partner_id.company_registry', string="Company ID", readonly=False)
    paperformat_id = fields.Many2one('report.paperformat', 'Paper format', default=lambda self: self.env.ref('base.paperformat_euro', raise_if_not_found=False))
    external_report_layout_id = fields.Many2one('ir.ui.view', 'Document Template')
    font = fields.Selection([("Lato", "Lato"), ("Roboto", "Roboto"), ("Open_Sans", "Open Sans"), ("Montserrat", "Montserrat"), ("Oswald", "Oswald"), ("Raleway", "Raleway"), ('Tajawal', 'Tajawal')], default="Lato")
    primary_color = fields.Char()
    secondary_color = fields.Char()
    color = fields.Integer(compute='_compute_color', inverse='_inverse_color')
    layout_background = fields.Selection([('Blank', 'Blank'), ('Geometric', 'Geometric'), ('Custom', 'Custom')], default="Blank", required=True)
    layout_background_image = fields.Binary("Background Image")
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The company name must be unique!')
    ]

    def init(self):
        for company in self.search([('paperformat_id', '=', False)]):
            paperformat_euro = self.env.ref('base.paperformat_euro', False)
            if paperformat_euro:
                company.write({'paperformat_id': paperformat_euro.id})
        sup = super(Company, self)
        if hasattr(sup, 'init'):
            sup.init()

    def _get_company_root_delegated_field_names(self):
        """Get the set of fields delegated to the root company.

        Some fields need to be identical on all branches of the company. All
        fields listed by this function will be copied from the root company and
        appear as readonly in the form view.
        :rtype: set
        """
        return ['currency_id']

    def _get_company_address_field_names(self):
        """ Return a list of fields coming from the address partner to match
        on company address fields. Fields are labeled same on both models. """
        return ['street', 'street2', 'city', 'zip', 'state_id', 'country_id']

    def _get_company_address_update(self, partner):
        return dict((fname, partner[fname])
                    for fname in self._get_company_address_field_names())

    @api.depends('parent_path')
    def _compute_parent_ids(self):
        for company in self.with_context(active_test=False):
            company.parent_ids = self.browse(int(id) for id in company.parent_path.split('/') if id) if company.parent_path else company
            company.root_id = company.parent_ids[0]

    # TODO @api.depends(): currently now way to formulate the dependency on the
    # partner's contact address
    def _compute_address(self):
        for company in self.filtered(lambda company: company.partner_id):
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.browse(address_data['contact']).sudo()
                company.update(company._get_company_address_update(partner))

    def _inverse_street(self):
        for company in self:
            company.partner_id.street = company.street

    def _inverse_street2(self):
        for company in self:
            company.partner_id.street2 = company.street2

    def _inverse_zip(self):
        for company in self:
            company.partner_id.zip = company.zip

    def _inverse_city(self):
        for company in self:
            company.partner_id.city = company.city

    def _inverse_state(self):
        for company in self:
            company.partner_id.state_id = company.state_id

    def _inverse_country(self):
        for company in self:
            company.partner_id.country_id = company.country_id

    @api.depends('partner_id.image_1920')
    def _compute_logo_web(self):
        for company in self:
            img = company.partner_id.image_1920
            company.logo_web = img and base64.b64encode(tools.image_process(base64.b64decode(img), size=(180, 0)))

    @api.depends('partner_id.image_1920')
    def _compute_uses_default_logo(self):
        default_logo = self._get_logo()
        for company in self:
            company.uses_default_logo = not company.logo or company.logo == default_logo

    @api.depends('root_id')
    def _compute_color(self):
        for company in self:
            company.color = company.root_id.partner_id.color or (company.root_id._origin.id % 12)

    def _inverse_color(self):
        for company in self:
            company.root_id.partner_id.color = company.color

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            self.currency_id = self.country_id.currency_id

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id:
            for fname in self._get_company_root_delegated_field_names():
                if self[fname] != self.parent_id[fname]:
                    self[fname] = self.parent_id[fname]

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        def make_delegated_fields_readonly(node):
            for child in node.iterchildren():
                if child.tag == 'field' and child.get('name') in delegated_fnames:
                    child.set('attrs', "{'readonly': [('parent_id', '!=', False)]}")
                else:
                    make_delegated_fields_readonly(child)
            return node

        delegated_fnames = set(self._get_company_root_delegated_field_names())
        arch, view = super()._get_view(view_id, view_type, **options)
        arch = make_delegated_fields_readonly(arch)
        return arch, view

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        context = dict(self.env.context)
        newself = self
        if context.pop('user_preference', None):
            # We browse as superuser. Otherwise, the user would be able to
            # select only the currently visible companies (according to rules,
            # which are probably to allow to see the child companies) even if
            # she belongs to some other companies.
            companies = self.env.user.company_ids
            domain = (domain or []) + [('id', 'in', companies.ids)]
            newself = newself.sudo()
        self = newself.with_context(context)
        return super()._name_search(name, domain, operator, limit, order)

    @api.model
    @api.returns('self', lambda value: value.id)
    def _company_default_get(self, object=False, field=False):
        """ Returns the user's company
            - Deprecated
        """
        _logger.warning("The method '_company_default_get' on res.company is deprecated and shouldn't be used anymore")
        return self.env.company

    @api.depends('company_details')
    def _compute_empty_company_details(self):
        # In recent change when an html field is empty a <p> balise remains with a <br> in it,
        # but when company details is empty we want to put the info of the company
        for record in self:
            record.is_company_details_empty = not html2plaintext(record.company_details or '')

    @api.model_create_multi
    def create(self, vals_list):

        # create missing partners
        no_partner_vals_list = [
            vals
            for vals in vals_list
            if vals.get('name') and not vals.get('partner_id')
        ]
        if no_partner_vals_list:
            partners = self.env['res.partner'].create([
                {
                    'name': vals['name'],
                    'is_company': True,
                    'image_1920': vals.get('logo'),
                    'email': vals.get('email'),
                    'phone': vals.get('phone'),
                    'website': vals.get('website'),
                    'vat': vals.get('vat'),
                    'country_id': vals.get('country_id'),
                }
                for vals in no_partner_vals_list
            ])
            # compute stored fields, for example address dependent fields
            partners.flush_model()
            for vals, partner in zip(no_partner_vals_list, partners):
                vals['partner_id'] = partner.id

        for vals in vals_list:
            # Copy delegated fields from root to branches
            if parent := self.browse(vals.get('parent_id')):
                for fname in self._get_company_root_delegated_field_names():
                    vals.setdefault(fname, self._fields[fname].convert_to_write(parent[fname], parent))

        self.env.registry.clear_cache()
        companies = super().create(vals_list)

        # The write is made on the user to set it automatically in the multi company group.
        if companies:
            (self.env.user | self.env['res.users'].browse(SUPERUSER_ID)).write({
                'company_ids': [Command.link(company.id) for company in companies],
            })

        # Make sure that the selected currencies are enabled
        companies.currency_id.sudo().filtered(lambda c: not c.active).active = True

        return companies

    def cache_invalidation_fields(self):
        # This list is not well defined and tests should be improved
        return {
            'active', # user._get_company_ids and other potential cached search
            'sequence', # user._get_company_ids and other potential cached search
        }

    def write(self, values):
        invalidation_fields = self.cache_invalidation_fields()
        asset_invalidation_fields = {'font', 'primary_color', 'secondary_color', 'external_report_layout_id'}
        if not invalidation_fields.isdisjoint(values):
            self.env.registry.clear_cache()

        if not asset_invalidation_fields.isdisjoint(values):
            # this is used in the content of an asset (see asset_styles_company_report)
            # and thus needs to invalidate the assets cache when this is changed
            self.env.registry.clear_cache('assets')  # not 100% it is useful a test is missing if it is the case

        if 'parent_id' in values:
            raise UserError(_("The company hierarchy cannot be changed."))

        if values.get('currency_id'):
            currency = self.env['res.currency'].browse(values['currency_id'])
            if not currency.active:
                currency.write({'active': True})

        res = super(Company, self).write(values)

        for company in self:
            # Copy modified delegated fields from root to branches
            if (changed := set(values) & set(self._get_company_root_delegated_field_names())) and not company.parent_id:
                branches = self.sudo().search([
                    ('id', 'child_of', company.id),
                    ('id', '!=', company.id),
                ])
                for fname in sorted(changed):
                    branches[fname] = company[fname]

        # invalidate company cache to recompute address based on updated partner
        company_address_fields = self._get_company_address_field_names()
        company_address_fields_upd = set(company_address_fields) & set(values.keys())
        if company_address_fields_upd:
            self.invalidate_model(company_address_fields)
        return res

    @api.constrains('active')
    def _check_active(self):
        for company in self:
            if not company.active:
                company_active_users = self.env['res.users'].search_count([
                    ('company_id', '=', company.id),
                    ('active', '=', True),
                ])
                if company_active_users:
                    # You cannot disable companies with active users
                    raise ValidationError(_(
                        'The company %(company_name)s cannot be archived because it is still used '
                        'as the default company of %(active_users)s users.',
                        company_name=company.name,
                        active_users=company_active_users,
                    ))

    @api.constrains(lambda self: self._get_company_root_delegated_field_names() +['parent_id'])
    def _check_root_delegated_fields(self):
        for company in self:
            if company.parent_id:
                for fname in company._get_company_root_delegated_field_names():
                    if company[fname] != company.parent_id[fname]:
                        description = self.env['ir.model.fields']._get("res.company", fname).field_description
                        raise ValidationError(_("The %s of a subsidiary must be the same as it's root company.", description))

    def open_company_edit_report(self):
        warnings.warn("Since 17.0.", DeprecationWarning, 2)
        self.ensure_one()
        return self.env['res.config.settings'].open_company()

    def write_company_and_print_report(self):
        warnings.warn("Since 17.0.", DeprecationWarning, 2)
        context = self.env.context
        report_name = context.get('default_report_name')
        active_ids = context.get('active_ids')
        active_model = context.get('active_model')
        if report_name and active_ids and active_model:
            docids = self.env[active_model].browse(active_ids)
            return (self.env['ir.actions.report'].search([('report_name', '=', report_name)], limit=1)
                        .report_action(docids))

    @api.model
    def _get_main_company(self):
        try:
            main_company = self.sudo().env.ref('base.main_company')
        except ValueError:
            main_company = self.env['res.company'].sudo().search([], limit=1, order="id")

        return main_company

    @ormcache('tuple(self.env.companies.ids)', 'self.id', 'self.env.uid')
    def __accessible_branches(self):
        # Get branches of this company that the current user can use
        self.ensure_one()

        accessible_branch_ids = []
        accessible = self.env.companies
        current = self.sudo()
        while current:
            accessible_branch_ids.extend((current & accessible).ids)
            current = current.child_ids

        if not accessible_branch_ids and self.env.uid == SUPERUSER_ID:
            # Accessible companies will always be the same for super user when called in a cron.
            # Because of that, the intersection between them and self might be empty. The super user anyway always has
            # access to all companies (as it bypasses the record rules), so we return the current company in this case.
            return self.ids

        return accessible_branch_ids

    def _accessible_branches(self):
        return self.browse(self.__accessible_branches())

    def _all_branches_selected(self):
        """Return whether or all the branches of the companies in self are selected.

        Is ``True`` if all the branches, and only those, are selected.
        Can be used when some actions only make sense for whole companies regardless of the
        branches.
        """
        return self == self.sudo().search([('id', 'child_of', self.root_id.ids)])

    def action_all_company_branches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Branches'),
            'res_model': 'res.company',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'active_test': False,
                'default_parent_id': self.id,
            },
            'views': [[False, 'tree'], [False, 'kanban'], [False, 'form']],
        }
