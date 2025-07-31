# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

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
    items = fields.Char(string='Items')
    shipmentid = fields.Char(string='Shipment ID')

    @api.model
    def cron_process_shipping_logs(self):
        logs = self.search([
            ('is_synced', '=', False),
            ('status', '=', 'success'),
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
                    })

                # --- Validate eligible pickings ---
                if sale_order:
                    all_pickings = self.env['stock.picking'].search([
                        ('sale_id', '=', sale_order.id),
                        ('state', 'not in', ['done', 'cancel'])
                    ])
                    for pick in all_pickings.filtered(lambda p: p.picking_type_id.picking_process_type == 'pick'):
                        all_packed = all(m.packed for m in pick.move_ids_without_package)
                        if all_packed:
                            pick.write({'current_state': 'pack'})
                            pick.with_context(from_cron=True).button_validate()
                        else:
                            _logger.warning(
                                f"[Shipping Log Cron] Skipping picking {pick.name} because not all lines are packed."
                            )

                # --- Send tracking update ---
                if sale_order:
                    self.env['custom.pack.app.wizard'].send_tracking_update_to_ot_orders(
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
                _logger.error(f"[Shipping Log Cron] Error syncing log {log.id}: {str(e)}")


