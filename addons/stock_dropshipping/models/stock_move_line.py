from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_lot_partner(self):
        self.ensure_one()
        if self.picking_id.is_dropship and self.picking_id.sale_id.partner_shipping_id:
            return self.picking_id.sale_id.partner_shipping_id
        return super()._get_lot_partner()

    def _action_done(self):
        res = super()._action_done()
        for ml in self:
            if ml.lot_id and ml.picking_id.picking_type_id.code == 'dropship':
                if partner := ml._get_lot_partner():
                    ml.lot_id.sudo().partner_ids |= partner
        return res
