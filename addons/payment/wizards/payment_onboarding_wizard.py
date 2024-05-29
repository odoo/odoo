# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentWizard(models.TransientModel):
    _name = 'payment.provider.onboarding.wizard'
    _description = 'Payment provider onboarding wizard'

    payment_method = fields.Selection([
        ('stripe', "Credit & Debit card (via Stripe)"),
        ('paypal', "PayPal"),
        ('manual', "Custom payment instructions"),
    ], string="Payment Method", default=lambda self: self._get_default_payment_provider_onboarding_value('payment_method'))
    paypal_email_account = fields.Char("Email", default=lambda self: self._get_default_payment_provider_onboarding_value('paypal_email_account'))

    # Account-specific logic. It's kept here rather than moved in `account_payment` as it's not used by `account` module.
    manual_name = fields.Char("Method", default=lambda self: self._get_default_payment_provider_onboarding_value('manual_name'))
    journal_name = fields.Char("Bank Name", default=lambda self: self._get_default_payment_provider_onboarding_value('journal_name'))
    acc_number = fields.Char("Account Number", default=lambda self: self._get_default_payment_provider_onboarding_value('acc_number'))
    manual_post_msg = fields.Html("Payment Instructions")

    _data_fetched = fields.Boolean(store=False)

    @api.onchange('journal_name', 'acc_number')
    def _set_manual_post_msg_value(self):
        self.manual_post_msg = _(
            '<h3>Please make a payment to: </h3><ul><li>Bank: %(bank)s</li><li>Account Number: %(account_number)s</li><li>Account Holder: %(account_holder)s</li></ul>',
            bank=self.journal_name or _("Bank"),
            account_number=self.acc_number or _("Account"),
            account_holder=self.env.company.name,
        )

    _payment_provider_onboarding_cache = {}

    def _get_manual_payment_provider(self, env=None):
        if env is None:
            env = self.env
        module_id = env.ref('base.module_payment_custom').id
        return env['payment.provider'].search([
            *env['payment.provider']._check_company_domain(self.env.company),
            ('module_id', '=', module_id),
        ], limit=1)

    def _get_default_payment_provider_onboarding_value(self, key):
        if not self.env.is_admin():
            raise UserError(_("Only administrators can access this data."))

        if self._data_fetched:
            return self._payment_provider_onboarding_cache.get(key, '')

        self._data_fetched = True

        self._payment_provider_onboarding_cache['payment_method'] = self.env.company.payment_onboarding_payment_method

        installed_modules = self.env['ir.module.module'].sudo().search([
            ('name', 'in', ('payment_paypal', 'payment_stripe')),
            ('state', '=', 'installed'),
        ]).mapped('name')

        if 'payment_paypal' in installed_modules:
            provider = self.env['payment.provider'].search([
                *self.env['payment.provider']._check_company_domain(self.env.company),
                ('code', '=', 'paypal'),

            ], limit=1)
            self._payment_provider_onboarding_cache['paypal_email_account'] = provider['paypal_email_account'] or self.env.company.email
        else:
            self._payment_provider_onboarding_cache['paypal_email_account'] = self.env.company.email

        manual_payment = self._get_manual_payment_provider()
        journal = manual_payment.journal_id

        self._payment_provider_onboarding_cache['manual_name'] = manual_payment['name']
        self._payment_provider_onboarding_cache['manual_post_msg'] = manual_payment['pending_msg']
        self._payment_provider_onboarding_cache['journal_name'] = journal.name if journal.name != "Bank" else ""
        self._payment_provider_onboarding_cache['acc_number'] = journal.bank_acc_number

        return self._payment_provider_onboarding_cache.get(key, '')

    def add_payment_methods(self):
        """ Install required payment providers, configure them and mark the
            onboarding step as done."""
        payment_method = self.payment_method

        if self.payment_method == 'paypal':
            self.env.company._install_modules(['payment_paypal', 'account_payment'])
        elif self.payment_method == 'manual':
            self.env.company._install_modules(['account_payment'])

        if self.payment_method in ('paypal', 'manual'):
            # create a new env including the freshly installed module(s)
            new_env = api.Environment(self.env.cr, self.env.uid, self.env.context)

            if self.payment_method == 'paypal':
                provider = new_env['payment.provider'].search([
                    *self.env['payment.provider']._check_company_domain(self.env.company),
                    ('code', '=', 'paypal')
                ], limit=1)
                if not provider:
                    base_provider = self.env.ref('payment.payment_provider_paypal')
                    # Use sudo to access payment provider record that can be in different company.
                    provider = base_provider.sudo().copy(default={'company_id':self.env.company.id})
                provider.write({
                    'paypal_email_account': self.paypal_email_account,
                    'state': 'enabled',
                    'is_published': 'True',
                })
            elif self.payment_method == 'manual':
                manual_provider = self._get_manual_payment_provider(new_env)
                if not manual_provider:
                    raise UserError(_(
                        'No manual payment method could be found for this company. '
                        'Please create one from the Payment Provider menu.'
                    ))
                manual_provider.name = self.manual_name
                manual_provider.pending_msg = self.manual_post_msg
                manual_provider.state = 'enabled'

                journal = manual_provider.journal_id
                if journal:
                    journal.name = self.journal_name
                    journal.bank_acc_number = self.acc_number

        if self.payment_method in ('paypal', 'manual', 'stripe'):
            self.env.company.payment_onboarding_payment_method = self.payment_method

        # delete wizard data immediately to get rid of residual credentials
        self.sudo().unlink()

        if payment_method == 'stripe':
            return self._start_stripe_onboarding()

        # the user clicked `apply` and not cancel, so we can assume this step is done.
        self.env['onboarding.onboarding.step'].sudo().action_validate_step_payment_provider()
        return {'type': 'ir.actions.act_window_close'}

    def _start_stripe_onboarding(self):
        """ Start Stripe Connect onboarding. """
        menu = self.env.ref('account_payment.payment_provider_menu', False)
        menu_id = menu and menu.id  # Only set if `account_payment` is installed.
        return self.env.company._run_payment_onboarding_step(menu_id)
