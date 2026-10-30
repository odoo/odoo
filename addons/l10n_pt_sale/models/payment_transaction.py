from odoo import Command, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _post_process(self):
        # EXTENDS sale
        # A confirmed online payment posts the invoices it pays and reconciles them at once: the
        # customer gets them right away, so they are issued as they are posted.
        return super(PaymentTransaction, self.with_context(l10n_pt_issue_automatically=True))._post_process()

    def _check_amount_and_confirm_order(self):
        # EXTENDS sale
        # A PT quotation is confirmed as from its form (D-6): it stays as issued, and a new sales order
        # is confirmed from it. The payment is for that sales order, and the customer lands on it.
        pt_txs = self.filtered(lambda tx: len(tx.sale_order_ids) == 1 and tx.sale_order_ids._l10n_pt_country_ok())
        confirmed_orders = super(PaymentTransaction, self - pt_txs)._check_amount_and_confirm_order()
        for tx in pt_txs:
            quotation = tx.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent'))
            if not quotation:
                continue
            if sales_order := quotation.sales_order_ids.filtered(lambda so: so.state == 'sale').sorted('id')[-1:]:
                # Confirmed from its form already (e.g. paid through a payment link sent before).
                tx.sale_order_ids = [Command.set(sales_order.ids)]
            elif not quotation._has_to_be_signed() and quotation._is_confirmation_amount_reached():
                sales_order = quotation.with_context(
                    send_email=True, sale_include_signature=True,
                )._l10n_pt_create_sales_order(transactions=tx)
                confirmed_orders |= sales_order
            else:
                continue
            tx.landing_route = sales_order.get_portal_url()
        return confirmed_orders
