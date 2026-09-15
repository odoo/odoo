from odoo import api, fields, models


class StockInventoryAdjustmentName(models.TransientModel):
    _inherit = "stock.inventory.adjustment.name"

    accounting_date = fields.Date(
        help="Date at which the accounting entries will be created"
        " in case of automated inventory valuation."
        " If empty, the inventory date will be used."
    )
    should_show_accounting_date = fields.Boolean(
        compute="_compute_should_show_accounting_date"
    )

    @api.depends("quant_ids.product_id")
    def _compute_should_show_accounting_date(self):
        for wizard in self:
            wizard.should_show_accounting_date = any(
                product.valuation == "real_time"
                for product in wizard.quant_ids.product_id
            )

    def _prepare_quants_context(self):
        res = super()._prepare_quants_context()
        res["force_period_date"] = self.accounting_date
        return res
