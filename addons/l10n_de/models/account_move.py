from odoo import models, api, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.country_code == 'DE':
                move.show_delivery_date = move.is_sale_document()

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        self.filtered(lambda m: (
            m.country_code == 'DE'
            and m.move_type != 'entry'
            and (m.state == 'draft' or m.taxable_supply_date)
        )).show_taxable_supply_date = True

    def _post(self, soft=True):
        for move in self:
            if move.country_code == 'DE' and move.is_sale_document() and not move.delivery_date:
                move.delivery_date = move.invoice_date or fields.Date.context_today(self)
        return super()._post(soft)

    def _get_accounting_date_source(self):
        return (self.country_code == 'DE' and self.taxable_supply_date) or super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        return (self.country_code == 'DE' and self.taxable_supply_date) or super()._get_invoice_currency_rate_date()
