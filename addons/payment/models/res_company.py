# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    payment_onboarding_payment_method = fields.Selection(
        string="Selected onboarding payment method",
        selection=[('razorpay', "Razorpay"), ('stripe', "Stripe")],
        compute="_compute_payment_onboarding_payment_method",
        store=True,
    )

    @api.depends('country_id', 'currency_id')
    def _compute_payment_onboarding_payment_method(self):
        for company in self:
            if company.currency_id.name == 'INR':
                company.payment_onboarding_payment_method = 'razorpay'
            elif company.country_id.is_stripe_supported_country:
                company.payment_onboarding_payment_method = 'stripe'
            else:
                company.payment_onboarding_payment_method = False

    def _run_payment_onboarding_step(self, menu_id=None):
        """ Install the suggested payment modules and configure the providers.

        It's checked that the current company has a Chart of Account.

        :param int menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id
        :return: The action returned by `action_stripe_connect_account` or
                 `action_razorpay_redirect_to_oauth_url`
        :rtype: dict
        """
        self.env.company.get_chart_of_accounts_or_fail()

        if not self.payment_onboarding_payment_method:
            return {}

        provider_code = self.payment_onboarding_payment_method

        self._install_modules([f'payment_{provider_code}'])

        # Create a new env including the freshly installed module(s)
        new_env = api.Environment(self.env.cr, self.env.uid, self.env.context)

        # Configure Provider
        provider = new_env['payment.provider'].search([
            *self.env['payment.provider']._check_company_domain(self.env.company),
            ('code', '=', provider_code)
        ], limit=1)
        if not provider:
            base_provider = self.env.ref(f'payment.payment_provider_{provider_code}')
            # Use sudo to access payment provider record that can be in different company.
            provider = base_provider.sudo().with_context(
                provider_onboarding=True,
            ).copy(default={'company_id': self.env.company.id})

        return (
            provider.action_razorpay_redirect_to_oauth_url()
            if provider_code == 'razorpay'
            else provider.action_stripe_connect_account(menu_id=menu_id)
        )

    def _install_modules(self, module_names):
        modules_sudo = self.env['ir.module.module'].sudo().search([('name', 'in', module_names)])
        STATES = ['installed', 'to install', 'to upgrade']
        modules_sudo.filtered(lambda m: m.state not in STATES).button_immediate_install()
