from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    under_warranty = fields.Boolean(
        'Under Warranty',
        help='If ticked, the sales price will be set to 0 for all products transferred from the repair order.')

    # Sale Order Binding
    sale_order_id = fields.Many2one(
        'sale.order', 'Sale Order', check_company=True, readonly=True, index='btree_not_null',
        copy=False, help="Sale Order from which the Repair Order comes from.")
    sale_order_line_id = fields.Many2one(
        'sale.order.line', check_company=True, readonly=True,
        copy=False, index='btree_not_null', help="Sale Order Line from which the Repair Order comes from.")
    repair_request = fields.Text(
        related='sale_order_line_id.name',
        string='Repair Request',
        help="Sale Order Line Description.")

    # Invoice Binding
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')
    invoice_ids = fields.One2many('account.move', 'repair_order_id', string='Invoice', compute='_compute_invoice_ids', store=True, copy=False)
    can_create_extra_invoice = fields.Boolean(compute='_compute_can_create_sale_or_invoice')
    can_create_sale_or_invoice = fields.Boolean(compute='_compute_can_create_sale_or_invoice')

    @api.depends('invoice_ids', 'invoice_ids.state')
    def _compute_invoice_count(self):
        for repair in self:
            repair.invoice_count = len(repair.sudo().invoice_ids)

    @api.depends('invoice_ids', 'invoice_ids.state', 'partner_id', 'sale_order_id', 'state', 'move_ids', 'repair_service_line_ids')
    def _compute_can_create_sale_or_invoice(self):
        for repair in self:
            repair.can_create_sale_or_invoice = (
                repair.partner_id
                and not repair.sudo().invoice_ids
                and not repair.sale_order_id
                and repair.state != "cancel"
            )
            repair.can_create_extra_invoice = (
                    repair.partner_id
                    and all(invoice.state == "posted" for invoice in repair.invoice_ids)
                    and not repair.sale_order_id
                    and (
                        any(not move.invoice_line_ids for move in repair.move_ids)
                        or any(not repair_service_line.invoice_line_ids for repair_service_line in repair.repair_service_line_ids
                        )
                    )
                )

    @api.depends('sale_order_id.invoice_ids')
    def _compute_invoice_ids(self):
        self.invoice_ids |= self.sale_order_id.invoice_ids

    def write(self, vals):
        res = super().write(vals)
        for repair in self:
            if 'under_warranty' in vals:
                repair._update_sale_order_line_price()
                repair._update_invoice_line_price()
        return res

    def action_create_sale_order(self):
        self._create_sale_order()
        return self.action_view_sale_order()

    def action_repair_cancel(self):
        repair_cancel = super().action_repair_cancel()
        for repair in self:
            if repair.sale_order_id:
                repair.sale_order_line_id.write({'product_uom_qty': 0.0})  # Quantity of the product that generated the RO is set to 0
        return repair_cancel

    def action_create_invoice(self):
        self.ensure_one()
        invoice = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_id.id,
                'repair_order_id': self.id,
            })
        self.move_ids._create_repair_invoice_line()
        self.repair_service_line_ids._create_repair_invoice_line()
        return self.action_view_invoice(invoice)

    def action_view_invoice(self, invoice=False):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if not invoice and len(self.invoice_ids) == 1:
            invoice = self.invoice_ids[0]
        action.update({
            'views': [[False, 'form']] if invoice else [[False, 'list'], [False, 'form']],
            'domain': [('id', 'in', self.invoice_ids.ids)],
            'res_id': invoice.id if invoice else False,
            'context': {'create': False},
        })
        return action

    def action_repair_cancel_draft(self):
        repair_cancel_draft = super().action_repair_cancel_draft()
        sale_line_to_update = self.move_ids.sale_line_id.filtered(lambda l: l.order_id.state != 'cancel' and l.product_uom_id.is_zero(l.product_uom_qty))
        sale_line_to_update.move_ids._update_repair_sale_order_line()
        return repair_cancel_draft

    def action_repair_done(self):
        repair_done = super().action_repair_done()
        # Cancel moves with 0 quantity
        self.move_ids.filtered(lambda m: m.uom_id.is_zero(m.quantity))._action_cancel()

        no_service_policy = 'service_policy' not in self.env['product.template']
        for repair in self:
            if repair.sale_order_line_id:
                ro_origin_product = repair.sale_order_line_id.product_template_id
                # TODO: As 'service_policy' only appears with 'sale_project' module, isolate conditions related to this field in a 'sale_project_repair' module if it's worth
                if ro_origin_product.type == 'service' and (no_service_policy or ro_origin_product.service_policy == 'ordered_prepaid'):
                    repair.sale_order_line_id.qty_delivered = repair.sale_order_line_id.product_uom_qty
        self.move_ids._update_repair_linked_line()
        self.repair_service_line_ids._update_repair_linked_line()
        self.repair_service_line_ids._set_service_qty_delivered()
        return repair_done

    def action_view_sale_order(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_order_id.id,
        }

    def _update_sale_order_line_price(self):
        for repair in self:
            add_moves = repair.move_ids.filtered(lambda m: m.repair_line_type == 'add' and m.sale_line_id)
            sale_order_lines = add_moves.sale_line_id | repair.repair_service_line_ids.sale_line_id
            if repair.under_warranty:
                sale_order_lines.write({'price_unit': 0.0, 'technical_price_unit': 0.0})
            else:
                sale_order_lines._compute_price_unit()

    def _update_invoice_line_price(self):
        invoices = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        if self.under_warranty:
            invoices.invoice_line_ids.write({'price_unit': 0.0})
        else:
            invoices.invoice_line_ids._compute_price_unit()

    def _get_sale_order_values(self):
        self.ensure_one()
        return {
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "warehouse_id": self.picking_type_id.warehouse_id.id,
            "repair_order_ids": [Command.link(self.id)],
            "origin": self.name,
        }

    def _create_sale_order(self):
        if any(repair.sale_order_id for repair in self):
            concerned_ro = self.filtered('sale_order_id')
            ref_str = "\n".join(ro.name for ro in concerned_ro)
            raise UserError(
                _(
                    "You cannot create a quotation for a repair order that is already linked to an existing sale order.\nConcerned repair order(s):\n%(ref_str)s",
                    ref_str=ref_str,
                ),
            )
        if any(not repair.partner_id for repair in self):
            concerned_ro = self.filtered(lambda ro: not ro.partner_id)
            ref_str = "\n".join(ro.name for ro in concerned_ro)
            raise UserError(
                _(
                    "You need to define a customer for a repair order in order to create an associated quotation.\nConcerned repair order(s):\n%(ref_str)s",
                    ref_str=ref_str,
                ),
            )
        sale_order_values_list = [repair._get_sale_order_values() for repair in self]
        sale_orders = self.env['sale.order'].create(sale_order_values_list)
        # Add Sale Order Lines for 'add' move_ids and services
        self.move_ids._create_repair_sale_order_line()
        self.repair_service_line_ids._create_repair_sale_order_line()
        return sale_orders
