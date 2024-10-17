# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class DeliveryReceiptOrders(models.Model):
    _name = 'delivery.receipt.orders'
    _description = 'Delivery Receipt Orders'

    name = fields.Char(string='Reference', required=True,default=lambda self: _('New'))
    receipt_number = fields.Char(string="Scan Barcode of receipt")
    process_type = fields.Selection([
        ('automation', 'Automation Process'),
        ('manual', 'Manual Process'),
    ], string='Automation/Manual Process')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Select Receipt'
    )
    partner_id = fields.Many2one(related='picking_id.partner_id', string='Customer')
    # product_ids = fields.Many2many('product.product', string='Products')
    # quantity = fields.Integer(string='Quantity')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='Status', readonly=True)

    delivery_receipt_orders_line_ids = fields.One2many(
        comodel_name='delivery.receipt.orders.line',
        inverse_name='delivery_receipt_order_line_id',
        string='Product Lines'
    )
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        related='partner_id.tenant_code_id',
        readonly=True
    )
    site_code_id = fields.Many2one('site.code.configuration',
                                   related='picking_id.site_code_id', string='Site Code')


    def button_action_draft(self):
        """
        Change the state of the delivery receipt order to 'in_progress'
        and open the wizard to create a delivery receipt.
        """
        self.state = 'in_progress'
        return {
            'name': _('Create Delivery Receipt'),
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.receipt.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

    def button_action_done(self):
        """
        Validate that all license plates in related lines are closed before
        changing the state of the delivery receipt order to 'done'.
        Raises a UserError if any license plate is still open.
        """
        for order in self:
            # Initialize a list to hold the line states
            line_states = []

            # Check if all related delivery receipt order lines have the license plate closed
            all_closed = all(line.license_plate_closed for line in order.delivery_receipt_orders_line_ids)

            # Log the status of each line for debugging
            for line in order.delivery_receipt_orders_line_ids:
                line_states.append((line.id, line.license_plate_closed))

            # Print out the line states
            print("\n\n\n Line states (ID, License Plate Closed):", line_states)

            if not all_closed:
                raise UserError(_("All license plates must be closed before marking as done."))

            # Change the state to 'done' if validation passes
            order.state = 'done'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('delivery.receipt.orders') or _('New')
        return super().create(vals_list)


class DeliveryReceiptOrdersLine(models.Model):
    _name = 'delivery.receipt.orders.line'
    _description = 'Delivery Receipt Orders Line'
    _order = 'sequence, delivery_receipt_order_line_id, id'

    name = fields.Char(string='Name')
    delivery_receipt_order_line_id = fields.Many2one(
        comodel_name='delivery.receipt.orders',
        string='Delivery Receipt',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string="Sequence")
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )
    quantity = fields.Float(string='Quantity', required=True)
    sku_code = fields.Char(related='product_id.default_code',string='SKU')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='State', default='open')
    display_type = fields.Selection(
        selection=[
            ('line_section', "Section"),
            ('line_note', "Note"),
        ],
        default=False)
    available_quantity = fields.Float(string='Available Quantity')
    remaining_quantity = fields.Float(string='Remaining Quantity')
    license_plate_closed = fields.Boolean(string='License Plate Closed', default=False)
    display_type_line_section = fields.Boolean(string='Display Type Line Section', default=False)

    def button_close_license_plate(self):
        """
        Close the license plate for this delivery receipt order line.
        This method sets the license_plate_closed field to True
        and updates the state to 'closed'.
        """
        self.license_plate_closed = True
        self.state = 'closed'

    @api.model
    def create(self, vals_list):
        """
        Override the create method to handle special cases for certain
        display types. If the display_type indicates a section, the
        product_id and quantity are set to default values.
        """
        if vals_list.get('display_type'):
            vals_list.update(product_id=False, quantity=0)
        return super().create(vals_list)
