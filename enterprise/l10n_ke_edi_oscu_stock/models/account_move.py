# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ke_oscu_show_create_purchase_order_button = fields.Boolean(
        compute='_compute_l10n_ke_oscu_show_create_purchase_order_button'
    )
    l10n_ke_oscu_show_create_sale_order_button = fields.Boolean(
        compute='_compute_l10n_ke_oscu_show_create_sale_order_button'
    )

    @api.depends('line_ids.purchase_line_id', 'state', 'move_type', 'l10n_ke_oscu_invoice_number')
    def _compute_l10n_ke_oscu_show_create_purchase_order_button(self):
        for move in self:
            move.l10n_ke_oscu_show_create_purchase_order_button = (
                move.country_code == 'KE'
                and not move.line_ids.purchase_line_id
                and move.state == 'draft'
                and move.is_purchase_document(include_receipts=True)
                and not move.l10n_ke_oscu_invoice_number
            )

    @api.depends('line_ids.sale_line_ids', 'state', 'move_type', 'l10n_ke_oscu_invoice_number')
    def _compute_l10n_ke_oscu_show_create_sale_order_button(self):
        for move in self:
            move.l10n_ke_oscu_show_create_sale_order_button = (
                move.country_code == 'KE'
                and not move.line_ids.sale_line_ids
                and move.state == 'draft'
                and move.is_sale_document(include_receipts=True)
                and not move.l10n_ke_oscu_invoice_number
            )

    # === Overrides === #

    @api.depends(
        'invoice_line_ids.purchase_line_id',
        'invoice_line_ids.purchase_line_id.qty_received',
        'invoice_line_ids.sale_line_ids.qty_delivered',
        'move_type',
    )
    def _compute_l10n_ke_validation_message(self):
        # EXTENDS 'l10n_ke_edi_oscu'
        super()._compute_l10n_ke_validation_message()

        # Invoices which have at least one storable product should not be sent to eTIMS until
        # the products have been delivered or received.
        for move in self.filtered(lambda m: m.company_id.l10n_ke_oscu_is_active and any(l.product_id.is_storable for l in m.invoice_line_ids)):
            if move.is_purchase_document() and (
                not (purchase_lines_to_check := move.invoice_line_ids.mapped('purchase_line_id'))
                or any(
                    pl.qty_received != pl.qty_invoiced and pl.product_id.is_storable
                    for pl in purchase_lines_to_check
                )
            ):
                message = move.l10n_ke_validation_message or {}
                message['waiting_receipt'] = {
                    'message': _("Received quantities and vendor bill do not correspond"),
                    'blocking': True,
                }
                move.l10n_ke_validation_message = message

            if move.is_sale_document() and (
                not (sale_lines_to_check := move.invoice_line_ids.mapped('sale_line_ids'))
                or any(
                    sl.qty_delivered != sl.qty_invoiced and sl.product_id.is_storable
                    for sl in sale_lines_to_check
                )
            ):
                message = move.l10n_ke_validation_message or {}
                message['waiting_picking'] = {
                    'message': _("Sent quantities and customer invoice do not correspond"),
                    'blocking': True,
                }
                move.l10n_ke_validation_message = message

    def _l10n_ke_oscu_send_customer_invoice(self):
        # EXTENDS 'l10n_ke_edi_oscu'
        content, error = super()._l10n_ke_oscu_send_customer_invoice()
        if not error:
            self.env.ref('l10n_ke_edi_oscu_stock.ir_cron_send_stock_moves')._trigger()
        return content, error

    def action_l10n_ke_oscu_confirm_vendor_bill(self):
        # EXTENDS 'l10n_ke_edi_oscu'
        super().action_l10n_ke_oscu_confirm_vendor_bill()
        if any(move.l10n_ke_oscu_invoice_number for move in self):
            self.env.ref('l10n_ke_edi_oscu_stock.ir_cron_send_stock_moves')._trigger()

    # === Actions === #

    def action_l10n_ke_create_purchase_order(self):
        self.ensure_one()
        if self.invoice_line_ids.purchase_line_id:
            raise UserError(_("A purchase order already exists for this vendor bill."))
        lines = self.invoice_line_ids
        vals = []
        for line in lines:
            if line.display_type == 'product' and (not line.product_id or not line.product_uom_id):
                raise UserError(_("Please make sure that all the lines have a product and a Unit of Measure set."))
            vals.append(Command.create({
                'product_id': line.product_id.id,
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'invoice_lines': line.ids,
                'date_planned': fields.Date.context_today(self),
                'taxes_id': line.tax_ids.ids,
                'display_type': line.display_type if line.display_type in ['line_section', 'line_note'] else False,
            }))

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': vals,
            'company_id': self.company_id.id,
        })
        action = {
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': po.id,
        }
        return action

    def action_l10n_ke_create_sale_order(self):
        self.ensure_one()
        if self.invoice_line_ids.mapped('sale_line_ids'):
            raise UserError(_("A sale order already exists for this invoice."))
        lines = self.invoice_line_ids
        vals = []
        for line in lines:
            if line.display_type == 'product' and (not line.product_id or not line.product_uom_id):
                raise UserError(_("Please make sure that all the lines have a product and a Unit of Measure set."))
            vals.append(Command.create({
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'invoice_lines': line.ids,
                'tax_id': line.tax_ids.ids,
                'display_type': line.display_type if line.display_type in ['line_section', 'line_note'] else False,
            }))

        so = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': vals,
            'company_id': self.company_id.id,
        })
        action = {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': so.id,
        }
        return action


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_id = fields.Many2one(compute='_compute_product_id', store=True, readonly=False, precompute=True)

    @api.depends('purchase_line_id')
    def _compute_product_id(self):
        """ Quality-of-life: When linking an imported vendor bill to a purchase order,
            automatically set the product on the vendor bill (if it is not yet set) to the
            product already on the purchase order.
            This is because often, the product will not be recognized when importing a
            vendor bill.
        """
        for line in self.filtered(lambda l: not l.product_id and l.purchase_line_id.product_id):
            line.product_id = line.purchase_line_id.product_id.id
