# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, Command


class PurchaseRequisitionCreateAlternative(models.TransientModel):
    _name = 'purchase.requisition.create.alternative'
    _description = 'Wizard to preset values for alternative PO'

    origin_po_id = fields.Many2one(
        'purchase.order', help="The original PO that this alternative PO is being created for."
    )
    partner_ids = fields.Many2many(
        'res.partner', string='Vendor', required=True,
        help="Choose a vendor for alternative PO")
    purchase_warn_msg = fields.Text(
        'Warning Messages',
        compute="_compute_purchase_warn_msg",
        groups="purchase.group_warning_purchase")
    copy_products = fields.Boolean(
        "Copy Products", default=True,
        help="If this is checked, the product quantities of the original PO will be copied")

    @api.depends('partner_ids', 'copy_products')
    def _compute_purchase_warn_msg(self):
        self.purchase_warn_msg = ''
        # follows partner warning logic from PurchaseOrder
        if not self.env.user.has_group('purchase.group_warning_purchase'):
            return
        for partner in self.partner_ids:
            # If partner has no warning, check its company
            if not partner.purchase_warn_msg:
                partner = partner.parent_id
            if partner and partner.purchase_warn_msg:
                self.purchase_warn_msg = _("Warning for %(partner)s:\n%(warning_message)s\n", partner=partner.name, warning_message=partner.purchase_warn_msg)
            if self.copy_products and self.origin_po_id.order_line:
                for line in self.origin_po_id.order_line:
                    if line.product_id.purchase_line_warn_msg:
                        self.purchase_warn_msg += _("Warning for %(product)s:\n%(warning_message)s\n", product=line.product_id.name, warning_message=line.product_id.purchase_line_warn_msg)

    def action_create_alternative(self):
        vals = self._get_alternative_values()
        alt_purchase_orders = self.env['purchase.order'].with_context(origin_po_id=self.origin_po_id.id, default_requisition_id=False).create(vals)
        alt_purchase_orders.order_line._compute_tax_id()
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'list,kanban,form,calendar',
            'res_model': 'purchase.order',
        }
        if len(alt_purchase_orders) == 1:
            action['res_id'] = alt_purchase_orders.id
            action['view_mode'] = 'form'
        else:
            action['name'] = _('Alternative Purchase Orders')
            action['domain'] = [('id', 'in', alt_purchase_orders.ids)]
        return action

    def _get_alternative_values(self):
        vals = []
        origin_po = self.origin_po_id
        partner_product_tmpl_dict = {}
        if self.copy_products and origin_po:
            supplierinfo = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', 'in', origin_po.order_line.product_id.product_tmpl_id.ids),
                ('partner_id', 'in', self.partner_ids.ids),
                '|', ('product_code', '!=', False), ('product_name', '!=', False)
            ])
            # Build dict: {partner: set(product_tmpl_ids)}
            for info in supplierinfo:
                partner_product_tmpl_dict.setdefault(info.partner_id.id, set()).add(info.product_tmpl_id.id)

        for partner in self.partner_ids:
            product_tmpl_ids_with_description = partner_product_tmpl_dict.get(partner.id, set())
            val = {
                'date_order': origin_po.date_order,
                'partner_id': partner.id,
                'user_id': origin_po.user_id.id,
                'dest_address_id': origin_po.dest_address_id.id,
                'origin': origin_po.origin,
                'currency_id': partner.property_purchase_currency_id.id or self.env.company.currency_id.id,
                'payment_term_id': partner.property_supplier_payment_term_id.id,
            }
            if self.copy_products and origin_po:
                val['order_line'] = [Command.create(self._get_alternative_line_value(line, product_tmpl_ids_with_description)) for line in origin_po.order_line]
            vals.append(val)

        return vals

    @api.model
    def _get_alternative_line_value(self, order_line, product_tmpl_ids_with_description):
        has_product_description = order_line.product_id.product_tmpl_id.id in product_tmpl_ids_with_description
        return {
            'product_id': order_line.product_id.id,
            'product_qty': order_line.product_qty,
            'product_uom_id': order_line.product_uom_id.id,
            'display_type': order_line.display_type,
            'analytic_distribution': order_line.analytic_distribution,
            **({'name': order_line.name} if order_line.display_type in ('line_section', 'line_subsection', 'line_note') or not has_product_description else {}),
        }
