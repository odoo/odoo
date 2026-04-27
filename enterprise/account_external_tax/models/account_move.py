# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command, _
from collections import defaultdict


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'account.external.tax.mixin']

    def _compute_tax_totals(self):
        """ super() computes these using account.tax.compute_all(). For price-included taxes this will show the wrong totals
        because it uses the percentage amount on the tax which will always be 1%. This sets the correct totals using
        account.move.line fields set by `_set_external_taxes()`. """
        super()._compute_tax_totals()
        for move in self.filtered(lambda move: move.is_tax_computed_externally and move.tax_totals):
            lines = move.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            tax_totals = move.tax_totals
            subtotal = tax_totals['subtotals'] and tax_totals['subtotals'][0] or {}
            tax_totals['same_tax_base'] = True
            tax_totals['total_amount_currency'] = move.currency_id.round(sum(lines.mapped('price_total')))
            tax_totals['base_amount_currency'] = move.currency_id.round(sum(lines.mapped('price_subtotal')))
            tax_totals['tax_amount_currency'] = tax_totals['total_amount_currency'] - tax_totals['base_amount_currency']
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
            move.tax_totals = tax_totals

    def button_draft(self):
        res = super().button_draft()
        self._filtered_external_tax_moves()._uncommit_external_taxes()
        return res

    def unlink(self):
        self._filtered_external_tax_moves()._void_external_taxes()
        return super().unlink()

    def _post(self, soft=True):
        """ Ensure taxes are correct before posting. """
        self._get_and_set_external_taxes_on_eligible_records()
        return super()._post(soft=soft)

    def _filtered_external_tax_moves(self):
        return self.filtered(lambda move: move.is_tax_computed_externally and
                                          move.move_type in ('out_invoice', 'out_refund') and
                                          not move._is_downpayment())

    def _get_and_set_external_taxes_on_eligible_records(self):
        """ account.external.tax.mixin override. """
        eligible_moves = self._filtered_external_tax_moves().filtered(lambda move: move.state != 'posted')
        eligible_moves._set_external_taxes(*eligible_moves._get_external_taxes())
        return super()._get_and_set_external_taxes_on_eligible_records()

    def _get_lines_eligible_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        return self.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and not line._get_downpayment_lines())

    def _get_date_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        return self.invoice_date

    def _get_line_data_for_external_taxes(self):
        """ account.external.tax.mixin override. """
        res = []
        for line in self._get_lines_eligible_for_external_taxes():
            res.append({
                "id": line.id,
                "model_name": line._name,
                "product_id": line.product_id,
                "qty": line.quantity,
                "price_subtotal": line.price_subtotal,
                "price_unit": line.price_unit,
                "discount": line.discount,
                "is_refund": self.move_type == 'out_refund',
            })

        return res

    def _set_external_taxes(self, mapped_taxes, summary):
        """ account.external.tax.mixin override. """
        business_line_ids_commands = defaultdict(list)
        accounting_line_ids_commands = defaultdict(list)
        for line, detail in mapped_taxes.items():
            move = line.move_id
            price_subtotal = detail['total']
            amount_currency = line.move_id.direction_sign * price_subtotal
            if line.currency_rate:
                balance = amount_currency / line.currency_rate
            else:
                balance = 0.0 if line.currency_id != line.company_currency_id else amount_currency
            business_line_ids_commands[move].append(Command.update(line.id, {
                'tax_ids': [Command.set(detail['tax_ids'].ids)],
            }))
            accounting_line_ids_commands[move].append(Command.update(line.id, {
                'price_subtotal': price_subtotal,
                'price_total': detail['tax_amount'] + detail['total'],
                'amount_currency': amount_currency,
                'balance': balance,
            }))

        # Trigger the taxes computation to get the tax lines.
        for move, line_ids_commands in business_line_ids_commands.items():
            move.line_ids = line_ids_commands
        for move in self:
            for tax, external_amount in summary.get(move, {}).items():
                tax_lines = move.line_ids.filtered(lambda l: l.tax_line_id == tax)
                if not tax_lines:
                    continue

                # Check that the computed taxes are close enough. For exemptions this could not be the case
                # since some integrations will return the non-exempt rate%. In that case this will manually fix the tax
                # lines to what the external service says they should be.
                computed_taxes = sum(tax_lines.mapped('amount_currency'))
                if move.currency_id.compare_amounts(computed_taxes, external_amount) != 0:
                    diff = external_amount - computed_taxes
                    for i, tax_line in enumerate(tax_lines):
                        line_diff = move.currency_id.round(diff / (len(tax_lines) - i))
                        diff -= line_diff
                        accounting_line_ids_commands[move].append(Command.update(tax_line.id, {'amount_currency': tax_line.amount_currency + line_diff}))

        # Force custom values for the accounting side.
        for move, line_ids_commands in accounting_line_ids_commands.items():
            move.line_ids = line_ids_commands
