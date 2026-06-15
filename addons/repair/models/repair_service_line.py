from odoo import api, fields, models
from odoo.exceptions import UserError


class RepairServiceLine(models.Model):
    _name = 'repair.service.line'
    _description = "Repair Service Line"
    _order = 'sequence, id'
    _inherit = ['product.catalog.line.mixin']

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

    @api.depends('product_id')
    def _compute_uom_id(self):
        for line in self:
            line.uom_id = line.product_id.uom_id

    @api.depends('product_id', 'product_id.uom_id')
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id._get_available_uoms()

    @api.model_create_multi
    def create(self, vals_list):
        repair_service_line = super().create(vals_list)
        repair_service_line._create_repair_linked_line()
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

                if not line.invoice_line_ids and line.repair_id.invoice_ids:
                    lines_to_create |= line
                elif line.invoice_line_ids:
                    lines_to_update |= line

            lines_to_create._create_repair_linked_line()
            lines_to_update._update_repair_linked_line()
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_repair_service_line(self):
        self.filtered(
            lambda r: r.repair_id and r.sale_line_id
        ).sale_line_id.write({'product_uom_qty': 0.0})

        self.filtered(
            lambda r: r.repair_id and r.invoice_line_ids and r.invoice_line_ids.move_id.state != 'posted'
        ).invoice_line_ids.write({'quantity': 0.0})

    def _update_repair_linked_line(self):
        if self.repair_id.sale_order_id:
            return self._update_repair_sale_order_line()
        if self.repair_id.invoice_ids:
            return self._update_repair_invoice_line()

    def _create_repair_linked_line(self):
        if self.repair_id.sale_order_id:
            return self._create_repair_sale_order_line()
        if self.repair_id.invoice_ids:
            return self._create_repair_invoice_line()

    def _update_repair_invoice_line(self):
        lines_to_recreate = self.env['repair.service.line']
        for line in self:
            if line.invoice_line_ids.move_id.state == 'posted':
                raise UserError(self.env._("This line is linked to a posted invoice and cannot be modified.\n"
                                    "Please create a new line to link to a new invoice or reset the invoice to draft."))
            if line.product_id != line.invoice_line_ids.product_id:
                lines_to_recreate |= line
                continue

            line.invoice_line_ids.write({
                'product_uom_id': line.uom_id.id,
                'quantity': line.quantity,
            })

        lines_to_recreate.invoice_line_ids.unlink()
        lines_to_recreate._create_repair_invoice_line()
        if self.repair_id.under_warranty:
            self.price_unit = 0.0

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
        vals_list = []

        for line in self:
            invoice_id = line.repair_id.invoice_ids.filtered(lambda invoice: invoice.state != 'posted')
            if line.invoice_line_ids or not invoice_id:
                continue

            vals_list.append({
                **line._prepare_repair_service_line_common_vals(),
                'move_id': invoice_id[0].id,
                'quantity': line.quantity,
            })

        self.env['account.move.line'].create(vals_list)

    def _set_service_qty_delivered(self):
        for line in self.mapped('sale_line_id'):
            line.qty_delivered = line.product_uom_qty

    def action_add_service_from_repair_catalog(self):
        repair_order = self.env['repair.order'].browse(self.env.context.get('order_id'))
        return repair_order.with_context(child_field='repair_service_line_ids').action_add_from_catalog()

    def _get_quantity_field(self) -> str:
        return "quantity"

    def _get_product_uom_field(self) -> str:
        return "uom_id"
