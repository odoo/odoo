from odoo import fields, models
from odoo.tools.misc import clean_context

from ..tools import debug_log as dbg


class StockWarnInsufficientQtyScrap(models.TransientModel):
    _name = "stock.warn.insufficient.qty.scrap"
    _inherit = ["mixin.stock.warn.insufficient.qty"]
    _description = "Warn Insufficient Scrap Quantity"

    scrap_id = fields.Many2one(comodel_name="stock.scrap")

    def _get_reference_document_company_id(self):
        return self.scrap_id.company_id

    def action_done(self):
        dbg.pipeline.debug(
            "insufficient qty confirmed: scrap %s proceeds", self.scrap_id.id
        )
        return self.with_context(
            clean_context(self.env.context)
        ).scrap_id._action_done()

    def action_cancel(self):
        if self.env.context.get("not_unlink_on_discard"):
            return True
        scrap = self.scrap_id
        if not scrap or scrap.state != "draft":
            return True
        scrap.check_access("write")
        dbg.lifecycle.debug(
            "insufficient qty cancelled: draft scrap %s unlinked", scrap.id
        )
        return scrap.sudo().unlink()
