# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.float_utils import float_round
from openerp.tools.translate import _
from openerp import api, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError


from openerp.report import report_sxw

class stock_pack_operation(osv.osv):
    _name = "stock.pack.operation"
    _description = "Packing Operation"

    _order = "result_package_id desc, id"

    def _get_remaining_prod_quantities(self, cr, uid, ids, context=None):
        '''Get the remaining quantities per product on an operation with a package. This function returns a dictionary'''
        operation = self.browse(cr, uid, ids[0], context=context)
        #if the operation doesn't concern a package, it's not relevant to call this function
        if not operation.package_id or operation.product_id:
            return {operation.product_id: operation.remaining_qty}
        #get the total of products the package contains
        res = self.pool.get('stock.quant.package')._get_all_products_quantities(cr, uid, [operation.package_id.id], context=context)
        #reduce by the quantities linked to a move
        for record in operation.linked_move_operation_ids:
            if record.move_id.product_id.id not in res:
                res[record.move_id.product_id] = 0
            res[record.move_id.product_id] -= record.qty
        return res

    def _get_remaining_qty(self, cr, uid, ids, name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        for ops in self.browse(cr, uid, ids, context=context):
            res[ops.id] = 0
            if ops.package_id and not ops.product_id:
                #dont try to compute the remaining quantity for packages because it's not relevant (a package could include different products).
                #should use _get_remaining_prod_quantities instead
                continue
            else:
                qty = ops.product_qty
                if ops.product_uom_id:
                    qty = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, ops.product_qty, ops.product_id.uom_id, context=context)
                for record in ops.linked_move_operation_ids:
                    qty -= record.qty
                res[ops.id] = float_round(qty, precision_rounding=ops.product_id.uom_id.rounding)
        return res

    def product_id_change(self, cr, uid, ids, product_id, product_uom_id, product_qty, context=None):
        res = self.on_change_tests(cr, uid, ids, product_id, product_uom_id, product_qty, context=context)
        uom_obj = self.pool['product.uom']
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        if product_id and not product_uom_id or uom_obj.browse(cr, uid, product_uom_id, context=context).category_id.id != product.uom_id.category_id.id:
            res['value']['product_uom_id'] = product.uom_id.id
        if product:
            res['value']['lots_visible'] = (product.tracking != 'none')
            res['domain'] = {'product_uom_id': [('category_id','=',product.uom_id.category_id.id)]}
        else:
            res['domain'] = {'product_uom_id': []}
        return res

    def on_change_tests(self, cr, uid, ids, product_id, product_uom_id, product_qty, context=None):
        res = {'value': {}}
        uom_obj = self.pool.get('product.uom')
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            product_uom_id = product_uom_id or product.uom_id.id
            selected_uom = uom_obj.browse(cr, uid, product_uom_id, context=context)
            if selected_uom.category_id.id != product.uom_id.category_id.id:
                res['warning'] = {
                    'title': _('Warning: wrong UoM!'),
                    'message': _('The selected UoM for product %s is not compatible with the UoM set on the product form. \nPlease choose an UoM within the same UoM category.') % (product.name)
                }
            if product_qty and 'warning' not in res:
                rounded_qty = uom_obj._compute_qty(cr, uid, product_uom_id, product_qty, product_uom_id, round=True)
                if rounded_qty != product_qty:
                    res['warning'] = {
                        'title': _('Warning: wrong quantity!'),
                        'message': _('The chosen quantity for product %s is not compatible with the UoM rounding. It will be automatically converted at confirmation') % (product.name)
                    }
        return res

    def _compute_location_description(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for op in self.browse(cr, uid, ids, context=context):
            from_name = op.location_id.name
            to_name = op.location_dest_id.name
            if op.package_id and op.product_id:
                from_name += " : " + op.package_id.name
            if op.result_package_id:
                to_name += " : " + op.result_package_id.name
            res[op.id] = {'from_loc': from_name,
                          'to_loc': to_name}
        return res

    def _compute_is_done(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            res[pack.id] = (pack.qty_done > 0.0)
        return res
    _get_bool = _compute_is_done

    def _set_processed_qty(self, cr, uid, id, field_name, field_value, arg, context=None):
        op = self.browse(cr, uid, id, context=context)
        if not op.product_id:
            if field_value and op.qty_done == 0:
                self.write(cr, uid, [id], {'qty_done': 1.0}, context=context)
            if not field_value and op.qty_done != 0:
                self.write(cr, uid, [id], {'qty_done': 0.0}, context=context)
        return True

    def _compute_lots_visible(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for pack in self.browse(cr, uid, ids, context=context):
            if pack.pack_lot_ids:
                res[pack.id] = True
                continue
            pick = pack.picking_id
            product_requires = (pack.product_id.tracking != 'none')
            if pick.picking_type_id:
                res[pack.id] = (pick.picking_type_id.use_existing_lots or pick.picking_type_id.use_create_lots) and product_requires
            else:
                res[pack.id] = product_requires
        return res

    def _get_default_from_loc(self, cr, uid, context=None):
        default_loc = context.get('default_location_id')
        if default_loc:
            return self.pool['stock.location'].browse(cr, uid, default_loc, context=context).name

    def _get_default_to_loc(self, cr, uid, context=None):
        default_loc = context.get('default_location_dest_id')
        if default_loc:
            return self.pool['stock.location'].browse(cr, uid, default_loc, context=context).name

    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Stock Picking', help='The stock operation where the packing has been made', required=True),
        'product_id': fields.many2one('product.product', 'Product', ondelete="CASCADE"),  # 1
        'product_uom_id': fields.many2one('product.uom', 'Unit of Measure'),
        'product_qty': fields.float('To Do', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'qty_done': fields.float('Done', digits_compute=dp.get_precision('Product Unit of Measure')),
        'is_done': fields.function(_compute_is_done, fnct_inv=_set_processed_qty, type='boolean', string='Done', oldname='processed_boolean'),
        'package_id': fields.many2one('stock.quant.package', 'Source Package'),  # 2
        'pack_lot_ids': fields.one2many('stock.pack.operation.lot', 'operation_id', 'Lots Used'),
        'result_package_id': fields.many2one('stock.quant.package', 'Destination Package', help="If set, the operations are packed into this package", required=False, ondelete='cascade'),
        'date': fields.datetime('Date', required=True),
        'owner_id': fields.many2one('res.partner', 'Owner', help="Owner of the quants"),
        'linked_move_operation_ids': fields.one2many('stock.move.operation.link', 'operation_id', string='Linked Moves', readonly=True, help='Moves impacted by this operation for the computation of the remaining quantities'),
        'remaining_qty': fields.function(_get_remaining_qty, type='float', digits = 0, string="Remaining Qty", help="Remaining quantity in default UoM according to moves matched with this operation. "),
        'location_id': fields.many2one('stock.location', 'Source Location', required=True),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True),
        'picking_source_location_id': fields.related('picking_id', 'location_id', type='many2one', relation='stock.location'),
        'picking_destination_location_id': fields.related('picking_id', 'location_dest_id', type='many2one', relation='stock.location'),
        'from_loc': fields.function(_compute_location_description, type='char', string='From', multi='loc'),
        'to_loc': fields.function(_compute_location_description, type='char', string='To', multi='loc'),
        'fresh_record': fields.boolean('Newly created pack operation'),
        'lots_visible': fields.function(_compute_lots_visible, type='boolean'),
        'state': fields.related('picking_id', 'state', type='selection', selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('partially_available', 'Partially Available'),
                ('assigned', 'Available'),
                ('done', 'Done'),
                ]),
        'ordered_qty': fields.float('Ordered Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
    }

    _defaults = {
        'date': fields.date.context_today,
        'qty_done': 0.0,
        'product_qty': 0.0,
        'processed_boolean': lambda *a: False,
        'fresh_record': True,
        'from_loc': _get_default_from_loc,
        'to_loc': _get_default_to_loc,
    }

    def split_quantities(self, cr, uid, ids, context=None):
        for pack in self.browse(cr, uid, ids, context=context):
            if pack.product_qty - pack.qty_done > 0.0 and pack.qty_done < pack.product_qty:
                pack2 = self.copy(cr, uid, pack.id, default={'qty_done': 0.0, 'product_qty': pack.product_qty - pack.qty_done}, context=context)
                self.write(cr, uid, [pack.id], {'product_qty': pack.qty_done}, context=context)
            else:
                raise UserError(_('The quantity to split should be smaller than the quantity To Do.  '))
        return True

    def create(self, cr, uid, vals, context=None):
        vals['ordered_qty'] = vals.get('product_qty')
        return super(stock_pack_operation, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        vals['fresh_record'] = False
        context = context or {}
        res = super(stock_pack_operation, self).write(cr, uid, ids, vals, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        if any([x.state in ('done', 'cancel') for x in self.browse(cr, uid, ids, context=context)]):
            raise UserError(_('You can not delete pack operations of a done picking'))
        return super(stock_pack_operation, self).unlink(cr, uid, ids, context=context)

    def check_tracking(self, cr, uid, ids, context=None):
        """ Checks if serial number is assigned to stock move or not and raise an error if it had to.
        """
        operations = self.browse(cr, uid, ids, context=context)
        for ops in operations:
            if ops.picking_id and (ops.picking_id.picking_type_id.use_existing_lots or ops.picking_id.picking_type_id.use_create_lots) and \
                ops.product_id and ops.product_id.tracking != 'none' and ops.qty_done > 0.0:
                if not ops.pack_lot_ids:
                    raise UserError(_('You need to provide a Lot/Serial Number for product %s') % ops.product_id.name)
                if ops.product_id.tracking == 'serial':
                    for opslot in ops.pack_lot_ids:
                        if opslot.qty not in (1.0, 0.0):
                            raise UserError(_('You should provide a different serial number for each piece'))

    def save(self, cr, uid, ids, context=None):
        for pack in self.browse(cr, uid, ids, context=context):
            if pack.product_id.tracking != 'none':
                qty_done = sum([x.qty for x in pack.pack_lot_ids])
                self.pool['stock.pack.operation'].write(cr, uid, [pack.id], {'qty_done': qty_done}, context=context)
        return {'type': 'ir.actions.act_window_close'}

    def action_split_lots(self, cr, uid, ids, context=None):
        context = context or {}
        ctx=context.copy()
        assert len(ids) > 0
        data_obj = self.pool['ir.model.data']
        pack = self.browse(cr, uid, ids[0], context=context)
        picking_type = pack.picking_id.picking_type_id
        serial = (pack.product_id.tracking == 'serial')
        view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_pack_operation_lot_form')
        only_create = picking_type.use_create_lots and not picking_type.use_existing_lots
        show_reserved = any([x for x in pack.pack_lot_ids if x.qty_todo > 0.0])
        ctx.update({'serial': serial,
                    'only_create': only_create,
                    'create_lots': picking_type.use_create_lots,
                    'state_done': pack.picking_id.state == 'done',
                    'show_reserved': show_reserved})
        return {
             'name': _('Lot Details'),
             'type': 'ir.actions.act_window',
             'view_type': 'form',
             'view_mode': 'form',
             'res_model': 'stock.pack.operation',
             'views': [(view, 'form')],
             'view_id': view,
             'target': 'new',
             'res_id': pack.id,
             'context': ctx,
        }
    split_lot = action_split_lots

    def show_details(self, cr, uid, ids, context=None):
        data_obj = self.pool['ir.model.data']
        view = data_obj.xmlid_to_res_id(cr, uid, 'stock.view_pack_operation_details_form_save')
        pack = self.browse(cr, uid, ids[0], context=context)
        return {
             'name': _('Operation Details'),
             'type': 'ir.actions.act_window',
             'view_type': 'form',
             'view_mode': 'form',
             'res_model': 'stock.pack.operation',
             'views': [(view, 'form')],
             'view_id': view,
             'target': 'new',
             'res_id': pack.id,
             'context': context,
        }


class stock_pack_operation_lot(osv.osv):
    _name = "stock.pack.operation.lot"
    _description = "Specifies lot/serial number for pack operations that need it"

    def _get_plus(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for packlot in self.browse(cr, uid, ids, context=context):
            if packlot.operation_id.product_id.tracking == 'serial':
                res[packlot.id] = (packlot.qty == 0.0)
            else:
                res[packlot.id] = (packlot.qty_todo == 0.0) or (packlot.qty < packlot.qty_todo)
        return res

    _columns = {
        'operation_id': fields.many2one('stock.pack.operation'),
        'qty': fields.float('Done'),
        'lot_id': fields.many2one('stock.production.lot', 'Lot/Serial Number'),
        'lot_name': fields.char('Lot Name'),
        'qty_todo': fields.float('To Do'),
        'plus_visible': fields.function(_get_plus, type='boolean'),
    }

    _defaults = {
        'qty': lambda cr, uid, ids, c: 1.0,
        'qty_todo': lambda cr, uid, ids, c: 0.0,
        'plus_visible': True,
    }

    def _check_lot(self, cr, uid, ids, context=None):
        for packlot in self.browse(cr, uid, ids, context=context):
            if not packlot.lot_name and not packlot.lot_id:
                return False
        return True

    _constraints = [
        (_check_lot,
            'Lot is required',
            ['lot_id', 'lot_name']),
    ]

    _sql_constraints = [
        ('qty', 'CHECK(qty >= 0.0)','Quantity must be greater than or equal to 0.0!'),
        ('uniq_lot_id', 'unique(operation_id, lot_id)', 'You have already mentioned this lot in another line'),
        ('uniq_lot_name', 'unique(operation_id, lot_name)', 'You have already mentioned this lot name in another line')]

    def action_add_quantity(self, cr, uid, ids, context=None):
        pack_ids = []
        for packlot in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [packlot.id], {'qty': packlot.qty + 1}, context=context)
            pack = packlot.operation_id
            pack_ids = [pack.id]
            qty_done = sum([x.qty for x in pack.pack_lot_ids])
            pack.write({'qty_done': qty_done})
        return self.pool['stock.pack.operation'].action_split_lots(cr, uid, pack_ids, context=context)
    do_plus = action_add_quantity

    def action_remove_quantity(self, cr, uid, ids, context=None):
        pack_ids = []
        for packlot in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [packlot.id], {'qty': packlot.qty - 1}, context=context)
            pack = packlot.operation_id
            pack_ids = [pack.id]
            qty_done = sum([x.qty for x in pack.pack_lot_ids])
            pack.write({'qty_done': qty_done})
        return self.pool['stock.pack.operation'].action_split_lots(cr, uid, pack_ids, context=context)
    do_minus = action_remove_quantity


class stock_move_operation_link(osv.osv):
    """
    Table making the link between stock.moves and stock.pack.operations to compute the remaining quantities on each of these objects
    """
    _name = "stock.move.operation.link"
    _description = "Link between stock moves and pack operations"

    _columns = {
        'qty': fields.float('Quantity', help="Quantity of products to consider when talking about the contribution of this pack operation towards the remaining quantity of the move (and inverse). Given in the product main uom."),
        'operation_id': fields.many2one('stock.pack.operation', 'Operation', required=True, ondelete="cascade"),
        'move_id': fields.many2one('stock.move', 'Move', required=True, ondelete="cascade"),
        'reserved_quant_id': fields.many2one('stock.quant', 'Reserved Quant', help="Technical field containing the quant that created this link between an operation and a stock move. Used at the stock_move_obj.action_done() time to avoid seeking a matching quant again"),
    }


class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    @api.onchange('pack_lot_ids')
    def _onchange_packlots(self):
        self.qty_done = sum([x.qty for x in self.pack_lot_ids])
