from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    taxable_supply_date = fields.Date()

    def _post(self, soft=True):
        posted = super()._post(soft)
        for move in posted.filtered(lambda m: m.country_code == 'PL' and not m.taxable_supply_date):
            move.taxable_supply_date = move.invoice_date
        return posted

    @api.depends('taxable_supply_date')
    def _compute_date(self):
        pl_taxable_supply_date_moves = self.filtered(lambda m: m.country_code == 'PL' and m.taxable_supply_date and m.is_invoice() and m.state == 'draft')
        other_moves = self - pl_taxable_supply_date_moves
        super(AccountMove, other_moves)._compute_date()
        for move in pl_taxable_supply_date_moves:
            accounting_date = move.taxable_supply_date
            if not move.is_sale_document():
                accounting_date = move._get_accounting_date(accounting_date, move._affect_tax_report())
            if accounting_date and accounting_date != move.date:
                move.date = accounting_date
                # _affect_tax_report may trigger premature recompute of line_ids.date
                self.env.add_to_compute(move.line_ids._fields['date'], move.line_ids)
                # might be protected because `_get_accounting_date` requires the `name`
                self.env.add_to_compute(self._fields['name'], move)

    @api.depends('taxable_supply_date')
    def _compute_invoice_currency_rate(self):
        # In Poland, the currency rate should be based on the taxable supply date.
        super()._compute_invoice_currency_rate()

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        if self.country_code == 'PL' and self.taxable_supply_date:
            return self.taxable_supply_date
        return super()._get_invoice_currency_rate_date()
