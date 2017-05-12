# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    default_acquirer = fields.Many2one("payment.acquirer",
                                       string="Default Acquirer",
                                       help="Default payment acquirer for website payments; your provider needs to be visible in the website.",
                                       domain="[('website_published','=',True)]"
                                       )

    @api.model
    def get_default_acquirer(self, fields):
        default_acquirer = False
        if 'default_acquirer' in fields:
            default_acquirer = self.env['ir.values'].get_default('payment.transaction', 'acquirer_id', company_id=self.env.user.company_id.id)
        return {
            'default_acquirer': default_acquirer
        }

    @api.multi
    def set_default_acquirer(self):
        for wizard in self:
            ir_values = self.env['ir.values']
            if self.user_has_groups('base.group_erp_manager'):
                ir_values = ir_values.sudo()
            ir_values.set_default('payment.transaction', 'acquirer_id', wizard.default_acquirer.id, company_id=self.env.user.company_id.id)
