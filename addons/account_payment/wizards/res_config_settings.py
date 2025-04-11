# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    onboarding_payment_provider = fields.Selection(
        selection=[('razorpay', "Razorpay"), ('stripe', "Stripe")],
        compute='_compute_onboarding_payment_provider',
        store=True,
    )
    pay_invoices_online = fields.Boolean(config_parameter='account_payment.enable_portal_payment')
    providers_state = fields.Selection(
        selection=[('primary_provider', "Primary Provider"), ('other', "Other Provider")],
        compute='_compute_providers_state',
        default=False,
    )

    # === COMPUTE METHODS === #

    @api.depends('company_id.country_id', 'company_id.currency_id')
    def _compute_onboarding_payment_provider(self):
        for config in self:
            if config.company_id.currency_id.name == 'INR':
                config.onboarding_payment_provider = 'razorpay'
            elif config.company_id.country_id.is_stripe_supported_country:
                config.onboarding_payment_provider = 'stripe'

    def _compute_providers_state(self):
        for config in self:
            providers = config._get_activated_providers()
            primary_provider = next(
                (p for p in providers if p.code == config.onboarding_payment_provider),
                None
            )
            config.providers_state = (
                'primary_provider' if primary_provider else 'other' if providers else False
            )

    # === ACTION METHODS === #

    def action_configure_primary_provider(self):
        self.ensure_one()
        provider = self.env['payment.provider'].search([
            *self.env['payment.provider']._check_company_domain(self.env.company),
            ('code', '=', self.onboarding_payment_provider),
        ], limit=1)
        providers = self._get_activated_providers()
        return {
            'name': self.env._("Configure %s", provider.name) if provider else '',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'views': [[False, 'form']],
            'res_id': provider.id if provider in providers else False,
        }

    # === BUSINESS METHODS === #

    def _activate_payment_provider(self, menu_id):
        self.ensure_one()
        if not self.onboarding_payment_provider:
            return False
        return self.env.company._run_payment_onboarding_step(
            menu_id=menu_id, provider_code=self.onboarding_payment_provider
        )

    def _get_activated_providers(self):
        self.ensure_one()
        return self.env['payment.provider'].search(self._get_activate_providers_domain())

    def _get_activate_providers_domain(self):
        return [('state', '!=', 'disabled'), ('code', 'not in', ['custom', 'demo'])]
