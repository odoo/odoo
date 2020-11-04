# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import api, models


class SalePaymentLink(models.TransientModel):
    _inherit = "payment.link.wizard"
    _description = "Generate Sales Payment Link"

    @api.model
    def default_get(self, fields):
        res = super(SalePaymentLink, self).default_get(fields)
        if res['res_id'] and res['res_model'] == 'sale.order':
            record = self.env[res['res_model']].browse(res['res_id'])
            res.update({
                'description': record.name,
                'amount': record.amount_total - sum(record.invoice_ids.mapped('amount_total')),
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'amount_max': record.amount_total
            })
        return res

    def _generate_link(self):
        """ Override of the base method to add the sale_order_id in the link. """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for payment_link in self:
            # The sale_order_id field only makes sense if the document is a sale order
            if payment_link.res_model == 'sale.order':
                payment_link.link = f'{base_url}/payment/pay' \
                                    f'?reference={urls.url_quote(payment_link.description)}' \
                                    f'&sale_order_id={payment_link.res_id}' \
                                    f'&access_token={payment_link.access_token}'
                # Order-related fields (amount, ...) are retrieved in the controller
            else:
                super(SalePaymentLink, payment_link)._generate_link()
