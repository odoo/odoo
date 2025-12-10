# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Sha6erShipment(models.Model):
    _name = 'sha6er.shipment'
    _description = 'Sha6er Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Shipment Reference', required=True, default=lambda self: _('New'), readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True, ondelete='cascade')
    order_id = fields.Many2one('sale.order', related='picking_id.sale_id', store=True, readonly=True)
    
    # Sha6er API fields
    sha6er_shipment_id = fields.Char(string='Sha6er Shipment ID', readonly=True)
    sha6er_tracking_number = fields.Char(string='Tracking Number', readonly=True)
    sha6er_status = fields.Selection([
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('assigned', 'Courier Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ], string='Sha6er Status', default='pending', tracking=True)
    
    # Delivery details
    courier_id = fields.Char(string='Courier ID')
    courier_name = fields.Char(string='Courier Name')
    pickup_date = fields.Datetime(string='Pickup Date')
    delivery_date = fields.Datetime(string='Delivery Date')
    
    # Proofs
    signature_image = fields.Binary(string='Signature')
    photo_proof = fields.Binary(string='Photo Proof')
    otp_verified = fields.Boolean(string='OTP Verified', default=False)
    otp_code = fields.Char(string='OTP Code', readonly=True)
    
    # API Configuration
    sha6er_api_url = fields.Char(string='Sha6er API URL', default='https://api.sha6er.com/v1', readonly=True)
    sha6er_api_key = fields.Char(string='Sha6er API Key', related='company_id.sha6er_api_key', readonly=True)
    company_id = fields.Many2one('res.company', related='picking_id.company_id', store=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('sha6er.shipment') or _('New')
        return super().create(vals)
    
    def action_create_shipment(self):
        """Create shipment in Sha6er"""
        for shipment in self:
            if shipment.sha6er_shipment_id:
                raise UserError(_('Shipment already created in Sha6er.'))
            
            # Prepare shipment data
            shipment_data = self._prepare_shipment_data()
            
            # Call Sha6er API
            response = self._call_sha6er_api('create_shipment', shipment_data)
            
            if response and response.get('success'):
                shipment.write({
                    'sha6er_shipment_id': response.get('shipment_id'),
                    'sha6er_tracking_number': response.get('tracking_number'),
                    'sha6er_status': 'accepted',
                })
            else:
                raise UserError(_('Failed to create shipment in Sha6er: %s') % response.get('error', 'Unknown error'))
    
    def _prepare_shipment_data(self):
        """Prepare data for Sha6er API"""
        picking = self.picking_id
        partner = picking.partner_id
        
        return {
            'pickup_address': {
                'name': picking.picking_type_id.warehouse_id.partner_id.name or '',
                'street': picking.picking_type_id.warehouse_id.partner_id.street or '',
                'city': picking.picking_type_id.warehouse_id.partner_id.city or '',
                'phone': picking.picking_type_id.warehouse_id.partner_id.phone or '',
            },
            'delivery_address': {
                'name': partner.name,
                'street': partner.street or '',
                'city': partner.city or '',
                'phone': partner.phone or '',
            },
            'weight': sum(picking.move_ids.mapped('product_id.weight')) or 1.0,
            'reference': picking.name,
            'order_id': picking.sale_id.name if picking.sale_id else '',
        }
    
    def _call_sha6er_api(self, endpoint, data):
        """Call Sha6er API"""
        api_url = self.sha6er_api_url or 'https://api.sha6er.com/v1'
        api_key = self.sha6er_api_key
        
        if not api_key:
            raise UserError(_('Sha6er API Key not configured.'))
        
        try:
            url = f"{api_url}/{endpoint}"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Sha6er API error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def action_update_status(self):
        """Update shipment status from Sha6er"""
        for shipment in self:
            if not shipment.sha6er_shipment_id:
                continue
            
            response = self._call_sha6er_api(f'tracking/{shipment.sha6er_shipment_id}', {})
            
            if response and response.get('success'):
                status_mapping = {
                    'accepted': 'accepted',
                    'assigned': 'assigned',
                    'picked_up': 'picked_up',
                    'in_transit': 'in_transit',
                    'delivered': 'delivered',
                    'failed': 'failed',
                }
                
                sha6er_status = response.get('status')
                if sha6er_status in status_mapping:
                    shipment.write({
                        'sha6er_status': status_mapping[sha6er_status],
                        'courier_id': response.get('courier_id'),
                        'courier_name': response.get('courier_name'),
                        'pickup_date': response.get('pickup_date'),
                        'delivery_date': response.get('delivery_date'),
                    })
                    
                    # Update picking status
                    if sha6er_status == 'delivered':
                        shipment.picking_id.write({'state': 'done'})
                        if shipment.order_id:
                            shipment.order_id.write({'state': 'sale'})
    
    @api.model
    def cron_update_shipments(self):
        """Cron job to update shipment statuses"""
        shipments = self.search([
            ('sha6er_status', 'not in', ['delivered', 'failed']),
            ('sha6er_shipment_id', '!=', False),
        ])
        for shipment in shipments:
            try:
                shipment.action_update_status()
            except Exception as e:
                _logger.error(f"Error updating shipment {shipment.name}: {str(e)}")


class ResCompany(models.Model):
    _inherit = 'res.company'

    sha6er_api_key = fields.Char(string='Sha6er API Key', help='API key for Sha6er delivery service')
    sha6er_api_url = fields.Char(string='Sha6er API URL', default='https://api.sha6er.com/v1')

