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
    module_payment_paypal = fields.Boolean(
        string='Paypal - Express Checkout')
    is_stripe_supported_country = fields.Boolean(
        related='company_id.country_id.is_stripe_supported_country')

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
        for config in self:
            providers = config._get_activated_providers()
            first_provider = stripe if stripe in providers else providers[0] if providers else providers
            config.first_provider_label = _('Configure %s', first_provider.name)
            if len(providers) == 1 and providers == paypal:
                config.providers_state = 'paypal_only'
            elif len(providers) >= 1:
                config.providers_state = 'other_than_paypal'
            else:
                config.providers_state = 'none'

    def action_activate_stripe(self):
        self.ensure_one()
        if not self.is_stripe_supported_country:
            return False
        stripe = self.env.ref('payment.payment_provider_stripe')
        stripe.button_immediate_install()
        # This will make sure that a new request is made between the installation and the call to `action_stripe_connect_account`.
        return self.env['ir.actions.actions']._for_xml_id('website_payment.action_stripe_connect_account')

    def action_configure_first_provider(self):
        self.ensure_one()
        stripe = self.env.ref('payment.payment_provider_stripe')
        providers = self._get_activated_providers()
        return {
            'name': self.first_provider_label,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'views': [[False, 'form']],
            'res_id': stripe.id if stripe in providers else providers[0].id,
        }
