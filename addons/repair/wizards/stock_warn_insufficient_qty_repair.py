from odoo import fields, models
from odoo.tools.misc import clean_context


class StockWarnInsufficientQtyRepair(models.TransientModel):
    _name = "stock.warn.insufficient.qty.repair"
    _inherit = ["mixin.stock.warn.insufficient.qty"]
    _description = "Warn Insufficient Repair Quantity"

    repair_id = fields.Many2one(comodel_name="repair.order")

    def _get_reference_document_company_id(self):
        return self.repair_id.company_id

    def action_done(self):
        self.check_singleton()
        self = self.with_context(clean_context(self.env.context))
        return self.repair_id._action_repair_confirm()
