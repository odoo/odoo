# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockLotReport(models.Model):
    _name = "stock.lot.report"
    _description = "Customer Lot Report"
    _rec_name = 'lot_id'
    _auto = False

    lot_id = fields.Many2one('stock.lot', 'Lot/Serial', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    picking_id = fields.Many2one('stock.picking', readonly=True)
    quantity = fields.Float(readonly=True)
    uom_id = fields.Many2one('uom.uom', readonly=True)
    delivery_date = fields.Datetime(readonly=True)
    address = fields.Char(readonly=True)
    has_return = fields.Boolean(readonly=True)

    def _select(self):
        return """
            MIN(sml.id) AS id,
            lot.id lot_id,
            lot.product_id,
            picking.partner_id,
            picking.id picking_id,
            sml.quantity,
            sml.product_uom_id uom_id,
            CONCAT_WS(', ', partner.street, partner.street2, partner.city,  partner.zip, state.name, country.code) address,
            (SELECT COUNT(sp_return.id) FROM stock_picking sp_return WHERE sp_return.return_id = picking.id) > 0 AS has_return,
            picking.date_done delivery_date
        """

    def _from(self):
        return """
            stock_lot lot
            JOIN stock_move_line AS sml
            ON lot.id = sml.lot_id
            JOIN stock_picking AS picking
            ON picking.id = sml.picking_id
            JOIN stock_picking_type AS type
            ON picking.picking_type_id = type.id and type.code = 'outgoing'
            JOIN res_partner AS partner
            ON partner.id = picking.partner_id
            LEFT JOIN res_country_state AS state
            ON state.id = partner.state_id
            LEFT JOIN res_country AS country
            ON country.id = partner.country_id
        """

    def _group_by(self):
        return """
            picking.id,
            picking.partner_id,
            lot.id,
            lot.product_id,
            country.code,
            state.name,
            partner.zip,
            partner.city,
            partner.street,
            partner.street2,
            sml.quantity,
            sml.product_uom_id,
            picking.date_done
        """

    def _query(self):
        return f"""
            SELECT {self._select()}
              FROM {self._from()}
          GROUP BY {self._group_by()}
        """

    @property
    def _table_query(self):
        return self._query()
