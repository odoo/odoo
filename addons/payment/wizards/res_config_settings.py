# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    active_provider_id = fields.Many2one(
        string="Active Provider",
        comodel_name='payment.provider',
        compute='_compute_active_provider_id',
    )
    has_enabled_provider = fields.Boolean(
        string="Has Enabled Provider", compute='_compute_has_enabled_provider'
    )
    onboarding_payment_module = fields.Selection(
        string="Onboarding Payment Module",
        selection=[
            ('mercado_pago', "Mercado Pago"),
            ('razorpay', "Razorpay"),
            ('stripe', "Stripe"),
        ],
        compute='_compute_onboarding_payment_module',
    )

    # === COMPUTE METHODS === #

    @api.depends('company_id')
    def _compute_active_provider_id(self):
        for config in self:
            active_providers_domain = config._get_active_providers_domain()
            if active_providers := self.env['payment.provider'].search(
                active_providers_domain, limit=1
            ):
                config.active_provider_id = active_providers[0]
            else:
                config.active_provider_id = None

    @api.depends('company_id')
    def _compute_has_enabled_provider(self):
        for config in self:
            enabled_providers_domain = config._get_active_providers_domain(enabled_only=True)
            config.has_enabled_provider = bool(
                self.env['payment.provider'].search(enabled_providers_domain, limit=1)
            )

    def _get_active_providers_domain(self, enabled_only=False):
        """Return the domain to search for active providers.

        :param bool enabled_only: Whether only enabled providers should be considered active.
        :return: The active providers domain.
        :rtype: Domain
        """
        return Domain.AND([
            [('state', '=', 'enabled') if enabled_only else ('state', '!=', 'disabled')],
            self.env['payment.provider']._check_company_domain(self.company_id),
        ])

    @api.depends('company_id.currency_id', 'company_id.country_id.is_stripe_supported_country')
    def _compute_onboarding_payment_module(self):
        for config in self:
            if config.company_id.currency_id.name == 'INR':
                config.onboarding_payment_module = 'razorpay'
            elif config.company_id.country_id.is_stripe_supported_country:
                config.onboarding_payment_module = 'stripe'
            elif config.company_id.country_id.is_mercado_pago_supported_country:
                config.onboarding_payment_module = 'mercado_pago'
            else:
                config.onboarding_payment_module = None

    # === ACTION METHODS === #

    def action_view_active_provider(self):
        provider = self.active_provider_id.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.provider',
            'views': [[False, 'form']],
            'res_id': provider.id,
        }

    def _start_payment_onboarding(self, menu_id=None):
        """Install the onboarding module, configure the provider and run the onboarding action.

        :param int menu_id: The menu from which the onboarding is started, as an `ir.ui.menu` id.
        :return: The action returned by `action_start_onboarding`.
        :rtype: dict
        """
        self.ensure_one()
        if not self.onboarding_payment_module:
            return False

        # Install the onboarding module if needed.
        onboarding_module = self.env['ir.module.module'].search(
            [('name', '=', f'payment_{self.onboarding_payment_module}')]
        )
        self._install_modules(onboarding_module)
        # Create a new env including the freshly installed module.
        new_env = api.Environment(self.env.cr, self.env.uid, self.env.context)

        # Configure the provider.
        provider_code = self.onboarding_payment_module
        provider = new_env['payment.provider'].search([
            ('code', '=', provider_code),
            *self.env['payment.provider']._check_company_domain(self.env.company),
        ], limit=1)
        if not provider:
            return False

        return provider.action_start_onboarding(menu_id=menu_id)
