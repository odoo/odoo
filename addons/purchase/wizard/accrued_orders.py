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
        qty_to_bill = order_line._get_qty_to_invoice_at_date()

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

    def _get_purchase_accrual_amounts_and_label(self, order_line, qty_to_bill, price_unit):
        """ (amount, amount_currency, label) for the accrual entry of a single purchase.order.line. """
        order = order_line.order_id
        product = order_line.product_id
        if any(tax.price_include for tax in order_line.tax_ids):
            price_subtotal = order_line.tax_ids.compute_all(
                price_unit,
                currency=order_line.currency_id,
                quantity=qty_to_bill,
                product=product,
                partner=order.partner_id)['total_excluded']
        else:
            price_subtotal = qty_to_bill * price_unit
        amount_currency = order_line.currency_id.round(price_subtotal)
        amount = order.currency_id._convert(amount_currency, self.company_id.currency_id, self.company_id)
        label = _(
            '%(order)s - %(order_line)s; %(quantity_billed)s Billed, %(quantity_received)s Received at %(unit_price)s each',
            order=order.display_name,
            order_line=ellipsis(order_line.name or product.name, 20),
            quantity_billed=order_line.qty_invoiced_at_date,
            quantity_received=order_line.qty_received_at_date,
            unit_price=formatLang(self.env, price_unit, currency_obj=order.currency_id),
        )
        return amount, amount_currency, label

    def _get_accrual_main_line_vals(self, order_lines, is_purchase, accrual_entry_date):
        if not is_purchase:
            return super()._get_accrual_main_line_vals(order_lines, is_purchase, accrual_entry_date)

        expense_vals_list = []
        counterpart_vals_list = []
        price_diff_vals_list = []
        for order_line in order_lines:
            product = order_line.product_id
            if product.is_storable and product.valuation == 'real_time':
                continue
            order = order_line.order_id
            order_line_label = ellipsis(order_line.name or product.name, 20)
            qty_to_bill, price_unit = self._get_purchase_accrual_qty_and_price_unit(order_line, accrual_entry_date)
            amount, amount_currency, label = self._get_purchase_accrual_amounts_and_label(order_line, qty_to_bill, price_unit)

            if not self.company_id.currency_id.is_zero(amount):
                accounts = product.with_company(order.company_id).product_tmpl_id.get_product_accounts(fiscal_pos=order.fiscal_position_id)
                distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
                expense_vals = self._get_aml_vals(True, order, amount, amount_currency, accounts['expense'].id, label=label, analytic_distribution=distribution)

                accrual_account = self.account_id or accounts['bills_to_receive' if qty_to_bill > 0 else 'billed_not_received']
                counterpart_vals = self._get_aml_vals(
                    True, order, -amount, -amount_currency, accrual_account.id,
                    label=_('Accrued total'), analytic_distribution=distribution,
                )
                counterpart_vals_list.append(counterpart_vals)
                expense_vals_list.append(expense_vals)

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
                    price_diff_vals_list += [
                        self._get_aml_vals(
                            True, order, -price_diff, price_diff, price_diff_account.id,
                            label=diff_label, analytic_distribution=False,
                        ),
                        self._get_aml_vals(
                            True, order, price_diff, price_diff, product.categ_id.account_stock_variation_id.id,
                            label=diff_label, analytic_distribution=False,
                        ),
                    ]

        return expense_vals_list + price_diff_vals_list, self._merge_aml_vals(counterpart_vals_list)

    def _get_accrual_pending_cogs_vals(self, order_lines, is_purchase, accrual_entry_date):
        if not is_purchase:
            return super()._get_accrual_pending_cogs_vals(order_lines, is_purchase, accrual_entry_date)

        vals_list = []
        counterpart_vals_list = []
        for order_line in order_lines:
            product = order_line.product_id
            if not (product.is_storable and product.valuation == 'real_time'):
                continue
            order = order_line.order_id
            qty_to_bill, price_unit = self._get_purchase_accrual_qty_and_price_unit(order_line, accrual_entry_date)
            amount, amount_currency, label = self._get_purchase_accrual_amounts_and_label(order_line, qty_to_bill, price_unit)

            accounts = product.with_company(order.company_id).product_tmpl_id.get_product_accounts(fiscal_pos=order.fiscal_position_id)
            distribution = order_line.analytic_distribution if order_line.analytic_distribution else {}
            vals = self._get_aml_vals(True, order, amount, amount_currency, accounts['stock_valuation'].id, label=label, analytic_distribution=distribution)

            accrual_account = self.account_id or accounts['bills_to_receive' if qty_to_bill > 0 else 'billed_not_received']
            counterpart_vals = self._get_aml_vals(
                True, order, -amount, -amount_currency, accrual_account.id,
                label=_('Accrued total'), analytic_distribution=distribution,
            )
            counterpart_vals_list.append(counterpart_vals)
            vals_list.append(vals)
        return vals_list, self._merge_aml_vals(counterpart_vals_list)
