# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import requests


_logger = logging.getLogger(__name__)

class AutomationDecantingOrdersProcess(models.Model):
    _name = 'automation.decanting.orders.process'
    _description = 'Automation Decanting Orders Process'

    name = fields.Char(string='Name', required=True,default=lambda self: _('New'))
    barcode_option = fields.Selection([('pallet', 'Pallet'),
                                       ('Box', 'Box'),
                                       ('crate', 'Crate'),])
    pallet_barcode = fields.Char(string='License Plate Barcode')
    hu_barcode = fields.Char(string='Handling Unit Barcode')
    crate_barcode = fields.Char(string='Crate Barcode')
    container_id = fields.Many2one('crate.container.configuration', string='Container')
    container_partition = fields.Integer(related='container_id.crate_container_partition', string='Container Partition')
    container_code = fields.Char(related='container_id.crate_code', string='Container Code')
    automation_decanting_process_line_ids = fields.One2many('automation.decanting.orders.process.line',
                            'automation_decanting_process_id', string='Items')
    crate_status = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Crate Status Closed'),
    ], string='Crate Status', default='open')
    state = fields.Selection([
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='State', default='in_progress')
    license_plate_id = fields.Many2one('license.plate.orders', string='License Plate Barcode')
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        related='license_plate_id.picking_id',
        string='Receipt Order'
    )
    partner_id = fields.Many2one(related='picking_id.partner_id', string='Customer')
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        related='partner_id.tenant_code_id',
    )
    site_code_id = fields.Many2one('site.code.configuration',
                                   related='picking_id.site_code_id', string='Site Code')

    @api.constrains('crate_barcode')
    def _check_unique_barcode(self):
        """Ensure that the same pallet and crate barcode are not used in an in-progress record."""
        for record in self:
            if record.state == 'in_progress':
                existing_record = self.search([
                    ('crate_barcode', '=', record.crate_barcode),
                    ('state', '=', 'in_progress'),
                    ('id', '!=', record.id)  # Exclude the current record
                ], limit=1)

                if existing_record:
                    raise ValidationError(
                        f"Crate Barcode '{record.crate_barcode}' is already in progress. "
                        "Please complete or close the existing record before creating a new one."
                    )

    @api.onchange('license_plate_id')
    def _onchange_license_plate_id(self):
        """Allow only closed license plates with done delivery receipt order."""
        if self.license_plate_id:
            if self.license_plate_id.state != 'closed' or self.license_plate_id.automation_manual != 'automation':
                raise ValidationError(
                    f"The selected License Plate '{self.license_plate_id.name}' is not available or its status is not 'closed'."
                )

            # Check the related delivery receipt order
            delivery_order = self.license_plate_id.delivery_receipt_order_id
            if delivery_order and delivery_order.state != 'done':
                raise ValidationError(
                    f"The related Delivery Receipt Order '{delivery_order.name}' is still in progress. "
                    "Please complete the order (Manual/Automation Order Process) before proceeding."
                )


    @api.onchange('crate_barcode')
    def _onchange_crate_barcode(self):
        """Check if crate barcode exists and is available in the crate.barcode.configuration model."""
        if self.crate_barcode:
            # Search for the crate barcode in crate.barcode.configuration model
            crate = self.env['crate.barcode.configuration'].search([
                ('name', '=', self.crate_barcode),
                ('crate_status', '=', 'available'),
            ], limit=1)

            # If crate not found or not available, raise a ValidationError
            if not crate:
                raise ValidationError(
                    f"The scanned Crate Barcode '{self.crate_barcode}' is not available for use. Please check the barcode and try again.")


    def action_button_close(self):
        """ Action button close method is to update status and close crate status."""
        self.state = 'done'
        self.crate_status = 'closed'

        # Update crate status to not_available in crate.barcode.configuration
        crate_config = self.env['crate.barcode.configuration'].search([
            ('name', '=', self.crate_barcode)
        ], limit=1)

        if crate_config:
            crate_config.crate_status = 'not_available'
        else:
            raise UserError(f"Crate Barcode '{self.crate_barcode}' not found in the crate configuration.")

        # Prepare data in the required format
        receipt_list = []
        sku_list = []

        # Loop through decanting process lines
        for line in self.automation_decanting_process_line_ids:
            sku_list.append({
                "amount": line.quantity,  # Quantity
                "out_batch_code": 'ECOM',  # Tenant Code
                "owner_code": self.tenant_code_id.name,  # Partner Name (Customer)
                "sku_code": line.sku_code,  # SKU Code
                "sku_level": 0,  # Assuming SKU Level is 0
                "container_code": self.crate_barcode,  # Crate Barcode
                "container_type": self.container_code,  # Container Code
                "bin_code": line.bin_code,  # Bin Code
                "batch_property07": 'yyy',  # Assuming Color is stored here
                "batch_property08": 'zzz',
            })

        # Add the receipt entry
        receipt_list.append({
            "warehouse_code": self.site_code_id.name,  # Site Code
            "receipt_code": self.picking_id.name,  # Decanting Order Name as Receipt Code
            "sku_list": sku_list,
            "type": 1  # Assuming type is always 1
        })

        # Prepare the final data structure
        data = {
            "body": {
                "receipt_list": receipt_list
            },
            "header": {
                "user_id": "system",
                "user_key": "system",
                "warehouse_code": self.site_code_id.name  # Site Code
            }
        }

        # Convert data to JSON format
        json_data = json.dumps(data, indent=4)

        # Log the generated data
        _logger.info(f"Generated data for crate close: {json_data}")

        # Define the URLs for Shiperoo Connect
        # url_geekplus = "https://shiperooconnect.automation.shiperoo.com/api/interface/geekplus/"
        url_automation_putaway = "https://shiperooconnect.automation.shiperoo.com/api/interface/automationputaway"

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            # Send the data to the Geekplus URL
            # response_geekplus = requests.post(url_geekplus, headers=headers, data=json_data)
            # if response_geekplus.status_code != 200:
            #     raise UserError(f"Failed to send data to Geekplus: {response_geekplus.content.decode()}")

            # Send the data to the Automation Putaway URL
            response_putaway = requests.post(url_automation_putaway, headers=headers, data=json_data)
            if response_putaway.status_code != 200:
                raise UserError(f"Failed to send data to Automation Putaway: {response_putaway.content.decode()}")

        except requests.exceptions.RequestException as e:
            raise UserError(f"Error occurred during API request: {str(e)}")

        return {'type': 'ir.actions.act_window_close'}


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('automation.decanting.orders.process') or _('New')

            # Get the current instance for the automation process
            current_process = self.new(vals)  # Create a new record in memory

            # Fetch the actual license plate record
            if current_process.license_plate_id:
                license_plate = self.env['license.plate.orders'].browse(current_process.license_plate_id.id)
                for line in current_process.automation_decanting_process_line_ids:
                    # Find the corresponding license plate order line based on product_id
                    existing_line = license_plate.license_plate_order_line_ids.filtered(
                        lambda l: l.product_id.id == line.product_id.id)
                    if existing_line:
                        # Update remaining_qty for the existing line
                        existing_line.write({
                            'remaining_qty': line.remaining_quantity,
                            'is_remaining_qty': True,
                        })
                    license_plate.check_and_update_license_plate_state()
        return super().create(vals_list)

    def write(self, vals):
        # Call the super write method first to ensure updates are made
        result = super().write(vals)

        for record in self:
            # Fetch the license plate if it exists
            if record.license_plate_id:
                license_plate = self.env['license.plate.orders'].browse(record.license_plate_id.id)

                for line in record.automation_decanting_process_line_ids:
                    # Find the corresponding license plate order line based on product_id
                    existing_line = license_plate.license_plate_order_line_ids.filtered(
                        lambda l: l.product_id.id == line.product_id.id
                    )
                    if existing_line:
                        # Update remaining_qty and set is_remaining_qty to True for the existing line
                        existing_line.write({
                            'remaining_qty': line.remaining_quantity,
                            'is_remaining_qty': True,
                        })

                # Check and update the license plate state based on updated lines
                license_plate.check_and_update_license_plate_state()

        return result

class AutomationDecantingOrdersProcessLine(models.Model):
    _name = 'automation.decanting.orders.process.line'
    _description = 'Decanting Orders process line'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        domain="[('id', 'in', available_product_ids)]",  # Domain to filter products
    )
    sku_code = fields.Char(related='product_id.default_code', string='SKU')
    quantity = fields.Float(string='Quantity', required=True)
    barcode = fields.Char(string='Item Barcode')
    automation_decanting_process_id = fields.Many2one('automation.decanting.orders.process', string='Decanting Process')
    section = fields.Integer(string='Section')
    partition_code = fields.Char(string='Partition Code')
    bin_code = fields.Char(string='Bin Code', compute='_compute_bin_code', store=True)
    available_product_ids = fields.Many2many('product.product', string='Available Products', compute='_compute_available_products')
    available_quantity = fields.Float(string='Available Quantity', compute='_compute_available_quantity')
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity', store=True)

    @api.depends('product_id', 'automation_decanting_process_id.license_plate_id')
    def _compute_available_quantity(self):
        """
        Compute the available quantity of the product based on the
        stock moves associated with the picking_id in the wizard.
        This method sums up the quantities from the stock moves for the
        given product.
        """
        for line in self:
            if line.automation_decanting_process_id and line.automation_decanting_process_id.license_plate_id:
                move_lines = line.automation_decanting_process_id.license_plate_id.license_plate_order_line_ids.filtered(
                    lambda m: m.product_id == line.product_id)
                line.available_quantity = sum(move_lines.mapped('quantity'))  # Sum of all quantities from the picking
            else:
                line.available_quantity = 0.0

    @api.depends('product_id', 'automation_decanting_process_id.license_plate_id')
    def _compute_remaining_quantity(self):
        """
        Compute the remaining quantity for the product by subtracting the total quantity
        already  from the available quantity.
        """
        for line in self:
            if line.automation_decanting_process_id and line.automation_decanting_process_id.license_plate_id:
                total_quantity_selected = sum(
                    l.quantity for l in line.automation_decanting_process_id.automation_decanting_process_line_ids if l.product_id == line.product_id)
                move_lines = line.automation_decanting_process_id.license_plate_id.license_plate_order_line_ids.filtered(
                    lambda m: m.product_id == line.product_id)
                available_qty = sum(move_lines.mapped('quantity'))

                line.remaining_quantity = (
                    available_qty - total_quantity_selected
                    if not move_lines.is_remaining_qty
                    else move_lines.remaining_qty - total_quantity_selected
                )
            else:
                line.remaining_quantity = 0.0

    @api.depends('automation_decanting_process_id.license_plate_id')
    def _compute_available_products(self):
        """Compute available products based on the selected pallet_barcode."""
        for line in self:
            if line.automation_decanting_process_id:
                license_plate = line.automation_decanting_process_id.license_plate_id
                if license_plate and license_plate.state == 'closed':
                    line.available_product_ids = [
                        (6, 0, license_plate.license_plate_order_line_ids.mapped('product_id').ids)]
                else:
                    line.available_product_ids = [(5,)]

    @api.depends('automation_decanting_process_id.crate_barcode', 'partition_code')
    def _compute_bin_code(self):
        """Compute the bin_code as a combination of crate_barcode and partition_code."""
        for line in self:
            crate_barcode = line.automation_decanting_process_id.crate_barcode
            partition_code = line.partition_code
            if crate_barcode and partition_code:
                line.bin_code = f"{crate_barcode}F{partition_code}"
            else:
                line.bin_code = False

    @api.onchange('automation_decanting_process_id')
    def _onchange_process_id(self):
        """Ensure the line limit is checked when changing the process."""
        if self.automation_decanting_process_id:
            current_line_count = len(self.automation_decanting_process_id.automation_decanting_process_line_ids)
            if current_line_count > self.automation_decanting_process_id.container_partition:
                raise UserError(
                    "You are not allowed to add more than {} items.".format(
                        self.automation_decanting_process_id.container_partition)
                )

    @api.constrains('quantity')
    def _check_quantity(self):
        """Ensure that the quantity does not exceed available quantity from license.plate.orders."""
        for line in self:
            total_quantity = sum(line.automation_decanting_process_id.license_plate_id.license_plate_order_line_ids.filtered(lambda l: l.product_id == line.product_id).mapped('remaining_qty'))
            if line.quantity > total_quantity:
                raise ValidationError(
                    f"The quantity of '{line.product_id.name}' exceeds the available quantity on the License Plate. "
                    f"Available: {total_quantity}, Requested: {line.quantity}"
                )

    @api.model
    def create(self, vals):
        """Override the create method to assign partition codes and check quantity."""
        process_id = vals.get('automation_decanting_process_id')
        if process_id:
            process = self.env['automation.decanting.orders.process'].browse(process_id)
            current_line_count = len(process.automation_decanting_process_line_ids)

            # Calculate partition_code based on current line count and container_partition
            container_partition = process.container_partition
            partition_code = self._generate_partition_code(current_line_count, container_partition)
            vals['partition_code'] = partition_code

        # Call the original create method
        new_record = super(AutomationDecantingOrdersProcessLine, self).create(vals)
        # Check the quantity after creation
        new_record._check_quantity()
        return new_record

    @api.model
    def write(self, vals):
        """Override the write method to check quantity when updating."""
        res = super(AutomationDecantingOrdersProcessLine, self).write(vals)
        for line in self:
            if 'quantity' in vals:
                line._check_quantity()  # Re-check quantity if it was updated
        return res

    def _generate_partition_code(self, line_index, container_partition):
        """Generate partition code based on line index and container partition."""
        partition_group = (line_index // 2) + 1  # Determine the group number (1A, 1B, etc.)
        partition_letter = chr(65 + (line_index % 2))  # 65 is the ASCII for 'A'
        return "{}{}".format(partition_group, partition_letter)
