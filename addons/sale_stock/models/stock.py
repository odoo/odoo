# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
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


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _should_show_lot_in_invoice(self):
        return 'customer' in {self.location_id.usage, self.location_dest_id.usage}


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    sale_id = fields.Many2one('sale.order', 'Sale Order')


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_custom_move_fields(self):
        fields = super(StockRule, self)._get_custom_move_fields()
        fields += ['sale_line_id', 'partner_id', 'sequence', 'to_refund']
        return fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_id = fields.Many2one('sale.order', compute="_compute_sale_id", inverse="_set_sale_id", string="Sales Order", store=True, index='btree_not_null')

    @api.depends('group_id')
    def _compute_sale_id(self):
        for picking in self:
            picking.sale_id = picking.group_id.sale_id

    def _set_sale_id(self):
        if self.group_id:
            self.group_id.sale_id = self.sale_id
        else:
            if self.sale_id:
                vals = {
                    'sale_id': self.sale_id.id,
                    'name': self.sale_id.name,
                }
            else:
                vals = {}

            pg = self.env['procurement.group'].create(vals)
            self.group_id = pg

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
        sale_orders = defaultdict(lambda: self.env['sale.order'])
        for move_line in self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('state', '=', 'done')]):
            move = move_line.move_id
            if move.picking_id.location_dest_id.usage in ('customer', 'transit') and move.sale_line_id.order_id:
                sale_orders[move_line.lot_id.id] |= move.sale_line_id.order_id
        for lot in self:
            lot.sale_order_ids = sale_orders[lot.id]
            lot.sale_order_count = len(lot.sale_order_ids)

    def action_view_so(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['domain'] = [('id', 'in', self.mapped('sale_order_ids.id'))]
        action['context'] = dict(self.env.context, create=False)
        return action
