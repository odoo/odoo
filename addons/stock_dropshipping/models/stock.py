# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.fields import Domain


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        """ Do not group purchase order line if they are linked to different
        sale order line. The purpose is to compute the delivered quantities.
        """
        return procurement.values.get('sale_line_id'), super(StockRule, self)._get_procurements_to_merge_groupby(procurement)

    def _compute_picking_type_code_domain(self):
        super()._compute_picking_type_code_domain()
        for rule in self:
            if rule.action == 'buy':
                rule.picking_type_code_domain += ['dropship']

    @api.model
    def _get_rule_domain(self, location, values):
        domain = super()._get_rule_domain(location, values)
        if 'sale_line_id' in values and values.get('company_id'):
            domain = Domain.AND([domain, [('company_id', '=', values['company_id'].id)]])
        return domain


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_dropship = fields.Boolean("Is a Dropship", compute='_compute_is_dropship')

    @api.depends('location_dest_id.usage', 'location_dest_id.company_id', 'location_id.usage', 'location_id.company_id')
    def _compute_is_dropship(self):
        for picking in self:
            source, dest = picking.location_id, picking.location_dest_id
            picking.is_dropship = (source.usage == 'supplier' or (source.usage == 'transit' and not source.company_id)) \
                              and (dest.usage == 'customer' or (dest.usage == 'transit' and not dest.company_id))

    def _is_to_external_location(self):
        self.ensure_one()
        return super()._is_to_external_location() or self.is_dropship

    def _check_backorder(self):
        backorder_pickings = super()._check_backorder()
        for picking in self.filtered(lambda p: p.picking_type_id.code == 'dropship' and p.purchase_id):
            if picking.picking_type_id.create_backorder != 'ask':
                continue
            order_lines = picking.purchase_id.order_line.filtered(lambda l: l.product_id.type == "consu")
            if not all(order_lines.mapped(lambda l: bool(l.move_ids))):
                backorder_pickings |= picking
        return backorder_pickings

    def _get_moves_to_backorder(self):
        backorder_moves = super()._get_moves_to_backorder()
        for picking in self.filtered(lambda p: p.picking_type_id.code == 'dropship' and p.purchase_id):
            for line in picking.purchase_id.order_line:
                if line.product_id.type == "consu" and not line.move_ids:
                    backorder_moves |= self.env['stock.move'].create([{
                        'product_id': line.product_id.id,
                        'purchase_line_id': line.id,
                        'sale_line_id': line.sale_line_id.id,
                        'product_uom_qty': line.product_uom_qty - line.qty_received,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                        'company_id': picking.company_id.id,
                    }])
        return backorder_moves


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(
        selection_add=[('dropship', 'Dropship')], ondelete={'dropship': lambda recs: recs.write({'code': 'outgoing', 'active': False})})

    def _compute_default_location_src_id(self):
        dropship_types = self.filtered(lambda pt: pt.code == 'dropship')
        dropship_types.default_location_src_id = self.env.ref('stock.stock_location_suppliers').id

        super(StockPickingType, self - dropship_types)._compute_default_location_src_id()

    def _compute_default_location_dest_id(self):
        dropship_types = self.filtered(lambda pt: pt.code == 'dropship')
        dropship_types.default_location_dest_id = self.env.ref('stock.stock_location_customers').id

        super(StockPickingType, self - dropship_types)._compute_default_location_dest_id()

    @api.depends('default_location_src_id', 'default_location_dest_id')
    def _compute_warehouse_id(self):
        super()._compute_warehouse_id()
        for picking_type in self:
            if picking_type.code == 'dropship':
                picking_type.warehouse_id = False

    @api.depends('code')
    def _compute_show_picking_type(self):
        super()._compute_show_picking_type()
        for record in self:
            if record.code == "dropship":
                record.show_picking_type = True

    def _compute_show_return_picking_type(self):
        super()._compute_show_return_picking_type()
        self.filtered(lambda pt: pt.code == 'dropship').show_return_picking_type = True


class StockLot(models.Model):
    _inherit = 'stock.lot'

    def _get_outgoing_domain(self):
        res = super()._get_outgoing_domain()
        return Domain.OR([res, [
            ('location_dest_id.usage', '=', 'customer'),
            ('location_id.usage', '=', 'supplier'),
        ]])
