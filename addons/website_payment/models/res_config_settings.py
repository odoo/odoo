# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acquirers_state = fields.Selection(
        selection=[
            ('none', 'None'),
            ('paypal_only', 'Paypal Only'),
            ('other_than_paypal', 'Other than Paypal')
        ],
        compute='_compute_acquirers_state')
    first_provider_label = fields.Char(
        compute='_compute_acquirers_state')
    module_payment_paypal = fields.Boolean(
        string='Paypal - Express Checkout')

    def _get_activated_acquirers(self):
        self.ensure_one()
        wire_transfer = self.env.ref('payment.payment_acquirer_transfer', raise_if_not_found=False)
        return self.env['payment.acquirer'].search([
            ('state', '!=', 'disabled'),
            ('id', '!=', wire_transfer.id if wire_transfer else False),
            '|',
            ('website_id', '=', False),
            ('website_id', '=', self.website_id.id)
        ])

    @api.depends('website_id')
    def _compute_acquirers_state(self):
        paypal = self.env.ref('payment.payment_acquirer_paypal', raise_if_not_found=False)
        stripe = self.env.ref('payment.payment_acquirer_stripe', raise_if_not_found=False)
        for config in self:
            acquirers = config._get_activated_acquirers()
            first_provider = stripe if stripe in acquirers else acquirers[0] if acquirers else acquirers
            config.first_provider_label = _('Configure %s', first_provider.name)
            if len(acquirers) == 1 and acquirers == paypal:
                config.acquirers_state = 'paypal_only'
            elif len(acquirers) >= 1:
                config.acquirers_state = 'other_than_paypal'
            else:
                config.acquirers_state = 'none'

    def action_activate_stripe(self):
        stripe = self.env.ref('payment.payment_acquirer_stripe')
        stripe.button_immediate_install()
        if stripe.state == 'disabled':
            stripe.state = 'test'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_configure_first_provider(self):
        self.ensure_one()
        stripe = self.env.ref('payment.payment_acquirer_stripe')
        acquirers = self._get_activated_acquirers()
        return {
            'name': self.first_provider_label,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'payment.acquirer',
            'views': [[False, 'form']],
            'res_id': stripe.id if stripe in acquirers else acquirers[0].id,
        }
