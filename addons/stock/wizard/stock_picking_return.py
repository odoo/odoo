# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError


class StockReturnPickingLine(models.TransientModel):
    _name = 'stock.return.picking.line'
    _rec_name = 'product_id'
    _description = 'Return Picking Line'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    move_quantity = fields.Float(related="move_id.quantity", string="Move Quantity")
    quantity = fields.Float("Quantity", digits='Product Unit', default=1, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', related='product_id.uom_id')
    wizard_id = fields.Many2one('stock.return.picking', string="Wizard")
    move_id = fields.Many2one('stock.move', "Move")

    def _prepare_move_default_values(self, new_picking):
        picking = new_picking or self.wizard_id.picking_id
        vals = {
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.product_id.uom_id.id,
            'picking_id': picking.id,
            'state': 'draft',
            'date': fields.Datetime.now(),
            'location_id': picking.location_id.id or self.move_id.location_dest_id.id,
            'location_dest_id': picking.location_dest_id.id or self.move_id.location_id.id,
            'location_final_id': False,
            'picking_type_id': picking.picking_type_id.id,
            'warehouse_id': picking.picking_type_id.warehouse_id.id,
            'origin_returned_move_id': self.move_id.id,
            'procure_method': 'make_to_stock',
            'group_id': self.wizard_id.picking_id.group_id.id,
        }
        if picking.picking_type_id.code == 'outgoing':
            vals['partner_id'] = picking.partner_id.id
        return vals

    def _process_line(self, new_picking):
        self.ensure_one()
        if not self.uom_id.is_zero(self.quantity):
            vals = self._prepare_move_default_values(new_picking)

            if self.move_id:
                new_return_move = self.move_id.copy(vals)
                vals = {}
                # +--------------------------------------------------------------------------------------------------------+
                # |       picking_pick     <--Move Orig--    picking_pack     --Move Dest-->   picking_ship
                # |              | returned_move_ids              ↑                                  | returned_move_ids
                # |              ↓                                | return_line.move_id              ↓
                # |       return pick(Add as dest)          return toLink                    return ship(Add as orig)
                # +--------------------------------------------------------------------------------------------------------+
                move_orig_to_link = self.move_id.move_dest_ids.returned_move_ids
                # link to original move
                move_orig_to_link |= self.move_id
                # link to siblings of original move, if any
                move_orig_to_link |= self.move_id\
                    .move_dest_ids.filtered(lambda m: m.state not in ('cancel'))\
                    .move_orig_ids.filtered(lambda m: m.state not in ('cancel'))
                move_dest_to_link = self.move_id.move_orig_ids.returned_move_ids
                # link to children of originally returned moves, if any. Note that the use of
                # 'return_line.move_id.move_orig_ids.returned_move_ids.move_orig_ids.move_dest_ids'
                # instead of 'return_line.move_id.move_orig_ids.move_dest_ids' prevents linking a
                # return directly to the destination moves of its parents. However, the return of
                # the return will be linked to the destination moves.
                move_dest_to_link |= self.move_id.move_orig_ids.returned_move_ids\
                    .move_orig_ids.filtered(lambda m: m.state not in ('cancel'))\
                    .move_dest_ids.filtered(lambda m: m.state not in ('cancel'))
                vals['move_orig_ids'] = [Command.link(m.id) for m in move_orig_to_link]
                vals['move_dest_ids'] = [Command.link(m.id) for m in move_dest_to_link]
                new_return_move.write(vals)
            else:
                self.env['stock.move'].create(vals)
            return True


class StockReturnPicking(models.TransientModel):
    _name = 'stock.return.picking'
    _description = 'Return Picking'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'stock.picking':
            if len(self.env.context.get('active_ids', [])) > 1:
                raise UserError(_("You may only return one picking at a time."))
            picking = self.env['stock.picking'].browse(self.env.context.get('active_id'))
            if picking.exists():
                res.update({'picking_id': picking.id})
        return res

    picking_id = fields.Many2one('stock.picking')
    product_return_moves = fields.One2many('stock.return.picking.line', 'wizard_id', 'Moves', compute='_compute_moves_locations', precompute=True, readonly=False, store=True)
    company_id = fields.Many2one(related='picking_id.company_id')

    @api.depends('picking_id')
    def _compute_moves_locations(self):
        for wizard in self:
            if not wizard.picking_id:
                continue
            product_return_moves = [Command.clear()]
            if not wizard.picking_id._can_return():
                raise UserError(_("You may only return Done pickings."))
            # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
            # default values for creation.
            line_fields = list(self.env['stock.return.picking.line']._fields)
            product_return_moves_data_tmpl = self.env['stock.return.picking.line'].default_get(line_fields)
            for move in wizard.picking_id.move_ids:
                if move.state == 'cancel':
                    continue
                if move.scrapped:
                    continue
                product_return_moves_data = dict(product_return_moves_data_tmpl)
                product_return_moves_data.update(wizard._prepare_stock_return_picking_line_vals_from_move(move))
                product_return_moves.append(Command.create(product_return_moves_data))
            if not product_return_moves:
                raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)."))
            wizard.product_return_moves = product_return_moves

    @api.model
    def _prepare_stock_return_picking_line_vals_from_move(self, stock_move):
        return {
            'product_id': stock_move.product_id.id,
            'quantity': 0,
            'move_id': stock_move.id,
            'uom_id': stock_move.product_id.uom_id.id,
        }

    def _prepare_picking_default_values(self):
        return self._prepare_picking_default_values_based_on(self.picking_id)

    def _prepare_picking_default_values_based_on(self, picking):
        location = picking.location_dest_id
        return_type = picking.picking_type_id.return_picking_type_id
        if return_type and return_type.code == 'incoming':
            location_dest = return_type.default_location_dest_id
        else:
            location_dest = picking.location_id

        vals = {
            'move_ids': [],
            'picking_type_id': return_type.id or picking.picking_type_id.id,
            'state': 'draft',
            'return_id': picking.id,
            'origin': _("Return of %(picking_name)s", picking_name=picking.name),
            'location_id': location.id,
            'location_dest_id': location_dest.id,
        }
        return vals

    def _create_return(self):
        for return_move in self.product_return_moves.move_id:
            return_move.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))._do_unreserve()

        # create new picking for returned products
        new_picking = self.picking_id.copy(self._prepare_picking_default_values())
        new_picking.user_id = False
        new_picking.message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': new_picking, 'origin': self.picking_id},
            subtype_xmlid='mail.mt_note',
        )
        returned_lines = False
        for return_line in self.product_return_moves:
            if return_line._process_line(new_picking):
                returned_lines = True
        if not returned_lines:
            raise UserError(_("Please specify at least one non-zero quantity."))

        new_picking.action_confirm()
        new_picking.action_assign()
        return new_picking

    def _create_exchange(self, return_picking):
        # Create a new picking for exchanged products
        exchange_picking = return_picking.copy(self._prepare_picking_default_values_based_on(return_picking))
        exchange_picking.user_id = False
        exchange_picking.message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': exchange_picking, 'origin': return_picking},
            subtype_xmlid='mail.mt_note',
        )
        for return_line in self.product_return_moves:
            return_line._process_line(exchange_picking)

        exchange_picking.action_confirm()
        exchange_picking.action_assign()
        return exchange_picking

    def action_create_returns(self):
        self.ensure_one()
        new_picking = self._create_return()
        return {
            'name': _('Returned Picking'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': new_picking.id,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }

    def action_create_returns_all(self):
        """ Create a return matching the total delivered quantity and open it.
        """
        self.ensure_one()
        for return_move in self.product_return_moves:
            stock_move = return_move.move_id
            if not stock_move or stock_move.state == 'cancel' or stock_move.scrapped:
                continue
            quantity = stock_move.quantity
            for move in stock_move.move_dest_ids:
                if not move.origin_returned_move_id or move.origin_returned_move_id != stock_move:
                    continue
                quantity -= move.quantity
            quantity = stock_move.product_id.uom_id.round(quantity)
            return_move.quantity = quantity
        return self.action_create_returns()

    def action_create_exchanges(self):
        """ Create a return for the active picking, then create a return of
        the return for the exchange picking and open it."""
        action = self.action_create_returns()
        # For receipts: ignore the procurement and create an exchange directly
        if self.picking_id.picking_type_id.code == 'incoming':
            return_picking = self.env['stock.picking'].browse([action['res_id']])
            exchange_picking = self._create_exchange(return_picking)
            # Set the exchange as a return of the return
            exchange_picking.return_id = return_picking
            return action

        proc_list = []
        for line in self.product_return_moves:
            if not line.move_id:
                continue
            proc_values = self._get_proc_values(line)
            proc_list.append(self.env["procurement.group"].Procurement(
                line.product_id, line.quantity, line.uom_id,
                line.move_id.location_dest_id or self.picking_id.location_dest_id,
                line.product_id.display_name, self.picking_id.origin, self.picking_id.company_id,
                proc_values,
            ))
        if proc_list:
            self.env['procurement.group'].run(proc_list)
        return action

    def _get_proc_values(self, line):
        self.ensure_one()
        return {
            'group_id': self.picking_id.group_id,
            'date_planned': line.move_id.date or fields.Datetime.now(),
            'warehouse_id': self.picking_id.picking_type_id.warehouse_id,
            'partner_id': self.picking_id.partner_id.id,
            'location_final_id': line.move_id.location_final_id or self.picking_id.location_dest_id,
            'company_id': self.picking_id.company_id,
        }
