# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _

from odoo.tools import format_list, SQL
from odoo.exceptions import UserError


class PurchaseBillLineMatch(models.Model):
    _description = "Purchase Line and Vendor Bill line matching view"
    _auto = False
    _order = 'product_id, aml_id, pol_id'

    pol_id = fields.Many2one(comodel_name='purchase.order.line')
    aml_id = fields.Many2one(comodel_name='account.move.line')
    company_id = fields.Many2one(comodel_name='res.company')
    partner_id = fields.Many2one(comodel_name='res.partner')
    product_id = fields.Many2one(comodel_name='product.product')
    line_qty = fields.Float()
    line_uom_id = fields.Many2one(comodel_name='uom.uom')
    qty_invoiced = fields.Float()
    purchase_order_id = fields.Many2one(comodel_name='purchase.order')
    account_move_id = fields.Many2one(comodel_name='account.move')
    line_amount_untaxed = fields.Monetary()
    currency_id = fields.Many2one(comodel_name='res.currency')
    state = fields.Char()

    product_uom_id = fields.Many2one(comodel_name='uom.uom', related='product_id.uom_id')
    product_uom_qty = fields.Float(compute='_compute_product_uom_qty')
    billed_amount_untaxed = fields.Monetary(compute='_compute_amount_untaxed_fields', currency_field='currency_id')
    purchase_amount_untaxed = fields.Monetary(compute='_compute_amount_untaxed_fields', currency_field='currency_id')
    reference = fields.Char(compute='_compute_reference')

    def _compute_amount_untaxed_fields(self):
        for line in self:
            line.billed_amount_untaxed = line.line_amount_untaxed if line.account_move_id else False
            line.purchase_amount_untaxed = line.line_amount_untaxed if line.purchase_order_id else False

    def _compute_reference(self):
        for line in self:
            line.reference = line.purchase_order_id.display_name or line.account_move_id.display_name

    def _compute_display_name(self):
        for line in self:
            line.display_name = line.product_id.display_name or line.aml_id.name or line.pol_id.name

    def _compute_product_uom_qty(self):
        for line in self:
            line.product_uom_qty = line.line_uom_id._compute_quantity(line.line_qty, line.product_uom_id)

    def _select_po_line(self):
        return SQL("""
            SELECT pol.id,
                   pol.id as pol_id,
                   NULL as aml_id,
                   pol.company_id as company_id,
                   pol.partner_id as partner_id,
                   pol.product_id as product_id,
                   pol.product_qty as line_qty,
                   pol.product_uom as line_uom_id,
                   pol.qty_invoiced as qty_invoiced,
                   po.id as purchase_order_id,
                   NULL as account_move_id,
                   pol.price_subtotal as line_amount_untaxed,
                   pol.currency_id as currency_id,
                   po.state as state
              FROM purchase_order_line pol
         LEFT JOIN purchase_order po ON pol.order_id = po.id
             WHERE pol.state in ('purchase', 'done')
               AND pol.product_qty > pol.qty_invoiced
                OR ((pol.display_type = '' OR pol.display_type IS NULL) AND pol.is_downpayment AND pol.qty_invoiced > 0)
        """)

    def _select_am_line(self):
        return SQL("""
            SELECT -aml.id,
                   NULL as pol_id,
                   aml.id as aml_id,
                   aml.company_id as company_id,
                   aml.partner_id as partner_id,
                   aml.product_id as product_id,
                   aml.quantity as line_qty,
                   aml.product_uom_id as line_uom_id,
                   NULL as qty_invoiced,
                   NULL as purchase_order_id,
                   am.id as account_move_id,
                   aml.amount_currency as line_amount_untaxed,
                   aml.currency_id as currency_id,
                   aml.parent_state as state
              FROM account_move_line aml
         LEFT JOIN account_move am on aml.move_id = am.id
             WHERE aml.display_type = 'product'
               AND am.move_type in ('in_invoice', 'in_refund')
               AND aml.parent_state in ('draft', 'posted')
               AND aml.purchase_line_id IS NULL
        """)

    @property
    def _table_query(self):
        return SQL("%s UNION ALL %s", self._select_po_line(), self._select_am_line())

    def action_open_line(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move' if self.account_move_id else 'purchase.order',
            'view_mode': 'form',
            'res_id': self.account_move_id.id if self.account_move_id else self.purchase_order_id.id,
        }

    def action_match_lines(self):
        if not self.pol_id or not self.aml_id:
            raise UserError(_("You must select at least one Purchase Order line and one Vendor Bill line to match them."))

        matches_found = 0
        problem_products = self.env['product.product']
        pol_by_product = self.pol_id.grouped('product_id')
        aml_by_product = self.aml_id.grouped('product_id')

        for product, po_lines in pol_by_product.items():
            if len(po_lines) > 1:
                problem_products += product
                continue
            matching_bill_lines = aml_by_product.get(product)
            if matching_bill_lines:
                matching_bill_lines.purchase_line_id = po_lines.id
                matches_found += 1
        if problem_products:
            message = _("More than 1 Purchase Order line has the same product: %(products)s",
                        products=format_list(self.env, problem_products.mapped('display_name')))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Unable to match"),
                    'type': "warning",
                    'message': message,
                    'next': {
                        'type': 'ir.actions.act_window_close',
                    },
                }
            }
        if not matches_found:
            raise UserError(_("No matching products found."))

    def action_add_to_po(self):
        if not self or not self.aml_id:
            raise UserError(_("Select Vendor Bill lines to add to a Purchase Order"))
        context = {
            'default_partner_id': self.partner_id.id,
            'dialog_size': 'medium',
            'has_products': bool(self.aml_id.product_id),
        }
        if len(self.purchase_order_id) > 1:
            raise UserError(_("Vendor Bill lines can only be added to one Purchase Order."))
        elif self.purchase_order_id:
            context['default_purchase_order_id'] = self.purchase_order_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': _("Add to Purchase Order"),
            'res_model': 'bill.to.po.wizard',
            'target': 'new',
            'views': [(self.env.ref('purchase.bill_to_po_wizard_form').id, 'form')],
            'context': context,
        }
