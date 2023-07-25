# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    payment_acquirer_onboarding_state = fields.Selection(
        string="State of the onboarding payment acquirer step",
        selection=[('not_done', "Not done"), ('just_done', "Just done"), ('done', "Done")],
        default='not_done')
    payment_onboarding_payment_method = fields.Selection(
        string="Selected onboarding payment method",
        selection=[
            ('paypal', "PayPal"),
            ('stripe', "Stripe"),
            ('manual', "Manual"),
            ('other', "Other"),
        ])

    @api.model
    def action_open_payment_onboarding_payment_acquirer(self):
        """ Called by onboarding panel above the customer invoice list. """
        # TODO remove me in master.
        #  This action is never used anywhere because the onboarding step's method is overridden in
        #  website_sale to call action_open_website_sale_onboarding_payment_acquirer instead.
        # Fail if there are no existing accounts
        self.env.company.get_chart_of_accounts_or_fail()

        action = self.env['ir.actions.actions']._for_xml_id(
            'payment.action_open_payment_onboarding_payment_acquirer_wizard'
        )
        return action

    def _run_payment_onboarding_step(self, menu_id):
        """ Install the suggested payment modules and configure the acquirers.

        It's checked that the current company has a Chart of Account.

        :param int menu_id: The menu from which the user started the onboarding step, as an
                            `ir.ui.menu` id
        :return: The action returned by `action_stripe_connect_account`
        :rtype: dict
        """
        self.env.company.get_chart_of_accounts_or_fail()

        self._install_modules(['payment_stripe', 'account_payment'])

        # Create a new env including the freshly installed module(s)
        new_env = api.Environment(self.env.cr, self.env.uid, self.env.context)

        # Configure Stripe
        default_journal = new_env['account.journal'].search(
            [('type', '=', 'bank'), ('company_id', '=', new_env.company.id)], limit=1
        )

        stripe_acquirer = new_env['payment.acquirer'].search(
            [('company_id', '=', self.env.company.id), ('name', '=', 'Stripe')], limit=1
        )
        if not stripe_acquirer:
            base_acquirer = self.env.ref('payment.payment_acquirer_stripe')
            # Use sudo to access payment acquirer record that can be in different company.
            stripe_acquirer = base_acquirer.sudo().copy(default={'company_id': self.env.company.id})
            stripe_acquirer.company_id = self.env.company.id
        stripe_acquirer.journal_id = stripe_acquirer.journal_id or default_journal

        return stripe_acquirer.action_stripe_connect_account(menu_id=menu_id)

    def _install_modules(self, module_names):
        modules_sudo = self.env['ir.module.module'].sudo().search([('name', 'in', module_names)])
        STATES = ['installed', 'to install', 'to upgrade']
        modules_sudo.filtered(lambda m: m.state not in STATES).button_immediate_install()

    def _mark_payment_onboarding_step_as_done(self):
        """ Mark the payment onboarding step as done.

        :return: None
        """
        self.set_onboarding_step_done('payment_acquirer_onboarding_state')

    def get_account_invoice_onboarding_steps_states_names(self):
        """ Override of account. """
        steps = super().get_account_invoice_onboarding_steps_states_names()
        return steps + ['payment_acquirer_onboarding_state']
