# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import api, models


class PaymentLinkWizard(models.TransientModel):
    _inherit = 'payment.link.wizard'
    _description = 'Generate Sales Payment Link'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if res['res_id'] and res['res_model'] == 'sale.order':
            record = self.env[res['res_model']].browse(res['res_id'])
            res.update({
                'description': record.name,
                'amount': record.amount_total - sum(record.invoice_ids.filtered(lambda x: x.state != 'cancel').mapped('amount_total')),
                'currency_id': record.currency_id.id,
                'partner_id': record.partner_id.id,
                'amount_max': record.amount_total
            })
        return res

    def _get_payment_acquirer_available(self, company_id=None, partner_id=None, currency_id=None, sale_order_id=None):
        """ Select and return the acquirers matching the criteria.

        :param int company_id: The company to which acquirers must belong, as a `res.company` id
        :param int partner_id: The partner making the payment, as a `res.partner` id
        :param int currency_id: The payment currency if known beforehand, as a `res.currency` id
        :param int sale_order_id: The sale order currency if known beforehand, as a `sale.order` id
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        return self.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            company_id=company_id or self.company_id.id,
            partner_id=partner_id or self.partner_id.id,
            currency_id=currency_id or self.currency_id.id,
            sale_order_id=sale_order_id or self.res_id,
        )

    def _generate_link(self):
        """ Override of payment to add the sale_order_id in the link. """
        for payment_link in self:
            # The sale_order_id field only makes sense if the document is a sales order
            if payment_link.res_model == 'sale.order':
                related_document = self.env[payment_link.res_model].browse(payment_link.res_id)
                base_url = related_document.get_base_url()
                payment_link.link = f'{base_url}/payment/pay' \
                                    f'?reference={urls.url_quote(payment_link.description)}' \
                                    f'&amount={payment_link.amount}' \
                                    f'&sale_order_id={payment_link.res_id}' \
                                    f'{"&acquirer_id=" + str(payment_link.payment_acquirer_selection) if payment_link.payment_acquirer_selection != "all" else "" }' \
                                    f'&access_token={payment_link.access_token}'
                # Order-related fields are retrieved in the controller
            else:
                super(PaymentLinkWizard, payment_link)._generate_link()
