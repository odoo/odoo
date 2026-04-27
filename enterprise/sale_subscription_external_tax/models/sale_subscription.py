# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class SaleSubscription(models.Model):
    _inherit = "sale.order"

    def _create_recurring_invoice(self, batch_size=30):
        invoices = super()._create_recurring_invoice(batch_size)
        # Already compute taxes for unvalidated documents as they can already be paid
        invoices._get_and_set_external_taxes_on_eligible_records()
        return invoices

    def _do_payment(self, payment_token, invoice, auto_commit=False):
        invoice._get_and_set_external_taxes_on_eligible_records()
        return super()._do_payment(payment_token, invoice, auto_commit=auto_commit)

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        moves._get_and_set_external_taxes_on_eligible_records()
        return moves

    def _compute_recurring_total(self):
        """Use the externally provided values when calculating recurring totals to ensure they are correct
        and match the amounts from _calculate_amounts."""
        external_tax_orders = self.filtered('is_tax_computed_externally')
        for order in external_tax_orders:
            if order.is_subscription or order.subscription_state == '7_upsell':
                order_lines = order.order_line.filtered(lambda x: x.recurring_invoice and not x.display_type)
                order.recurring_total = sum(order_lines.mapped('price_subtotal'))
            else:
                order.recurring_total = 0
        super(SaleSubscription, self - external_tax_orders)._compute_recurring_total()

    def action_confirm(self):
        """Override to recompute taxes after confirmation. sale_external_tax already recomputes taxes before
        confirmation but sale_subscription makes sale.order.line.discount depend on subscription_state.
        subscription_state gets written to during confirmation. This launches a re-computation of
        sale.order.line.discount, which leads to a re-computation of sale.order.line.price_* fields. This will lead
        to the wrong taxes in the case of (partial) exemptions. When this happens subscriptions also won't be
        auto-invoiced because the payment will be seen as a partial payment by
        _get_partial_payment_subscription_transaction()."""
        res = super().action_confirm()
        self._get_and_set_external_taxes_on_eligible_records()
        return res

    def _get_date_for_external_taxes(self):
        """Override to always send a current date for subscriptions. order_date will never change and if taxes change
        it will never be reflected on the subscription. This overrides it to be either the next invoice date so
        customers know what they will be charged. Or it will be the current date for new or churned subscriptions
        without a next invoice date."""
        return (self.next_invoice_date or fields.Date.context_today(self)) if self.is_subscription else super()._get_date_for_external_taxes()

    def _next_billing_details(self):
        """
        Override to re-compute taxes for exempted customers in portal view.
        """
        res = super()._next_billing_details()

        if self.is_tax_computed_externally:
            amount_total = 0
            amount_untaxed = 0
            amount_tax = 0
            for line in res.get('display_lines', []):
                amount_total += line.price_total
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax

            res['tax_totals'] = self._get_external_tax_totals(amount_total, amount_untaxed, amount_tax)
            res['next_invoice_amount'] = self.currency_id.round(sum(self._get_invoiceable_lines().mapped('price_total')))

        return res
