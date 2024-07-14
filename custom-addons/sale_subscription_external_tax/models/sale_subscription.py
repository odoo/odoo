# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


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
