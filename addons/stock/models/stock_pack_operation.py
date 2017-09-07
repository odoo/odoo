# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round, float_compare


class PackOperation(models.Model):
    _name = "stock.pack.operation"
    _description = "Packing Operation"
    _order = "result_package_id desc, id"

    # TDE FIXME: strange, probably to remove
    def _get_default_from_loc(self):
        default_loc = self.env.context.get('default_location_id')
        if default_loc:
            return self.env['stock.location'].browse(default_loc).name

    # TDE FIXME: strange, probably to remove
    def _get_default_to_loc(self):
        default_loc = self.env.context.get('default_location_dest_id')
        if default_loc:
            return self.env['stock.location'].browse(default_loc).name

    picking_id = fields.Many2one(
        'stock.picking', 'Stock Picking',
        required=True,
        help='The stock operation where the packing has been made')
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade")
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
    product_qty = fields.Float('To Do', default=0.0, digits=dp.get_precision('Product Unit of Measure'), required=True)
    ordered_qty = fields.Float('Ordered Quantity', digits=dp.get_precision('Product Unit of Measure'))
    qty_done = fields.Float('Done', default=0.0, digits=dp.get_precision('Product Unit of Measure'))
    qty_done_uom_ordered = fields.Float(
        'Quantity Done', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty_done_uom_ordered',
        help='Quantity done in UOM ordered')
    is_done = fields.Boolean(compute='_compute_is_done', string='Done', readonly=False, oldname='processed_boolean')
    package_id = fields.Many2one('stock.quant.package', 'Source Package')
    pack_lot_ids = fields.One2many('stock.pack.operation.lot', 'operation_id', 'Lots/Serial Numbers Used')
    result_package_id = fields.Many2one(
        'stock.quant.package', 'Destination Package',
        ondelete='cascade', required=False,
        help="If set, the operations are packed into this package")
    date = fields.Datetime('Date', default=fields.Date.context_today, required=True)
    owner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the quants")
    linked_move_operation_ids = fields.One2many(
        'stock.move.operation.link', 'operation_id', string='Linked Moves',
        readonly=True,
        help='Moves impacted by this operation for the computation of the remaining quantities')
    remaining_qty = fields.Float(
        compute='_get_remaining_qty', string="Remaining Qty", digits=0,
        help="Remaining quantity in default UoM according to moves matched with this operation.")
    location_id = fields.Many2one('stock.location', 'Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    picking_source_location_id = fields.Many2one('stock.location', related='picking_id.location_id')
    picking_destination_location_id = fields.Many2one('stock.location', related='picking_id.location_dest_id')
    # TDE FIXME: unnecessary fields IMO, to remove
    from_loc = fields.Char(compute='_compute_location_description', default=_get_default_from_loc, string='From')
    to_loc = fields.Char(compute='_compute_location_description', default=_get_default_to_loc, string='To')
    fresh_record = fields.Boolean('Newly created pack operation', default=True)
    lots_visible = fields.Boolean(compute='_compute_lots_visible')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')], related='picking_id.state')

    @api.one
    def _compute_is_done(self):
        self.is_done = self.qty_done > 0.0

    @api.onchange('is_done')
    def on_change_is_done(self):
        if not self.product_id:
            if self.is_done and self.qty_done == 0:
                self.qty_done = 1.0
            if not self.is_done and self.qty_done != 0:
                self.qty_done = 0.0

    def _get_remaining_prod_quantities(self):
        '''Get the remaining quantities per product on an operation with a package. This function returns a dictionary'''
        # TDE CLEANME: merge with _get_all_products_quantities in quant to ease code understanding + clean code
        # if the operation doesn't concern a package, it's not relevant to call this function
        if not self.package_id or self.product_id:
            return {self.product_id: self.remaining_qty}
        # get the total of products the package contains
        res = self.package_id._get_all_products_quantities()
        # reduce by the quantities linked to a move
        for record in self.linked_move_operation_ids:
            if record.move_id.product_id not in res:
                res[record.move_id.product_id] = 0
            res[record.move_id.product_id] -= record.qty
        return res

    @api.one
    def _get_remaining_qty(self):
        if self.package_id and not self.product_id:
            # dont try to compute the remaining quantity for packages because it's not relevant (a package could include different products).
            # should use _get_remaining_prod_quantities instead
            # TDE FIXME: actually resolve the comment hereabove
            self.remaining_qty = 0
        else:
            qty = self.product_qty
            if self.product_uom_id:
                qty = self.product_uom_id._compute_quantity(self.product_qty, self.product_id.uom_id)
            for record in self.linked_move_operation_ids:
                qty -= record.qty
            self.remaining_qty = float_round(qty, precision_rounding=self.product_id.uom_id.rounding)

    @api.multi
    def _compute_location_description(self):
        for operation, operation_sudo in zip(self, self.sudo()):
            operation.from_loc = '%s%s' % (operation_sudo.location_id.name, operation.product_id and operation_sudo.package_id.name or '')
            operation.to_loc = '%s%s' % (operation_sudo.location_dest_id.name, operation_sudo.result_package_id.name or '')

    @api.one
    def _compute_lots_visible(self):
        if self.pack_lot_ids:
            self.lots_visible = True
        elif self.picking_id.picking_type_id and self.product_id.tracking != 'none':  # TDE FIXME: not sure correctly migrated
            picking = self.picking_id
            self.lots_visible = picking.picking_type_id.use_existing_lots or picking.picking_type_id.use_create_lots
        else:
            self.lots_visible = self.product_id.tracking != 'none'

    @api.multi
    def _compute_qty_done_uom_ordered(self):
        for pack in self:
            if pack.product_uom_id and pack.linked_move_operation_ids:
                pack.qty_done_uom_ordered = pack.product_uom_id._compute_quantity(pack.qty_done, pack.linked_move_operation_ids[0].move_id.product_uom)
            else:
                pack.qty_done_uom_ordered = pack.qty_done

    @api.onchange('pack_lot_ids')
    def _onchange_packlots(self):
        self.qty_done = sum([x.qty for x in self.pack_lot_ids])

    @api.multi
    @api.onchange('product_id', 'product_uom_id')
    def onchange_product_id(self):
        if self.product_id:
            self.lots_visible = self.product_id.tracking != 'none'
            if not self.product_uom_id or self.product_uom_id.category_id != self.product_id.uom_id.category_id:
                self.product_uom_id = self.product_id.uom_id.id
            res = {'domain': {'product_uom_id': [('category_id', '=', self.product_uom_id.category_id.id)]}}
        else:
            res = {'domain': {'product_uom_id': []}}
        return res

    @api.model
    def create(self, vals):
        vals['ordered_qty'] = vals.get('product_qty')
        return super(PackOperation, self).create(vals)

    @api.multi
    def write(self, values):
        # TDE FIXME: weird stuff, protectin pack op ?
        values['fresh_record'] = False
        return super(PackOperation, self).write(values)

    @api.multi
    def unlink(self):
        if any([operation.state in ('done', 'cancel') for operation in self]):
            raise UserError(_('You can not delete pack operations of a done picking'))
        return super(PackOperation, self).unlink()

    @api.multi
    def split_quantities(self):
        for operation in self:
            if float_compare(operation.product_qty, operation.qty_done, precision_rounding=operation.product_uom_id.rounding) == 1:
                cpy = operation.copy(default={'qty_done': 0.0, 'product_qty': operation.product_qty - operation.qty_done})
                operation.write({'product_qty': operation.qty_done})
                operation._copy_remaining_pack_lot_ids(cpy)
            else:
                raise UserError(_('The quantity to split should be smaller than the quantity To Do.  '))
        return True

    @api.multi
    def save(self):
        # TDE FIXME: does not seem to be used -> actually, it does
        # TDE FIXME: move me somewhere else, because the return indicated a wizard, in pack op, it is quite strange
        # HINT: 4. How to manage lots of identical products?
        # Create a picking and click on the Mark as TODO button to display the Lot Split icon. A window will pop-up. Click on Add an item and fill in the serial numbers and click on save button
        for pack in self:
            if pack.product_id.tracking != 'none':
                pack.write({'qty_done': sum(pack.pack_lot_ids.mapped('qty'))})
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_split_lots(self):
        action_ctx = dict(self.env.context)
        # If it's a returned stock move, we do not want to create a lot
        returned_move = self.linked_move_operation_ids.mapped('move_id').mapped('origin_returned_move_id')
        picking_type = self.picking_id.picking_type_id
        action_ctx.update({
            'serial': self.product_id.tracking == 'serial',
            'only_create': picking_type.use_create_lots and not picking_type.use_existing_lots and not returned_move,
            'create_lots': picking_type.use_create_lots,
            'state_done': self.picking_id.state == 'done',
            'show_reserved': any([lot for lot in self.pack_lot_ids if lot.qty_todo > 0.0])})
        view_id = self.env.ref('stock.view_pack_operation_lot_form').id
        return {
            'name': _('Lot/Serial Number Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.pack.operation',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': action_ctx}
    split_lot = action_split_lots

    @api.multi
    def show_details(self):
        # TDE FIXME: does not seem to be used
        view_id = self.env.ref('stock.view_pack_operation_details_form_save').id
        return {
            'name': _('Operation Details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.pack.operation',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context}

    @api.multi
    def _check_serial_number(self):
        for operation in self:
            if operation.picking_id and \
                    (operation.picking_id.picking_type_id.use_existing_lots or operation.picking_id.picking_type_id.use_create_lots) and \
                    operation.product_id and operation.product_id.tracking != 'none' and \
                    operation.qty_done > 0.0:
                if not operation.pack_lot_ids:
                    raise UserError(_('You need to provide a Lot/Serial Number for product %s') % operation.product_id.name)
                if operation.product_id.tracking == 'serial':
                    for opslot in operation.pack_lot_ids:
                        if opslot.qty not in (1.0, 0.0):
                            raise UserError(_('You should provide a different serial number for each piece'))
    check_tracking = _check_serial_number

    @api.multi
    def _copy_remaining_pack_lot_ids(self, new_operation):
        for op in self:
            for lot in op.pack_lot_ids:
                new_qty_todo = lot.qty_todo - lot.qty

                if float_compare(new_qty_todo, 0, precision_rounding=op.product_uom_id.rounding) > 0:
                    lot.copy({
                        'operation_id': new_operation.id,
                        'qty_todo': new_qty_todo,
                        'qty': 0,
                    })


class PackOperationLot(models.Model):
    _name = "stock.pack.operation.lot"
    _description = "Lot/Serial number for pack ops"

    operation_id = fields.Many2one('stock.pack.operation')
    qty = fields.Float('Done', default=1.0)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    lot_name = fields.Char('Lot/Serial Number')
    qty_todo = fields.Float('To Do', default=0.0)
    plus_visible = fields.Boolean(compute='_compute_plus_visible', default=True)

    _sql_constraints = [
        ('qty', 'CHECK(qty >= 0.0)', 'Quantity must be greater than or equal to 0.0!'),
        ('uniq_lot_id', 'unique(operation_id, lot_id)', 'You have already mentioned this lot in another line'),
        ('uniq_lot_name', 'unique(operation_id, lot_name)', 'You have already mentioned this lot name in another line')]

    @api.one
    def _compute_plus_visible(self):
        if self.operation_id.product_id.tracking == 'serial':
            self.plus_visible = (self.qty == 0.0)
        else:
            self.plus_visible = (self.qty_todo == 0.0) or (self.qty < self.qty_todo)

    @api.constrains('lot_id', 'lot_name')
    def _check_lot(self):
        if any(not lot.lot_name and not lot.lot_id for lot in self):
            raise ValidationError(_('Lot/Serial Number required'))
        return True

    def action_add_quantity(self, quantity):
        for lot in self:
            lot.write({'qty': lot.qty + quantity})
            lot.operation_id.write({'qty_done': sum(operation_lot.qty for operation_lot in lot.operation_id.pack_lot_ids)})
        return self.mapped('operation_id').action_split_lots()

    @api.multi
    def do_plus(self):
        return self.action_add_quantity(1)

    @api.multi
    def do_minus(self):
        return self.action_add_quantity(-1)


class OperationLink(models.Model):
    """ Make link between stock.move and stock.pack.operation in order to compute
    the remaining quantities on each of those objects. """
    _name = "stock.move.operation.link"
    _description = "Pack Operation / Moves Link"

    qty = fields.Float(
        'Quantity', help="Quantity of products to consider when talking about the contribution of this pack operation towards the "
                         "remaining quantity of the move (and inverse). Given in the product main uom.")
    operation_id = fields.Many2one(
        'stock.pack.operation', 'Operation',
        ondelete="cascade", required=True)
    move_id = fields.Many2one(
        'stock.move', 'Move',
        ondelete="cascade", required=True)
    reserved_quant_id = fields.Many2one(
        'stock.quant', 'Reserved Quant',
        help="Technical field containing the quant that created this link between an operation and a stock move. "
             "Used at the stock_move_obj.action_done() time to avoid seeking a matching quant again")
