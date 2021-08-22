from odoo import api, fields, models


class InventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    expiration_date = fields.Datetime('Expiration Date')

    @api.model
    def create(self, vals):
        if vals.get('prod_lot_id'):
            lot = self.env['stock.production.lot'].browse(vals['prod_lot_id'])
            if lot.expiration_date:
                vals['expiration_date'] = lot.expiration_date
        return super(InventoryLine, self).create(vals)

    @api.onchange('prod_lot_id')
    def _onchange_lot(self):
        for rec in self:
            if rec.prod_lot_id and rec.prod_lot_id.expiration_date:
                rec.expiration_date = rec.prod_lot_id.expiration_date
