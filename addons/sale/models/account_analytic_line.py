from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    reinvoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        readonly=True,
        copy=False,
        help="Invoice created from related SO line",
        index='btree_not_null',
    )
    so_line = fields.Many2one(
        'sale.order.line',
        string='Sales Order Item',
        domain=[('qty_delivered_method', '=', 'analytic')],
        index='btree_not_null',
    )
    order_id = fields.Many2one('sale.order', string="Customer Order", index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_id', False):
                vals[self.env.ref('sale.analytic_plan_sale_orders')._column_name()] = (
                    self._get_or_create_account_from_so(vals['order_id']).id
                )

        lines = super().create(vals_list)
        lines._sync_so_lines()
        return lines

    def write(self, vals):
        # completely against this shit but without this it could be problematic when order_id is
        # recomputed from some other place for ex. see test_sol_determined_when_project_is_employee_rate
        if self.env.context.get('from_services_and_material'):
            if 'order_id' in vals:
                self._sync_so_quantity(0, self.so_line, True)

            if 'unit_amount' in vals:
                self._sync_so_quantity(vals['unit_amount'], self.so_line, True)

            res = super().write(vals)

            if 'order_id' in vals:
                self._sync_so_lines()

        else:
            res = super().write(vals)

        return res

    @api.ondelete(at_uninstall=False)
    def _unsync_so_lines(self):
        if self.env.context.get('from_services_and_material'):
            for line in self:
                line._sync_so_quantity(-line.unit_amount, line.so_line)

    def _sync_so_lines(self):
        for line in self:
            if not line.order_id or not line.product_id:
                continue

            policy = line.product_id.expense_policy

            if policy == 'cost':
                so_line = self._create_so_line(
                    qty_delivered=line.unit_amount,
                    description=line.name,
                    policy=policy,
                )
                line.so_line = so_line

            elif policy == 'sales_price':
                so_line = line._get_existing_so_line()

                if so_line:
                    line._sync_so_quantity(line.unit_amount, so_line)
                else:
                    so_line = self._create_so_line(
                        qty_delivered=line.unit_amount,
                        description=line.name,
                        policy=policy,
                    )

                line.so_line = so_line

    def _get_existing_so_line(self):
        return self.order_id.order_line.filtered(lambda line: line.product_id == self.product_id)[:1]

    def _create_so_line(self, qty_delivered, description, policy):
        values = {
            'order_id': self.order_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'product_uom_qty': 0,
            'qty_delivered': qty_delivered,
        }

        if description:
            values['name'] = description

        if policy == 'cost':
            values['price_unit'] = self.product_id.standard_price
        elif policy == 'sales_price':
            values['price_unit'] = self.product_id.list_price

        return self.env['sale.order.line'].create(values)

    def _sync_so_quantity(self, quantity, so_line, from_write=False):
        if not so_line:
            return
        if from_write:
            quantity_diff = quantity - self.unit_amount
        else:
            quantity_diff = quantity
        so_line.qty_delivered += quantity_diff

    def _get_or_create_account_from_so(self, order_id):
        sale_order = self.env['sale.order'].browse(order_id)

        if sale_order.analytic_account_id:
            return sale_order.analytic_account_id

        sale_order.analytic_account_id = self.env['account.analytic.account'].create(
            sale_order._prepare_analytic_account_data(
                plan_id=self.env.ref('sale.analytic_plan_sale_orders')
            )
        )
        return sale_order.analytic_account_id
