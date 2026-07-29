# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.tools import formatLang

from odoo.addons.account.wizard.accrued_orders import ellipsis


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    @api.model
    def _get_accrual_line_vals(self, order, order_line, is_purchase, accrual_entry_date):
        if is_purchase:
            return super()._get_accrual_line_vals(order, order_line, is_purchase, accrual_entry_date)

        product = order_line.product_id
        order_line_label = ellipsis(order_line.name, 20)
        # Positive: delivered more than invoiced ("Invoices to be Issued").
        # Negative: invoiced more than delivered ("Invoiced Not Delivered").
        qty_to_invoice = order_line.qty_delivered_at_date - order_line.qty_invoiced_at_date

        account = self._get_computed_account(order, product, is_purchase)
        price_unit = order_line.price_unit
        if qty_to_invoice > 0:
            amount_currency = order_line.amount_to_invoice_at_date
            amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
        elif qty_to_invoice < 0:
            amount_currency, amount, processed_qty = 0, 0, 0
            for inv_line in order_line.invoice_lines.filtered(lambda ivl: ivl.move_id.state == 'posted').sorted(reverse=True):
                amount_currency -= inv_line.price_subtotal
                amount -= order.currency_id._convert(inv_line.price_subtotal, self.company_id.currency_id, self.company_id)
                processed_qty += inv_line.quantity
                if processed_qty >= abs(qty_to_invoice):
                    break
            if processed_qty:
                price_unit = abs(amount / processed_qty)
        label = _(
            '%(order)s - %(order_line)s; %(quantity_invoiced)s Invoiced, %(quantity_delivered)s Delivered at %(unit_price)s each',
            order=order.display_name,
            order_line=order_line_label,
            quantity_invoiced=order_line.qty_invoiced_at_date,
            quantity_delivered=order_line.qty_delivered_at_date,
            unit_price=formatLang(self.env, price_unit, currency_obj=order.currency_id),
        )
        distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
        aml_vals = self._get_aml_vals(is_purchase, order, amount, amount_currency, account.id, label=label, analytic_distribution=distribution)

        accrual_account = self.account_id or product.product_tmpl_id._get_product_accounts()[
            'invoices_to_issue' if qty_to_invoice > 0 else 'invoiced_not_delivered'
        ]
        counterpart_vals = self._get_aml_vals(
            is_purchase, order, -amount, -amount_currency, accrual_account.id,
            label=_('Accrued total'), analytic_distribution=distribution,
        )
        vals_list = [aml_vals, counterpart_vals]

        if qty_to_invoice and product.valuation == 'real_time' and product.is_storable:
            product_accounts = product._get_product_accounts()
            expense_account = product_accounts.get('expense')
            stock_valuation_account = product_accounts.get('stock_valuation')
            if expense_account and stock_valuation_account:
                if qty_to_invoice > 0:
                    # Delivered, not invoiced yet: no COGS posted for this quantity yet,
                    # simulate it at the standard price.
                    perpetual_price_unit = product.standard_price
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
                    perpetual_price_unit = sum(cogs_lines.mapped('debit')) / posted_quantity if posted_quantity else 0
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
                vals_list += [
                    self._get_aml_vals(is_purchase, order, perpetual_amount, 0.0, stock_valuation_account.id, label=perpetual_line_label),
                    self._get_aml_vals(is_purchase, order, -perpetual_amount, 0.0, expense_account.id, label=perpetual_label),
                ]
        return vals_list
