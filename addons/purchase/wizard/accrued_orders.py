# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.tools import float_is_zero, formatLang

from odoo.addons.account.wizard.accrued_orders import ellipsis


class AccountAccruedOrdersWizard(models.TransientModel):
    _inherit = 'account.accrued.orders.wizard'

    @api.model
    def _get_purchase_accrual_qty_and_price_unit(self, order_line, accrual_entry_date):
        """ (qty received - qty billed) and its unit price. """
        # Positive: received more than billed ("Bills to Receive").
        # Negative: billed more than received ("Billed Not Received").
        qty_to_bill = order_line.qty_received_at_date - order_line.qty_invoiced_at_date

        price_unit = order_line.price_unit_discounted
        if qty_to_bill < 0:
            posted_invoice_lines = order_line.invoice_lines.filtered(lambda ivl:
                ivl.move_id.state == 'posted' and ivl.date <= accrual_entry_date
            )
            invoiced_values = sum(ivl.price_subtotal for ivl in posted_invoice_lines)
            received_values = order_line.qty_received_at_date * order_line.price_unit_discounted
            value_to_invoice = invoiced_values - received_values
            price_unit = -value_to_invoice / qty_to_bill

        return qty_to_bill, price_unit

    @api.model
    def _get_accrual_line_vals(self, order, order_line, is_purchase, accrual_entry_date):
        if not is_purchase:
            return super()._get_accrual_line_vals(order, order_line, is_purchase, accrual_entry_date)

        product = order_line.product_id
        order_line_label = ellipsis(order_line.name, 20)
        qty_to_bill, price_unit = self._get_purchase_accrual_qty_and_price_unit(order_line, accrual_entry_date)

        account = self._get_computed_account(order, product, is_purchase)
        if any(tax.price_include for tax in order_line.tax_ids):
            # price_unit ignores included taxes, so recompute the subtotal.
            price_subtotal = order_line.tax_ids.compute_all(
                price_unit,
                currency=order_line.order_id.currency_id,
                quantity=qty_to_bill,
                product=product,
                partner=order_line.order_id.partner_id)['total_excluded']
        else:
            price_subtotal = qty_to_bill * price_unit
        amount_currency = order_line.currency_id.round(price_subtotal)
        amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
        label = _(
            '%(order)s - %(order_line)s; %(quantity_billed)s Billed, %(quantity_received)s Received at %(unit_price)s each',
            order=order.display_name,
            order_line=order_line_label,
            quantity_billed=order_line.qty_invoiced_at_date,
            quantity_received=order_line.qty_received_at_date,
            unit_price=formatLang(self.env, price_unit, currency_obj=order.currency_id),
        )
        distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
        aml_vals = self._get_aml_vals(is_purchase, order, amount, amount_currency, account.id, label=label, analytic_distribution=distribution)

        accrual_account = self.account_id or product.product_tmpl_id._get_product_accounts()[
            'bills_to_receive' if qty_to_bill > 0 else 'billed_not_received'
        ]
        counterpart_vals = self._get_aml_vals(
            is_purchase, order, -amount, -amount_currency, accrual_account.id,
            label=_('Accrued total'), analytic_distribution=distribution,
        )
        vals_list = [aml_vals, counterpart_vals]

        if qty_to_bill and product.valuation == 'real_time' and product.is_storable:
            product_accounts = product._get_product_accounts()
            expense_account = product_accounts.get('expense')
            stock_valuation_account = product_accounts.get('stock_valuation')
            if expense_account and stock_valuation_account:
                if qty_to_bill > 0:
                    # Received, not billed yet: nothing posted to `stock_valuation` for
                    # this quantity yet, simulate it at the purchase price.
                    perpetual_price_unit = price_unit
                else:
                    # Billed, not received yet: the bill already posted to `stock_valuation`,
                    # revert it at the average cost of what was actually posted.
                    posted_lines = order_line.invoice_lines.filtered(lambda l:
                        l.move_id.state == 'posted' and l.account_id == stock_valuation_account and l.date <= accrual_entry_date
                    )
                    posted_quantity = sum(posted_lines.mapped('quantity'))
                    perpetual_price_unit = sum(posted_lines.mapped('debit')) / posted_quantity if posted_quantity else 0
                perpetual_amount = perpetual_price_unit * qty_to_bill
                perpetual_label = _('Goods Received not Billed (perpetual valuation)') if qty_to_bill > 0 \
                    else _('Goods Billed not Received (perpetual valuation)')
                perpetual_line_label = _(
                    "%(order)s - %(order_line)s; %(qty_billed)s billed, %(qty_received)s received at %(unit_price)s",
                    order=order.display_name,
                    order_line=order_line_label,
                    qty_billed=order_line.qty_invoiced_at_date,
                    qty_received=order_line.qty_received_at_date,
                    unit_price=formatLang(self.env, perpetual_price_unit, currency_obj=order.currency_id),
                )
                vals_list += [
                    self._get_aml_vals(is_purchase, order, perpetual_amount, 0.0, stock_valuation_account.id, label=perpetual_line_label),
                    self._get_aml_vals(is_purchase, order, -perpetual_amount, 0.0, expense_account.id, label=perpetual_label),
                ]

        # Price-difference lines, only needed for standard-cost products.
        price_diff_account = product._get_price_diff_account()
        if price_diff_account:
            diff_label = _('%(order)s - %(order_line)s; price difference for %(product)s',
                order=order.display_name,
                order_line=order_line_label,
                product=product.display_name,
            )
            unit_price_diff = product.standard_price - price_unit
            price_diff = qty_to_bill * unit_price_diff
            if not float_is_zero(price_diff, precision_rounding=order_line.currency_id.rounding):
                vals_list += [
                    self._get_aml_vals(
                        is_purchase, order, -price_diff, price_diff, price_diff_account.id,
                        label=diff_label, analytic_distribution=False,
                    ),
                    self._get_aml_vals(
                        is_purchase, order, price_diff, price_diff, product.categ_id.account_stock_variation_id.id,
                        label=diff_label, analytic_distribution=False,
                    ),
                ]

        return vals_list
