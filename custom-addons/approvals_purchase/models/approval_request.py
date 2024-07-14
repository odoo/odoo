# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    purchase_order_count = fields.Integer(compute='_compute_purchase_order_count')

    @api.depends('product_line_ids.purchase_order_line_id')
    def _compute_purchase_order_count(self):
        for request in self:
            purchases = request.product_line_ids.purchase_order_line_id.order_id
            request.purchase_order_count = len(purchases)

    def action_approve(self, approver=None):
        if self.approval_type == 'purchase' and any(not line.product_id for line in self.product_line_ids):
            raise UserError(_("You must select a product for each line of requested products."))
        return super().action_approve(approver)

    def action_cancel(self):
        """ Override to notify Purchase Orders when the Approval Request is cancelled. """
        res = super().action_cancel()
        purchases = self.product_line_ids.purchase_order_line_id.order_id
        for purchase in purchases:
            product_lines = self.product_line_ids.filtered(
                lambda line: line.purchase_order_line_id.order_id.id == purchase.id
            )
            purchase._activity_schedule_with_view(
                'mail.mail_activity_data_warning',
                views_or_xmlid='approvals_purchase.exception_approval_request_canceled',
                user_id=self.env.user.id,
                render_context={
                    'approval_requests': self,
                    'product_lines': product_lines,
                }
            )
        return res

    def action_confirm(self):
        for request in self:
            if request.approval_type == 'purchase' and not request.product_line_ids:
                raise UserError(_("You cannot create an empty purchase request."))
        return super().action_confirm()

    def action_create_purchase_orders(self):
        """ Create and/or modifier Purchase Orders. """
        self.ensure_one()
        self.product_line_ids._check_products_vendor()

        for line in self.product_line_ids:
            seller = line._get_seller_id()
            vendor = seller.partner_id
            po_domain = line._get_purchase_orders_domain(vendor)
            purchase_orders = self.env['purchase.order'].search(po_domain)

            if purchase_orders:
                # Existing RFQ found: check if we must modify an existing
                # purchase order line or create a new one.
                purchase_line = self.env['purchase.order.line'].search([
                    ('order_id', 'in', purchase_orders.ids),
                    ('product_id', '=', line.product_id.id),
                    ('product_uom', '=', line.product_id.uom_po_id.id),
                ], limit=1)
                purchase_order = self.env['purchase.order']
                if purchase_line:
                    # Compatible po line found, only update the quantity.
                    line.purchase_order_line_id = purchase_line.id
                    purchase_line.product_qty += line.po_uom_qty
                    purchase_order = purchase_line.order_id
                else:
                    # No purchase order line found, create one.
                    purchase_order = purchase_orders[0]
                    po_line_vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                        line.product_id,
                        line.quantity,
                        line.product_uom_id,
                        line.company_id,
                        seller,
                        purchase_order,
                    )
                    new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                    line.purchase_order_line_id = new_po_line.id
                    purchase_order.order_line = [(4, new_po_line.id)]

                # Add the request name on the purchase order `origin` field.
                new_origin = set([self.name])
                if purchase_order.origin:
                    missing_origin = new_origin - set(purchase_order.origin.split(', '))
                    if missing_origin:
                        purchase_order.write({'origin': purchase_order.origin + ', ' + ', '.join(missing_origin)})
                else:
                    purchase_order.write({'origin': ', '.join(new_origin)})
            else:
                # No RFQ found: create a new one.
                po_vals = line._get_purchase_order_values(vendor)
                new_purchase_order = self.env['purchase.order'].create(po_vals)
                po_line_vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                    line.product_id,
                    line.quantity,
                    line.product_uom_id,
                    line.company_id,
                    seller,
                    new_purchase_order,
                )
                new_po_line = self.env['purchase.order.line'].create(po_line_vals)
                line.purchase_order_line_id = new_po_line.id
                new_purchase_order.order_line = [(4, new_po_line.id)]

    def action_open_purchase_orders(self):
        """ Return the list of purchase orders the approval request created or
        affected in quantity. """
        self.ensure_one()
        purchase_ids = self.product_line_ids.purchase_order_line_id.order_id.ids
        domain = [('id', 'in', purchase_ids)]
        action = {
            'name': _('Purchase Orders'),
            'view_type': 'tree',
            'view_mode': 'list,form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'domain': domain,
        }
        return action
