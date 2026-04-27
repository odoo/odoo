# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _create_invoices(self, sale_orders):

        if self.advance_payment_method != 'delivered':
            return super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)

        else:

            subscriptions = sale_orders.filtered('is_subscription')

            if subscriptions:
                # Close ending subscriptions
                auto_close_subscription = subscriptions.filtered_domain([('end_date', '!=', False)])
                auto_close_subscription._subscription_auto_close()

                # Set quantity to invoice before the invoice creation. If something goes wrong, the line will appear as "to invoice"
                subscription_invoiceable_lines = subscriptions._get_invoiceable_lines()
                subscription_invoiceable_lines._reset_subscription_qty_to_invoice()

            invoices = super(SaleAdvancePaymentInv, self)._create_invoices(sale_orders)

            if subscriptions:
                subscriptions._process_invoices_to_send(invoices)

            return invoices
