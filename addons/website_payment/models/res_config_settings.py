# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    providers_state = fields.Selection(
        selection=[
            ('none', 'None'),
            ('paypal_only', 'Paypal Only'),
            ('other_than_paypal', 'Other than Paypal')
        ],
        compute='_compute_providers_state')
    first_provider_label = fields.Char(
        compute='_compute_providers_state')
    is_stripe_supported_country = fields.Boolean(
        related='company_id.country_id.is_stripe_supported_country')
    is_inr_currency = fields.Boolean(compute='_compute_is_inr_currency')

    @api.depends('company_id.currency_id')
    def _compute_is_inr_currency(self):
        for config in self:
            config.is_inr_currency = config.company_id.currency_id.name == 'INR'

    def _get_activated_providers(self):
        self.ensure_one()
        wire_transfer = self.env.ref('payment.payment_provider_transfer', raise_if_not_found=False)
        return self.env['payment.provider'].search([
            ('state', '!=', 'disabled'),
            ('id', '!=', wire_transfer.id if wire_transfer else False),
            '|',
            ('website_id', '=', False),
            ('website_id', '=', self.website_id.id)
        ])

    @api.depends('website_id')
    def _compute_providers_state(self):
        paypal = self.env.ref('payment.payment_provider_paypal', raise_if_not_found=False)
        stripe = self.env.ref('payment.payment_provider_stripe', raise_if_not_found=False)
        razorpay = self.env.ref('payment.payment_provider_razorpay', raise_if_not_found=False)
        for config in self:
            providers = config._get_activated_providers()
            first_provider = (
                razorpay if config.is_inr_currency and razorpay in providers
                else stripe if stripe in providers
                else providers[0] if providers
                else providers
            )
            config.first_provider_label = _('Configure %s', first_provider.name)
            if len(providers) == 1 and providers == paypal:
                config.providers_state = 'paypal_only'
            elif len(providers) >= 1:
                config.providers_state = 'other_than_paypal'
            else:
                config.providers_state = 'none'

    def action_activate_payment_provider(self):
        self.ensure_one()
        if not (self.is_stripe_supported_country or self.is_inr_currency):
            return False
        menu = self.env.ref('website.menu_website_website_settings', raise_if_not_found=False)
        menu_id = menu and menu.id
        return self.env.company._run_payment_onboarding_step(menu_id=menu_id)

    def action_configure_first_provider(self):
        self.ensure_one()
        provider_code = 'razorpay' if self.is_inr_currency else 'stripe'
        provider = self.env['payment.provider'].search([
            *self.env['payment.provider']._check_company_domain(self.env.company),
            ('code', '=', provider_code)
        ], limit=1)
        providers = self._get_activated_providers()
        return {
            'name': self.first_provider_label,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'views': [[False, 'form']],
            'res_id': provider.id if provider in providers else providers[0].id,
        }
