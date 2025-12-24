from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pos_session_id = fields.Many2one('pos.session', index=True)
    pos_order_id = fields.Many2one('pos.order', index=True)

    def _prepare_picking_vals(self, partner, picking_type, location_id, location_dest_id):
        return {
            'partner_id': partner.id if partner else False,
            'user_id': False,
            'picking_type_id': picking_type.id,
            'move_type': 'direct',
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'state': 'draft',
        }

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """We'll create some picking based on order_lines"""

        pickings = self.env['stock.picking']
        stockable_lines = lines.filtered(lambda l: l.product_id.type == 'consu' and not l.product_id.uom_id.is_zero(l.qty))
        if not stockable_lines:
            return pickings
        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            location_id = picking_type.default_location_src_id.id
            positive_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
            )

            positive_picking._create_move_from_pos_order_lines(positive_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    positive_picking._action_done()
            except (UserError, ValidationError):
                pass

            pickings |= positive_picking
        if negative_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id

            negative_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
            )
            negative_picking._create_move_from_pos_order_lines(negative_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    negative_picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= negative_picking
        return pickings

    def _prepare_stock_move_vals(self, first_line, order_lines):
        return {
            'uom_id': first_line.product_id.uom_id.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': first_line.product_id.id,
            'product_uom_qty': abs(sum(order_lines.mapped('qty'))),
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
            'never_product_template_attribute_value_ids': first_line.attribute_value_ids.filtered(lambda a: a.attribute_id.create_variant == 'no_variant'),
        }

    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()

        def get_grouping_key(line):
            return (line.product_id.id, tuple(sorted(line.attribute_value_ids.ids)))

        move_vals = [
            self._prepare_stock_move_vals(order_lines[0], order_lines)
            for order_lines in lines.grouped(get_grouping_key).values()
        ]
        moves = self.env['stock.move'].create(move_vals)
        confirmed_moves = moves._action_confirm()
        confirmed_moves._add_mls_related_to_order(lines, are_qties_done=True)
        confirmed_moves.picked = True
        self._link_owner_on_return_picking(lines)

    def _link_owner_on_return_picking(self, lines):
        """This method tries to retrieve the owner of the returned product"""
        if lines and lines[0].order_id.refunded_order_id.picking_ids:
            returned_lines_picking = lines[0].order_id.refunded_order_id.picking_ids
            returnable_qty_by_product = {}
            for move_line in returned_lines_picking.move_line_ids:
                returnable_qty_by_product[(move_line.product_id.id, move_line.owner_id.id or 0)] = move_line.quantity  # noqa: RUF031
            for move in self.move_line_ids:
                for keys in returnable_qty_by_product:  # noqa: PLC0206
                    if move.product_id.id == keys[0] and keys[1] and returnable_qty_by_product[keys] > 0:
                        move.write({'owner_id': keys[1]})
                        returnable_qty_by_product[keys] -= move.quantity

    def _send_confirmation_email(self):
        # Avoid sending Mail/SMS for POS deliveries
        pickings = self.filtered(lambda p: p.picking_type_id != p.picking_type_id.warehouse_id.pos_type_id)
        return super(StockPicking, pickings)._send_confirmation_email()


class StockPickingType(models.Model):
    _name = 'stock.picking.type'
    _inherit = ['stock.picking.type', 'pos.load.mixin']

    @api.depends('warehouse_id')
    def _compute_hide_reservation_method(self):
        super()._compute_hide_reservation_method()
        for picking_type in self:
            if picking_type == picking_type.warehouse_id.pos_type_id:
                picking_type.hide_reservation_method = True

    @api.constrains('active')
    def _check_active(self):
        for picking_type in self:
            if picking_type.active:
                continue
            pos_config = self.env['pos.config'].sudo().search([('picking_type_id', '=', picking_type.id)], limit=1)
            if pos_config:
                raise ValidationError(_("You cannot archive '%(picking_type)s' as it is used by POS configuration '%(config)s'.", picking_type=picking_type.name, config=pos_config.name))

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', '=', config.picking_type_id.id)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'use_create_lots', 'use_existing_lots']
