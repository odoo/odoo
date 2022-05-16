# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    l10n_in_tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        compute="_compute_l10n_in_tax_ids",
        store=True,
        readonly=False,
        copy=False,
    )
    l10n_in_price_taxexcl = fields.Float(
        "Price Tax excl",
        compute="_compute_l10n_in_unit_price",
        store=True,
        readonly=False,
        copy=False,
    )

    @api.depends("product_id", "partner_id", "picking_id.l10n_in_fiscal_position_id")
    def _compute_l10n_in_tax_ids(self):
        for move_line in self:
            tax_ids = False
            if move_line.product_id:
                fiscal_position_id = move_line.picking_id.l10n_in_fiscal_position_id
                if not fiscal_position_id:
                    fiscal_position_id = self.env["account.fiscal.position"]._get_fiscal_position(move_line.partner_id)
                tax_ids = move_line.product_id.taxes_id.filtered(lambda t: t.company_id == move_line.company_id)
                tax_ids = fiscal_position_id.map_tax(tax_ids._origin)
            move_line.l10n_in_tax_ids = tax_ids

    @api.depends("product_uom", "product_id", "partner_id")
    def _compute_l10n_in_unit_price(self):
        for move_line in self:
            price_taxexcl = 0.00
            partner = move_line.partner_id
            if move_line.product_id:
                lst_price = move_line.product_id.with_context(
                    pricelist=partner.property_product_pricelist.id,
                    partner=partner.id,
                    uom=move_line.product_uom.id,
                    date=move_line.picking_id.date_done,
                ).lst_price
                price_taxexcl = self.env["account.tax"]._fix_tax_included_price_company(
                    lst_price,
                    move_line.product_id.taxes_id,
                    move_line.l10n_in_tax_ids,
                    move_line.company_id,
                )
            move_line.l10n_in_price_taxexcl = price_taxexcl
