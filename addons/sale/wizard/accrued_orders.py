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

        vals_list = []
        counterpart_vals_list = []
        for order_line in order_lines:
            order = order_line.order_id
            product = order_line.product_id
            order_line_label = ellipsis(order_line.name or product.name, 20)
            qty_to_invoice, price_unit, amount, amount_currency = self._get_accrual_qty_price_and_amount(order_line)

            if self.company_id.currency_id.is_zero(amount):
                continue

            accounts = product.with_company(order.company_id).product_tmpl_id.get_product_accounts(fiscal_pos=order.fiscal_position_id)
            account = accounts['income']
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

            accrual_account = self.account_id or accounts['invoices_to_issue' if qty_to_invoice > 0 else 'invoiced_not_delivered']
            counterpart_vals = self._get_aml_vals(
                False, order, -amount, -amount_currency, accrual_account.id,
                label=_('Accrued total'), analytic_distribution=distribution,
            )
            counterpart_vals_list.append(counterpart_vals)
            vals_list.append(revenue_vals)
        return vals_list, self._merge_aml_vals(counterpart_vals_list)

    def _get_accrual_pending_cogs_vals(self, order_lines, is_purchase, accrual_entry_date):
        if is_purchase:
            return super()._get_accrual_pending_cogs_vals(order_lines, is_purchase, accrual_entry_date)

        vals_list = []
        counterpart_vals_list = []
        for order_line in order_lines:
            order = order_line.order_id
            product = order_line.product_id
            order_line_label = ellipsis(order_line.name or product.name, 20)
            if product.valuation != 'real_time' or not product.is_storable:
                continue
            qty_to_invoice, __, __, __ = self._get_accrual_qty_price_and_amount(order_line)
            if not qty_to_invoice:
                continue
            product_accounts = product._get_product_accounts()
            expense_account = product_accounts.get('expense')
            stock_valuation_account = product_accounts.get('stock_valuation')
            if not expense_account or not stock_valuation_account:
                continue

            if qty_to_invoice > 0:
                perpetual_price_unit = product.standard_price
            else:
                posted_lines = order_line.invoice_lines.filtered(lambda l:
                    l.move_id.state == 'posted' and l.date <= accrual_entry_date
                )
                cogs_lines = posted_lines.move_id.line_ids.filtered(lambda l:
                    l.display_type == 'cogs' and l.account_id == expense_account and l.cogs_origin_id in posted_lines
                )
                posted_quantity = sum(posted_lines.mapped('quantity'))
                if not posted_quantity:
                    continue
                perpetual_price_unit = sum(cogs_lines.mapped('debit')) / posted_quantity
            perpetual_amount = perpetual_price_unit * qty_to_invoice
            perpetual_label = _(
                '%(order)s - %(order_line)s: Goods Delivered not Invoiced (perpetual valuation)',
                order=order.display_name, order_line=order_line_label,
            ) if qty_to_invoice > 0 else _(
                '%(order)s - %(order_line)s: Goods Invoiced not Delivered (perpetual valuation)',
                order=order.display_name, order_line=order_line_label,
            )
            vals = self._get_aml_vals(False, order, perpetual_amount, 0.0, stock_valuation_account.id, label=perpetual_label)
            counterpart_vals = self._get_aml_vals(False, order, -perpetual_amount, 0.0, expense_account.id, label=perpetual_label)
            vals['display_type'] = counterpart_vals['display_type'] = 'cogs'
            vals_list.append(vals)
            counterpart_vals_list.append(counterpart_vals)
        return vals_list, self._merge_aml_vals(counterpart_vals_list)
