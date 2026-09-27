# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools import formatLang

from odoo.addons.account.wizard.accrued_orders import ellipsis


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    def _get_accrual_qty_price_and_amount(self, order_line):
        """ (qty_to_invoice, price_unit, amount, amount_currency) for a single accrual line.
        Positive qty_to_invoice: delivered more than invoiced ("Invoices to be Issued").
        Negative: invoiced more than delivered ("Invoiced Not Delivered").
        """
        qty_to_invoice = order_line.qty_delivered_at_date - order_line.qty_invoiced_at_date
        price_unit = order_line.price_unit
        if qty_to_invoice > 0:
            amount_currency = order_line.amount_to_invoice_at_date
            amount = order_line.order_id.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
        else:
            amount_currency, amount, processed_qty = 0, 0, 0
            for inv_line in order_line.invoice_lines.filtered(lambda ivl: ivl.move_id.state == 'posted').sorted(reverse=True):
                amount_currency -= inv_line.price_subtotal
                amount -= order_line.order_id.currency_id._convert(inv_line.price_subtotal, self.company_id.currency_id, self.company_id)
                processed_qty += inv_line.quantity
                if processed_qty >= abs(qty_to_invoice):
                    break
            if processed_qty:
                price_unit = abs(amount / processed_qty)
        return qty_to_invoice, price_unit, amount, amount_currency

    def _get_accrual_main_line_vals(self, order_lines, is_purchase, accrual_entry_date):
        if is_purchase:
            return super()._get_accrual_main_line_vals(order_lines, is_purchase, accrual_entry_date)

        # For each line in `order_lines` (sale.order.line): its revenue line and its
        # invoices_to_issue/invoiced_not_delivered counterpart.
        vals_list = []
        counterpart_vals_list = []
        for order_line in order_lines:
            order = order_line.order_id
            product = order_line.product_id
            order_line_label = ellipsis(order_line.name, 20)
            qty_to_invoice, price_unit, amount, amount_currency = self._get_accrual_qty_price_and_amount(order_line)

            account = self._get_computed_account(order, product, False)
            label = _(
                '%(order)s - %(order_line)s; %(quantity_invoiced)s Invoiced, %(quantity_delivered)s Delivered at %(unit_price)s each',
                order=order.display_name,
                order_line=order_line_label,
                quantity_invoiced=order_line.qty_invoiced_at_date,
                quantity_delivered=order_line.qty_delivered_at_date,
                unit_price=formatLang(self.env, price_unit, currency_obj=order.currency_id),
            )
            distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
            revenue_vals = self._get_aml_vals(False, order, amount, amount_currency, account.id, label=label, analytic_distribution=distribution)

            accrual_account = self.account_id or product.product_tmpl_id._get_product_accounts()[
                'invoices_to_issue' if qty_to_invoice > 0 else 'invoiced_not_delivered'
            ]
            counterpart_vals = self._get_aml_vals(
                False, order, -amount, -amount_currency, accrual_account.id,
                label=_('Accrued total'), analytic_distribution=distribution,
            )
            counterpart_vals_list.append(counterpart_vals)
            vals_list.append(revenue_vals)
        return vals_list, self._merge_aml_vals(counterpart_vals_list)

    def _get_accrual_cogs_line_vals(self, order_lines, is_purchase, accrual_entry_date):
        if is_purchase:
            return super()._get_accrual_cogs_line_vals(order_lines, is_purchase, accrual_entry_date)

        # For real-time-valued, storable products, the perpetual-valuation adjustment needed
        # because perpetual valuation already posts COGS in real time instead of waiting for
        # the invoice.
        inventory_vals_list = []
        counterpart_vals_list = []
        for order_line in order_lines:
            order = order_line.order_id
            product = order_line.product_id
            if product.valuation != 'real_time' or not product.is_storable:
                continue
            qty_to_invoice, __, __, __ = self._get_accrual_qty_price_and_amount(order_line)
            if not qty_to_invoice:
                continue
            product_accounts = product._get_product_accounts()
            expense_account = product_accounts.get('expense')
            stock_variation_account = product_accounts.get('stock_variation')
            if not expense_account or not stock_variation_account:
                continue

            order_line_label = ellipsis(order_line.name, 20)
            if qty_to_invoice > 0:
                # Delivered, not invoiced yet: no COGS posted for this quantity yet, simulate
                # it at the actual weighted cost of what was delivered — `standard_price`
                # alone doesn't reflect the real per-unit cost under FIFO.
                delivery_moves = order_line.move_ids.filtered(lambda m: m.state == 'done' and m.is_out)
                delivered_qty = sum(delivery_moves.mapped('quantity'))
                perpetual_price_unit = -sum(delivery_moves.mapped('value')) / delivered_qty if delivered_qty else product.standard_price
            else:
                # Invoiced, not delivered yet: the COGS is already posted, revert it
                # at the average cost of what was actually posted.
                posted_lines = order_line.invoice_lines.filtered(lambda l:
                    l.move_id.state == 'posted' and l.date <= accrual_entry_date
                )
                # The COGS line is synthetic, linked back only via `cogs_origin_id`, not `sale_line_ids`.
                cogs_lines = posted_lines.move_id.line_ids.filtered(lambda l:
                    l.display_type == 'cogs' and l.account_id == expense_account and l.cogs_origin_id in posted_lines
                )
                posted_quantity = sum(posted_lines.mapped('quantity'))
                if not posted_quantity:
                    # Nothing was actually posted yet (e.g. a draft invoice already counts
                    # towards `qty_invoiced_at_date`): there is no COGS to revert.
                    continue
                perpetual_price_unit = sum(cogs_lines.mapped('debit')) / posted_quantity
            perpetual_amount = perpetual_price_unit * qty_to_invoice
            perpetual_label = _('Goods Delivered not Invoiced (perpetual valuation)') if qty_to_invoice > 0 \
                else _('Goods Invoiced not Delivered (perpetual valuation)')
            perpetual_line_label = _(
                "%(order)s - %(order_line)s; %(qty_invoiced)s invoiced, %(qty_delivered)s delivered at %(unit_price)s",
                order=order.display_name,
                order_line=order_line_label,
                qty_invoiced=order_line.qty_invoiced_at_date,
                qty_delivered=order_line.qty_delivered_at_date,
                unit_price=formatLang(self.env, perpetual_price_unit, currency_obj=order.currency_id),
            )
            inventory_vals = self._get_aml_vals(False, order, perpetual_amount, 0.0, stock_variation_account.id, label=perpetual_line_label)
            counterpart_vals = self._get_aml_vals(False, order, -perpetual_amount, 0.0, expense_account.id, label=perpetual_label)
            inventory_vals['display_type'] = counterpart_vals['display_type'] = 'cogs'
            inventory_vals_list.append(inventory_vals)
            counterpart_vals_list.append(counterpart_vals)
        return inventory_vals_list, self._merge_aml_vals(counterpart_vals_list)
