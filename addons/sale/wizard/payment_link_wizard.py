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

    def _get_payment_acquirer_available(self, res_model, res_id, **kwargs):
        """ Select and return the acquirers matching the criteria.

        :param str res_model: active model
        :param int res_id: id of 'active_model' record
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        if res_model == 'sale.order':
            kwargs['sale_order_id'] = res_id
        return super()._get_payment_acquirer_available(**kwargs)

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
