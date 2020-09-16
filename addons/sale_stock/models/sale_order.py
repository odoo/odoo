# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _default_warehouse_id(self):
        company = self.env.company.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    incoterm = fields.Many2one(
        'account.incoterms', 'Incoterm',
        help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    picking_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready')],
        string='Shipping Policy', required=True, readonly=True, default='direct',
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}
        ,help="If you deliver all products at once, the delivery order will be scheduled based on the greatest "
        "product lead time. Otherwise, it will be based on the shortest.")
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id, check_company=True)
    picking_ids = fields.One2many('stock.picking', 'sale_id', string='Transfers')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    effective_date = fields.Date("Effective Date", compute='_compute_effective_date', store=True, help="Completion date of the first delivery order.")
    expected_date = fields.Datetime( help="Delivery date you can promise to the customer, computed from the minimum lead time of "
                                          "the order lines in case of Service products. In case of shipping, the shipping policy of "
                                          "the order will be taken into account to either use the minimum or maximum lead time of "
                                          "the order lines.")

    @api.depends('picking_ids.date_done')
    def _compute_effective_date(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
            dates_list = [date for date in pickings.mapped('date_done') if date]
            order.effective_date = min(dates_list).date() if dates_list else False

    @api.depends('picking_policy')
    def _compute_expected_date(self):
        super(SaleOrder, self)._compute_expected_date()
        for order in self:
            dates_list = []
            for line in order.order_line.filtered(lambda x: x.state != 'cancel' and not x._is_delivery() and not x.display_type):
                dt = line._expected_date()
                dates_list.append(dt)
            if dates_list:
                expected_date = min(dates_list) if order.picking_policy == 'direct' else max(dates_list)
                order.expected_date = fields.Datetime.to_string(expected_date)

    @api.model
    def create(self, vals):
        if 'warehouse_id' not in vals and 'company_id' in vals and vals.get('company_id') != self.env.company.id:
            vals['warehouse_id'] = self.env['stock.warehouse'].search([('company_id', '=', vals.get('company_id'))], limit=1).id
        return super(SaleOrder, self).create(vals)

    def write(self, values):
        if values.get('order_line') and self.state == 'sale':
            for order in self:
                pre_order_line_qty = {order_line: order_line.product_uom_qty for order_line in order.mapped('order_line') if not order_line.is_expense}

        if values.get('partner_shipping_id'):
            new_partner = self.env['res.partner'].browse(values.get('partner_shipping_id'))
            for record in self:
                picking = record.mapped('picking_ids').filtered(lambda x: x.state not in ('done', 'cancel'))
                addresses = (record.partner_shipping_id.display_name, new_partner.display_name)
                message = _("""The delivery address has been changed on the Sales Order<br/>
                        From <strong>"%s"</strong> To <strong>"%s"</strong>,
                        You should probably update the partner on this document.""") % addresses
                picking.activity_schedule('mail.mail_activity_data_warning', note=message, user_id=self.env.user.id)

        res = super(SaleOrder, self).write(values)
        if values.get('order_line') and self.state == 'sale':
            for order in self:
                to_log = {}
                for order_line in order.order_line:
                    if float_compare(order_line.product_uom_qty, pre_order_line_qty.get(order_line, 0.0), order_line.product_uom.rounding) < 0:
                        to_log[order_line] = (order_line.product_uom_qty, pre_order_line_qty.get(order_line, 0.0))
                if to_log:
                    documents = self.env['stock.picking']._log_activity_get_documents(to_log, 'move_ids', 'UP')
                    documents = {k:v for k, v in documents.items() if k[0].state != 'cancel'}
                    order._log_decrease_ordered_quantity(documents)
        return res

    def _action_confirm(self):
        self.order_line._action_launch_stock_rule()
        return super(SaleOrder, self)._action_confirm()

    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = len(order.picking_ids)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse_id = self.env['ir.default'].get_model_defaults('sale.order').get('warehouse_id')
            self.warehouse_id = warehouse_id or self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)

    @api.onchange('partner_shipping_id')
    def _onchange_partner_shipping_id(self):
        res = {}
        pickings = self.picking_ids.filtered(
            lambda p: p.state not in ['done', 'cancel'] and p.partner_id != self.partner_shipping_id
        )
        if pickings:
            res['warning'] = {
                'title': _('Warning!'),
                'message': _(
                    'Do not forget to change the partner on the following delivery orders: %s'
                ) % (','.join(pickings.mapped('name')))
            }
        return res

    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        # Prepare the context.
        picking_id = pickings.filtered(lambda l: l.picking_type_id.code == 'outgoing')
        if picking_id:
            picking_id = picking_id[0]
        else:
            picking_id = pickings[0]
        action['context'] = dict(self._context, default_partner_id=self.partner_id.id, default_picking_id=picking_id.id, default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name, default_group_id=picking_id.group_id.id)
        return action

    def action_cancel(self):
        documents = None
        for sale_order in self:
            if sale_order.state == 'sale' and sale_order.order_line:
                sale_order_lines_quantities = {order_line: (order_line.product_uom_qty, 0) for order_line in sale_order.order_line}
                documents = self.env['stock.picking']._log_activity_get_documents(sale_order_lines_quantities, 'move_ids', 'UP')
        self.mapped('picking_ids').action_cancel()
        if documents:
            filtered_documents = {}
            for (parent, responsible), rendering_context in documents.items():
                if parent._name == 'stock.picking':
                    if parent.state == 'cancel':
                        continue
                filtered_documents[(parent, responsible)] = rendering_context
            self._log_decrease_ordered_quantity(filtered_documents, cancel=True)
        return super(SaleOrder, self).action_cancel()

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['invoice_incoterm_id'] = self.incoterm.id
        return invoice_vals

    @api.model
    def _get_customer_lead(self, product_tmpl_id):
        super(SaleOrder, self)._get_customer_lead(product_tmpl_id)
        return product_tmpl_id.sale_delay

    def _log_decrease_ordered_quantity(self, documents, cancel=False):

        def _render_note_exception_quantity_so(rendering_context):
            order_exceptions, visited_moves = rendering_context
            visited_moves = list(visited_moves)
            visited_moves = self.env[visited_moves[0]._name].concat(*visited_moves)
            order_line_ids = self.env['sale.order.line'].browse([order_line.id for order in order_exceptions.values() for order_line in order[0]])
            sale_order_ids = order_line_ids.mapped('order_id')
            impacted_pickings = visited_moves.filtered(lambda m: m.state not in ('done', 'cancel')).mapped('picking_id')
            values = {
                'sale_order_ids': sale_order_ids,
                'order_exceptions': order_exceptions.values(),
                'impacted_pickings': impacted_pickings,
                'cancel': cancel
            }
            return self.env.ref('sale_stock.exception_on_so').render(values=values)

        self.env['stock.picking']._log_activity(_render_note_exception_quantity_so, documents)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    qty_delivered_method = fields.Selection(selection_add=[('stock_move', 'Stock Moves')])
    product_packaging = fields.Many2one( 'product.packaging', string='Package', default=False, check_company=True)
    route_id = fields.Many2one('stock.location.route', string='Route', domain=[('sale_selectable', '=', True)], ondelete='restrict', check_company=True)
    move_ids = fields.One2many('stock.move', 'sale_line_id', string='Stock Moves')
    product_type = fields.Selection(related='product_id.type')
    virtual_available_at_date = fields.Float(compute='_compute_qty_at_date')
    scheduled_date = fields.Datetime(compute='_compute_qty_at_date')
    free_qty_today = fields.Float(compute='_compute_qty_at_date')
    qty_available_today = fields.Float(compute='_compute_qty_at_date')
    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_qty_at_date')
    qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver')
    is_mto = fields.Boolean(compute='_compute_is_mto')
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')

    @api.depends('product_id', 'product_uom_qty', 'qty_delivered', 'state')
    def _compute_qty_to_deliver(self):
        """Compute the visibility of the inventory widget."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_delivered
            if line.state == 'draft' and line.product_type == 'product' and line.qty_to_deliver > 0:
                line.display_qty_widget = True
            else:
                line.display_qty_widget = False

    @api.depends('product_id', 'customer_lead', 'product_uom_qty', 'product_uom', 'order_id.warehouse_id', 'order_id.commitment_date')
    def _compute_qty_at_date(self):
        """ Compute the quantity forecasted of product at delivery date. There are
        two cases:
         1. The quotation has a commitment_date, we take it as delivery date
         2. The quotation hasn't commitment_date, we compute the estimated delivery
            date based on lead time"""
        qty_processed_per_product = defaultdict(lambda: 0)
        grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
        # We first loop over the SO lines to group them by warehouse and schedule
        # date in order to batch the read of the quantities computed field.
        for line in self:
            if not (line.product_id and line.display_qty_widget):
                continue
            line.warehouse_id = line.order_id.warehouse_id
            if line.order_id.commitment_date:
                date = line.order_id.commitment_date
            else:
                date = line._expected_date()
            grouped_lines[(line.warehouse_id.id, date)] |= line

        treated = self.browse()
        for (warehouse, scheduled_date), lines in grouped_lines.items():
            product_qties = lines.mapped('product_id').with_context(to_date=scheduled_date, warehouse=warehouse).read([
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
                if line.product_uom and line.product_id.uom_id and line.product_uom != line.product_id.uom_id:
                    line.qty_available_today = line.product_id.uom_id._compute_quantity(line.qty_available_today, line.product_uom)
                    line.free_qty_today = line.product_id.uom_id._compute_quantity(line.free_qty_today, line.product_uom)
                    line.virtual_available_at_date = line.product_id.uom_id._compute_quantity(line.virtual_available_at_date, line.product_uom)
                qty_processed_per_product[line.product_id.id] += line.product_uom_qty
            treated |= lines
        remaining = (self - treated)
        remaining.virtual_available_at_date = False
        remaining.scheduled_date = False
        remaining.free_qty_today = False
        remaining.qty_available_today = False
        remaining.warehouse_id = False

    @api.depends('product_id', 'route_id', 'order_id.warehouse_id', 'product_id.route_ids')
    def _compute_is_mto(self):
        """ Verify the route of the product based on the warehouse
            set 'is_available' at True if the product availibility in stock does
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
                    mto_route = self.env['stock.warehouse']._find_global_route('stock.route_warehouse0_mto', _('Make To Order'))
                except UserError:
                    # if route MTO not found in ir_model_data, we treat the product as in MTS
                    pass

            if mto_route and mto_route in product_routes:
                line.is_mto = True
            else:
                line.is_mto = False

    @api.depends('product_id')
    def _compute_qty_delivered_method(self):
        """ Stock module compute delivered qty for product [('type', 'in', ['consu', 'product'])]
            For SO line coming from expense, no picking should be generate: we don't manage stock for
            thoses lines, even if the product is a storable.
        """
        super(SaleOrderLine, self)._compute_qty_delivered_method()

        for line in self:
            if not line.is_expense and line.product_id.type in ['consu', 'product']:
                line.qty_delivered_method = 'stock_move'

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            if line.qty_delivered_method == 'stock_move':
                qty = 0.0
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                for move in outgoing_moves:
                    if move.state != 'done':
                        continue
                    qty += move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                for move in incoming_moves:
                    if move.state != 'done':
                        continue
                    qty -= move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                line.qty_delivered = qty

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(SaleOrderLine, self).create(vals_list)
        lines.filtered(lambda line: line.state == 'sale')._action_launch_stock_rule()
        return lines

    def write(self, values):
        lines = self.env['sale.order.line']
        if 'product_uom_qty' in values:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            lines = self.filtered(
                lambda r: r.state == 'sale' and not r.is_expense and float_compare(r.product_uom_qty, values['product_uom_qty'], precision_digits=precision) == -1)
        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        res = super(SaleOrderLine, self).write(values)
        if lines:
            lines._action_launch_stock_rule(previous_product_uom_qty)
        return res

    @api.depends('order_id.state')
    def _compute_invoice_status(self):
        super(SaleOrderLine, self)._compute_invoice_status()
        for line in self:
            # We handle the following specific situation: a physical product is partially delivered,
            # but we would like to set its invoice status to 'Fully Invoiced'. The use case is for
            # products sold by weight, where the delivered quantity rarely matches exactly the
            # quantity ordered.
            if line.order_id.state == 'done'\
                    and line.invoice_status == 'no'\
                    and line.product_id.type in ['consu', 'product']\
                    and line.product_id.invoice_policy == 'delivery'\
                    and line.move_ids \
                    and all(move.state in ['done', 'cancel'] for move in line.move_ids):
                line.invoice_status = 'invoiced'

    @api.depends('move_ids')
    def _compute_product_updatable(self):
        for line in self:
            if not line.move_ids.filtered(lambda m: m.state != 'cancel'):
                super(SaleOrderLine, line)._compute_product_updatable()
            else:
                line.product_updatable = False

    @api.onchange('product_id')
    def _onchange_product_id_set_customer_lead(self):
        self.customer_lead = self.product_id.sale_delay

    @api.onchange('product_packaging')
    def _onchange_product_packaging(self):
        if self.product_packaging:
            return self._check_package()

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        # When modifying a one2many, _origin doesn't guarantee that its values will be the ones
        # in database. Hence, we need to explicitly read them from there.
        if self._origin:
            product_uom_qty_origin = self._origin.read(["product_uom_qty"])[0]["product_uom_qty"]
        else:
            product_uom_qty_origin = 0

        if self.state == 'sale' and self.product_id.type in ['product', 'consu'] and self.product_uom_qty < product_uom_qty_origin:
            # Do not display this warning if the new quantity is below the delivered
            # one; the `write` will raise an `UserError` anyway.
            if self.product_uom_qty < self.qty_delivered:
                return {}
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message' : _('You are decreasing the ordered quantity! Do not forget to manually update the delivery order if needed.'),
            }
            return {'warning': warning_mess}
        return {}

    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a stock rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        date_planned = self.order_id.date_order\
            + timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
        values.update({
            'group_id': group_id,
            'sale_line_id': self.id,
            'date_planned': date_planned,
            'route_ids': self.route_id,
            'warehouse_id': self.order_id.warehouse_id or False,
            'partner_id': self.order_id.partner_shipping_id.id,
            'company_id': self.order_id.company_id,
        })
        for line in self.filtered("order_id.commitment_date"):
            date_planned = fields.Datetime.from_string(line.order_id.commitment_date) - timedelta(days=line.order_id.company_id.security_lead)
            values.update({
                'date_planned': fields.Datetime.to_string(date_planned),
            })
        return values

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        self.ensure_one()
        qty = 0.0
        outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
        for move in outgoing_moves:
            qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
        for move in incoming_moves:
            qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
        return qty

    def _get_outgoing_incoming_moves(self):
        outgoing_moves = self.env['stock.move']
        incoming_moves = self.env['stock.move']

        for move in self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id):
            if move.location_dest_id.usage == "customer":
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    outgoing_moves |= move
            elif move.location_dest_id.usage != "customer" and move.to_refund:
                incoming_moves |= move

        return outgoing_moves, incoming_moves

    def _get_procurement_group(self):
        return self.order_id.procurement_group_id

    def _prepare_procurement_group_vals(self):
        return {
            'name': self.order_id.name,
            'move_type': self.order_id.picking_policy,
            'sale_id': self.order_id.id,
            'partner_id': self.order_id.partner_shipping_id.id,
        }

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        procurements = []
        for line in self:
            if line.state != 'sale' or not line.product_id.type in ('consu','product'):
                continue
            qty = line._get_qty_procurement(previous_product_uom_qty)
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
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
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(product_qty, quant_uom)
            procurements.append(self.env['procurement.group'].Procurement(
                line.product_id, product_qty, procurement_uom,
                line.order_id.partner_shipping_id.property_stock_customer,
                line.name, line.order_id.name, line.order_id.company_id, values))
        if procurements:
            self.env['procurement.group'].run(procurements)
        return True

    def _check_package(self):
        default_uom = self.product_id.uom_id
        pack = self.product_packaging
        qty = self.product_uom_qty
        q = default_uom._compute_quantity(pack.qty, self.product_uom)
        # We do not use the modulo operator to check if qty is a mltiple of q. Indeed the quantity
        # per package might be a float, leading to incorrect results. For example:
        # 8 % 1.6 = 1.5999999999999996
        # 5.4 % 1.8 = 2.220446049250313e-16
        if (
            qty
            and q
            and float_compare(
                qty / q, float_round(qty / q, precision_rounding=1.0), precision_rounding=0.001
            )
            != 0
        ):
            newqty = qty - (qty % q) + q
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _("This product is packaged by %.2f %s. You should sell %.2f %s.") % (pack.qty, default_uom.name, newqty, self.product_uom.name),
                },
            }
        return {}

    def _update_line_quantity(self, values):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        line_products = self.filtered(lambda l: l.product_id.type in ['product', 'consu'])
        if line_products.mapped('qty_delivered') and float_compare(values['product_uom_qty'], max(line_products.mapped('qty_delivered')), precision_digits=precision) == -1:
            raise UserError(_('You cannot decrease the ordered quantity below the delivered quantity.\n'
                              'Create a return first.'))
        super(SaleOrderLine, self)._update_line_quantity(values)
