from collections import defaultdict

from odoo import api, fields, models


class RepairServiceLine(models.Model):
    _name = 'repair.service.line'
    _description = "Repair Service Line"
    _order = 'sequence, id'

    repair_id = fields.Many2one('repair.order', check_company=True, index='btree_not_null', copy=False, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Service',
        domain="[('type', '=', 'service'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        check_company=True)
    uom_id = fields.Many2one(
        'uom.uom', 'Unit', domain="[('id', 'in', allowed_uom_ids)]",
        readonly=False, required=True, compute='_compute_uom_id', store=True, copy=True, precompute=True)
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    quantity = fields.Float(
        'Quantity', digits='Product Unit', required=True, default=1.0)
    company_id = fields.Many2one(related='repair_id.company_id')
    sale_line_id = fields.One2many('sale.order.line', 'repair_service_line_id', 'Sale Line', index='btree_not_null')
    invoice_line_ids = fields.One2many('account.move.line', 'repair_service_line_id', string='Invoice Line', index='btree_not_null')
    sequence = fields.Integer('Sequence', default=0)
    description = fields.Text(string="Description", translate=True)
    qty_invoiced = fields.Float(string='Invoiced Quantity', compute='_compute_qty_invoiced', digits='Product Unit')
    qty_to_invoice = fields.Float(string='Quantity To Invoice', compute='_compute_qty_to_invoice', digits='Product Unit')

    @api.depends('product_id')
    def _compute_uom_id(self):
        for line in self:
            line.uom_id = line.product_id.uom_id

    @api.depends('product_id', 'product_id.uom_id')
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id._get_available_uoms()

    @api.depends('invoice_line_ids.move_id.state', 'invoice_line_ids.quantity')
    def _compute_qty_invoiced(self):
        invoiced_quantities = self._prepare_qty_invoiced()
        for line in self:
            line.qty_invoiced = invoiced_quantities[line]

    @api.depends('qty_invoiced', 'quantity', 'uom_id', 'invoice_line_ids', 'repair_id.state')
    def _compute_qty_to_invoice(self):
        for line in self:
            invoice_policy = line.product_id.invoice_policy
            if line.repair_id.state == 'done' and invoice_policy == 'delivery' or line.product_id.invoice_policy == 'order':
                line.qty_to_invoice = line.quantity - line.qty_invoiced
                continue
            line.qty_to_invoice = 0

    @api.model_create_multi
    def create(self, vals_list):
        repair_service_line = super().create(vals_list)
        repair_service_line._create_repair_sale_order_line()
        return repair_service_line

    def write(self, vals):
        res = super().write(vals)
        if any(field in vals for field in ('quantity', 'uom_id', 'product_id')):
            lines_to_create = lines_to_update = self.env['repair.service.line']
            for line in self:
                if not line.sale_line_id and line.repair_id.sale_order_id:
                    lines_to_create |= line
                elif line.sale_line_id:
                    lines_to_update |= line

            lines_to_create._create_repair_sale_order_line()
            lines_to_update._update_repair_sale_order_line()
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_repair_service_line(self):
        self.filtered(
            lambda r: r.repair_id and r.sale_line_id
        ).sale_line_id.write({'product_uom_qty': 0.0})

    def _update_repair_sale_order_line(self):
        lines_to_recreate = self.env['repair.service.line']
        for line in self:
            if line.product_id != line.sale_line_id.product_id:
                lines_to_recreate |= line
                continue

            line.sale_line_id.write({
                'product_uom_id': line.uom_id.id,
                'product_uom_qty': line.quantity,
                'discount': line.sale_line_id.discount,
            })

        lines_to_recreate.sale_line_id.unlink()
        lines_to_recreate._create_repair_sale_order_line()
        if self.repair_id.under_warranty:
            self.price_unit = 0.0

    def _prepare_repair_service_line_common_vals(self):
        self.ensure_one()
        comman_vals = {
            'product_id': self.product_id.id,
            'product_uom_id': self.uom_id.id,
            'repair_service_line_id': self.id,
        }
        if self.repair_id.under_warranty:
            comman_vals['price_unit'] = 0.0
        return comman_vals

    def _create_repair_sale_order_line(self):
        vals_list = []

        for line in self:
            if line.sale_line_id or not line.repair_id.sale_order_id:
                continue

            vals_list.append({
                **line._prepare_repair_service_line_common_vals(),
                'order_id': line.repair_id.sale_order_id.id,
                'product_uom_qty': line.quantity,
                'qty_delivered': line.quantity if line.repair_id.state == 'done' else 0.0,
            })

        self.env['sale.order.line'].create(vals_list)

    def _create_repair_invoice_line(self):
        if not self:
            return
        vals_list = []
        invoice_id = self.repair_id.invoice_ids[0]
        is_refund_type = invoice_id.move_type == 'out_refund'
        for line in self:
            if not invoice_id or not line.qty_to_invoice:
                continue
            line_qty = line.qty_to_invoice
            if is_refund_type:
                line_qty *= -1

            vals_list.append({
                **line._prepare_repair_service_line_common_vals(),
                'move_id': invoice_id[0].id,
                'quantity': line_qty,
            })

        self.env['account.move.line'].create(vals_list)

    def _set_service_qty_delivered(self):
        for line in self.mapped('sale_line_id'):
            line.qty_delivered = line.product_uom_qty

    def action_add_service_from_repair_catalog(self):
        repair_order = self.env['repair.order'].browse(self.env.context.get('order_id'))
        return repair_order.with_context(child_field='repair_service_line_ids').action_add_from_catalog()

    def _get_product_catalog_lines_data(self, parent_record=False, **kwargs):
        if not (parent_record and self):
            return {
                'quantity': 0,
            }
        self.product_id.ensure_one()
        return {
            'quantity': self[0].quantity,
            'readOnly': len(self) > 1,
            **parent_record._get_product_catalog_uom_data(self.product_id, self[0].uom_id),
        }

    def _prepare_qty_invoiced(self):
        invoiced_qties = defaultdict(float)
        for line in self:
            for invoice_line in line.invoice_line_ids:
                if (
                    invoice_line.move_id.state != 'cancel'
                    or invoice_line.move_id.payment_state == 'invoicing_legacy'
                ):
                    invoice_qty = invoice_line.product_uom_id._compute_quantity(
                        invoice_line.quantity, line.uom_id, round=False
                    )
                    if invoice_line.move_id.move_type == 'out_invoice':
                        invoiced_qties[line] += invoice_qty
                    elif invoice_line.move_id.move_type == 'out_refund':
                        invoiced_qties[line] -= invoice_qty
        return invoiced_qties
