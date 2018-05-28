# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PaymentWizard(models.TransientModel):
    _name = 'payment.acquirer.onboarding.wizard'

    paypal_checked = fields.Boolean('Paypal', default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_checked'))
    paypal_email_account = fields.Char('Paypal Email ID', default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_email_account'))
    paypal_seller_account = fields.Char('Paypal Merchant ID', default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_seller_account'))
    paypal_pdt_token = fields.Char('Paypal PDT Token', default=lambda self: self._get_default_payment_acquirer_onboarding_value('paypal_pdt_token'))

    stripe_checked = fields.Boolean('Credit Card (via Stripe)', default=lambda self: self._get_default_payment_acquirer_onboarding_value('stripe_checked'))
    stripe_secret_key = fields.Char(default=lambda self: self._get_default_payment_acquirer_onboarding_value('stripe_secret_key'))
    stripe_publishable_key = fields.Char(default=lambda self: self._get_default_payment_acquirer_onboarding_value('stripe_publishable_key'))

    manual_checked = fields.Boolean('Manual Payment', default=lambda self: self._get_default_payment_acquirer_onboarding_value('manual_checked'))
    manual_name = fields.Char('Method name', default=lambda self: self._get_default_payment_acquirer_onboarding_value('manual_name'))
    manual_post_msg = fields.Html('Payment instructions', default=lambda self: self._get_default_payment_acquirer_onboarding_value('manual_post_msg'))

    _payment_acquirer_onboarding_cache = {}
    _data_fetched = False

    def _get_manual_payment(self, env=None):
        if env is None:
            env = self.env
        return env['payment.acquirer'].search(
            [('provider', '=', 'transfer'),
             ('sequence', '=', 2),
             ('company_id', '=', self.env.user.company_id.id)], limit=1)

    def _get_default_payment_acquirer_onboarding_value(self, key):
        if not self.env.user._is_admin():
            raise UserError(_('Only administators can access this data.'))

        if self._data_fetched:
            return self._payment_acquirer_onboarding_cache.get(key, '')

        self._data_fetched = True

        installed_modules = self.env['ir.module.module'].sudo().search([
            ('name', 'in', ('payment_paypal', 'payment_stripe')),
            ('state', '=', 'installed'),
        ]).mapped('name')

        if 'payment_paypal' in installed_modules:
            self._payment_acquirer_onboarding_cache['paypal_checked'] = True
            acquirer = self.env.ref('payment.payment_acquirer_paypal')
            self._payment_acquirer_onboarding_cache['paypal_email_account'] = acquirer['paypal_email_account']
            self._payment_acquirer_onboarding_cache['paypal_seller_account'] = acquirer['paypal_seller_account']
            self._payment_acquirer_onboarding_cache['paypal_pdt_token'] = acquirer['paypal_pdt_token']

        if 'payment_stripe' in installed_modules:
            self._payment_acquirer_onboarding_cache['stripe_checked'] = True
            acquirer = self.env.ref('payment.payment_acquirer_stripe')
            self._payment_acquirer_onboarding_cache['stripe_secret_key'] = acquirer['stripe_secret_key']
            self._payment_acquirer_onboarding_cache['stripe_publishable_key'] = acquirer['stripe_publishable_key']

        manual_payment = self._get_manual_payment()
        # manual payment is checked if the user has renamed it
        self._payment_acquirer_onboarding_cache['manual_checked'] = \
            (manual_payment['name'] != 'Wire Transfer')
        self._payment_acquirer_onboarding_cache['manual_name'] = manual_payment['name']
        self._payment_acquirer_onboarding_cache['manual_post_msg'] = manual_payment['post_msg']

        return self._payment_acquirer_onboarding_cache.get(key, '')

    def _install_module(self, module_name):
        module = self.env['ir.module.module'].sudo().search([('name', '=', module_name)])
        if module.state not in ('installed', 'to install', 'to upgrade'):
            module.button_immediate_install()

    def _hook_on_save_onboarding_payment_acquirer(self):
        # if any payment method is selected activate "Online Payment" in invoicing settings
        self._install_module('account_payment')

    @api.multi
    def add_payment_methods(self):
        if self.paypal_checked is True:
            self._install_module('payment_paypal')

        if self.stripe_checked is True:
            self._install_module('payment_stripe')

        if self.paypal_checked is True or self.stripe_checked is True or self.manual_checked is True:

            # the wizard is inherited in `sale`
            self._hook_on_save_onboarding_payment_acquirer()

            # create a new env including the freshly installed module(s)
            new_env = api.Environment(self.env.cr, self.env.uid, self.env.context)

            if self.paypal_checked is True:
                new_env.ref('payment.payment_acquirer_paypal').write({
                    'paypal_email_account': self.paypal_email_account,
                    'paypal_seller_account': self.paypal_seller_account,
                    'paypal_pdt_token': self.paypal_pdt_token,
                    'website_published': True,
                })
            if self.stripe_checked is True:
                new_env.ref('payment.payment_acquirer_stripe').write({
                    'stripe_secret_key': self.stripe_secret_key,
                    'stripe_publishable_key': self.stripe_publishable_key,
                    'website_published': True,
                })
            if self.manual_checked is True:
                self._get_manual_payment(new_env).write({
                    'name': self.manual_name,
                    'post_msg': self.manual_post_msg,
                    'website_published': True,
                })
            self._set_payment_acquirer_onboarding_step_done()
            # delete wizard data immediately to get rid of residual credentials
            self.unlink()

        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_skip_payment_onboarding_payment_acquirer_step(self):
        self._set_payment_acquirer_onboarding_step_done()
        return {'type': 'ir.actions.act_window_close'}

    def _set_payment_acquirer_onboarding_step_done(self):
        self.env.user.company_id.write({'payment_acquirer_onboarding_done': True})
