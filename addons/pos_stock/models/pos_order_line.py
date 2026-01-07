from itertools import groupby
from datetime import UTC
from odoo import api, Command, fields, models
from odoo.exceptions import UserError


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    pack_lot_ids = fields.One2many('pos.pack.operation.lot', 'pos_order_line_id', string='Lot/serial Number')

    @api.model
    def _load_pos_data_fields(self, config):
        pos_data_fields = super()._load_pos_data_fields(config)
        pos_data_fields.append('pack_lot_ids')
        return pos_data_fields

    def _prepare_refund_data(self, refund_order, PosPackOperationLot=False):
        refund_data = super()._prepare_refund_data(refund_order, PosPackOperationLot)
        refund_data.update({'pack_lot_ids': PosPackOperationLot})
        return refund_data

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
                lines_by_tracked_product = groupby(sorted(tracked_lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
                pickings_to_confirm.action_confirm()
                for product_id, lines in lines_by_tracked_product:
                    lines = self.env['pos.order.line'].concat(*lines)
                    moves = pickings_to_confirm.move_ids.filtered(lambda m: m.product_id.id == product_id)
                    moves.move_line_ids.unlink()
                    moves._add_mls_related_to_order(lines, are_qties_done=False)
                    moves._recompute_state()
        return True

    def _is_product_storable_fifo_avco(self):
        self.ensure_one()
        return self.product_id.is_storable and self.product_id.cost_method in ['fifo', 'average']

    def _compute_total_cost(self, stock_moves=False):
        """
        Compute the total cost of the order lines.
        :param stock_moves: recordset of `stock.move`, used for fifo/avco lines
        """
        for line in self.filtered(lambda l: not l.is_total_cost_computed):
            product = line.product_id
            cost_currency = product.sudo().cost_currency_id
            if line._is_product_storable_fifo_avco() and stock_moves:
                moves = line._get_stock_moves_to_consider(stock_moves, product)
                product_cost = moves._get_price_unit()
                if (cost_currency.is_zero(product_cost) and line.order_id.shipping_date and line.refunded_orderline_id):
                    product_cost = line.refunded_orderline_id.total_cost / line.refunded_orderline_id.qty
            else:
                product_cost = product.standard_price
            line.total_cost = line.qty * cost_currency._convert(
                from_amount=product_cost,
                to_currency=line.currency_id,
                company=line.company_id or self.env.company,
                date=line.order_id.date_order or fields.Date.today(),
                round=False,
            )
            line.is_total_cost_computed = True

    def _get_stock_moves_to_consider(self, stock_moves, product):
        self.ensure_one()
        return stock_moves.filtered(lambda ml: ml.product_id.id == product.id)
