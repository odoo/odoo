from odoo import fields, models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    def _action_done(self):
        res = super()._action_done()
        for scrap in self.filtered(
            lambda scrap: scrap.state == "done" and scrap.lot_id.asset_id
        ):
            assets = scrap.lot_id.asset_id.filtered(
                lambda asset: asset.state != "disposed"
            )
            assets._dispose(fields.Date.context_today(scrap, scrap.date_done))
        return res
