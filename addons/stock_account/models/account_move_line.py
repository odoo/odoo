from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    stock_move_id = fields.Many2one('stock.move', index='btree_not_null')
    cogs_move_ids = fields.Many2many(
        "stock.move", string="COGS stock moves",
        help="Inventory moves used to compute COGS values.",
        compute="_compute_cogs_move_ids",
    )

    def _compute_cogs_move_ids(self):
        self.cogs_move_ids = False

    def _set_cogs(self):
        """Re-evaluate the COGS of the originating invoice lines after the value of
        one of their backing stock moves changed, by reusing ``_get_cogs_lines_vals``.
        The delta is written onto the matching existing cogs line in place when its
        period is open; otherwise, its vals are returned so the caller can book them
        (e.g. in a correction entry)."""
        self = self.sudo()  # noqa: PLW0642
        correction_line_vals = []
        lines_by_cogs_origin = self.grouped('cogs_origin_id')
        for cogs_origin, lines in lines_by_cogs_origin.items():
            account_move = cogs_origin.move_id
            if account_move.state != 'posted':
                continue
            account_move = account_move.with_company(account_move.company_id)
            locked = bool(account_move.company_id._get_lock_date_violations(account_move.date, purchase=False))
            vals_list = account_move.with_context(cogs_origin_line_id=cogs_origin.id, cogs_invoice_line_ids=lines.ids)._get_cogs_lines_vals()
            for vals in vals_list:
                cogs_line = lines.filtered(
                    lambda l, vals=vals: l.move_id == account_move
                    and l.account_id.id == vals['account_id']
                    and l.cogs_origin_id.id == vals['cogs_origin_id']
                )
                if not locked and cogs_line:
                    vals['balance'] += cogs_line.balance
                    cogs_line.with_context(check_move_validity=False).write(vals)
                else:
                    product = cogs_line.product_id or self.env['product.product'].browse(vals['product_id'])
                    vals['name'] = f"{account_move.name} - {product.name}"
                    correction_line_vals.append(vals)
        return correction_line_vals

    def _get_cogs_value(self):
        """ Get the COGS price unit in the product's default unit of measure.
        """
        self.ensure_one()

        if not self.product_id or self.product_uom_id.is_zero(self.quantity):
            return self.price_unit

        cogs_qty = self._get_cogs_qty()
        if moves := self.cogs_move_ids:
            price_unit = moves._get_price_unit(include_consigned=True, product=self.product_id)
        else:
            if self.product_id.cost_method in ['standard', 'average']:
                price_unit = self.product_id.standard_price
            else:
                price_unit = self.product_id._get_fifo_value(cogs_qty) / cogs_qty if cogs_qty else 0
        line_quantity_uom = self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
        return abs(price_unit * cogs_qty / line_quantity_uom)

    def _get_cogs_qty(self):
        self.ensure_one()
        return (
            self.product_uom_id._compute_quantity(self.quantity, self.product_id.uom_id)
            * (-1 if self.move_id.move_type == "out_refund" else 1)
        )
