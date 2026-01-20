# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    reinvoice_move_id = fields.Many2one(
        string="Invoice",
        comodel_name='account.move',
        readonly=True,
        copy=False,
        help="Invoice created from related SO line",
        index='btree_not_null',
    )
    so_line = fields.Many2one(
        string='Sales Order Item',
        comodel_name='sale.order.line',
        compute='_compute_so_line',
        store=True,
        readonly=False,
        index='btree_not_null',
        domain=lambda self: self._domain_so_line(),
    )
    order_id = fields.Many2one(
        string="Customer Order",
        comodel_name='sale.order',
        compute='_compute_order_id',
        store=True,
        readonly=False,
        index=True,
    )

    def _compute_so_line(self):
        return

    def _domain_so_line(self):
        return Domain('qty_delivered_method', '=', 'analytic')

    def _compute_order_id(self):
        return

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if self.env.context.get('from_services_and_material'):
            lines._sync_so_accounts_and_partners()
            lines._sync_so_lines()
        return lines

    def write(self, vals):
        if self and self.env.context.get('from_services_and_material'):
            order_changed_aals = self.env['account.analytic.line']
            product_changed_aals = self.env['account.analytic.line']

            if vals.get('order_id'):
                order_changed_aals = self.filtered(
                    lambda aal: aal.order_id.id != vals['order_id']
                )

            if vals.get('product_id'):
                product_changed_aals = self.filtered(
                    lambda aal: aal.product_id.id != vals['product_id']
                )

            product_or_order_changed_aals = order_changed_aals | product_changed_aals

            res = super().write(vals)

            # if order changed then we need to reassign accounts and partners
            order_changed_aals._sync_so_accounts_and_partners()

            product_or_order_changed_aals._unsync_so_lines()
            product_or_order_changed_aals._sync_so_lines()
        else:
            res = super().write(vals)
        return res

    def _check_can_write(self, vals):
        if self.filtered(
            lambda aal: aal.reinvoice_move_id and aal.reinvoice_move_id.state != 'cancel'
        ):
            if any(field_name in vals for field_name in self._restricted_fields_when_invoiced()):
                raise UserError(self._get_invoiced_line_write_error())

        if 'unit_amount' in vals and vals['unit_amount'] < 0 and self.so_line:
            raise UserError(self.env._("You cannot set a negative quantity on services."))

        super()._check_can_write(vals)

    def _restricted_fields_when_invoiced(self):
        return ['unit_amount', 'order_id', 'product_id', 'so_line', 'date', 'partner_id']

    def _get_invoiced_line_write_error(self):
        return self.env._("You cannot modify already invoiced services.")

    @api.ondelete(at_uninstall=False)
    def _unlink_so_lines_except_invoiced(self):
        """Cleanup related sale order lines when analytic lines are deleted.

        Analytic lines linked to a posted invoice cannot be removed.

        For other lines, the related sale order line is deleted only if its
        delivery method is manual. Lines originating from timesheets or
        expenses are left unchanged.
        """
        if any(
            line.reinvoice_move_id and line.reinvoice_move_id.state == 'posted' for line in self
        ):
            raise UserError(self._get_invoiced_line_delete_error())
        self._unsync_so_lines()

    def _get_invoiced_line_delete_error(self):
        return self.env._("You cannot remove already invoiced services.")

    def _sync_so_lines(self):
        """Ensure that a corresponding sale order line exists and is synchronized
        with the current analytic line.

        Depending on the product's expense policy:

        - For 'cost' policy:
          A new sale order line with product's cost is always created with delivered quantity
          equal to the analytic line's unit amount.

        - For 'sales_price' policy:
          The method first attempts to find an existing sale order line
          matching the product. If found, its delivered quantity is recomputed.
          Otherwise, a new sale order line is created with product's sales price.

        The analytic line is then linked to the resulting sale order line.
        """
        for line in self:
            if not line.order_id or not line.product_id:
                continue

            so_line = self.env['sale.order.line']
            if line.product_id.expense_policy == 'sales_price':
                so_line = line._get_existing_so_line()
            line.so_line = so_line or line._create_so_line()

    def _get_existing_so_line(self):
        """Retrieve the first matching sale order line from the related order, if any."""
        self.ensure_one()
        return self.order_id.order_line.filtered(
            lambda line: line.product_id == self.product_id
            and line.product_uom_id == self.product_uom_id
            and line._is_reinvoicing_line()
        )[:1]

    def _create_so_line(self):
        """Create a new sale order line corresponding to this analytic line.

        The created line is initialized with delivered quantity based on the
        analytic line amount, unit price derived from the product's expense
        policy, and an optional custom description.

        :rtype: sale.order.line
        :return: The newly created sale order line record.
        """
        self.ensure_one()
        values = {
            'order_id': self.order_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'product_uom_qty': 0,
        }

        if self.product_id.expense_policy == 'cost':
            product = self.product_id.with_company(self.order_id.company_id)
            values['price_unit'] = product.currency_id._convert(
                product.standard_price, self.order_id.currency_id, round=False
            )

        return self.env['sale.order.line'].create(values)

    def _unsync_so_lines(self):
        """Revert synchronization of delivered quantities on related sale order lines.

        If the linked sale order line has an expense policy of `cost` and no
        ordered quantity, it indicates that the line was created solely for
        reinvoicing purposes and can be safely removed.
        If not, the analytic line update will automatically trigger the recomputation
        of the `qty_delivered` field on the linked so lines .
        """
        for line in self.filtered(lambda line: line.so_line):
            if not line.so_line._is_reinvoicing_line():
                continue
            if (
                line.product_id.expense_policy == 'cost'
                and not line.so_line.product_uom_qty
                and line.unit_amount == line.so_line.qty_delivered
            ):
                line.so_line.unlink()

    def _sync_so_accounts_and_partners(self):
        """Synchronize analytic account fields and partner with the related sale order.

        This method ensures that each analytic line is linked to the correct
        analytic account derived from its associated sale order.

        The analytic account is retrieved (or created if necessary) using
        the analytic plan dedicated to sale orders. If that plan no longer
        exists, the project plan is used as a fallback.

        Since analytic plans are stored as dynamic columns on the analytic
        line model, the method determines the effective column name based
        on the plan actually used and assigns the corresponding analytic
        account to that field.
        """
        if not self:
            return

        plan_id = self.env.ref('sale.analytic_plan_sale_orders', raise_if_not_found=False)
        if not plan_id:
            plan_id, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        column_name = plan_id._column_name()

        for line in self:
            line.partner_id = line.order_id.partner_id
            analytic_account = line.order_id._get_or_create_analytic_account(plan_id)
            used_plan_id = analytic_account.plan_id

            effective_column_name = column_name
            if used_plan_id != plan_id:
                effective_column_name = used_plan_id._column_name()

            line[effective_column_name] = analytic_account.id
