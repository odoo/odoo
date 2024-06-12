# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from markupsafe import Markup

from odoo import api, Command, fields, models, SUPERUSER_ID, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _default_picking_type(self):
        return self._get_picking_type(self.env.context.get('company_id') or self.env.company.id)

    incoterm_location = fields.Char(string='Incoterm Location')
    incoming_picking_count = fields.Integer("Incoming Shipment count", compute='_compute_incoming_picking_count')
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Receptions', copy=False, store=True)
    dest_address_id = fields.Many2one('res.partner', compute='_compute_dest_address_id', store=True, readonly=False)
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', required=True, default=_default_picking_type, domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]",
        help="This will determine operation type of incoming shipment")
    default_location_dest_id_usage = fields.Selection(related='picking_type_id.default_location_dest_id.usage', string='Destination Location Type',
        help="Technical field used to display the Drop Ship Address", readonly=True)
    group_id = fields.Many2one('procurement.group', string="Procurement Group", copy=False)
    is_shipped = fields.Boolean(compute="_compute_is_shipped")
    effective_date = fields.Datetime("Arrival", compute='_compute_effective_date', store=True, copy=False,
        help="Completion date of the first receipt order.")
    on_time_rate = fields.Float(related='partner_id.on_time_rate', compute_sudo=False)
    receipt_status = fields.Selection([
        ('pending', 'Not Received'),
        ('partial', 'Partially Received'),
        ('full', 'Fully Received'),
    ], string='Receipt Status', compute='_compute_receipt_status', store=True)

    @api.depends('order_line.move_ids.picking_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = order.order_line.move_ids.picking_id

    @api.depends('picking_ids')
    def _compute_incoming_picking_count(self):
        for order in self:
            order.incoming_picking_count = len(order.picking_ids)

    @api.depends('picking_ids.date_done')
    def _compute_effective_date(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda x: x.state == 'done' and x.location_dest_id.usage != 'supplier' and x.date_done)
            order.effective_date = min(pickings.mapped('date_done'), default=False)

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_is_shipped(self):
        for order in self:
            if order.picking_ids and all(x.state in ['done', 'cancel'] for x in order.picking_ids):
                order.is_shipped = True
            else:
                order.is_shipped = False

    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_receipt_status(self):
        for order in self:
            if not order.picking_ids or all(p.state == 'cancel' for p in order.picking_ids):
                order.receipt_status = False
            elif all(p.state in ['done', 'cancel'] for p in order.picking_ids):
                order.receipt_status = 'full'
            elif any(p.state == 'done' for p in order.picking_ids):
                order.receipt_status = 'partial'
            else:
                order.receipt_status = 'pending'

    @api.depends('picking_type_id')
    def _compute_dest_address_id(self):
        self.filtered(lambda po: po.picking_type_id.default_location_dest_id.usage != 'customer').dest_address_id = False

    @api.onchange('company_id')
    def _onchange_company_id(self):
        p_type = self.picking_type_id
        if not(p_type and p_type.code == 'incoming' and (p_type.warehouse_id.company_id == self.company_id or not p_type.warehouse_id)):
            self.picking_type_id = self._get_picking_type(self.company_id.id)

    # --------------------------------------------------
    # CRUD
    # --------------------------------------------------

    def write(self, vals):
        if vals.get('order_line') and self.state == 'purchase':
            for order in self:
                pre_order_line_qty = {order_line: order_line.product_qty for order_line in order.mapped('order_line')}
        res = super(PurchaseOrder, self).write(vals)
        if vals.get('order_line') and self.state == 'purchase':
            for order in self:
                to_log = {}
                for order_line in order.order_line:
                    if pre_order_line_qty.get(order_line, False) and float_compare(pre_order_line_qty[order_line], order_line.product_qty, precision_rounding=order_line.product_uom.rounding) > 0:
                        to_log[order_line] = (order_line.product_qty, pre_order_line_qty[order_line])
                if to_log:
                    order._log_decrease_ordered_quantity(to_log)
        return res

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def action_add_from_catalog(self):
        # Replaces the product's kanban view by the purchase specific one.
        action = super().action_add_from_catalog()
        kanban_view_id = self.env.ref('purchase_stock.product_view_kanban_catalog_purchase_only').id
        action['views'][0] = (kanban_view_id, 'kanban')
        return action

    def button_approve(self, force=False):
        result = super(PurchaseOrder, self).button_approve(force=force)
        self._create_picking()
        return result

    def button_cancel(self):
        for order in self:
            for move in order.order_line.mapped('move_ids'):
                if move.state == 'done':
                    raise UserError(_('Unable to cancel purchase order %s as some receptions have already been done.', order.name))
            # If the product is MTO, change the procure_method of the closest move to purchase to MTS.
            # The purpose is to link the po that the user will manually generate to the existing moves's chain.
            if order.state in ('draft', 'sent', 'to approve', 'purchase'):
                for order_line in order.order_line:
                    order_line.move_ids._action_cancel()
                    if order_line.move_dest_ids:
                        move_dest_ids = order_line.move_dest_ids.filtered(lambda move: move.state != 'done' and not move.scrapped)
                        moves_to_unlink = move_dest_ids.filtered(lambda m: len(m.created_purchase_line_ids.ids) > 1)
                        if moves_to_unlink:
                            moves_to_unlink.created_purchase_line_ids = [Command.unlink(order_line.id)]
                        move_dest_ids -= moves_to_unlink
                        if order_line.propagate_cancel:
                            move_dest_ids._action_cancel()
                        else:
                            move_dest_ids.write({'procure_method': 'make_to_stock'})
                            move_dest_ids._recompute_state()

            for pick in order.picking_ids.filtered(lambda r: r.state != 'cancel'):
                pick.action_cancel()

            order.order_line.write({'move_dest_ids': [(5, 0, 0)]})

        return super().button_cancel()

    def action_view_picking(self):
        return self._get_action_view_picking(self.picking_ids)

    def _get_action_view_picking(self, pickings):
        """ This function returns an action that display existing picking orders of given purchase order ids. When only one found, show the picking immediately.
        """
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_origin': self.name, 'default_picking_type_id': self.picking_type_id.id}
        # choose the view_mode accordingly
        if not pickings or len(pickings) > 1:
            result['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = pickings.id
        return result

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        invoice_vals['invoice_incoterm_id'] = self.incoterm_id.id
        return invoice_vals

    # --------------------------------------------------
    # Business methods
    # --------------------------------------------------

    def _log_decrease_ordered_quantity(self, purchase_order_lines_quantities):

        def _keys_in_groupby(move):
            """ group by picking and the responsible for the product the
            move.
            """
            return (move.picking_id, move.product_id.responsible_id)

        def _render_note_exception_quantity_po(order_exceptions):
            order_line_ids = self.env['purchase.order.line'].browse([order_line.id for order in order_exceptions.values() for order_line in order[0]])
            purchase_order_ids = order_line_ids.mapped('order_id')
            move_ids = self.env['stock.move'].concat(*rendering_context.keys())
            impacted_pickings = move_ids.mapped('picking_id')._get_impacted_pickings(move_ids) - move_ids.mapped('picking_id')
            values = {
                'purchase_order_ids': purchase_order_ids,
                'order_exceptions': order_exceptions.values(),
                'impacted_pickings': impacted_pickings,
            }
            return self.env['ir.qweb']._render('purchase_stock.exception_on_po', values)

        documents = self.env['stock.picking']._log_activity_get_documents(purchase_order_lines_quantities, 'move_ids', 'DOWN', _keys_in_groupby)
        filtered_documents = {}
        for (parent, responsible), rendering_context in documents.items():
            if parent._name == 'stock.picking':
                if parent.state in ['cancel', 'done']:
                    continue
            filtered_documents[(parent, responsible)] = rendering_context
        self.env['stock.picking']._log_activity(_render_note_exception_quantity_po, filtered_documents)

    def _get_destination_location(self):
        self.ensure_one()
        if self.dest_address_id:
            return self.dest_address_id.property_stock_customer.id
        return self.picking_type_id.default_location_dest_id.id

    @api.model
    def _get_picking_type(self, company_id):
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return picking_type[:1]

    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        if not self.partner_id.property_stock_supplier.id:
            raise UserError(_("You must set a Vendor Location for this partner %s", self.partner_id.name))
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
            'state': 'draft',
        }

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
            if any(product.type in ['product', 'consu'] for product in order.order_line.product_id):
                order = order.with_company(order.company_id)
                pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                if not pickings:
                    res = order._prepare_picking()
                    picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                    pickings = picking
                else:
                    picking = pickings[0]
                moves = order.order_line._create_stock_moves(picking)
                moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                seq = 0
                for move in sorted(moves, key=lambda move: move.date):
                    seq += 5
                    move.sequence = seq
                moves._action_assign()
                # Get following pickings (created by push rules) to confirm them as well.
                forward_pickings = self.env['stock.picking']._get_impacted_pickings(moves)
                (pickings | forward_pickings).action_confirm()
                picking.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': picking, 'origin': order},
                    subtype_xmlid='mail.mt_note',
                )
        return True

    def _add_picking_info(self, activity):
        """Helper method to add picking info to the Date Updated activity when
        vender updates date_planned of the po lines.
        """
        validated_picking = self.picking_ids.filtered(lambda p: p.state == 'done')
        if validated_picking:
            message = _("Those dates couldn’t be modified accordingly on the receipt %s which had already been validated.", validated_picking[0].name)
        elif not self.picking_ids:
            message = _("Corresponding receipt not found.")
        else:
            message = _("Those dates have been updated accordingly on the receipt %s.", self.picking_ids[0].name)
        activity.note += Markup('<p>{}</p>').format(message)

    def _create_update_date_activity(self, updated_dates):
        activity = super()._create_update_date_activity(updated_dates)
        self._add_picking_info(activity)

    def _update_update_date_activity(self, updated_dates, activity):
        # remove old picking info to update it
        note_lines = activity.note.split('<p>')
        note_lines.pop()
        activity.note = Markup('<p>').join(note_lines)
        super()._update_update_date_activity(updated_dates, activity)
        self._add_picking_info(activity)

    @api.model
    def _get_orders_to_remind(self):
        """When auto sending reminder mails, don't send for purchase order with
        validated receipts."""
        return super()._get_orders_to_remind().filtered(lambda p: not p.effective_date)
