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
        """ Override of the base method to add the order_id in the link. """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for payment_link in self:
            # only add order_id for SOs,
            # otherwise the controller might try to link it with an unrelated record
            # NOTE: company_id is not necessary here, we have it in order_id
            # however, should parsing of the id fail in the controller, let's include
            # it anyway
            if payment_link.res_model == 'sale.order':
                payment_link.link = ('%s/website_payment/pay?reference=%s&amount=%s&currency_id=%s'
                                    '&partner_id=%s&order_id=%s&company_id=%s&access_token=%s') % (
                                        base_url,
                                        urls.url_quote(payment_link.description),
                                        payment_link.amount,
                                        payment_link.currency_id.id,
                                        payment_link.partner_id.id,
                                        payment_link.res_id,
                                        payment_link.company_id.id,
                                        payment_link.access_token
                                    )
            else:
                super(SalePaymentLink, payment_link)._generate_link()