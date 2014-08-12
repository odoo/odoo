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
from openerp.tools.translate import _


class stock_transfer_details(models.TransientModel):
    _name = 'stock.transfer_details'
    _description = 'Picking wizard'

    item_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Items')
    packop_ids = fields.One2many('stock.transfer_details_packs', 'transfer_id', 'Packs')

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking', 'stock.picking.in', 'stock.picking.out'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items=[]
        for op in picking.pack_operation_ids:
            if op.product_id:
                item = {
                    'packop_id': op.id,
                    'name': op.product_id.id,
                    'quantity': op.product_qty,
                    'sourceloc_id': op.location_id.id if op.location_id else False,
                    'destinationloc_id': op.location_dest_id.id if op.location_dest_id else False,
                    'package_id': op.result_package_id.id if op.result_package_id else False,
                    'lot_id': op.lot_id.id if op.lot_id else False,
                }
                items.append(item)
            elif op.package_id:
                print "Package %s" % op.package_id.id
            else:
                print "other"

        res.update(item_ids=items)
        return res

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
            'context': self._context,
        }


class stock_transfer_details_items(models.TransientModel):
    _name = 'stock.transfer_details_items'
    _description = 'Picking wizard items'

    transfer_id = fields.Many2one('stock.transfer_details', 'Transfer')
    packop_id = fields.Many2one('stock.pack.operation', 'Operation')
    name = fields.Many2one('product.product', 'Item')
    quantity = fields.Float('Quantity')
    sourceloc_id = fields.Many2one('stock.location', 'Source Location')
    destinationloc_id = fields.Many2one('stock.location', 'Destination Location')
    package_id = fields.Many2one('stock.quant.package', 'Package')
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')

    def split_in_packages(self, cr, uid, ids, context=None):
        dets = self.pool['stock.transfer_details_items'].browse(cr, uid, ids, context)
        for det in dets:
            if det.quantity>1:
                det.quantity = (det.quantity-1)
                new_id = det.copy(context=context)
                new_id.quantity = 1
                new_id.packop_id = False
        if dets and dets[0]:
            return self.pool['stock.transfer_details'].wizard_view(cr, uid, dets[0].transfer_id.id, context=context)

    @api.multi
    def put_in_pack(self):
        newpack = self.pool['stock.quant.package'].create(self._cr, self._uid, {}, self._context)
        for packop in self:
            packop.package_id = newpack
            result = packop.transfer_id.wizard_view()
            print result
            return result

class stock_transfer_details_packs(models.TransientModel):
    _name = 'stock.transfer_details_packs'
    _description = 'Picking wizard packs'

    transfer_id = fields.Many2one('stock.transfer_details', 'Transfer')
    packop_id = fields.Many2one('stock.pack.operation', 'Operation')
    name = fields.Many2one('stock.quant.package', 'Package')
    sourceloc_id = fields.Many2one('stock.location', 'Source Location')
    destinationloc_id = fields.Many2one('stock.location', 'Destination Location')
    package_id = fields.Many2one('stock.quant.package', 'Destination Package')
