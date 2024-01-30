# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import os
import re

from odoo import api, fields, models, tools, _, Command
from odoo.exceptions import ValidationError, UserError
from odoo.modules.module import get_resource_path
from odoo.tools import html2plaintext
from random import randrange
from PIL import Image

_logger = logging.getLogger(__name__)


class Company(models.Model):
    _name = "res.company"
    _description = 'Companies'
    _order = 'sequence, name'

    def copy(self, default=None):
        raise UserError(_('Duplicating a company is not allowed. Please create a new company instead.'))

    def _get_logo(self):
        return base64.b64encode(open(os.path.join(tools.config['root_path'], 'addons', 'base', 'static', 'img', 'res_company_logo.png'), 'rb') .read())

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    def _get_default_favicon(self, original=False):
        img_path = get_resource_path('web', 'static/img/favicon.ico')
        with tools.file_open(img_path, 'rb') as f:
            if original:
                return base64.b64encode(f.read())
            # Modify the source image to add a colored bar on the bottom
            # This could seem overkill to modify the pixels 1 by 1, but
            # Pillow doesn't provide an easy way to do it, and this 
            # is acceptable for a 16x16 image.
            color = (randrange(32, 224, 24), randrange(32, 224, 24), randrange(32, 224, 24))
            original = Image.open(f)
            new_image = Image.new('RGBA', original.size)
            height = original.size[1]
            width = original.size[0]
            bar_size = 1
            for y in range(height):
                for x in range(width):
                    pixel = original.getpixel((x, y))
                    if height - bar_size <= y + 1 <= height:
                        new_image.putpixel((x, y), (color[0], color[1], color[2], 255))
                    else:
                        new_image.putpixel((x, y), (pixel[0], pixel[1], pixel[2], pixel[3]))
            stream = io.BytesIO()
            new_image.save(stream, format="ICO")
            return base64.b64encode(stream.getvalue())

    name = fields.Char(related='partner_id.name', string='Company Name', required=True, store=True, readonly=False)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)
    parent_id = fields.Many2one('res.company', string='Parent Company', index=True)
    child_ids = fields.One2many('res.company', 'parent_id', string='Child Companies')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    report_header = fields.Html(string='Company Tagline', help="Appears by default on the top right corner of your printed documents (report header).")
    report_footer = fields.Html(string='Report Footer', translate=True, help="Footer text displayed at the bottom of all reports.")
    company_details = fields.Html(string='Company Details', help="Header text displayed at the top of all reports.")
    is_company_details_empty = fields.Boolean(compute='_compute_empty_company_details')
    logo = fields.Binary(related='partner_id.image_1920', default=_get_logo, string="Company Logo", readonly=False)
    # logo_web: do not store in attachments, since the image is retrieved in SQL for
    # performance reasons (see addons/web/controllers/main.py, Binary.company_logo)
    logo_web = fields.Binary(compute='_compute_logo_web', store=True, attachment=False)
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
    base_onboarding_company_state = fields.Selection([
        ('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding company step", default='not_done')
    favicon = fields.Binary(string="Company Favicon", help="This field holds the image used to display a favicon for a given company.", default=_get_default_favicon)
    font = fields.Selection([("Lato", "Lato"), ("Roboto", "Roboto"), ("Open_Sans", "Open Sans"), ("Montserrat", "Montserrat"), ("Oswald", "Oswald"), ("Raleway", "Raleway"), ('Tajawal', 'Tajawal')], default="Lato")
    primary_color = fields.Char()
    secondary_color = fields.Char()
    layout_background = fields.Selection([('Blank', 'Blank'), ('Geometric', 'Geometric'), ('Custom', 'Custom')], default="Blank", required=True)
    layout_background_image = fields.Binary("Background Image")
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The company name must be unique !')
    ]

    def init(self):
        for company in self.search([('paperformat_id', '=', False)]):
            paperformat_euro = self.env.ref('base.paperformat_euro', False)
            if paperformat_euro:
                company.write({'paperformat_id': paperformat_euro.id})
        sup = super(Company, self)
        if hasattr(sup, 'init'):
            sup.init()

    def _get_company_address_field_names(self):
        """ Return a list of fields coming from the address partner to match
        on company address fields. Fields are labeled same on both models. """
        return ['street', 'street2', 'city', 'zip', 'state_id', 'country_id']

    def _get_company_address_update(self, partner):
        return dict((fname, partner[fname])
                    for fname in self._get_company_address_field_names())
    
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

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            self.currency_id = self.country_id.currency_id

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        context = dict(self.env.context)
        newself = self
        if context.pop('user_preference', None):
            # We browse as superuser. Otherwise, the user would be able to
            # select only the currently visible companies (according to rules,
            # which are probably to allow to see the child companies) even if
            # she belongs to some other companies.
            companies = self.env.user.company_ids
            args = (args or []) + [('id', 'in', companies.ids)]
            newself = newself.sudo()
        return super(Company, newself.with_context(context))._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

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

    # deprecated, use clear_caches() instead
    def cache_restart(self):
        self.clear_caches()

    @api.model_create_multi
    def create(self, vals_list):
        # add default favicon
        for vals in vals_list:
            if not vals.get('favicon'):
                vals['favicon'] = self._get_default_favicon()

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

        self.clear_caches()
        companies = super().create(vals_list)

        # The write is made on the user to set it automatically in the multi company group.
        if companies:
            self.env.user.write({
                'company_ids': [Command.link(company.id) for company in companies],
            })

        # Make sure that the selected currencies are enabled
        companies.currency_id.sudo().filtered(lambda c: not c.active).active = True

        return companies

    def write(self, values):
        self.clear_caches()
        # Make sure that the selected currency is enabled
        if values.get('currency_id'):
            currency = self.env['res.currency'].browse(values['currency_id'])
            if not currency.active:
                currency.write({'active': True})

        res = super(Company, self).write(values)

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

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive companies.'))

    def open_company_edit_report(self):
        self.ensure_one()
        return self.env['res.config.settings'].open_company()

    def write_company_and_print_report(self):
        context = self.env.context
        report_name = context.get('default_report_name')
        active_ids = context.get('active_ids')
        active_model = context.get('active_model')
        if report_name and active_ids and active_model:
            docids = self.env[active_model].browse(active_ids)
            return (self.env['ir.actions.report'].search([('report_name', '=', report_name)], limit=1)
                        .report_action(docids))

    @api.model
    def action_open_base_onboarding_company(self):
        """ Onboarding step for company basic information. """
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_open_base_onboarding_company")
        action['res_id'] = self.env.company.id
        return action

    def set_onboarding_step_done(self, step_name):
        if self[step_name] == 'not_done':
            self[step_name] = 'just_done'

    def _get_and_update_onboarding_state(self, onboarding_state, steps_states):
        """ Needed to display onboarding animations only one time. """
        old_values = {}
        all_done = True
        for step_state in steps_states:
            old_values[step_state] = self[step_state]
            if self[step_state] == 'just_done':
                self[step_state] = 'done'
            all_done = all_done and self[step_state] == 'done'

        if all_done:
            if self[onboarding_state] == 'not_done':
                # string `onboarding_state` instead of variable name is not an error
                old_values['onboarding_state'] = 'just_done'
            else:
                old_values['onboarding_state'] = 'done'
            self[onboarding_state] = 'done'
        return old_values

    def action_save_onboarding_company_step(self):
        if bool(self.street):
            self.set_onboarding_step_done('base_onboarding_company_state')

    @api.model
    def _get_main_company(self):
        try:
            main_company = self.sudo().env.ref('base.main_company')
        except ValueError:
            main_company = self.env['res.company'].sudo().search([], limit=1, order="id")

        return main_company
