# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, tools

class StockAssignedManualMoves(models.Model):
    _name = 'stock.assigned.manual.moves'
    _auto = False
    _description = 'Stock Assigned Manual Moves View'

    origin = fields.Char('Sale Order Number')
    name = fields.Char('Pick Number')
    stock_picking_id = fields.Many2one('stock.picking')
    complete_name = fields.Char('Complete Location Name')
    location_name = fields.Char('Location Name')
    quantity = fields.Float('Quantity')
    product_id = fields.Many2one('product.product', string='Product')
    default_code = fields.Char('SKU Code')
    description = fields.Char('Name')
    carton_length = fields.Float('Carton Length')
    carton_width = fields.Float('Carton Width')
    carton_height = fields.Float('Carton Height')
    weight = fields.Float()
    tenant_id = fields.Many2one('res.partner')
    site_code = fields.Char()
    picking_type_id = fields.Many2one('stock.picking.type')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done')
    ], string="Status")

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW stock_assigned_manual_moves AS
            SELECT
              sp.origin,
              sp.name,
              sp.id AS stock_picking_id,
              sl.complete_name,
              sl.name AS location_name,
              COALESCE(sm.quantity, 0.0) AS quantity,
              pt.default_code,
              sm.product_id,
              pt."name"->>'en_US' AS description,
              CASE WHEN pt.carton_height ~ '^[0-9\\.]+$' THEN pt.carton_height::float ELSE 0.0 END AS carton_height,
              CASE WHEN pt.carton_length ~ '^[0-9\\.]+$' THEN pt.carton_length::float ELSE 0.0 END AS carton_length,
              CASE WHEN pt.carton_width ~ '^[0-9\\.]+$' THEN pt.carton_width::float ELSE 0.0 END AS carton_width,
              COALESCE(pt.weight, 0.0) AS weight,
              sp.tenant_id,
              sp.site_code,
              sp.picking_type_id,
              sp.state,
              ROW_NUMBER() OVER() AS id
            FROM stock_move sm
            JOIN stock_picking sp ON sp.id = sm.picking_id
            JOIN stock_move_line sml ON sml.move_id = sm.id
            JOIN stock_location sl ON sl.id = sml.location_id
            JOIN product_product pp ON pp.id = sm.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            WHERE sp.state = 'assigned'
              AND sp.current_state = 'draft'
              AND sl.system_type = 'manual';
        """)

