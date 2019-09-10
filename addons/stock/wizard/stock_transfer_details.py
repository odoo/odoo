# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api
from openerp.exceptions import Warning
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime

class stock_transfer_details(models.TransientModel):
    _name = 'stock.transfer_details'
    _description = 'Picking wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking')
    item_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Items', domain=[('product_id', '!=', False)])
    packop_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Packs', domain=[('product_id', '=', False)])
    picking_source_location_id = fields.Many2one('stock.location', string="Head source location", related='picking_id.location_id', store=False, readonly=True)
    picking_destination_location_id = fields.Many2one('stock.location', string="Head destination location", related='picking_id.location_dest_id', store=False, readonly=True)

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date, 
                'owner_id': op.owner_id.id,
            }
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res

    @api.one
    def do_detailed_transfer(self):
        if self.picking_id.state not in ['assigned', 'partially_available']:
            raise Warning(_('You cannot transfer a picking in state \'%s\'.') % self.picking_id.state)

        processed_ids = []
        # Create new and update existing pack operations
        for lstits in [self.item_ids, self.packop_ids]:
            for prod in lstits:
                pack_datas = {
                    'product_id': prod.product_id.id,
                    'product_uom_id': prod.product_uom_id.id,
                    'product_qty': prod.quantity,
                    'package_id': prod.package_id.id,
                    'lot_id': prod.lot_id.id,
                    'location_id': prod.sourceloc_id.id,
                    'location_dest_id': prod.destinationloc_id.id,
                    'result_package_id': prod.result_package_id.id,
                    'date': prod.date if prod.date else datetime.now(),
                    'owner_id': prod.owner_id.id,
                }
                if prod.packop_id:
                    prod.packop_id.with_context(no_recompute=True).write(pack_datas)
                    processed_ids.append(prod.packop_id.id)
                else:
                    pack_datas['picking_id'] = self.picking_id.id
                    packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    processed_ids.append(packop_id.id)
        # Delete the others
        packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
        packops.unlink()

        # Execute the transfer of the picking
        self.picking_id.do_transfer()

        return True

    @api.multi
    def wizard_view(self):
        view = self.env.ref('stock.view_stock_enter_transfer_details')

        return {
            'name': _('Enter transfer details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.transfer_details',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context,
        }


class stock_transfer_details_items(models.TransientModel):
    _name = 'stock.transfer_details_items'
    _description = 'Picking wizard items'

    transfer_id = fields.Many2one('stock.transfer_details', 'Transfer')
    packop_id = fields.Many2one('stock.pack.operation', 'Operation')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure')
    quantity = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), default = 1.0)
    package_id = fields.Many2one('stock.quant.package', 'Source package', domain="['|', ('location_id', 'child_of', sourceloc_id), ('location_id','=',False)]")
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    sourceloc_id = fields.Many2one('stock.location', 'Source Location', required=True)
    destinationloc_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    result_package_id = fields.Many2one('stock.quant.package', 'Destination package', domain="['|', ('location_id', 'child_of', destinationloc_id), ('location_id','=',False)]")
    date = fields.Datetime('Date')
    owner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the quants")



    @api.multi
    def split_quantities(self):
        for det in self:
            if det.quantity>1:
                det.quantity = (det.quantity-1)
                new_id = det.copy(context=self.env.context)
                new_id.quantity = 1
                new_id.packop_id = False
        if self and self[0]:
            return self[0].transfer_id.wizard_view()

    @api.multi
    def put_in_pack(self):
        newpack = None
        for packop in self:
            if not packop.result_package_id:
                if not newpack:
                    newpack = self.pool['stock.quant.package'].create(self._cr, self._uid, {'location_id': packop.destinationloc_id.id if packop.destinationloc_id else False}, self._context)
                packop.result_package_id = newpack
        if self and self[0]:
            return self[0].transfer_id.wizard_view()

    @api.multi
    def product_id_change(self, product, uom=False):
        result = {}
        if product:
            prod = self.env['product.product'].browse(product)
            result['product_uom_id'] = prod.uom_id and prod.uom_id.id
        return {'value': result, 'domain': {}, 'warning':{} }

    @api.multi
    def source_package_change(self, sourcepackage):
        result = {}
        if sourcepackage:
            pack = self.env['stock.quant.package'].browse(sourcepackage)
            result['sourceloc_id'] = pack.location_id and pack.location_id.id
        return {'value': result, 'domain': {}, 'warning':{} }
