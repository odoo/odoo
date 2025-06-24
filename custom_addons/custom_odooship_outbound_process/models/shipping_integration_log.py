# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ShippingIntegrationLog(models.Model):
    _name = 'shipping.integration.log'
    _description = 'Shipping Integration Log'
    _order = 'create_date desc'

    picking_id = fields.Many2one('stock.picking', string='Picking', ondelete='set null')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', ondelete='set null')
    order_number = fields.Char('Order Number', index=True)
    payload_json = fields.Text(string='Payload JSON')
    response_json = fields.Text(string='Response JSON')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skip', 'Skip (Duplicate)')
    ], default='pending', string='Status')
    error_message = fields.Text('Error')
    consignment_number = fields.Char('Consignment Number')
    tracking_url = fields.Char('Tracking URL')
    label_url = fields.Char('Label URL')
    attempted_at = fields.Datetime('Attempted At', default=fields.Datetime.now)
    carrier = fields.Char('Carrier')
    retry_count = fields.Integer('Retry Count', default=0)
    is_synced = fields.Boolean('Is Synced With Order', default=False)
    origin = fields.Char(string='Origin')

    @api.model
    def cron_process_shipping_logs(self):
        logs = self.search([
            # ('status', '=', 'success'),
            ('is_synced', '=', False),
        ])
        for log in logs:
            picking = log.picking_id
            sale_order = log.sale_order_id
            try:
                # --- Update sale order ---
                if sale_order:
                    sale_order.write({
                        'consignment_number': log.consignment_number,
                        'tracking_url': log.tracking_url,
                        'carrier': log.carrier,
                        'pick_status': "packed",
                        'status': log.label_url,
                        'is_released': 'released'
                        # 'delivery_status': "partial", # Uncomment if field exists
                    })
                # --- Validate ALL pickings for the sale order ---
                if sale_order:
                    all_pickings = self.env['stock.picking'].search([
                        ('sale_id', '=', sale_order.id),
                        ('state', 'not in', ['done', 'cancel'])
                    ])
                    pickings = all_pickings.filtered(
                        lambda p: p.state not in ('cancel', 'done')
                                  and getattr(p.picking_type_id, 'picking_process_type', 'pick') == 'pick'
                    )
                    for pick in pickings:
                        pick.button_validate()
                # --- Send tracking update if required ---
                sale_order and sale_order.env['custom.pack.app.wizard'].send_tracking_update_to_ot_orders(
                    so_number=sale_order.name,
                    con_id=log.consignment_number,
                    carrier=log.carrier,
                    origin=sale_order.origin or "N/A",
                    tenant_code=sale_order.tenant_code_id.name if sale_order.tenant_code_id else "N/A"
                )
                log.is_synced = True
            except Exception as e:
                log.error_message = str(e)
                log.retry_count += 1
                # log.status = 'failed'

