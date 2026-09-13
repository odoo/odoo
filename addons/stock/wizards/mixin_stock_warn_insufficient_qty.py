from odoo import api, fields, models

from ..tools import debug_log as dbg


class MixinStockWarnInsufficientQty(models.AbstractModel):
    _name = "mixin.stock.warn.insufficient.qty"
    _description = "Warn Insufficient Quantity"

    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        required=True,
        domain="[('usage', '=', 'internal')]",
    )
    quant_ids = fields.Many2many(
        comodel_name="stock.quant",
        compute="_compute_quant_ids",
    )
    quantity = fields.Float(required=True)
    product_uom_name = fields.Char(
        string="Unit",
        required=True,
    )

    def _get_reference_document_company_id(self):
        raise NotImplementedError

    @api.depends("product_id")
    def _compute_quant_ids(self):
        company_per_record = {
            quantity.id: quantity._get_reference_document_company_id()
            for quantity in self
        }
        quants = self.env["stock.quant"].search(
            [
                (
                    "company_id",
                    "in",
                    [False, *{company.id for company in company_per_record.values()}],
                ),
                ("product_id", "in", self.product_id.ids),
                ("location_id.usage", "=", "internal"),
            ]
        )
        dbg.performance.debug(
            "_compute_quant_ids: %d wizards, %d quants fetched", len(self), len(quants)
        )
        for quantity in self:
            company = company_per_record[quantity.id]
            quantity.quant_ids = quants.filtered(
                lambda quant, company=company, product=quantity.product_id: (
                    quant.product_id == product
                    and quant.company_id.id in (False, company.id)
                )
            )

    def action_done(self):
        raise NotImplementedError
