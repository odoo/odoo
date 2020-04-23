# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import os

from odoo import api, fields, models, tools
from odoo.modules.module import get_resource_path

from random import randrange
from PIL import Image


class Company(models.Model):
    _inherit = "res.company"
    _order = 'sequence, name'

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id

    def _get_default_favicon(self, original=False):
        img_path = get_resource_path('web', 'static/src/img/favicon.ico')
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

    def _get_logo(self):
        return base64.b64encode(open(os.path.join(tools.config['root_path'], 'addons', 'base', 'static', 'img', 'res_company_logo.png'), 'rb') .read())

    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)
    parent_id = fields.Many2one('res.company', string='Parent Company', index=True)
    child_ids = fields.One2many('res.company', 'parent_id', string='Child Companies')
    report_header = fields.Text(string='Company Tagline', help="Appears by default on the top right corner of your printed documents (report header).")
    report_footer = fields.Text(string='Report Footer', translate=True, help="Footer text displayed at the bottom of all reports.")
    street = fields.Char(compute='_compute_address', inverse='_inverse_street')
    street2 = fields.Char(compute='_compute_address', inverse='_inverse_street2')
    zip = fields.Char(compute='_compute_address', inverse='_inverse_zip')
    city = fields.Char(compute='_compute_address', inverse='_inverse_city')
    state_id = fields.Many2one(
        'res.country.state', compute='_compute_address', inverse='_inverse_state',
        string="Fed. State", domain="[('country_id', '=?', country_id)]"
    )
    bank_ids = fields.One2many('res.partner.bank', 'company_id', string='Bank Accounts', help='Bank accounts related to this company')
    country_id = fields.Many2one('res.country', compute='_compute_address', inverse='_inverse_country', string="Country")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self._default_currency_id())
    website = fields.Char(related='partner_id.website', readonly=False)
    vat = fields.Char(related='partner_id.vat', string="Tax ID", readonly=False)
    logo = fields.Binary(related='partner_id.image_1920', default=_get_logo, string="Company Logo", readonly=False)
    # logo_web: do not store in attachments, since the image is retrieved in SQL for
    # performance reasons (see addons/web/controllers/main.py, Binary.company_logo)
    logo_web = fields.Binary(compute='_compute_logo_web', store=True, attachment=False)
    phone = fields.Char(related='partner_id.phone', store=True, readonly=False)
    company_registry = fields.Char()
    paperformat_id = fields.Many2one('report.paperformat', 'Paper format', default=lambda self: self.env.ref('base.paperformat_euro', raise_if_not_found=False))
    external_report_layout_id = fields.Many2one('ir.ui.view', 'Document Template')
    base_onboarding_company_state = fields.Selection([
        ('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")], string="State of the onboarding company step", default='not_done')
    favicon = fields.Binary(string="Company Favicon", help="This field holds the image used to display a favicon for a given company.", default=_get_default_favicon)
    font = fields.Selection([("Lato", "Lato"), ("Roboto", "Roboto"), ("Open_Sans", "Open Sans"), ("Montserrat", "Montserrat"), ("Oswald", "Oswald"), ("Raleway", "Raleway")], default="Lato")
    primary_color = fields.Char()
    secondary_color = fields.Char()

    def init(self):
        for company in self.search([('paperformat_id', '=', False)]):
            paperformat_euro = self.env.ref('base.paperformat_euro', False)
            if paperformat_euro:
                company.write({'paperformat_id': paperformat_euro.id})
        sup = super(Company, self)
        if hasattr(sup, 'init'):
            sup.init()

    @api.depends('partner_id.image_1920')
    def _compute_logo_web(self):
        for company in self:
            company.logo_web = tools.image_process(company.partner_id.image_1920, size=(180, 0))

    def _get_create_partner_values(self, vals):
        res = super()._get_create_partner_values(vals)
        res.update({
            'is_company': True,
            'phone': vals.get('phone'),
            'image_1920': vals.get('logo'),
            'website': vals.get('website'),
            'vat': vals.get('vat'),
        })
        return res

    @api.model
    def create(self, vals):
        if not vals.get('favicon'):
            vals['favicon'] = self._get_default_favicon()
        res = super().create(vals)
        # Make sure that the selected currency is enabled
        if vals.get('currency_id'):
            currency = self.env['res.currency'].browse(vals['currency_id'])
            if not currency.active:
                currency.write({'active': True})
        return res

    def write(self, values):
        if values.get('currency_id'):
            currency = self.env['res.currency'].browse(values['currency_id'])
            if not currency.active:
                currency.write({'active': True})
        res = super().write(values)
        # invalidate company cache to recompute address based on updated partner
        company_address_fields = self._get_company_address_field_names()
        company_address_fields_upd = set(company_address_fields) & set(values.keys())
        if company_address_fields_upd:
            self.invalidate_cache(fnames=company_address_fields)
        return res

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

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            self.currency_id = self.country_id.currency_id

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
        action = self.env.ref('base.action_open_base_onboarding_company').read()[0]
        action['res_id'] = self.env.company.id
        return action

    def set_onboarding_step_done(self, step_name):
        if self[step_name] == 'not_done':
            self[step_name] = 'just_done'

    def get_and_update_onbarding_state(self, onboarding_state, steps_states):
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

