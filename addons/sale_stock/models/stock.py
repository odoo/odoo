# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, Command
from odoo.tools.sql import column_exists, create_column


class StockRoute(models.Model):
    _inherit = "stock.route"
    sale_selectable = fields.Boolean("Selectable on Sales Order Line")


class StockMove(models.Model):
    _inherit = "stock.move"
    sale_line_id = fields.Many2one('sale.order.line', 'Sale Line', index='btree_not_null')

    @api.depends('sale_line_id', 'sale_line_id.product_uom_id')
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.sale_line_id:
                move.packaging_uom_id = move.sale_line_id.product_uom_id

    @api.depends('sale_line_id')
    def _compute_description_picking(self):
        super()._compute_description_picking()
        for move in self:
            if move.sale_line_id and not move.description_picking_manual:
                sale_line_id = move.sale_line_id.with_context(lang=move.sale_line_id.order_id.partner_id.lang)
                if move.description_picking == move.product_id.display_name:
                    move.description_picking = ''
                move.description_picking = (sale_line_id._get_sale_order_line_multiline_description_variants() + '\n' + move.description_picking).strip()

    def _action_synch_order(self):
        sale_order_lines_vals = []
        for move in self:
            sale_order = move.picking_id.sale_id
            # Creates new SO line only when pickings linked to a sale order and
            # for moves with qty. done and not already linked to a SO line.
            if not sale_order or move.sale_line_id or not move.picked or not (
                (move.location_dest_id.usage in ['customer', 'transit'] and not move.move_dest_ids)
                or (move.location_id.usage == 'customer' and move.to_refund)
            ):
                continue

            product = move.product_id

            if line := sale_order.order_line.filtered(lambda l: l.product_id == product):
                move.sale_line_id = line[:1]
                continue

            quantity = move.quantity
            if move.location_id.usage in ['customer', 'transit']:
                quantity *= -1

            so_line_vals = {
                'move_ids': [(4, move.id, 0)],
                'name': product.display_name,
                'order_id': sale_order.id,
                'product_id': product.id,
                'product_uom_qty': 0,
                'qty_delivered': quantity,
                'product_uom_id': move.product_uom.id,
            }
            so_line = sale_order.order_line.filtered(lambda sol: sol.product_id == product)
            if product.invoice_policy == 'delivery':
                # Check if there is already a SO line for this product to get
                # back its unit price (in case it was manually updated).
                so_line = sale_order.order_line.filtered(lambda sol: sol.product_id == product)
                if so_line:
                    so_line_vals['price_unit'] = so_line[0].price_unit
            elif product.invoice_policy == 'order':
                # No unit price if the product is invoiced on the ordered qty.
                so_line_vals['price_unit'] = 0
            # New lines should be added at the bottom of the SO (higher sequence number)
            if not so_line:
                so_line_vals['sequence'] = max(sale_order.order_line.mapped('sequence')) + len(sale_order_lines_vals) + 1
            sale_order_lines_vals.append(so_line_vals)

        if sale_order_lines_vals:
            self.env['sale.order.line'].with_context(skip_procurement=True).create(sale_order_lines_vals)
        return super()._action_synch_order()

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        distinct_fields.append('sale_line_id')
        return distinct_fields

    def _get_related_invoices(self):
        """ Overridden from stock_account to return the customer invoices
        related to this stock move.
        """
        rslt = super(StockMove, self)._get_related_invoices()
        invoices = self.mapped('picking_id.sale_id.invoice_ids').filtered(lambda x: x.state == 'posted')
        rslt += invoices
        #rslt += invoices.mapped('reverse_entry_ids')
        return rslt

    def _get_source_document(self):
        res = super()._get_source_document()
        return self.sale_line_id.order_id or res

    def _get_sale_order_lines(self):
        """ Return all possible sale order lines for one stock move. """
        self.ensure_one()
        return (self + self.browse(self._rollup_move_origs() | self._rollup_move_dests())).sale_line_id

    def _assign_picking_post_process(self, new=False):
        super(StockMove, self)._assign_picking_post_process(new=new)
        if new:
            picking_id = self.mapped('picking_id')
            sale_order_ids = self.mapped('sale_line_id.order_id')
            for sale_order_id in sale_order_ids:
                picking_id.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': picking_id, 'origin': sale_order_id},
                    subtype_xmlid='mail.mt_note',
                )

    def _get_all_related_sm(self, product):
        return super()._get_all_related_sm(product) | self.filtered(lambda m: m.sale_line_id.product_id == product)

    def write(self, vals):
        res = super().write(vals)
        if 'product_id' in vals:
            for move in self:
                if move.sale_line_id and move.product_id != move.sale_line_id.product_id:
                    move.sale_line_id = False
        return res

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        # to pass sale_line_id fom SO to MO in mto
        if self.sale_line_id:
            res['sale_line_id'] = self.sale_line_id.id
        return res

    def _reassign_sale_lines(self, sale_order):
        current_order = self.sale_line_id.order_id
        if len(current_order) <= 1 and current_order != sale_order:
            ids_to_reset = set()
            if not sale_order:
                ids_to_reset.update(self.ids)
            else:
                line_ids_by_product = dict(self.env['sale.order.line']._read_group(
                    domain=[('order_id', '=', sale_order.id), ('product_id', 'in', self.product_id.ids)],
                    aggregates=['id:array_agg'],
                    groupby=['product_id']
                ))
                for move in self:
                    if line_id := line_ids_by_product.get(move.product_id, [])[:1]:
                        move.sale_line_id = line_id[0]
                    else:
                        ids_to_reset.add(move.id)

            if ids_to_reset:
                self.env['stock.move'].browse(ids_to_reset).sale_line_id = False


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _should_show_lot_in_invoice(self):
        return 'customer' in {self.location_id.usage, self.location_dest_id.usage} or self.env.ref('stock.stock_location_inter_company') in (self.location_id, self.location_dest_id)


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['sale_line_id', 'partner_id', 'sequence', 'to_refund']
        return fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one('sale.order', compute="_compute_sale_id", inverse="_set_sale_id", string="Sales Order", store=True, index='btree_not_null')

    @api.depends('reference_ids.sale_ids', 'move_ids.sale_line_id.order_id')
    def _compute_sale_id(self):
        for picking in self:
            # picking and move should have a link to the SO to see the picking on the stat button.
            # This will filter the move chain to the delivery moves only.
            sales_order = picking.move_ids.sale_line_id.order_id
            picking.sale_id = sales_order[0] if sales_order else False

    @api.depends('move_ids.sale_line_id')
    def _compute_move_type(self):
        super()._compute_move_type()
        for picking in self:
            sale_orders = picking.move_ids.sale_line_id.order_id
            if sale_orders:
                if any(so.picking_policy == "direct" for so in sale_orders):
                    picking.move_type = "direct"
                else:
                    picking.move_type = "one"

    def _set_sale_id(self):
        if self.reference_ids:
            if self.sale_id:
                self.reference_ids.sale_ids = [Command.link(self.sale_id.id)]
            else:
                sale_order = self.move_ids.sale_line_id.order_id
                if len(sale_order) == 1:
                    self.reference_ids.sale_ids = [Command.unlink(sale_order.id)]
        else:
            if self.sale_id:
                reference = self.env['stock.reference'].create({
                    'sale_ids': [Command.link(self.sale_id.id)],
                    'name': self.sale_id.name,
                })
                self._add_reference(reference)
        self.move_ids._reassign_sale_lines(self.sale_id)

    def _auto_init(self):
        """
        Create related field here, too slow
        when computing it afterwards through _compute_related.

        Since group_id.sale_id is created in this module,
        no need for an UPDATE statement.
        """
        if not column_exists(self.env.cr, 'stock_picking', 'sale_id'):
            create_column(self.env.cr, 'stock_picking', 'sale_id', 'int4')
        return super()._auto_init()

    def _action_done(self):
        res = super()._action_done()
        sale_order_lines_vals = []
        for move in self.move_ids:
            ref_sale = move.picking_id.reference_ids.sale_ids
            sale_order = ref_sale and ref_sale[0] or move.sale_line_id.order_id
            # Creates new SO line only when pickings linked to a sale order and
            # for moves with qty. done and not already linked to a SO line.
            if not sale_order or move.sale_line_id or not move.picked or not (
                (move.location_dest_id.usage in ['customer', 'transit'] and not move.move_dest_ids)
                or (move.location_id.usage == 'customer' and move.to_refund)
            ):
                continue
            product = move.product_id
            quantity = move.quantity
            if move.location_id.usage in ['customer', 'transit']:
                quantity *= -1

            so_line_vals = {
                'move_ids': [(4, move.id, 0)],
                'name': product.display_name,
                'order_id': sale_order.id,
                'product_id': product.id,
                'product_uom_qty': 0,
                'qty_delivered': quantity,
                'product_uom_id': move.product_uom.id,
            }
            so_line = sale_order.order_line.filtered(lambda sol: sol.product_id == product)
            if product.invoice_policy == 'delivery':
                # Check if there is already a SO line for this product to get
                # back its unit price (in case it was manually updated).
                if so_line:
                    so_line_vals['price_unit'] = so_line[0].price_unit
            elif product.invoice_policy == 'order':
                # No unit price if the product is invoiced on the ordered qty.
                so_line_vals['price_unit'] = 0
            # New lines should be added at the bottom of the SO (higher sequence number)
            if not so_line:
                so_line_vals['sequence'] = max(sale_order.order_line.mapped('sequence')) + len(sale_order_lines_vals) + 1
            sale_order_lines_vals.append(so_line_vals)

        if sale_order_lines_vals:
            self.env['sale.order.line'].with_context(skip_procurement=True).create(sale_order_lines_vals)
        return res

    def _log_less_quantities_than_expected(self, moves):
        """ Log an activity on sale order that are linked to moves. The
        note summarize the real processed quantity and promote a
        manual action.

        :param dict moves: a dict with a move as key and tuple with
        new and old quantity as value. eg: {move_1 : (4, 5)}
        """

        def _keys_in_groupby(sale_line):
            """ group by order_id and the sale_person on the order """
            return (sale_line.order_id, sale_line.order_id.user_id)

        def _render_note_exception_quantity(moves_information):
            """ Generate a note with the picking on which the action
            occurred and a summary on impacted quantity that are
            related to the sale order where the note will be logged.

            :param moves_information dict:
            {'move_id': ['sale_order_line_id', (new_qty, old_qty)], ..}

            :return: an html string with all the information encoded.
            :rtype: str
            """
            origin_moves = self.env['stock.move'].browse([move.id for move_orig in moves_information.values() for move in move_orig[0]])
            origin_picking = origin_moves.mapped('picking_id')
            values = {
                'origin_moves': origin_moves,
                'origin_picking': origin_picking,
                'moves_information': moves_information.values(),
            }
            return self.env['ir.qweb']._render('sale_stock.exception_on_picking', values)

        documents = self.sudo()._log_activity_get_documents(moves, 'sale_line_id', 'DOWN', _keys_in_groupby)
        self._log_activity(_render_note_exception_quantity, documents)

        return super(StockPicking, self)._log_less_quantities_than_expected(moves)

    def _can_return(self):
        self.ensure_one()
        return super()._can_return() or self.sale_id


class StockLot(models.Model):
    _inherit = 'stock.lot'

    sale_order_ids = fields.Many2many('sale.order', string="Sales Orders", compute='_compute_sale_order_ids')
    sale_order_count = fields.Integer('Sale order count', compute='_compute_sale_order_ids')

    @api.depends('name')
    def _compute_sale_order_ids(self):
        sale_orders = defaultdict(set)
        move_lines = self.env['stock.move.line'].search([
            ('lot_id', 'in', self.ids),
            ('state', '=', 'done'),
            ('move_id.sale_line_id.order_id', '!=', False),
            ('move_id.picking_id.location_dest_id.usage', 'in', ('customer', 'transit')),
        ])
        for ml in move_lines:
            so = ml.move_id.sale_line_id.order_id
            if so.with_user(self.env.user).has_access('read'):
                sale_orders[ml.lot_id.id].add(so.id)
        for lot in self:
            so_ids = sale_orders.get(lot.id, set())
            lot.sale_order_ids = [Command.set(list(so_ids))]
            lot.sale_order_count = len(so_ids)

    def action_view_so(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['domain'] = [('id', 'in', self.mapped('sale_order_ids.id'))]
        action['context'] = dict(self.env.context, create=False)
        return action
