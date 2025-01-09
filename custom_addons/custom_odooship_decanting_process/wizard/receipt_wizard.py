# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class DeliveryReceiptWizard(models.TransientModel):
    _name = 'delivery.receipt.wizard'
    _description = 'Delivery Receipt Wizard'

    license_plate_barcode = fields.Char(string='Scan Licence Plate Barcode', required=True)
    line_ids = fields.One2many('delivery.receipt.wizard.line', 'wizard_id', string='Product Lines')
    picking_id = fields.Many2one('stock.picking', string='Select Receipt')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='State', default='open')
    automation_manual = fields.Selection([('automation', 'Automation'),
                                          ('automation_bulk', 'Automation Bulk'),
                                          ('manual', 'Manual'),
                                          ('xdock','XDOCK')], string='Automation Manual')
    partner_id = fields.Many2one(related='picking_id.partner_id', string='Customer', store=True)
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        related='partner_id.tenant_code_id',
        store=True
    )
    site_code_id = fields.Many2one('site.code.configuration',
                                   related='picking_id.site_code_id', string='Site Code',
                                   store=True)
    # available_location_ids = fields.Many2many(
    #     'stock.location', compute='_compute_available_locations', store=True
    # )

    # Define location_dest_id with domain linked to available_location_ids
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        # domain="[('id', 'in', available_location_ids)]"
    )

    @api.onchange('automation_manual', 'picking_id', 'site_code_id')
    def _compute_available_locations(self):
        """
        Computes available locations for location_dest_id based on the automation_manual selection
        and site_code_id.
        """
        for record in self:
            if not record.site_code_id:
                raise UserError("Site Code is not available for this order.")

            if record.automation_manual == 'automation' and record.picking_id:
                # Automation: Use the destination location from picking's move records
                record.location_dest_id = record.picking_id.location_dest_id
            elif record.automation_manual == 'manual':
                # Manual: Search for locations based on Site Code
                manual_location = self.env['stock.location'].search([
                    ('system_type', '=', 'manual'),
                    ('name', '=', 'Putaway/Manual'),
                    ('site_code_id', '=', record.site_code_id.id)  # Filter by Site Code
                ], limit=1)
                record.location_dest_id = manual_location
            elif record.automation_manual == 'automation_bulk':
                # Automation Bulk: Search for locations based on Site Code
                automation_bulk_location = self.env['stock.location'].search([
                    ('system_type', '=', 'geek'),
                    ('name', '=', 'Automation Bulk Putaway'),
                    ('site_code_id', '=', record.site_code_id.id)  # Filter by Site Code
                ], limit=1)
                record.location_dest_id = automation_bulk_location

    @api.onchange('license_plate_barcode')
    def _onchange_license_plate_barcode(self):
        """
        This method checks if the License Plate already exists when the user enters the barcode.
        If it exists and is in a 'closed' or non-draft state, raise a warning.
        """
        if self.license_plate_barcode:
            existing_license_plate = self.env['license.plate.orders'].search([
                ('name', '=', self.license_plate_barcode),
                ('state', '!=', 'draft')
            ], limit=1)

            if existing_license_plate:
                # License Plate exists in a confirmed state, raise a warning
                raise ValidationError(
                    _("License Plate '%s' already exists and is in a confirmed state." % self.license_plate_barcode)
                )

    @api.model
    def default_get(self, fields):
        """
        Override the default_get method to automatically set the picking_id
        based on the active_id in the context when the wizard is opened.
        """
        res = super(DeliveryReceiptWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            delivery_order = self.env['delivery.receipt.orders'].browse(active_id)
            res['picking_id'] = delivery_order.picking_id.id  # Automatically set the picking_id
        return res

    def action_add_lines(self):
        """
        This method adds lines to the delivery receipt order based on the
        license plate barcode and the lines entered in the wizard.
        It creates a section line for the license plate and product lines
        for each entry in line_ids. If the product already exists, it combines the quantities.
        """
        # Raise ValidationError if no Product line items added and trying to create details for license plate
        if not self.line_ids:
            raise ValidationError(_("Please add at least one product line before proceeding."))

        # To ensure Product is added on line items
        for line in self.line_ids:
            if not line.product_id:
                raise ValidationError(_("Please ensure all line items have a product selected before proceeding."))

        active_id = self.env.context.get('active_id')
        delivery_order = self.env['delivery.receipt.orders'].browse(active_id)
        # Prepare data for License Plate Order
        license_plate_order_lines = []

        # Use the barcode as the section name
        section_name = self.license_plate_barcode

        # Create a section line for the license plate
        self.env['delivery.receipt.orders.line'].create({
            'delivery_receipt_order_line_id': delivery_order.id,
            'product_id': False,  # No product for section header
            'name': section_name,
            'quantity': 0,
            'sku_code': '',
            'available_quantity': 0,
            'remaining_quantity': 0,
            'display_type': 'line_section',  # Indicate this is a section
            'license_plate_closed': True,
        })

        # Dictionary to keep track of products already added to the License Plate Order
        license_plate_product_map = {}

        # Iterate through each line entered in the wizard
        for line in self.line_ids:
            self.env['delivery.receipt.orders.line'].create({
                'delivery_receipt_order_line_id': delivery_order.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'sku_code': line.product_id.default_code,
                'quantity': line.quantity,
                'available_quantity': line.available_quantity,
                'remaining_quantity': line.remaining_quantity,
                'license_plate_closed': True,
                'state': 'closed',
                'automation_manual': self.automation_manual,
                'location_dest_id': line.location_dest_id.id,
                'picking_id': line.picking_id.id,
            })
            # Check if the product already exists in the license_plate_product_map
            if line.product_id.id in license_plate_product_map:
                # If the product exists, update the quantity
                license_plate_product_map[line.product_id.id]['quantity'] += line.quantity
                license_plate_product_map[line.product_id.id]['remaining_qty'] += line.quantity
            else:
                # If it's a new product, add it to the map
                license_plate_product_map[line.product_id.id] = {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'sku_code': line.product_id.default_code,
                    'quantity': line.quantity,
                    'remaining_qty': line.quantity,
                }
            # Update remaining quantity in stock move lines
            move_lines = self.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id == line.product_id)
            move_lines.remaining_qty = sum(line.mapped('remaining_quantity'))  # Sum of all quantities from the picking
            move_lines.is_remaining_qty = True
            move_lines.delivery_receipt_state = 'fully_received' if move_lines.remaining_qty ==0.0 else 'partially_received'
            move_lines.picked = True if move_lines.remaining_qty == 0.0 else 'False'

        # Create License Plate Order lines from the product map
        for product_data in license_plate_product_map.values():
            license_plate_order_lines.append([0, 0, product_data])

        # Create License Plate Record with all the lines
        vals = {
            'name': self.license_plate_barcode,
            'state': 'closed',
            'automation_manual': self.automation_manual,
            'delivery_receipt_order_id': delivery_order.id,
            'picking_id': self.picking_id.id,
            'location_dest_id': self.location_dest_id.id,
            'license_plate_order_line_ids': license_plate_order_lines,  # Pass the list of lines
        }
        license_plate_order = self.env['license.plate.orders'].create(vals)
        # Update stock quantities to `location_dest_id`
        stock_quant_obj = self.env['stock.quant']
        for line in self.line_ids:
            stock_quant_obj._update_available_quantity(
                product_id=line.product_id,
                location_id=self.location_dest_id,
                quantity=line.quantity,
            )

        return {'type': 'ir.actions.act_window_close'}



class DeliveryReceiptWizardLine(models.TransientModel):
    _name = 'delivery.receipt.wizard.line'
    _description = 'Delivery Receipt Wizard Line'

    wizard_id = fields.Many2one('delivery.receipt.wizard', string='Wizard Reference', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('id', 'in', available_product_ids)]")
    # barcode = fields.Char(related='product_id.barcode')
    quantity = fields.Float(string='Quantity', required=True)
    available_quantity = fields.Float(string='Expected Quantity', compute='_compute_available_quantity')
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity')
    available_product_ids = fields.Many2many('product.product', string='Available Products', compute='_compute_available_products')
    location_dest_id = fields.Many2one('stock.location', string='Destination location')
    picking_id = fields.Many2one('stock.picking', string='Receipt')
    product_packaging_id = fields.Many2one('stock.move', string='Packaging')
    product_packaging_qty = fields.Float(string='Packaging Quantity')

    @api.depends('wizard_id.picking_id')
    def _compute_available_products(self):
        for line in self:
            if line.wizard_id and line.wizard_id.picking_id:
                product_ids = line.wizard_id.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id.automation_manual_product == line.wizard_id.automation_manual).mapped('product_id.id')
                product_ids = line.wizard_id.picking_id.move_ids_without_package.mapped('product_id.id')
                line.available_product_ids = [(6, 0, product_ids)]
            else:
                line.available_product_ids = [(5,)]

    @api.depends('product_id', 'wizard_id.picking_id')
    def _compute_available_quantity(self):
        for line in self:
            if line.wizard_id and line.wizard_id.picking_id:
                move_lines = line.wizard_id.picking_id.move_ids_without_package.filtered(lambda m: m.product_id == line.product_id)
                line.available_quantity = sum(move_lines.mapped('product_uom_qty'))
            else:
                line.available_quantity = 0.0

    @api.depends('product_id', 'wizard_id.picking_id', 'quantity')
    def _compute_remaining_quantity(self):
        for line in self:
            if line.wizard_id and line.wizard_id.picking_id:
                total_quantity_selected = sum(l.quantity for l in line.wizard_id.line_ids if l.product_id == line.product_id)
                move_lines = line.wizard_id.picking_id.move_ids_without_package.filtered(lambda m: m.product_id == line.product_id)
                available_qty = sum(move_lines.mapped('product_uom_qty'))
                line.remaining_quantity = move_lines.remaining_qty - total_quantity_selected
            else:
                line.remaining_quantity = 0.0

    @api.onchange('quantity')
    def onchange_quantity(self):
        for line in self:
            if line.remaining_quantity < 0:
                raise ValidationError(_("The selected quantity (%s) exceeds the remaining quantity (%s).") % (line.quantity, line.remaining_quantity))



    @api.onchange('product_id')
    def onchange_product_id(self):
        """
        On change method for product_id and quantity fields.
        This method checks if the selected product is valid based on
        the available products in the current picking and returns
        a warning if the product is not available.
        """
        if self.wizard_id and self.wizard_id.picking_id:
            product_ids = self.wizard_id.picking_id.move_ids_without_package.mapped('product_id.id')
            self.picking_id = self.wizard_id.picking_id
            self.location_dest_id = self.wizard_id.location_dest_id
            if self.product_id and self.product_id.id not in product_ids:
                return {
                    'warning': {
                        'title': _("Invalid Product Selection"),
                        'message': _("The selected product is not available in the selected picking."),
                    }
                }
            # Commented below code to remove validation while selecting product if it doesn't matches with the selected automation_manual selection
            # if self.product_id and self.product_id.automation_manual_product != self.wizard_id.automation_manual:
            #     raise ValidationError(
            #         "The selected product's automation/manual type does not match the wizard's automation/manual selection. "
            #         "Please select a product that corresponds to the chosen automation/manual type."
            #     )

            return {
                'domain': {
                    'product_id': [('id', 'in', product_ids)]
                }
            }

        return {'domain': {'product_id': []}}
