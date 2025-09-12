# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.constrains('payment_method_ids')
    def _check_online_payment_methods(self):
        """ Checks the journal currency with _get_online_payment_providers(..., error_if_invalid=True)"""
        for config in self:
            opm_amount = 0
            for pm in config.payment_method_ids:
                if pm.is_online_payment:
                    opm_amount += 1
                    if opm_amount > 1:
                        raise ValidationError(_("A POS config cannot have more than one online payment method."))
                    if not pm._get_online_payment_providers(config.id, error_if_invalid=True):
                        raise ValidationError(_("To use an online payment method in a POS config, it must have at least one published payment provider supporting the currency of that POS config."))

    def _get_cashier_online_payment_method(self):
        self.ensure_one()
        return self.payment_method_ids.filtered('is_online_payment')[:1]

    @api.model
    def _create_online_payment_demo(self):
        """For demo databases, create an online payment method using the demo payment provider if it does not already exist."""
        if self.env['ir.module.module']._get('point_of_sale').demo:
            if module_payment_demo := self.env['ir.module.module'].search([('name', '=', 'payment_demo'), ('state', '=', 'uninstalled')]):
                module_payment_demo.button_install()
            new_online_pm = self.env['pos.payment.method'].sudo()._get_or_create_online_payment_method(self.env.company.id, False)
            if demo_provider := self.env.ref('payment.payment_provider_demo', raise_if_not_found=False):
                new_online_pm.write({'online_payment_provider_ids': [(6, 0, demo_provider.ids)]})

    @api.model
    def _create_journal_and_payment_methods(self, cash_ref=None, cash_journal_vals=None):
        self._create_online_payment_demo()
        return super()._create_journal_and_payment_methods(cash_ref, cash_journal_vals)
