# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    onboarding_payment_module = fields.Selection(
        string="Onboarding Payment Module",
        selection=[
            ('mercado_pago', "Mercado Pago"),
            ('razorpay', "Razorpay"),
            ('stripe', "Stripe"),
        ],
        compute='_compute_onboarding_payment_module',
    )

    @api.depends('currency_id', 'country_id')
    def _compute_onboarding_payment_module(self):
        for company in self:
            if company.currency_id.name == 'INR':
                company.onboarding_payment_module = 'razorpay'
            elif company.country_id.is_stripe_supported_country:
                company.onboarding_payment_module = 'stripe'
            elif company.country_id.is_mercado_pago_supported_country:
                company.onboarding_payment_module = 'mercado_pago'
            else:
                company.onboarding_payment_module = None

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)

        # Duplicate installed providers in the new companies.
        providers_sudo = (
            self.env['payment.provider']
            .sudo()
            .search([
                ('company_id', '=', self.env.user.company_id.id),
                ('module_state', '=', 'installed'),
            ])
        )
        for company in companies:
            if company.parent_id:  # The company is a branch.
                continue  # Only consider top-level companies for provider duplication.

            for provider_sudo in providers_sudo:
                provider_sudo.copy({'company_id': company.id})

        return companies

    def _start_payment_onboarding(self, menu_id=None):
        """Install the onboarding module, configure the provider and run the onboarding action.

        Note: `self.ensure_one()`

        :param int menu_id: The menu from which the onboarding is started, as an `ir.ui.menu` id.
        :return: The action returned by `action_start_onboarding`.
        :rtype: dict
        """
        self.ensure_one()
        if not self.onboarding_payment_module:
            return False

        # Install the onboarding module if needed.
        onboarding_module = (
            self.env['ir.module.module']
            .sudo()  # In sudo mode to search the onboarding module.
            .search([('name', '=', f'payment_{self.onboarding_payment_module}')])
        )
        onboarding_module.filtered(lambda m: m.state == 'uninstalled').button_immediate_install()

        # Create a new env including the freshly installed module.
        new_env = api.Environment(self.env.cr, self.env.uid, self.env.context)

        # Configure the provider.
        provider_code = self.onboarding_payment_module
        provider = new_env['payment.provider'].search(
            [
                ('code', '=', provider_code),
                *self.env['payment.provider']._check_company_domain(self),
            ],
            limit=1,
        )
        if not provider:
            return False

        return provider.action_start_onboarding(menu_id=menu_id)
