from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    picking_ids = fields.One2many('stock.picking', 'pos_order_id')
    picking_count = fields.Integer(compute='_compute_picking_count')
    failed_pickings = fields.Boolean(compute='_compute_picking_count')
    picking_type_id = fields.Many2one('stock.picking.type', related='session_id.config_id.picking_type_id', string="Operation Type", readonly=False)
    stock_reference_ids = fields.Many2many('stock.reference', 'stock_reference_pos_order_rel', 'pos_order_id', 'reference_id', string="Reference")
    shipping_date = fields.Date('Shipping Date')

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_picking_count(self):
        for order in self:
            order.picking_count = len(order.picking_ids)
            order.failed_pickings = bool(order.picking_ids.filtered(lambda p: p.state != 'done'))

    def read_pos_data(self, data, config):
        pos_data = super().read_pos_data(data, config)
        pos_data['pos.pack.operation.lot'] = self.env['pos.pack.operation.lot']._load_pos_data_read(self.lines.pack_lot_ids, config) if config else []
        return pos_data

    def _create_order_picking(self):
        self.ensure_one()
        if self.picking_ids:
            return
        if self.shipping_date:
            self.sudo().lines._launch_stock_rule_from_pos_order_lines()
        else:
            if self._should_create_picking_real_time():
                picking_type = self.config_id.picking_type_id
                if self.partner_id.property_stock_customer:
                    destination_id = self.partner_id.property_stock_customer.id
                elif not picking_type or not picking_type.default_location_dest_id:
                    destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
                else:
                    destination_id = picking_type.default_location_dest_id.id

                pickings = self.env['stock.picking']._create_picking_from_pos_order_lines(destination_id, self.lines, picking_type, self.partner_id)
                all_pickings = pickings | pickings.backorder_ids
                all_pickings.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})

    def _get_pos_anglo_saxon_price_unit(self, product, quantity):
        moves = self.mapped('picking_ids.move_ids')\
            .filtered(lambda m: m.is_valued and m.product_id.valuation == 'real_time' and m.product_id.id == product.id)\
            .sorted(lambda x: x.date)
        return moves._get_price_unit()

    def process_saved_payments(self, order, existing_order):
        # update pickings
        if order.get('shipping_date'):
            existing_order.write({'shipping_date': order.get('shipping_date')})
            existing_order.picking_ids.filtered(lambda p: p.state not in ['done', 'cancel']).write({'scheduled_date': order.get('shipping_date')})
        super().process_saved_payments(order, existing_order)

    def _get_total_cost_in_real_time_lines(self):
        lines = super()._get_total_cost_in_real_time_lines()
        if not self._should_create_picking_real_time():
            storable_fifo_avco_lines = lines.filtered(lambda line: line._is_product_storable_fifo_avco())
            lines -= storable_fifo_avco_lines
        return lines

    def _compute_total_cost_at_session_closing(self):
        """
        Compute the margin at the end of the session. This method should be called to compute the remaining lines margin
        containing a storable product with a fifo/avco cost method and then compute the order margin
        """
        for order in self:
            storable_fifo_avco_lines = order.lines.filtered(lambda line: line._is_product_storable_fifo_avco())
            storable_fifo_avco_lines._compute_total_cost(at_closing=True)

    def action_stock_picking(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_ready')
        action['display_name'] = self.env._('Pickings')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

    def _prepare_missing_invoice_moves(self):
        is_picking_created = self._should_create_picking_real_time()
        move = super()._prepare_missing_invoice_moves()
        if not is_picking_created and self._should_create_picking_real_time() and self.session_id.state != 'closed':
            self._create_order_picking()
        return move

    def _should_create_picking_real_time(self):
        return not self.session_id.update_stock_at_closing or self._force_create_picking_real_time()

    def _force_create_picking_real_time(self):
        return self.company_id.anglo_saxon_accounting and self.to_invoice

    def _set_product_qty_available(self):
        super()._set_product_qty_available()
        for order in self:
            order._create_order_picking()

    @api.model
    def _should_update_quantity_on_product(self):
        return False

    def get_stock_reports_to_print(self):
        self.ensure_one()
        return self.picking_ids._get_autoprint_report_actions()
