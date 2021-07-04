from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    tax_ids = fields.Many2many(string='VAT')
    vat_amount = fields.Monetary(compute='_compute_vat_amount', string='VAT Amount')

    @api.depends('price_subtotal', 'price_total')
    def _compute_vat_amount(self):
        for record in self:
            record.vat_amount = record.price_total - record.price_subtotal
