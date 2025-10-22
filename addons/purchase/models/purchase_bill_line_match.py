# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.tools import SQL
from odoo.exceptions import UserError


class PurchaseBillLineMatch(models.Model):
    _name = 'purchase.bill.line.match'
    _description = "Purchase Line and Vendor Bill line matching view"
    _auto = False
    _order = 'product_id, aml_id, pol_id'

    pol_id = fields.Many2one(comodel_name='purchase.order.line', readonly=True)
    aml_id = fields.Many2one(comodel_name='account.move.line', readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', readonly=True)
    partner_id = fields.Many2one(comodel_name='res.partner', readonly=True)
    product_id = fields.Many2one(comodel_name='product.product', readonly=True)
    line_qty = fields.Float(readonly=True)
    line_uom_id = fields.Many2one(comodel_name='uom.uom', readonly=True)
    qty_invoiced = fields.Float(readonly=True)
    qty_to_invoice = fields.Float('Qty to invoice', readonly=True)
    purchase_order_id = fields.Many2one(comodel_name='purchase.order', readonly=True)
    account_move_id = fields.Many2one(comodel_name='account.move', readonly=True)
    line_amount_untaxed = fields.Monetary(readonly=True)
    currency_id = fields.Many2one(comodel_name='res.currency', readonly=True)
    state = fields.Char(readonly=True)

    product_uom_id = fields.Many2one(comodel_name='uom.uom', related='product_id.uom_id')
    product_uom_qty = fields.Float(compute='_compute_product_uom_qty', inverse='_inverse_product_uom_qty', readonly=False)
    product_uom_price = fields.Float(compute='_compute_product_uom_price', inverse='_inverse_product_uom_price', readonly=False)
    billed_amount_untaxed = fields.Monetary(compute='_compute_amount_untaxed_fields', currency_field='currency_id')
    purchase_amount_untaxed = fields.Monetary(compute='_compute_amount_untaxed_fields', currency_field='currency_id')
    reference = fields.Char(compute='_compute_reference')

    @api.onchange('product_uom_price')
    def _inverse_product_uom_price(self):
        for line in self:
            if line.aml_id:
                line.aml_id.price_unit = line.product_uom_price
            else:
                line.pol_id.price_unit = line.product_uom_price

    @api.onchange('product_uom_qty')
    def _inverse_product_uom_qty(self):
        for line in self:
            if line.aml_id:
                line.aml_id.quantity = line.product_uom_qty
            else:
                # on POL, setting product_qty will recompute price_unit to have the old value
                # this prevents the price to revert by saving the previous price and re-setting them again
                previous_price_unit = line.pol_id.price_unit
                line.pol_id.product_qty = line.product_uom_qty
                line.pol_id.price_unit = previous_price_unit

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

    @api.depends('aml_id.price_unit', 'pol_id.price_unit')
    def _compute_product_uom_price(self):
        for line in self:
            line.product_uom_price = line.aml_id.price_unit if line.aml_id else line.pol_id.price_unit

    @api.model
    def _select_po_line(self):
        return SQL("""
            SELECT pol.id,
                   pol.id as pol_id,
                   NULL as aml_id,
                   pol.company_id as company_id,
                   pol.partner_id as partner_id,
                   pol.product_id as product_id,
                   pol.product_qty as line_qty,
                   pol.product_uom_id as line_uom_id,
                   pol.qty_invoiced as qty_invoiced,
                   pol.qty_to_invoice as qty_to_invoice,
                   po.id as purchase_order_id,
                   NULL as account_move_id,
                   pol.price_subtotal as line_amount_untaxed,
                   po.currency_id as currency_id,
                   po.state as state
              FROM purchase_order_line pol
         LEFT JOIN purchase_order po ON pol.order_id = po.id
             WHERE po.state = 'purchase'
               AND (pol.product_qty > pol.qty_invoiced OR pol.qty_to_invoice != 0)
                OR ((pol.display_type = '' OR pol.display_type IS NULL) AND pol.is_downpayment AND pol.qty_invoiced > 0)
        """)

    @api.model
    def _select_am_line(self):
        return SQL("""
            SELECT -aml.id,
                   NULL as pol_id,
                   aml.id as aml_id,
                   aml.company_id as company_id,
                   am.partner_id as partner_id,
                   aml.product_id as product_id,
                   aml.quantity as line_qty,
                   aml.product_uom_id as line_uom_id,
                   NULL as qty_invoiced,
                   NULL as qty_to_invoice,
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

    @api.model
    def _action_create_bill_from_po_lines(self, partner, po_lines):
        """ Create a new vendor bill with the selected PO lines and returns an action to open it """
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
        })
        bill._add_purchase_order_lines(po_lines)
        return bill._get_records_action()

    def action_match_lines(self):
        if not self.pol_id:  # we need POL(s) to either match or create bill
            raise UserError(_("You must select at least one Purchase Order line to match or create bill."))
        if not self.aml_id:  # select POL(s) without AML -> create a draft bill with the POL(s)
            return self._action_create_bill_from_po_lines(self.partner_id, self.pol_id)

        pol_by_product = self.pol_id.grouped('product_id')
        aml_by_product = self.aml_id.grouped('product_id')
        residual_purchase_order_lines = self.pol_id
        residual_account_move_lines = self.aml_id

        # Match all matchable POL-AML lines and remove them from the residual group
        for product, po_line in pol_by_product.items():
            po_line = po_line[0]  # in case of multiple POL with same product, only match the first one
            matching_bill_lines = aml_by_product.get(product)
            if matching_bill_lines:
                matching_bill_lines.purchase_line_id = po_line.id
                residual_purchase_order_lines -= po_line
                residual_account_move_lines -= matching_bill_lines

        if len(residual_bill := self.aml_id.move_id) == 1:
            # Delete all unmatched selected AML
            if residual_account_move_lines:
                residual_account_move_lines.unlink()

            # Add all remaining POL to the residual bill
            residual_bill._add_purchase_order_lines(residual_purchase_order_lines)

    def action_add_to_po(self):
        if not self or not self.aml_id:
            raise UserError(_("Select Vendor Bill lines to add to a Purchase Order"))
        partner = self.mapped("partner_id.commercial_partner_id")
        if len(partner) > 1:
            raise UserError(_("Please select bill lines with the same vendor."))
        context = {
            'default_partner_id': partner.id,
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
