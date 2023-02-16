# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentWizard(models.TransientModel):
    _name = 'payment.acquirer.onboarding.wizard'
    _description = 'Payment acquire onboarding wizard'

    payment_method = fields.Selection([
        ('paypal', "PayPal"),
        ('stripe', "Credit card (via Stripe)"),
        ('other', "Other payment acquirer"),
        ('manual', "Custom payment instructions"),
    ], string="Payment Method", default=lambda self: self._get_default_payment_acquirer_onboarding_value('payment_method'))

    paypal_user_type = fields.Selection([
        ('new_user', "I don't have a Paypal account"),
        ('existing_user', 'I have a Paypal account')], string="Paypal User Type", default='new_user')
    paypal_email_account = fields.Char("Email", default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_email_account'))
    paypal_seller_account = fields.Char("Merchant Account ID")
    paypal_pdt_token = fields.Char("PDT Identity Token", default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_pdt_token'))

    stripe_secret_key = fields.Char(default=lambda self: self._get_default_payment_acquirer_onboarding_value('stripe_secret_key'))
    stripe_publishable_key = fields.Char(default=lambda self: self._get_default_payment_acquirer_onboarding_value('stripe_publishable_key'))

    manual_name = fields.Char("Method",  default=lambda self: self._get_default_payment_acquirer_onboarding_value('manual_name'))
    journal_name = fields.Char("Bank Name", default=lambda self: self._get_default_payment_acquirer_onboarding_value('journal_name'))
    acc_number = fields.Char("Account Number",  default=lambda self: self._get_default_payment_acquirer_onboarding_value('acc_number'))
    manual_post_msg = fields.Html("Payment Instructions")

    _data_fetched = fields.Boolean(store=False)

    @api.onchange('journal_name', 'acc_number')
    def _set_manual_post_msg_value(self):
        self.manual_post_msg = _(
            '<h3>Please make a payment to: </h3><ul><li>Bank: %s</li><li>Account Number: %s</li><li>Account Holder: %s</li></ul>',
            self.journal_name or _("Bank"),
            self.acc_number or _("Account"),
            self.env.company.name
        )

    _payment_acquirer_onboarding_cache = {}

    def _get_manual_payment_acquirer(self, env=None):
        if env is None:
            env = self.env
        module_id = env.ref('base.module_payment_transfer').id
        return env['payment.acquirer'].search([('module_id', '=', module_id),
            ('company_id', '=', env.company.id)], limit=1)

    def _get_default_payment_acquirer_onboarding_value(self, key):
        if not self.env.is_admin():
            raise UserError(_("Only administrators can access this data."))

        if self._data_fetched:
            return self._payment_acquirer_onboarding_cache.get(key, '')

        self._data_fetched = True

        self._payment_acquirer_onboarding_cache['payment_method'] = self.env.company.payment_onboarding_payment_method

        installed_modules = self.env['ir.module.module'].sudo().search([
            ('name', 'in', ('payment_paypal', 'payment_stripe')),
            ('state', '=', 'installed'),
        ]).mapped('name')

        if 'payment_paypal' in installed_modules:
            acquirer = self.env.ref('payment.payment_acquirer_paypal')
            self._payment_acquirer_onboarding_cache['paypal_email_account'] = acquirer['paypal_email_account'] or self.env.user.email or ''
            self._payment_acquirer_onboarding_cache['paypal_pdt_token'] = acquirer['paypal_pdt_token']

        if 'payment_stripe' in installed_modules:
            acquirer = self.env.ref('payment.payment_acquirer_stripe')
            self._payment_acquirer_onboarding_cache['stripe_secret_key'] = acquirer['stripe_secret_key']
            self._payment_acquirer_onboarding_cache['stripe_publishable_key'] = acquirer['stripe_publishable_key']

        manual_payment = self._get_manual_payment_acquirer()
        journal = manual_payment.journal_id

        self._payment_acquirer_onboarding_cache['manual_name'] = manual_payment['name']
        self._payment_acquirer_onboarding_cache['manual_post_msg'] = manual_payment['pending_msg']
        self._payment_acquirer_onboarding_cache['journal_name'] = journal.name if journal.name != "Bank" else ""
        self._payment_acquirer_onboarding_cache['acc_number'] = journal.bank_acc_number

        return self._payment_acquirer_onboarding_cache.get(key, '')

    def _install_module(self, module_name):
        module = self.env['ir.module.module'].sudo().search([('name', '=', module_name)])
        if module.state not in ('installed', 'to install', 'to upgrade'):
            module.button_immediate_install()

    def _on_save_payment_acquirer(self):
        self._install_module('account_payment')

    def add_payment_methods(self):
        """ Install required payment acquiers, configure them and mark the
            onboarding step as done."""
        if self.payment_method == 'stripe' and not self.stripe_publishable_key:
            self.env.company.payment_onboarding_payment_method = self.payment_method
            return self._start_stripe_onboarding()

        if self.payment_method == 'paypal':
            self._install_module('payment_paypal')

        if self.payment_method == 'stripe':
            self._install_module('payment_stripe')

        if self.payment_method  in ('paypal', 'stripe', 'manual', 'other'):

            self._on_save_payment_acquirer()

            self.env.company.payment_onboarding_payment_method = self.payment_method

            # create a new env including the freshly installed module(s)
            new_env = api.Environment(self.env.cr, self.env.uid, self.env.context)

            if self.payment_method == 'paypal':
                acquirer = new_env.ref('payment.payment_acquirer_paypal', raise_if_not_found=False)
                default_journal = new_env['account.journal'].search(
                    [('type', '=', 'bank'), ('company_id', '=', new_env.company.id)], limit=1
                )
                new_env.ref('payment.payment_acquirer_paypal').write({
                    'paypal_email_account': self.paypal_email_account,
                    'paypal_seller_account': self.paypal_seller_account,
                    'paypal_pdt_token': self.paypal_pdt_token,
                    'state': 'enabled',
                    'journal_id': acquirer.journal_id or default_journal
                })
            if self.payment_method == 'stripe':
                new_env.ref('payment.payment_acquirer_stripe').write({
                    'stripe_secret_key': self.stripe_secret_key,
                    'stripe_publishable_key': self.stripe_publishable_key,
                    'state': 'enabled',
                })
            if self.payment_method == 'manual':
                manual_acquirer = self._get_manual_payment_acquirer(new_env)
                if not manual_acquirer:
                    raise UserError(_(
                        'No manual payment method could be found for this company. '
                        'Please create one from the Payment Acquirer menu.'
                    ))
                manual_acquirer.name = self.manual_name
                manual_acquirer.pending_msg = self.manual_post_msg
                manual_acquirer.state = 'enabled'

                journal = manual_acquirer.journal_id
                if journal:
                    journal.name = self.journal_name
                    journal.bank_acc_number = self.acc_number

            # delete wizard data immediately to get rid of residual credentials
            self.sudo().unlink()
        # the user clicked `apply` and not cancel so we can assume this step is done.
        self._set_payment_acquirer_onboarding_step_done()
        return {'type': 'ir.actions.act_window_close'}

    def _set_payment_acquirer_onboarding_step_done(self):
        self.env.company.sudo().set_onboarding_step_done('payment_acquirer_onboarding_state')

    def action_onboarding_other_payment_acquirer(self):
        self._set_payment_acquirer_onboarding_step_done()
        action = self.env["ir.actions.actions"]._for_xml_id("payment.action_payment_acquirer")
        return action

    def _start_stripe_onboarding(self):
        """ Start Stripe Connect onboarding. """
        menu_id = self.env.ref('payment.payment_acquirer_menu').id
        return self.env.company._run_payment_onboarding_step(menu_id)
