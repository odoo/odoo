# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    l10n_vn_edi_unit_price = fields.Float(
        string='Unit Price',
        compute='_compute_l10n_vn_edi_unit_price',
        store=True,
        readonly=False,
    )
    l10n_vn_edi_total_price = fields.Float(
        string='Total Price',
        compute='_compute_l10n_vn_edi_total_price',
    )

    @api.depends('product_id')
    def _compute_l10n_vn_edi_unit_price(self):
        for move in self:
            if not move.l10n_vn_edi_unit_price:
                move.l10n_vn_edi_unit_price = move.product_id.lst_price if move.product_id else 0.0

    @api.depends('l10n_vn_edi_unit_price', 'product_uom_qty', 'quantity')
    def _compute_l10n_vn_edi_total_price(self):
        for move in self:
            qty = move.quantity if move.state != 'draft' else move.product_uom_qty
            move.l10n_vn_edi_total_price = move.l10n_vn_edi_unit_price * qty
