# -*- coding: utf-8 -*-

from odoo import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        """Track purchase order creation."""
        orders = super().create(vals_list)

        for order in orders:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='purchase_order_create',
                    description=f'Purchase order created: {order.name} - {order.partner_id.name}',
                    model_name='purchase.order',
                    res_id=order.id,
                    resource_name=order.name,
                    severity='info',
                    success=True,
                    new_values={
                        'name': order.name,
                        'partner': order.partner_id.name,
                        'amount_total': order.amount_total,
                        'currency': order.currency_id.name,
                        'date_order': str(order.date_order) if order.date_order else None,
                        'origin': order.origin,
                        'state': order.state,
                    }
                )
            except:
                pass

        return orders

    def button_confirm(self):
        """Track purchase order confirmation."""
        # Store info before confirmation
        order_info = [(o.id, o.name, o.partner_id.name, o.amount_total, o.state) for o in self]

        result = super().button_confirm()

        for order_id, order_name, partner_name, amount, old_state in order_info:
            try:
                order = self.browse(order_id)
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='purchase_order_confirm',
                    description=f'Purchase order confirmed: {order_name} - {partner_name} ({amount})',
                    model_name='purchase.order',
                    res_id=order_id,
                    resource_name=order_name,
                    severity='info',
                    success=True,
                    old_values={'state': old_state},
                    new_values={'state': order.state},
                    additional_data={
                        'partner': partner_name,
                        'amount_total': amount,
                    }
                )
            except:
                pass

        return result

    def button_approve(self, force=False):
        """Track purchase order approval."""
        # Store info before approval
        order_info = [(o.id, o.name, o.partner_id.name, o.amount_total, o.state) for o in self]

        result = super().button_approve(force=force)

        for order_id, order_name, partner_name, amount, old_state in order_info:
            try:
                order = self.browse(order_id)
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='purchase_order_approve',
                    description=f'Purchase order approved: {order_name} - {partner_name} ({amount})',
                    model_name='purchase.order',
                    res_id=order_id,
                    resource_name=order_name,
                    severity='warning',  # Higher severity for approvals
                    success=True,
                    old_values={'state': old_state},
                    new_values={'state': order.state},
                    additional_data={
                        'partner': partner_name,
                        'amount_total': amount,
                        'forced': force,
                    }
                )
            except:
                pass

        return result

    def button_cancel(self):
        """Track purchase order cancellation."""
        # Store info before cancellation
        order_info = [(o.id, o.name, o.partner_id.name, o.amount_total, o.state) for o in self]

        result = super().button_cancel()

        for order_id, order_name, partner_name, amount, old_state in order_info:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='purchase_order_cancel',
                    description=f'Purchase order cancelled: {order_name} - {partner_name}',
                    model_name='purchase.order',
                    res_id=order_id,
                    resource_name=order_name,
                    severity='warning',
                    success=True,
                    old_values={'state': old_state},
                    new_values={'state': 'cancel'},
                    additional_data={
                        'partner': partner_name,
                        'amount_total': amount,
                    }
                )
            except:
                pass

        return result

    def button_done(self):
        """Track purchase order completion."""
        # Store info before completion
        order_info = [(o.id, o.name, o.partner_id.name, o.state) for o in self]

        result = super().button_done()

        for order_id, order_name, partner_name, old_state in order_info:
            try:
                self.env['camtel.audit.log'].sudo().create_log(
                    event_type='purchase_order_done',
                    description=f'Purchase order completed: {order_name} - {partner_name}',
                    model_name='purchase.order',
                    res_id=order_id,
                    resource_name=order_name,
                    severity='info',
                    success=True,
                    old_values={'state': old_state},
                    new_values={'state': 'done'},
                    additional_data={'partner': partner_name}
                )
            except:
                pass

        return result

    def write(self, vals):
        """Track important field changes in purchase orders."""
        # Track changes to critical fields
        tracked_fields = ['state', 'partner_id', 'amount_total', 'date_order', 'date_approve']
        old_values_list = []

        if any(field in vals for field in tracked_fields):
            for order in self:
                old_vals = {}
                if 'state' in vals and vals['state'] not in ['purchase', 'done', 'cancel']:
                    # State changes are logged by specific methods, only log other state changes
                    old_vals['state'] = order.state
                if 'partner_id' in vals:
                    old_vals['partner'] = order.partner_id.name
                if 'date_approve' in vals and not order.date_approve:
                    # Track when order gets approved
                    old_vals['date_approve'] = None

                if old_vals:
                    old_values_list.append((order.id, order.name, old_vals))

        result = super().write(vals)

        # Log significant changes (excluding those logged by button methods)
        for order_id, order_name, old_vals in old_values_list:
            try:
                order = self.browse(order_id)
                new_vals = {}

                if 'state' in old_vals:
                    new_vals['state'] = order.state
                if 'partner' in old_vals:
                    new_vals['partner'] = order.partner_id.name
                if 'date_approve' in old_vals:
                    new_vals['date_approve'] = str(order.date_approve) if order.date_approve else None

                if new_vals:
                    self.env['camtel.audit.log'].sudo().create_log(
                        event_type='purchase_order_create',  # Generic modify event
                        description=f'Purchase order modified: {order_name}',
                        model_name='purchase.order',
                        res_id=order_id,
                        resource_name=order_name,
                        old_values=old_vals,
                        new_values=new_vals,
                        severity='info',
                        success=True,
                    )
            except:
                pass

        return result
