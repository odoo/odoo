# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

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
                                          ('manual', 'Manual')], string='Automation Manual')

    # Unique Constraint for License plate barcode
    _sql_constraints = [
        ('unique_license_plate_barcode', 'unique(license_plate_barcode)', 'The License Plate Barcode must be unique.')
    ]

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
        print("Section name created:", section_name)

        # Dictionary to keep track of products already added to the License Plate Order
        license_plate_product_map = {}

        # Iterate through each line entered in the wizard
        for line in self.line_ids:
            # Search for the product based on the provided barcode
            product = self.env['product.product'].search([('barcode', '=', line.barcode)], limit=1)
            if not product:
                raise UserError(_("No product found for barcode: %s") % line.barcode)
            self.env['delivery.receipt.orders.line'].create({
                'delivery_receipt_order_line_id': delivery_order.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'sku_code': product.default_code,
                'quantity': line.quantity,
                'available_quantity': line.available_quantity,
                'remaining_quantity': line.remaining_quantity,
                'license_plate_closed': True,
                'state': 'closed',
            })
            # Check if the product already exists in the license_plate_product_map
            if line.product_id.id in license_plate_product_map:
                # If the product exists, update the quantity
                license_plate_product_map[line.product_id.id]['quantity'] += line.quantity
                # license_plate_product_map[line.product_id.id]['remaining_qty'] += line.remaining_quantity
            else:
                # If it's a new product, add it to the map
                license_plate_product_map[line.product_id.id] = {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'sku_code': product.default_code,
                    'quantity': line.quantity,
                    # 'available_quantity': line.available_quantity,
                    # 'remaining_qty': line.remaining_quantity,
                }

            # Update remaining quantity in stock move lines
            move_lines = self.picking_id.move_ids_without_package.filtered(
                lambda m: m.product_id == line.product_id)
            move_lines.remaining_qty = sum(line.mapped('remaining_quantity'))  # Sum of all quantities from the picking
            move_lines.is_remaining_qty = True

        # Create License Plate Order lines from the product map
        for product_data in license_plate_product_map.values():
            license_plate_order_lines.append([0, 0, product_data])

        # Create License Plate Record with all the lines
        self.env['license.plate.orders'].create({
            'name': self.license_plate_barcode,
            'state': 'closed',
            'automation_manual': self.automation_manual,
            'delivery_receipt_order_id': delivery_order.id,
            'picking_id': self.picking_id.id,
            'license_plate_order_line_ids': license_plate_order_lines,  # Pass the list of lines
        })

        return {'type': 'ir.actions.act_window_close'}

    # def action_add_lines(self):
    #     """
    #     This method adds lines to the delivery receipt order based on the
    #     license plate barcode and the lines entered the wizard.
    #     It creates a section line for the license plate and product lines
    #     for each entry in line_ids.
    #     """
    #     active_id = self.env.context.get('active_id')
    #     delivery_order = self.env['delivery.receipt.orders'].browse(active_id)
    #     # Prepare data for License Plate Order
    #     license_plate_order_lines = []
    #     # Use the barcode as the section name
    #     section_name = self.license_plate_barcode
    #     # Create a section line
    #     self.env['delivery.receipt.orders.line'].create({
    #         'delivery_receipt_order_line_id': delivery_order.id,
    #         'product_id': False,  # No product for section header
    #         'name': section_name,
    #         'quantity': 0,
    #         'sku_code': '',
    #         'available_quantity': 0,
    #         'remaining_quantity': 0,
    #         'display_type': 'line_section',  # Indicate this is a section
    #         'license_plate_closed': True,
    #     })
    #     print("Section name created:", section_name)
    #
    #     for line in self.line_ids:
    #         # Search for the product based on the provided barcode
    #         product = self.env['product.product'].search([('barcode', '=', line.barcode)], limit=1)
    #         if not product:
    #             raise UserError(_("No product found for barcode: %s") % line.barcode)
    #         # Create product line
    #         self.env['delivery.receipt.orders.line'].create({
    #             'delivery_receipt_order_line_id': delivery_order.id,
    #             'product_id': line.product_id.id,
    #             'name': line.product_id.name,
    #             'sku_code': product.default_code,
    #             'quantity': line.quantity,
    #             'available_quantity': line.available_quantity,
    #             'remaining_quantity': line.remaining_quantity,
    #             'license_plate_closed': True,
    #             'state': 'closed',
    #         })
    #         # Prepare line data for the license plate order
    #         license_plate_order_lines.append([0, 0, {
    #             'product_id': line.product_id.id,
    #             'sku_code': line.product_id.default_code,
    #             'quantity': line.quantity,
    #         }])
    #         move_lines = self.picking_id.move_ids_without_package.filtered(
    #             lambda m: m.product_id == line.product_id)
    #         move_lines.remaining_qty = sum(line.mapped('remaining_quantity'))  # Sum of all quantities from the picking
    #         move_lines.is_remaining_qty = True
    #     # Create License Plate Record
    #     self.env['license.plate.orders'].create({
    #         'name': self.license_plate_barcode,
    #         'state': 'closed',
    #         'automation_manual': self.automation_manual,
    #         'delivery_receipt_order_id': delivery_order.id,
    #         'picking_id': self.picking_id.id,
    #         'license_plate_order_line_ids': license_plate_order_lines,  # Pass the list of lines
    #     })
    #     return {'type': 'ir.actions.act_window_close'}


class DeliveryReceiptWizardLine(models.TransientModel):
    _name = 'delivery.receipt.wizard.line'
    _description = 'Delivery Receipt Wizard Line'

    wizard_id = fields.Many2one('delivery.receipt.wizard', string='Wizard Reference', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                  domain="[('id', 'in', available_product_ids)]")  # Domain to filter products
    barcode = fields.Char(related='product_id.barcode')
    quantity = fields.Float(string='Quantity', required=True)
    available_quantity = fields.Float(string='Available Quantity', compute='_compute_available_quantity')
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity')
    available_product_ids = fields.Many2many('product.product', string='Available Products', compute='_compute_available_products')

    @api.depends('wizard_id.picking_id')
    def _compute_available_products(self):
        """
        Compute available products based on the selected picking_id.
        This method sets available_product_ids based on the products in the picking.
        """
        for line in self:
            if line.wizard_id and line.wizard_id.picking_id:
                product_ids = line.wizard_id.picking_id.move_ids_without_package.mapped('product_id.id')
                line.available_product_ids = [(6, 0, product_ids)]
            else:
                line.available_product_ids = [(5,)]  # Clear the field if no picking is set

    @api.depends('product_id', 'wizard_id.picking_id')
    def _compute_available_quantity(self):
        """
        Compute the available quantity of the product based on the
        stock moves associated with the picking_id in the wizard.
        This method sums up the quantities from the stock moves for the
        given product.
        """
        for line in self:
            if line.wizard_id and line.wizard_id.picking_id:
                move_lines = line.wizard_id.picking_id.move_ids_without_package.filtered(lambda m: m.product_id == line.product_id)
                line.available_quantity = sum(move_lines.mapped('quantity'))  # Sum of all quantities from the picking
            else:
                line.available_quantity = 0.0

    @api.depends('product_id', 'wizard_id.picking_id')
    def _compute_remaining_quantity(self):
        """
        Compute the remaining quantity for the product by subtracting the total quantity
        already entered in the wizard from the available quantity.
        """
        for line in self:
            if line.wizard_id and line.wizard_id.picking_id:
                total_quantity_selected = sum(
                    l.quantity for l in line.wizard_id.line_ids if l.product_id == line.product_id)
                move_lines = line.wizard_id.picking_id.move_ids_without_package.filtered(
                    lambda m: m.product_id == line.product_id)
                available_qty = sum(move_lines.mapped('quantity'))

                line.remaining_quantity = (
                    available_qty - total_quantity_selected
                    if not move_lines.is_remaining_qty
                    else move_lines.remaining_qty - total_quantity_selected
                )
            else:
                line.remaining_quantity = 0.0

    @api.onchange('quantity')
    def onchange_quantity(self):
        for line in self:
            line._compute_remaining_quantity()
            if line.remaining_quantity < 0:
                if line.remaining_quantity < line.quantity:
                    return {
                        'warning': {
                            'title': _("Invalid Quantity "),
                            'message': _("The selected quantity is greater than actual remaining quantity."),
                        }
                    }

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

            if self.product_id and self.product_id.id not in product_ids:
                return {
                    'warning': {
                        'title': _("Invalid Product Selection"),
                        'message': _("The selected product is not available in the selected picking."),
                    }
                }

            return {
                'domain': {
                    'product_id': [('id', 'in', product_ids)]
                }
            }

        return {'domain': {'product_id': []}}
