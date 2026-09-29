from odoo import api, fields, models


class RepairServiceLine(models.Model):
    _inherit = 'repair.service.line'

    sale_line_id = fields.One2many('sale.order.line', 'repair_service_line_id', 'Sale Line', index='btree_not_null')
    invoice_line_ids = fields.One2many('account.move.line', 'repair_service_line_id', string='Invoice Line', index='btree_not_null')

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

            lines_to_create._create_repair_linked_line()
            lines_to_update._update_repair_linked_line()
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_repair_service_line_linked_lines(self):
        self.filtered(
            lambda r: r.repair_id and r.sale_line_id
        ).sale_line_id.write({'product_uom_qty': 0.0})

    def _update_repair_linked_line(self):
        if self.repair_id.sale_order_id:
            return self._update_repair_sale_order_line()

    def _create_repair_linked_line(self):
        if self.repair_id.sale_order_id:
            return self._create_repair_sale_order_line()
        if self.repair_id.invoice_ids:
            return self._create_repair_invoice_line()

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
            self.sale_line_id.price_unit = 0.0

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
