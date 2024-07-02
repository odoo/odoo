# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.tools import format_amount


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'
    _description = 'Generate Sales Payment Link'

    amount_paid = fields.Monetary(string="Already Paid", readonly=True)
    confirmation_message = fields.Char(compute='_compute_confirmation_message')

    @api.depends('amount')
    def _compute_confirmation_message(self):
        self.confirmation_message = False
        for wizard in self.filtered(lambda w: w.res_model == 'sale.order'):
            sale_order = wizard.env['sale.order'].sudo().browse(wizard.res_id)
            if sale_order.state in ('draft', 'sent') and sale_order.require_payment:
                remaining_amount = sale_order._get_prepayment_required_amount() - sale_order.amount_paid
                if wizard.currency_id.compare_amounts(wizard.amount, remaining_amount) >= 0:
                    wizard.confirmation_message = _("This payment will confirm the quotation.")
                else:
                    wizard.confirmation_message = _(
                        "Customer needs to pay at least %(amount)s to confirm the order.",
                        amount=format_amount(wizard.env, remaining_amount, wizard.currency_id),
                    )

    def _generate_link(self, base_url, related_document=None):
        res = super()._generate_link(base_url, related_document)

        if self.res_model == 'sale.order':
            url_params = {
                'access_token': related_document._portal_ensure_token(),
                'link_amount': self.amount,
                'showPaymentModal': 'true',
            }
            res = f'{base_url}/my/orders/{related_document.id}?{urls.url_encode(url_params)}'

        return res
