# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    incoterm = fields.Many2one(
        'account.incoterms', 'Incoterm',
        help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    incoterm_location = fields.Char(string='Incoterm Location')
    picking_policy = fields.Selection([
        ('direct', 'As soon as possible'),
        ('one', 'When all products are ready')],
        string='Shipping Policy', required=True, default='direct',
        help="If you deliver all products at once, the delivery order will be scheduled based on the greatest "
        "product lead time. Otherwise, it will be based on the shortest.")
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        compute='_compute_warehouse_id', store=True, readonly=False, precompute=True,
        check_company=True)
    picking_ids = fields.One2many('stock.picking', 'sale_id', string='Transfers')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
    delivery_status = fields.Selection([
        ('pending', 'Not Delivered'),
        ('started', 'Started'),
        ('partial', 'Partially Delivered'),
        ('full', 'Fully Delivered'),
    ], string='Delivery Status', compute='_compute_delivery_status', store=True,
       help="Blue: Not Delivered/Started\n\
            Orange: Partially Delivered\n\
            Green: Fully Delivered")
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group', copy=False)
    effective_date = fields.Datetime("Effective Date", compute='_compute_effective_date', store=True, help="Completion date of the first delivery order.")
    expected_date = fields.Datetime( help="Delivery date you can promise to the customer, computed from the minimum lead time of "
                                          "the order lines in case of Service products. In case of shipping, the shipping policy of "
                                          "the order will be taken into account to either use the minimum or maximum lead time of "
                                          "the order lines.")
    json_popover = fields.Char('JSON data for the popover widget', compute='_compute_json_popover')
    show_json_popover = fields.Boolean('Has late picking', compute='_compute_json_popover')

    def _init_column(self, column_name):
        """ Ensure the default warehouse_id is correctly assigned

        At column initialization, the ir.model.fields for res.users.property_warehouse_id isn't created,
        which means trying to read the property field to get the default value will crash.
        We therefore enforce the default here, without going through
        the default function on the warehouse_id field.
        """
        if column_name != "warehouse_id":
            return super(SaleOrder, self)._init_column(column_name)
        field = self._fields[column_name]
        default = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        value = field.convert_to_write(default, self)
        value = field.convert_to_column_insert(value, self)
        if value is not None:
            _logger.debug("Table '%s': setting default value of new column %s to %r",
                self._table, column_name, value)
            query = f'UPDATE "{self._table}" SET "{column_name}" = %s WHERE "{column_name}" IS NULL'
            self._cr.execute(query, (value,))

    @api.depends('picking_ids.date_done')
    def _compute_effective_date(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.usage == 'customer')
            dates_list = [date for date in pickings.mapped('date_done') if date]
            order.effective_date = min(dates_list, default=False)

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_delivery_status(self):
        for order in self:
            if not order.picking_ids or all(p.state == 'cancel' for p in order.picking_ids):
                order.delivery_status = False
            elif all(p.state in ['done', 'cancel'] for p in order.picking_ids):
                order.delivery_status = 'full'
            elif any(p.state == 'done' for p in order.picking_ids) and any(
                    l.qty_delivered for l in order.order_line):
                order.delivery_status = 'partial'
            elif any(p.state == 'done' for p in order.picking_ids):
                order.delivery_status = 'started'
            else:
                order.delivery_status = 'pending'

    @api.depends('picking_policy')
    def _compute_expected_date(self):
        super(SaleOrder, self)._compute_expected_date()

    def _select_expected_date(self, expected_dates):
        if self.picking_policy == "direct":
            return super()._select_expected_date(expected_dates)
        return max(expected_dates)

    @api.constrains('warehouse_id', 'state', 'order_line')
    def _check_warehouse(self):
        """ Ensure that the warehouse is set in case of storable products """
        orders_without_wh = self.filtered(lambda order: order.state not in ('draft', 'cancel') and not order.warehouse_id)
        company_ids_with_wh = {group['company_id'][0] for group in self.env['stock.warehouse'].read_group(domain=[('company_id', 'in', orders_without_wh.mapped('company_id').ids)], fields=['id:recordset'], groupby=['company_id'])} if orders_without_wh else {}
        other_company = set()
        for order_line in orders_without_wh.order_line:
            if order_line.product_id.type != 'consu':
                continue
            if order_line.route_id.company_id and order_line.route_id.company_id != order_line.company_id:
                other_company.add(order_line.route_id.company_id.id)
                continue
            if order_line.order_id.company_id.id in company_ids_with_wh:
                raise UserError(_('You must set a warehouse on your sale order to proceed.'))
            self.env['stock.warehouse'].with_company(order_line.order_id.company_id)._warehouse_redirect_warning()
        other_company_warehouses = self.env['stock.warehouse'].search([('company_id', 'in', list(other_company))])
        if any(c not in other_company_warehouses.company_id.ids for c in other_company):
            raise UserError(_("You must have a warehouse for line using a delivery in different company."))

    def write(self, values):
        if values.get('order_line') and self.state == 'sale':
            for order in self:
                pre_order_line_qty = {order_line: order_line.product_uom_qty for order_line in order.mapped('order_line') if not order_line.is_expense}

        if values.get('partner_shipping_id') and self._context.get('update_delivery_shipping_partner'):
            for order in self:
                order.picking_ids.partner_id = values.get('partner_shipping_id')
        elif values.get('partner_shipping_id'):
            new_partner = self.env['res.partner'].browse(values.get('partner_shipping_id'))
            for record in self:
                picking = record.mapped('picking_ids').filtered(lambda x: x.state not in ('done', 'cancel'))
                message = _("""The delivery address has been changed on the Sales Order<br/>
                        From <strong>"%(old_address)s"</strong> to <strong>"%(new_address)s"</strong>,
                        You should probably update the partner on this document.""",
                            old_address=record.partner_shipping_id.display_name, new_address=new_partner.display_name)
                picking.activity_schedule('mail.mail_activity_data_warning', note=message, user_id=self.env.user.id)

        if 'commitment_date' in values:
            # protagate commitment_date as the deadline of the related stock move.
            # TODO: Log a note on each down document
            deadline_datetime = values.get('commitment_date')
            for order in self:
                order.order_line.move_ids.date_deadline = deadline_datetime or order.expected_date

        res = super(SaleOrder, self).write(values)
        if values.get('order_line') and self.state == 'sale':
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            for order in self:
                to_log = {}
                for order_line in order.order_line:
                    if order_line.display_type:
                        continue
                    if float_compare(order_line.product_uom_qty, pre_order_line_qty.get(order_line, 0.0), precision_rounding=order_line.product_uom.rounding or rounding) < 0:
                        to_log[order_line] = (order_line.product_uom_qty, pre_order_line_qty.get(order_line, 0.0))
                if to_log:
                    documents = self.env['stock.picking'].sudo()._log_activity_get_documents(to_log, 'move_ids', 'UP')
                    documents = {k: v for k, v in documents.items() if k[0].state != 'cancel'}
                    order._log_decrease_ordered_quantity(documents)
        return res

    def _compute_json_popover(self):
        for order in self:
            late_stock_picking = order.picking_ids.filtered(lambda p: p.delay_alert_date)
            order.json_popover = json.dumps({
                'popoverTemplate': 'sale_stock.DelayAlertWidget',
                'late_elements': [{
                        'id': late_move.id,
                        'name': late_move.display_name,
                        'model': 'stock.picking',
                    } for late_move in late_stock_picking
                ]
            })
            order.show_json_popover = bool(late_stock_picking)

    def _action_confirm(self):
        self.order_line._action_launch_stock_rule()
        return super(SaleOrder, self)._action_confirm()

    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = len(order.picking_ids)

    @api.depends('user_id', 'company_id')
    def _compute_warehouse_id(self):
        for order in self:
            default_warehouse_id = self.env['ir.default'].with_company(
                order.company_id.id)._get_model_defaults('sale.order').get('warehouse_id')
            if order.state in ['draft', 'sent'] or not order.ids:
                # Should expect empty
                if default_warehouse_id is not None:
                    order.warehouse_id = default_warehouse_id
                else:
                    order.warehouse_id = order.user_id.with_company(order.company_id.id)._get_default_warehouse_id()

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
                    'Do not forget to change the partner on the following delivery orders: %s',
                    ','.join(pickings.mapped('name')))
            }
        return res

    def action_view_delivery(self):
        return self._get_action_view_picking(self.picking_ids)

    def _action_cancel(self):
        documents = None
        for sale_order in self:
            if sale_order.state == 'sale' and sale_order.order_line:
                sale_order_lines_quantities = {order_line: (order_line.product_uom_qty, 0) for order_line in sale_order.order_line}
                documents = self.env['stock.picking'].with_context(include_draft_documents=True)._log_activity_get_documents(sale_order_lines_quantities, 'move_ids', 'UP')
        self.picking_ids.filtered(lambda p: p.state != 'done').action_cancel()
        if documents:
            filtered_documents = {}
            for (parent, responsible), rendering_context in documents.items():
                if parent._name == 'stock.picking':
                    if parent.state == 'cancel':
                        continue
                filtered_documents[(parent, responsible)] = rendering_context
            self._log_decrease_ordered_quantity(filtered_documents, cancel=True)
        return super()._action_cancel()

    def _get_action_view_picking(self, pickings):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_picking_tree_all")

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
        action['context'] = dict(default_partner_id=self.partner_id.id, default_picking_type_id=picking_id.picking_type_id.id, default_origin=self.name, default_group_id=picking_id.group_id.id)
        return action

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['invoice_incoterm_id'] = self.incoterm.id
        return invoice_vals

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
            return self.env['ir.qweb']._render('sale_stock.exception_on_so', values)

        self.env['stock.picking']._log_activity(_render_note_exception_quantity_so, documents)
