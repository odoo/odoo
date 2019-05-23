#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, _, api
from odoo.addons import decimal_precision as dp


class StockZeroQuantityCount(models.TransientModel):

    _name = 'stock.zero.quantity.count'
    _description = 'Zero Quantity Count'

    is_done = fields.Boolean('Wizard was processed', default=False)
    pick_ids = fields.Many2many('stock.picking')
    location_id = fields.Many2one('stock.location')

    def get_zqc_inventory_wizard(self):
        view = self.env.ref('stock.view_stock_zero_quantity_count_inventory')
        wiz = self.env['stock.zero.quantity.count.inventory'].create({
            'src_wiz_id': self.id,
            'pick_ids': self.pick_ids,
            'location_id': self.location_id.id,
        })
        return {
            'name': _('Zero Quantity Count - Inventory Adjustment'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.zero.quantity.count.inventory',
            'res_id': wiz.id,
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': self.env.context,
        }

    def confirm_zqc(self):
        self.is_done = True
        return self._update_remaining_zqc_wizards()

    def _update_remaining_zqc_wizards(self):
        wiz_ids = self.env.context.get('remaining_zqc_wizard_ids')
        if wiz_ids and self.id in wiz_ids:
            wiz_ids.remove(self.id)
        return self.pick_ids.with_context({'remaining_zqc_wizard_ids': wiz_ids})._get_next_zqc_wizard()

class StockZeroQuantityCountInventory(models.TransientModel):
    _name = 'stock.zero.quantity.count.inventory'
    _description = 'Adjust inventory if theorical quantities are wrong'

    src_wiz_id = fields.Many2one('stock.zero.quantity.count')
    location_id = fields.Many2one('stock.location', related='src_wiz_id.location_id')
    pick_ids = fields.Many2many('stock.picking')
    zqc_inventory_line_ids = fields.One2many('stock.zero.quantity.count.inventory.line', 'zqci_wiz_id')
    inventory_id = fields.Many2one('stock.inventory')

    def adjust_inventory(self):
        self.inventory_id = self.env['stock.inventory'].create({
            'name': 'Zero Quantity Count Adjustment',
            'line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'partner_id': line.partner_id.id if line.partner_id else None,
                'product_uom_id': line.product_uom_id.id,
                'product_qty': line.product_qty,
                'location_id': self.src_wiz_id.location_id.id,
                'package_id': line.package_id.id if line.package_id else None,
                'prod_lot_id': line.prod_lot_id.id if line.prod_lot_id else None,
                'theoretical_qty': 0,
                'product_tracking': line.product_tracking
            }) for line in self.zqc_inventory_line_ids]
        })
        self.inventory_id._action_start()
        self.inventory_id.action_validate()

        return self._update_remaining_zqc_wizards()

    def cancel_inventory(self):
        return self._update_remaining_zqc_wizards()

    def _update_remaining_zqc_wizards(self):
        wiz_ids = self.env.context.get('remaining_zqc_wizard_ids')
        if wiz_ids and self.src_wiz_id.id in wiz_ids:
            wiz_ids.remove(self.src_wiz_id.id)
        self.src_wiz_id.is_done = True
        return self.pick_ids.with_context({'remaining_zqc_wizard_ids': wiz_ids})._get_next_zqc_wizard()


class StockZeroQuantityCountInventoryLine(models.TransientModel):

    _name = 'stock.zero.quantity.count.inventory.line'
    _description = 'Abstract inventory Lines'

    zqci_wiz_id = fields.Many2one('stock.zero.quantity.count.inventory')
    location_id = fields.Many2one('stock.location', related='zqci_wiz_id.location_id')
    partner_id = fields.Many2one('res.partner', 'Owner')
    product_id = fields.Many2one(
        'product.product', 'Product',
        index=True, required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        required=True, readonly=True, related='product_id.uom_id')
    product_qty = fields.Float(
        'Counted Quantity',
        digits=dp.get_precision('Product Unit of Measure'), default=0)
    package_id = fields.Many2one(
        'stock.quant.package', 'Pack', index=True)
    prod_lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial Number',
        domain="[('product_id','=',product_id)]")
    theoretical_qty = fields.Float(
        'Theoretical Quantity',
        digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    difference_qty = fields.Float('Difference', compute='_compute_difference',
        help="Indicates the gap between the product's theoretical quantity and its newest quantity.",
        readonly=True, digits=dp.get_precision('Product Unit of Measure'))
    product_tracking = fields.Selection('Tracking', related='product_id.tracking', readonly=True)
