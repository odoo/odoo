# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PaymentWizard(models.TransientModel):
    _name = 'payment.acquirer.onboarding.wizard'
    _description = 'Payment acquire onboarding wizard'

    payment_method = fields.Selection([
        ('paypal', "Pay with PayPal"),
        ('stripe', "Pay with credit card (via Stripe)"),
        ('other', "Pay with another payment acquirer"),
        ('manual', "Custom payment instructions"),
    ], string="Payment Method", default=lambda self: self._get_default_payment_acquirer_onboarding_value('payment_method'))

    paypal_email_account = fields.Char("PayPal Email ID", default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_email_account'))
    paypal_seller_account = fields.Char("Paypal Merchant ID", default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_seller_account'))
    paypal_pdt_token = fields.Char("Paypal PDT Token", default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_pdt_token'))

    stripe_secret_key = fields.Char(default=lambda self: self._get_default_payment_acquirer_onboarding_value('stripe_secret_key'))
    stripe_publishable_key = fields.Char(default=lambda self: self._get_default_payment_acquirer_onboarding_value('stripe_publishable_key'))

    manual_name = fields.Char("Method",  default=lambda self: self._get_default_payment_acquirer_onboarding_value('manual_name'))
    journal_name = fields.Char("Bank Name", default=lambda self: self._get_default_payment_acquirer_onboarding_value('journal_name'))
    acc_number = fields.Char("Account Number",  default=lambda self: self._get_default_payment_acquirer_onboarding_value('acc_number'))
    manual_post_msg = fields.Html("Payment Instructions")

    @api.onchange('journal_name', 'acc_number')
    def _set_manual_post_msg_value(self):
        self.manual_post_msg = _('<h3>Please make a payment to: </h3><ul><li>Bank: %s</li><li>Account Number: %s</li><li>Account Holder: %s</li></ul>') %\
                               (self.journal_name or _("Bank") , self.acc_number or _("Account"), self.env.company.name)

    _payment_acquirer_onboarding_cache = {}
    _data_fetched = False

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
            self._payment_acquirer_onboarding_cache['paypal_email_account'] = acquirer['paypal_email_account']
            self._payment_acquirer_onboarding_cache['paypal_seller_account'] = acquirer['paypal_seller_account']
            self._payment_acquirer_onboarding_cache['paypal_pdt_token'] = acquirer['paypal_pdt_token']

        if 'payment_stripe' in installed_modules:
            acquirer = self.env.ref('payment.payment_acquirer_stripe')
            self._payment_acquirer_onboarding_cache['stripe_secret_key'] = acquirer['stripe_secret_key']
            self._payment_acquirer_onboarding_cache['stripe_publishable_key'] = acquirer['stripe_publishable_key']

        manual_payment = self._get_manual_payment_acquirer()
        journal = manual_payment.journal_id

        self._payment_acquirer_onboarding_cache['manual_name'] = manual_payment['name']
        self._payment_acquirer_onboarding_cache['manual_post_msg'] = manual_payment['post_msg']
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
                new_env.ref('payment.payment_acquirer_paypal').write({
                    'paypal_email_account': self.paypal_email_account,
                    'paypal_seller_account': self.paypal_seller_account,
                    'paypal_pdt_token': self.paypal_pdt_token,
                    'website_published': True,
                    'environment': 'prod',
                })
            if self.payment_method == 'stripe':
                new_env.ref('payment.payment_acquirer_stripe').write({
                    'stripe_secret_key': self.stripe_secret_key,
                    'stripe_publishable_key': self.stripe_publishable_key,
                    'website_published': True,
                    'environment': 'prod',
                })
            if self.payment_method == 'manual':
                manual_acquirer = self._get_manual_payment_acquirer(new_env)
                if not manual_acquirer:
                    raise UserError(_(
                        'No manual payment method could be found for this company. ' +
                        'Please create one from the Payment Acquirer menu.'
                    ))
                manual_acquirer.name = self.manual_name
                manual_acquirer.post_msg = self.manual_post_msg
                manual_acquirer.website_published = True
                manual_acquirer.environment = 'prod'

                journal = manual_acquirer.journal_id
                if journal:
                    journal.name = self.journal_name
                    journal.bank_acc_number = self.acc_number
                else:
                    raise UserError(_("You have to set a journal for your payment acquirer %s." % (self.manual_name,)))

            # delete wizard data immediately to get rid of residual credentials
            self.unlink()
        # the user clicked `apply` and not cancel so we can assume this step is done.
        self._set_payment_acquirer_onboarding_step_done()
        return {'type': 'ir.actions.act_window_close'}

    def _set_payment_acquirer_onboarding_step_done(self):
        self.env.company.set_onboarding_step_done('payment_acquirer_onboarding_state')

    def action_onboarding_other_payment_acquirer(self):
        self._set_payment_acquirer_onboarding_step_done()
        action = self.env.ref('payment.action_payment_acquirer').read()[0]
        return action
