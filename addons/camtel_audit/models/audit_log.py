# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CamtelAuditLog(models.Model):
    _name = 'camtel.audit.log'
    _description = 'CAMTEL Audit Log'
    _order = 'create_date desc'
    _rec_name = 'event_type'

    # Event Information
    event_type = fields.Selection([
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('login_failed', 'Failed Login Attempt'),
        ('stock_picking_create', 'Stock Picking Created'),
        ('stock_picking_validate', 'Stock Picking Validated'),
        ('stock_picking_cancel', 'Stock Picking Cancelled'),
        ('stock_move_create', 'Stock Move Created'),
        ('stock_move_done', 'Stock Move Completed'),
        ('stock_inventory_create', 'Inventory Adjustment Created'),
        ('stock_inventory_validate', 'Inventory Adjustment Validated'),
        ('purchase_order_create', 'Purchase Order Created'),
        ('purchase_order_confirm', 'Purchase Order Confirmed'),
        ('purchase_order_approve', 'Purchase Order Approved'),
        ('purchase_order_cancel', 'Purchase Order Cancelled'),
        ('purchase_order_done', 'Purchase Order Done'),
        ('user_create', 'User Created'),
        ('user_modify', 'User Modified'),
        ('user_deactivate', 'User Deactivated'),
        ('group_modify', 'User Groups Modified'),
        ('access_rights_modify', 'Access Rights Modified'),
        ('permission_modify', 'Permissions Modified'),
        ('other', 'Other Event'),
    ], string='Event Type', required=True, index=True)

    event_category = fields.Selection([
        ('authentication', 'Authentication'),
        ('inventory', 'Inventory'),
        ('purchase', 'Purchase'),
        ('security', 'Security & Permissions'),
        ('system', 'System'),
    ], string='Category', compute='_compute_event_category', store=True, index=True)

    # User Information
    user_id = fields.Many2one('res.users', string='User', required=True, index=True, ondelete='restrict')
    user_login = fields.Char(string='User Login', related='user_id.login', store=True)
    user_ip = fields.Char(string='IP Address')

    # Resource Information
    model_name = fields.Char(string='Model', index=True)
    model_id = fields.Many2one('ir.model', string='Model Reference', ondelete='set null')
    res_id = fields.Integer(string='Resource ID', index=True)
    resource_name = fields.Char(string='Resource Name')

    # Event Details
    description = fields.Text(string='Description', required=True)
    old_values = fields.Text(string='Old Values (JSON)')
    new_values = fields.Text(string='New Values (JSON)')
    additional_data = fields.Text(string='Additional Data (JSON)')

    # Metadata
    create_date = fields.Datetime(string='Event Date', required=True, index=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Status/Severity
    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ], string='Severity', default='info', index=True)

    success = fields.Boolean(string='Success', default=True)
    error_message = fields.Text(string='Error Message')

    @api.depends('event_type')
    def _compute_event_category(self):
        """Automatically categorize events based on event type."""
        category_mapping = {
            'login': 'authentication',
            'logout': 'authentication',
            'login_failed': 'authentication',
            'stock_picking_create': 'inventory',
            'stock_picking_validate': 'inventory',
            'stock_picking_cancel': 'inventory',
            'stock_move_create': 'inventory',
            'stock_move_done': 'inventory',
            'stock_inventory_create': 'inventory',
            'stock_inventory_validate': 'inventory',
            'purchase_order_create': 'purchase',
            'purchase_order_confirm': 'purchase',
            'purchase_order_approve': 'purchase',
            'purchase_order_cancel': 'purchase',
            'purchase_order_done': 'purchase',
            'user_create': 'security',
            'user_modify': 'security',
            'user_deactivate': 'security',
            'group_modify': 'security',
            'access_rights_modify': 'security',
            'permission_modify': 'security',
            'other': 'system',
        }
        for record in self:
            record.event_category = category_mapping.get(record.event_type, 'system')

    @api.model
    def create_log(self, event_type, description, model_name=None, res_id=None,
                   resource_name=None, old_values=None, new_values=None,
                   additional_data=None, severity='info', success=True,
                   error_message=None, user_id=None):
        """
        Helper method to create audit log entries.

        Args:
            event_type: Type of event (must match selection values)
            description: Human-readable description of the event
            model_name: Technical name of the model (e.g., 'stock.picking')
            res_id: ID of the affected record
            resource_name: Display name of the affected record
            old_values: Dictionary of old values (will be converted to JSON)
            new_values: Dictionary of new values (will be converted to JSON)
            additional_data: Additional data dictionary (will be converted to JSON)
            severity: Severity level ('info', 'warning', 'critical')
            success: Whether the operation was successful
            error_message: Error message if applicable
            user_id: User ID (defaults to current user)
        """
        import json

        # Get user IP if available
        user_ip = None
        if hasattr(self.env, 'context') and self.env.context.get('request'):
            try:
                request = self.env.context.get('request')
                user_ip = request.httprequest.remote_addr
            except:
                pass

        # Get model reference if model_name is provided
        model_id = None
        if model_name:
            model_id = self.env['ir.model'].sudo().search([('model', '=', model_name)], limit=1)

        # Prepare values
        values = {
            'event_type': event_type,
            'description': description,
            'user_id': user_id or self.env.uid,
            'user_ip': user_ip,
            'model_name': model_name,
            'model_id': model_id.id if model_id else None,
            'res_id': res_id,
            'resource_name': resource_name,
            'severity': severity,
            'success': success,
            'error_message': error_message,
        }

        # Convert dictionaries to JSON strings
        if old_values:
            values['old_values'] = json.dumps(old_values, default=str)
        if new_values:
            values['new_values'] = json.dumps(new_values, default=str)
        if additional_data:
            values['additional_data'] = json.dumps(additional_data, default=str)

        # Create log entry using sudo to ensure it's always created
        return self.sudo().create(values)

    def unlink(self):
        """Prevent deletion of audit logs."""
        raise models.UserError('Audit logs cannot be deleted for compliance reasons.')

    def write(self, vals):
        """Prevent modification of audit logs."""
        raise models.UserError('Audit logs cannot be modified for compliance reasons.')
