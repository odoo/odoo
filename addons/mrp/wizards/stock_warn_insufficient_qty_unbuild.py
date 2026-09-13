from odoo import fields, models


class StockWarnInsufficientQtyUnbuild(models.TransientModel):
    _name = "stock.warn.insufficient.qty.unbuild"
    _inherit = ["mixin.stock.warn.insufficient.qty"]
    _description = "Warn Insufficient Unbuild Quantity"

    unbuild_id = fields.Many2one(comodel_name="mrp.unbuild")

    def _get_reference_document_company_id(self):
        return self.unbuild_id.company_id

    def action_done(self):
        self.check_singleton()
        return self.unbuild_id.action_unbuild()
