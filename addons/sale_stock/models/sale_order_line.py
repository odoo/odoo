# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_compare
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_delivered_method = fields.Selection(selection_add=[('stock_move', 'Stock Moves')])
    route_id = fields.Many2one('stock.route', string='Route', domain=[('sale_selectable', '=', True)], ondelete='restrict')
    move_ids = fields.One2many('stock.move', 'sale_line_id', string='Stock Moves')
    virtual_available_at_date = fields.Float(compute='_compute_qty_at_date', digits='Product Unit of Measure')
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date')
    forecast_expected_date = fields.Datetime(compute='_compute_qty_at_date')
    free_qty_today = fields.Float(compute='_compute_qty_at_date', digits='Product Unit of Measure')
    qty_available_today = fields.Float(compute='_compute_qty_at_date')
    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouse_id', store=True)
    qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver', digits='Product Unit of Measure')
    is_mto = fields.Boolean(compute='_compute_is_mto')
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')
    is_storable = fields.Boolean(related='product_id.is_storable')
    customer_lead = fields.Float(
        compute='_compute_customer_lead', store=True, readonly=False, precompute=True,
        inverse='_inverse_customer_lead')

    @api.depends('route_id', 'order_id.warehouse_id', 'product_packaging_id', 'product_id')
    def _compute_warehouse_id(self):
        for line in self:
            line.warehouse_id = line.order_id.warehouse_id
            if line.route_id:
                domain = [
                    ('location_dest_id', '=', line.order_id.partner_shipping_id.property_stock_customer.id),
                    ('action', '!=', 'push'),
                ]
                # prefer rules on the route itself even if they pull from a different warehouse than the SO's
                rules = sorted(
                    self.env['stock.rule'].search(
                        domain=expression.AND([[('route_id', '=', line.route_id.id)], domain]),
                        order='route_sequence, sequence'
                    ),
                    # if there are multiple rules on the route, prefer those that pull from the SO's warehouse
                    # or those that are not warehouse specific
                    key=lambda rule: 0 if rule.location_src_id.warehouse_id in (False, line.order_id.warehouse_id) else 1
                )
                if rules:
                    line.warehouse_id = rules[0].location_src_id.warehouse_id

    @api.depends('is_storable', 'product_uom_qty', 'qty_delivered', 'state', 'move_ids', 'product_uom')
    def _compute_qty_to_deliver(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_delivered
            if line.state in ('draft', 'sent', 'sale') and line.is_storable and line.product_uom and line.qty_to_deliver > 0:
                if line.state == 'sale' and not line.move_ids:
                    line.display_qty_widget = False
                else:
                    line.display_qty_widget = True
            else:
                line.display_qty_widget = False

    @api.depends(
        'product_id', 'customer_lead', 'product_uom_qty', 'product_uom', 'order_id.commitment_date',
        'move_ids', 'move_ids.forecast_expected_date', 'move_ids.forecast_availability',
        'warehouse_id')
    def _compute_qty_at_date(self):
        """ Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a commitment_date, we take it as delivery date
         2. The quotation hasn't commitment_date, we compute the estimated delivery
            date based on lead time"""
        treated = self.browse()
        all_move_ids = {
            move.id
            for line in self
            if line.state == 'sale'
            for move in line.move_ids | self.env['stock.move'].browse(line.move_ids._rollup_move_origs())
            if move.product_id == line.product_id
        }
        all_moves = self.env['stock.move'].browse(all_move_ids)
        forecast_expected_date_per_move = dict(all_moves.mapped(lambda m: (m.id, m.forecast_expected_date)))
        # If the state is already in sale the picking is created and a simple forecasted quantity isn't enough
        # Then used the forecasted data of the related stock.move
        for line in self.filtered(lambda l: l.state == 'sale'):
            if not line.display_qty_widget:
                continue
            moves = line.move_ids | self.env['stock.move'].browse(line.move_ids._rollup_move_origs())
            moves = moves.filtered(
                lambda m: m.product_id == line.product_id and m.state not in ('cancel', 'done'))
            line.forecast_expected_date = max(
                (
                    forecast_expected_date_per_move[move.id]
                    for move in moves
                    if forecast_expected_date_per_move[move.id]
                ),
                default=False,
            )
            line.qty_available_today = 0
            line.free_qty_today = 0
            for move in moves:
                line.qty_available_today += move.product_uom._compute_quantity(move.quantity, line.product_uom)
                line.free_qty_today += move.product_id.uom_id._compute_quantity(move.forecast_availability, line.product_uom)
            line.scheduled_date = line.order_id.commitment_date or line._expected_date()
            line.virtual_available_at_date = False
            treated |= line

        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
        for line in self.filtered(lambda l: l.state in ('draft', 'sent')):
            if not (line.product_id and line.display_qty_widget):
                continue
            grouped_lines[(line.warehouse_id.id, line.order_id.commitment_date or line._expected_date())] |= line

        for (warehouse, scheduled_date), lines in grouped_lines.items():
            product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date, warehouse_id=warehouse).read([
                'qty_available',
                'free_qty',
                'virtual_available',
            ])
            qties_per_product = {
                product['id']: (product['qty_available'], product['free_qty'], product['virtual_available'])
                for product in product_qties
            }
            for line in lines:
                line.scheduled_date = scheduled_date
                qty_available_today, free_qty_today, virtual_available_at_date = qties_per_product[line.product_id.id]
                line.qty_available_today = qty_available_today - qty_processed_per_product[line.product_id.id]
                line.free_qty_today = free_qty_today - qty_processed_per_product[line.product_id.id]
                line.virtual_available_at_date = virtual_available_at_date - qty_processed_per_product[line.product_id.id]
                line.forecast_expected_date = False
                product_qty = line.product_uom_qty
                if line.product_uom and line.product_id.uom_id and line.product_uom != line.product_id.uom_id:
                    line.qty_available_today = line.product_id.uom_id._compute_quantity(line.qty_available_today, line.product_uom)
                    line.free_qty_today = line.product_id.uom_id._compute_quantity(line.free_qty_today, line.product_uom)
                    line.virtual_available_at_date = line.product_id.uom_id._compute_quantity(line.virtual_available_at_date, line.product_uom)
                    product_qty = line.product_uom._compute_quantity(product_qty, line.product_id.uom_id)
                qty_processed_per_product[line.product_id.id] += product_qty
            treated |= lines
        remaining = (self - treated)
        remaining.virtual_available_at_date = False
        remaining.scheduled_date = False
        remaining.forecast_expected_date = False
        remaining.free_qty_today = False
        remaining.qty_available_today = False

    @api.depends('product_id', 'route_id', 'order_id.warehouse_id', 'product_id.route_ids')
    def _compute_is_mto(self):
        """ Verify the route of the product based on the warehouse
            set 'is_available' at True if the product availability in stock does
            not need to be verified, which is the case in MTO, Cross-Dock or Drop-Shipping
        """
        self.is_mto = False
        for line in self:
            if not line.display_qty_widget:
                continue
            product = line.product_id
            product_routes = line.route_id or (product.route_ids + product.categ_id.total_route_ids)

            # Check MTO
            mto_route = line.order_id.warehouse_id.mto_pull_id.route_id
            if not mto_route:
                try:
                    mto_route = self.env['stock.warehouse']._find_or_create_global_route('stock.route_warehouse0_mto', _('Replenish on Order (MTO)'), create=False)
                except UserError:
                    # if route MTO not found in ir_model_data, we treat the product as in MTS
                    pass

            if mto_route and mto_route in product_routes:
                line.is_mto = True
            else:
                line.is_mto = False

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        """ Stock module compute delivered qty for product [('type', '=', 'consu')]
            For SO line coming from expense, no picking should be generate: we don't manage stock for
            those lines, even if the product is a storable.
        """
        super(SaleOrderLine, self)._compute_qty_delivered_method()

        for line in self:
            if not line.is_expense and line.product_id.type == 'consu':
                line.qty_delivered_method = 'stock_move'

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.quantity', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == 'stock_move':
                qty = 0.0
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                for move in outgoing_moves:
                    if move.state != 'done':
                        continue
                    qty += move.product_uom._compute_quantity(move.quantity, line.product_uom, rounding_method='HALF-UP')
                for move in incoming_moves:
                    if move.state != 'done':
                        continue
                    qty -= move.product_uom._compute_quantity(move.quantity, line.product_uom, rounding_method='HALF-UP')
                line.qty_delivered = qty

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        lines.filtered(lambda line: line.state == 'sale')._action_launch_stock_rule()
        return lines

    def write(self, values):
        lines = self.env['sale.order.line']
        if 'product_uom_qty' in values:
            lines = self.filtered(lambda r: r.state == 'sale' and not r.is_expense)

        if 'product_packaging_id' in values:
            self.move_ids.filtered(
                lambda m: m.state not in ['cancel', 'done']
            ).product_packaging_id = values['product_packaging_id']

        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        res = super(SaleOrderLine, self).write(values)
        if lines:
            lines._action_launch_stock_rule(previous_product_uom_qty)
        return res

    @api.depends('move_ids')
    def _compute_product_updatable(self):
        super()._compute_product_updatable()
        for line in self:
            if line.move_ids.filtered(lambda m: m.state != 'cancel'):
                line.product_updatable = False

    @api.depends('product_id')
    def _compute_customer_lead(self):
        super()._compute_customer_lead() # Reset customer_lead when the product is modified
        for line in self:
            line.customer_lead = line.product_id.sale_delay

    def _inverse_customer_lead(self):
        for line in self:
            if line.state == 'sale' and not line.order_id.commitment_date:
                # Propagate deadline on related stock move
                line.move_ids.date_deadline = line.order_id.date_order + timedelta(days=line.customer_lead or 0.0)

    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        # Use the delivery date if there is else use date_order and lead time
        date_deadline = self.order_id.commitment_date or self._expected_date()
        date_planned = date_deadline - timedelta(days=self.order_id.company_id.security_lead)
        values.update({
            'group_id': group_id,
            'sale_line_id': self.id,
            'date_planned': date_planned,
            'date_deadline': date_deadline,
            'route_ids': self.route_id,
            'warehouse_id': self.warehouse_id,
            'partner_id': self.order_id.partner_shipping_id.id,
            'location_final_id': self._get_location_final(),
            'product_description_variants': self.with_context(lang=self.order_id.partner_id.lang)._get_sale_order_line_multiline_description_variants(),
            'company_id': self.order_id.company_id,
            'product_packaging_id': self.product_packaging_id,
            'sequence': self.sequence,
            'never_product_template_attribute_value_ids': self.product_no_variant_attribute_value_ids,
        })
        return values

    def _get_location_final(self):
        # Can be overriden for inter-company transactions.
        self.ensure_one()
        return self.order_id.partner_shipping_id.property_stock_customer

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        qty = 0.0
        outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves(strict=False)
        for move in outgoing_moves:
            qty_to_compute = move.quantity if move.state == 'done' else move.product_uom_qty
            qty += move.product_uom._compute_quantity(qty_to_compute, self.product_uom, rounding_method='HALF-UP')
        for move in incoming_moves:
            qty_to_compute = move.quantity if move.state == 'done' else move.product_uom_qty
            qty -= move.product_uom._compute_quantity(qty_to_compute, self.product_uom, rounding_method='HALF-UP')
        return qty

    def _get_outgoing_incoming_moves(self, strict=True):
        """ Return the outgoing and incoming moves of the sale order line.
            @param strict: If True, only consider the moves that are strictly delivered to the customer (old behavior).
                           If False, consider the moves that were created through the initial rule of the delivery route,
                           to support the new push mechanism.
        """
        outgoing_moves_ids = set()
        incoming_moves_ids = set()

        moves = self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id)
        if moves and not strict:
            # The first move created was the one created from the intial rule that started it all.
            sorted_moves = moves.sorted('id')
            triggering_rule_ids = []
            seen_wh_ids = set()
            for move in sorted_moves:
                if move.warehouse_id.id not in seen_wh_ids:
                    triggering_rule_ids.append(move.rule_id.id)
                    seen_wh_ids.add(move.warehouse_id.id)
        if self._context.get('accrual_entry_date'):
            moves = moves.filtered(lambda r: fields.Date.context_today(r, r.date) <= self._context['accrual_entry_date'])

        for move in moves:
            if (strict and move.location_dest_id._is_outgoing()) or \
               (not strict and move.rule_id.id in triggering_rule_ids and (move.location_final_id or move.location_dest_id)._is_outgoing()):
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    outgoing_moves_ids.add(move.id)
            elif move.location_id._is_outgoing() and move.to_refund:
                incoming_moves_ids.add(move.id)

        return self.env['stock.move'].browse(outgoing_moves_ids), self.env['stock.move'].browse(incoming_moves_ids)

    def _get_procurement_group(self):
        return self.order_id.procurement_group_id

    def _prepare_procurement_group_vals(self):
        return {
            'name': self.order_id.name,
            'move_type': self.order_id.picking_policy,
            'sale_id': self.order_id.id,
            'partner_id': self.order_id.partner_shipping_id.id,
        }

    def _create_procurements(self, product_qty, procurement_uom, origin, values):
        self.ensure_one()
        return [self.env['procurement.group'].Procurement(
            self.product_id, product_qty, procurement_uom, self._get_location_final(),
            self.product_id.display_name, origin, self.order_id.company_id, values)]

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields generated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        if self._context.get("skip_procurement"):
            return True
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != 'sale' or line.order_id.locked or line.product_id.type != 'consu':
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) == 0:
                continue

            group_id = line._get_procurement_group()
            if not group_id:
                group_id = self.env['procurement.group'].create(line._prepare_procurement_group_vals())
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty

            line_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            origin = f'{line.order_id.name} - {line.order_id.client_order_ref}' if line.order_id.client_order_ref else line.order_id.name
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements += line._create_procurements(product_qty, procurement_uom, origin, values)
        if procurements:
            self.env['procurement.group'].run(procurements)

        # This next block is currently needed only because the scheduler trigger is done by picking confirmation rather than stock.move confirmation
        orders = self.mapped('order_id')
        for order in orders:
            pickings_to_confirm = order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
            if pickings_to_confirm:
                # Trigger the Scheduler for Pickings
                pickings_to_confirm.action_confirm()
        return True

    def _update_line_quantity(self, values):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        line_products = self.filtered(lambda l: l.product_id.type == 'consu')
        if line_products.mapped('qty_delivered') and float_compare(values['product_uom_qty'], max(line_products.mapped('qty_delivered')), precision_digits=precision) == -1:
            raise UserError(_('The ordered quantity of a sale order line cannot be decreased below the amount already delivered. Instead, create a return in your inventory.'))
        super(SaleOrderLine, self)._update_line_quantity(values)

    #=== HOOKS ===#

    def _get_action_add_from_catalog_extra_context(self, order):
        extra_context = super()._get_action_add_from_catalog_extra_context(order)
        extra_context.update(warehouse_id=order.warehouse_id.id)
        return extra_context

    def _get_product_catalog_lines_data(self, **kwargs):
        """ Override of `sale` to add the delivered quantity.

        :rtype: dict
        :return: A dict with the following structure:
            {
                'deliveredQty': float,
                'quantity': float,
                'price': float,
                'readOnly': bool,
            }
        """
        res = super()._get_product_catalog_lines_data(**kwargs)
        res['deliveredQty'] = sum(
            self.mapped(
                lambda line: line.product_uom._compute_quantity(
                    qty=line.qty_delivered,
                    to_unit=line.product_id.uom_id,
                )
            )
        )
        return res
