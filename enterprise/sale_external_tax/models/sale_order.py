# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['account.external.tax.mixin', 'sale.order']

    def _get_external_tax_totals(self, amount_total, amount_untaxed, amount_tax):
        tax_totals = self.tax_totals
        subtotal = tax_totals['subtotals'] and tax_totals['subtotals'][0] or {}
        tax_totals['same_tax_base'] = True
        tax_totals['total_amount_currency'] = amount_total
        tax_totals['base_amount_currency'] = amount_untaxed
        tax_totals['tax_amount_currency'] = amount_tax
        tax_totals['subtotals'] = [
            {
                **subtotal,
                'base_amount_currency': tax_totals['base_amount_currency'],
                'tax_amount_currency': tax_totals['tax_amount_currency'],
                'tax_groups': [],
            }
        ]
        if subtotal.get('tax_groups'):
            tax_group = subtotal['tax_groups'][0]
            tax_totals['subtotals'][0]['tax_groups'].append({
                **tax_group,
                'group_name': _('Taxes'),
                'base_amount_currency': tax_totals['base_amount_currency'],
                'tax_amount_currency': tax_totals['tax_amount_currency'],
            })
        return tax_totals

    def _compute_tax_totals(self):
        """This overrides the standard values which come from
        account.tax. The percentage (amount field) on account.tax
        won't be correct in case of (partial) exemptions. As always we
        should rely purely on the values the external tax integration
        returns, not the values Odoo computes. This will create a
        single tax group using the amount_* fields on the order which
        come from the external tax integration.
        """
        super()._compute_tax_totals()
        for order in self.filtered('is_tax_computed_externally'):
            order.tax_totals = order._get_external_tax_totals(order.amount_total, order.amount_untaxed, order.amount_tax)

    def _compute_amounts(self):
        """ This overrides the standard values for orders using external tax calculation. The round_globally option
        doesn't work when calculating taxes externally hence the tax (amount_tax field) on sale.order won't be
        correct in case of (partial) exemptions. As always we should rely purely on the values the external tax
        service returns, not the values Odoo computes.
        """
        external_tax_orders = self.filtered('is_tax_computed_externally')
        for order in external_tax_orders:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.amount_untaxed = sum(order_lines.mapped('price_subtotal'))
            order.amount_tax = sum(order_lines.mapped('price_tax'))
            order.amount_total = order.amount_untaxed + order.amount_tax
        super(SaleOrder, self - external_tax_orders)._compute_amounts()

    def _create_account_invoices(self, invoice_vals_list, final):
        """ Override. Always calculate taxes on final invoices that have down payment lines. We clear tax_ids on
        invoice lines in _prepare_invoice_line() to avoid confusing users when the tax amount Odoo calculates is
        different from what Avatax calculated for their SO. But because down payments are based on the total,
        not subtotal, this can lead to a negative total on the invoice. To avoid the invoice being turned into a
        credit note, automatically calculate taxes on invoices with a down payment line."""
        moves = super()._create_account_invoices(invoice_vals_list, final)
        if final:  # Don't needlessly do this for non-final invoices.
            moves.filtered(lambda move: any(move.line_ids.sale_line_ids.mapped('is_downpayment')))._get_and_set_external_taxes_on_eligible_records()
        return moves

    def action_confirm(self):
        """ Ensure confirmed orders have the right taxes. """
        self._get_and_set_external_taxes_on_eligible_records()
        return super().action_confirm()

    def action_quotation_send(self):
        """ Calculate taxes before presenting order to the customer. """
        self._get_and_set_external_taxes_on_eligible_records()
        return super().action_quotation_send()

    def _get_and_set_external_taxes_on_eligible_records(self):
        """ account.external.tax.mixin override. """
        eligible_orders = self.filtered(lambda order: order.is_tax_computed_externally and order.state in ('draft', 'sent', 'sale') and not order.locked)
        eligible_orders._set_external_taxes(*eligible_orders._get_external_taxes())
        return super()._get_and_set_external_taxes_on_eligible_records()

    def _get_lines_eligible_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        return self.order_line.filtered(lambda l: not l.display_type and not l.is_downpayment)

    def _get_line_data_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        res = []
        for line in self._get_lines_eligible_for_external_taxes():
            # Clear all taxes (e.g. default customer tax). Not every line will be sent to the external tax
            # calculation service, those lines would keep their default taxes otherwise.
            line.tax_id = False

            res.append({
                "id": line.id,
                "model_name": line._name,
                "product_id": line.product_id,
                "qty": line.product_uom_qty,
                "price_subtotal": line.price_subtotal,
                "price_unit": line.price_unit,
                "discount": line.discount,
                "is_refund": False,
            })

        return res

    def _set_external_taxes(self, mapped_taxes, summary):
        """ account.external.tax.mixin override. """
        to_flush = self.env['sale.order.line']
        for line, detail in mapped_taxes.items():
            line.tax_id = detail['tax_ids']
            to_flush += line

        # Trigger field computation due to changing the tax id. Do
        # this here because we will manually change the taxes.
        to_flush.flush_recordset(['price_tax', 'price_subtotal', 'price_total'])

        for line, detail in mapped_taxes.items():
            line.price_tax = detail['tax_amount']
            line.price_subtotal = detail['total']
            line.price_total = detail['tax_amount'] + detail['total']

    def _get_date_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        return self.date_order


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """ Override to clear tax_ids on lines. Brazilian taxes are variable and don't have the right amount set in Odoo (always 1%),
        so taxes are always wrong unless recomputed with button_external_tax_calculation. Although this automatically happens when needed, clearing the
        taxes here avoids potential confusion.
        """
        res = super()._prepare_invoice_line(**optional_values)

        if self.order_id.is_tax_computed_externally:
            res['tax_ids'] = False

        return res
