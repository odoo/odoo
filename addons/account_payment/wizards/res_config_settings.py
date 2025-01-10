# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pay_invoices_online = fields.Boolean(config_parameter='account_payment.enable_portal_payment')

    providers_state = fields.Selection(
        selection=[
            ('none', 'None'),
            ('primary_provider', 'Primary Provider'),
            ('other', 'Other Provider')
        ],
        compute='_compute_providers_state',
    )
    first_provider_label = fields.Char(compute='_compute_providers_state')
    primary_provider_code = fields.Char(compute='_compute_primary_provider_code')

    @api.depends('company_id.country_id', 'company_id.currency_id')
    def _compute_primary_provider_code(self):
        for config in self:
            if config.company_id.currency_id.name == 'INR':
                config.primary_provider_code = 'razorpay'
            elif config.company_id.country_id.is_stripe_supported_country:
                config.primary_provider_code = 'stripe'
            else:
                config.primary_provider_code = ''

    def _get_activated_providers(self):
        self.ensure_one()
        return self.env['payment.provider'].search([
            ('state', '!=', 'disabled'),
            ('code', 'not in', ['custom', 'demo']),
        ])

    def _compute_providers_state(self):
        for config in self:
            providers = config._get_activated_providers()
            primary_provider = next(
                (p for p in providers if p and p.code == config.primary_provider_code),
                None
            )

            config.providers_state = (
                'primary_provider' if primary_provider else 'other' if providers else 'none'
            )
            config.first_provider_label = (
                self.env._('Configure %s', primary_provider.name) if primary_provider else ''
            )

    def _activate_payment_provider(self, menu_id):
        self.ensure_one()
        if not self.primary_provider_code:
            return False

        return self.env.company._run_payment_onboarding_step(
            menu_id=menu_id,
            provider_code=self.primary_provider_code
        )

    def action_configure_first_provider(self):
        self.ensure_one()
        provider = self.env['payment.provider'].search([
            *self.env['payment.provider']._check_company_domain(self.env.company),
            ('code', '=', self.primary_provider_code)
        ], limit=1)
        providers = self._get_activated_providers()
        return {
            'name': self.first_provider_label,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'views': [[False, 'form']],
            'res_id': provider.id if provider in providers else False,
        }
