# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PaymentAcquirer(models.Model):
    _name = 'payment.acquirer'
    _inherit = ['payment.acquirer','website.published.mixin']

    is_cod = fields.Boolean()

    @api.model
    def _get_acquirer_buttons(self, order, button_values, add_domain=None):
        domain = [('website_published', '=', True), ('company_id', '=', order.company_id.id)]
        if add_domain:
            domain = domain + add_domain
        acquirers = self.search(domain)
        res = []
        for acquirer in acquirers:
            acquirer_button = acquirer.sudo().render(
                '/',
                order.amount_total,
                order.pricelist_id.currency_id.id,
                values=button_values
            )
            acquirer.button = acquirer_button
            res.append(acquirer)
        return res
