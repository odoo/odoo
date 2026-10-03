# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'

    @api.depends('res_model', 'res_id')
    def _compute_warning_message(self):
        stock_wizard = self.env['payment.link.wizard']
        for wizard in self:
            if wizard.res_model != 'sale.order':
                continue
            order = self.env['sale.order'].browse(wizard.res_id)
            if not order.warehouse_id and order.order_line.product_id.filtered(lambda p: p.type == 'consu'):
                wizard.warning_message = self.env._('You cannot generate a payment link for an order without a warehouse.')
                stock_wizard |= wizard
        super(PaymentLinkWizard, self - stock_wizard)._compute_warning_message()
