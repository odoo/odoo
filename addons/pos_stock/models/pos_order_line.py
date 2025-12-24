from datetime import UTC
from odoo import api, Command, fields, models
from odoo.exceptions import UserError


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    pack_lot_ids = fields.One2many('pos.pack.operation.lot', 'pos_order_line_id', string='Lot/serial Number')

    def write(self, vals):
        if vals.get('pack_lot_line_ids'):
            for pl in vals.get('pack_lot_ids'):
                if pl[2].get('server_id'):
                    pl[2]['id'] = pl[2]['server_id']
                    del pl[2]['server_id']
        return super().write(vals)

    @api.model
    def get_existing_lots(self, company_id, config_id, product_id):
        """
        Return the lots that are still available in the given company.
        The lot is available if its quantity in the corresponding stock_quant and pos stock location is > 0.
        """
        self.check_access('read')
        pos_config = self.env['pos.config'].browse(config_id)
        if not pos_config:
            raise UserError(self.env._('No PoS configuration found'))

        src_loc = pos_config.picking_type_id.default_location_src_id

        domain = [
            '|',
            ('company_id', '=', False),
            ('company_id', '=', company_id),
            ('product_id', '=', product_id),
            ('location_id', 'in', src_loc.child_internal_location_ids.ids),
            ('quantity', '>', 0),
            ('lot_id', '!=', False),
        ]

        groups = self.sudo().env['stock.quant']._read_group(
            domain=domain,
            groupby=['lot_id'],
            aggregates=['quantity:sum']
        )

        result = []
        has_lot_expiration_date = 'expiration_date' in self.env['stock.lot']._fields
        for lot_recordset, total_quantity in groups:
            if lot_recordset:
                result.append({
                    'id': lot_recordset.id,
                    'name': lot_recordset.name,
                    'product_qty': total_quantity,
                    'expiration_date': lot_recordset.expiration_date if has_lot_expiration_date else False,
                })

        return result

    @api.model
    def _load_pos_data_fields(self, config):
        pos_data_fields = super()._load_pos_data_fields(config)
        pos_data_fields.append('pack_lot_ids')
        return pos_data_fields

    def _prepare_procurement_values(self):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        if self.order_id.shipping_date:
            # get timezone from user
            # and convert to UTC to avoid any timezone issue
            # because shipping_date is date and date_planned is datetime
            from_zone = self.env.tz
            shipping_date = fields.Datetime.to_datetime(self.order_id.shipping_date)
            shipping_date = shipping_date.replace(tzinfo=from_zone)
            date_deadline = shipping_date.astimezone(UTC).replace(tzinfo=None)
        else:
            date_deadline = self.order_id.date_order

        values = {
            'date_planned': date_deadline,
            'date_deadline': date_deadline,
            'route_ids': self.order_id.config_id.route_id,
            'warehouse_id': self.order_id.config_id.warehouse_id or False,
            'partner_id': self.order_id.partner_id.id,
            'product_description_variants': self.full_product_name,
            'company_id': self.order_id.company_id,
            'reference_ids': self.order_id.stock_reference_ids,
        }
        return values

    def _launch_stock_rule_from_pos_order_lines(self):
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.product_id.type != 'consu':
                continue

            reference_ids = line.order_id.stock_reference_ids
            if not reference_ids:
                reference_ids = self.env['stock.reference'].create(line._prepare_reference_vals())
                line.order_id.stock_reference_ids = [Command.set(reference_ids.ids)]

            values = line._prepare_procurement_values()
            product_qty = line.qty

            procurement_uom = line.product_id.uom_id
            procurements.append(self.env['stock.rule'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['stock.rule'].run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                tracked_lines = order.lines.filtered(lambda l: l.product_id.tracking in ['lot', 'serial'])
                lines_by_tracked_product = tracked_lines.grouped('product_id')
                pickings_to_confirm.action_confirm()
                for product, lines in lines_by_tracked_product.items():
                    product_id = product.id
                    moves = pickings_to_confirm.move_ids.filtered(lambda m: m.product_id.id == product_id)
                    moves.move_line_ids.unlink()
                    moves._add_mls_related_to_order(lines, are_qties_done=False)
                    moves._recompute_state()
        return True

    def _is_product_storable_fifo_avco(self):
        self.ensure_one()
        return self.product_id.is_storable and self.product_id.cost_method in ['fifo', 'average']

    def _get_product_cost_with_moves(self, moves):
        self.ensure_one()
        return moves._get_price_unit()

    def _get_stock_moves_to_consider(self, stock_moves, product):
        self.ensure_one()
        return stock_moves.filtered(lambda ml: ml.product_id.id == product.id)

    def _prepare_refund_data(self, refund_order):
        refund_data = super()._prepare_refund_data(refund_order)
        lots = self.env['pos.pack.operation.lot']
        for lot in self.pack_lot_ids:
            lots += lot.copy()
        refund_data['pack_lot_ids'] = lots
        return refund_data

    def _get_product_cost(self, at_closing=False):
        self.ensure_one()
        product = self.product_id
        if at_closing:
            stock_moves = self.order_id.session_id.picking_ids.move_ids
        else:
            stock_moves = self.order_id.picking_ids.move_ids
        cost_currency = product.sudo().cost_currency_id
        moves = self._get_stock_moves_to_consider(stock_moves, product) if stock_moves else None
        if moves and self._is_product_storable_fifo_avco():
            product_cost = self._get_product_cost_with_moves(moves)
            if cost_currency.is_zero(product_cost) and self.order_id.shipping_date:
                if self.refunded_orderline_id:
                    product_cost = self.refunded_orderline_id.total_cost / self.refunded_orderline_id.qty
                else:
                    product_cost = product.standard_price
            return product_cost
        return super()._get_product_cost(at_closing)
