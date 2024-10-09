# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class AutomationDecantingOrdersProcess(models.Model):
    _name = 'automation.decanting.orders.process'
    _description = 'Automation Decanting Orders Process'

    name = fields.Char(string='Name', required=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('automation.decanting.orders.process') or '')
    barcode_option = fields.Selection([('pallet', 'Pallet'),
                                       ('Box', 'Box'),
                                       ('crate', 'Crate'),])
    pallet_barcode = fields.Char(string='License Plate Barcode')
    hu_barcode = fields.Char(string='Handling Unit Barcode')
    crate_barcode = fields.Char(string='Crate Barcode')
    compartments = fields.Selection([
        ('1', '1 Compartment'),
        ('2', '2 Compartments'),
        ('4', '4 Compartments'),
        ('8', '8 Compartments'),
    ], string='Select Compartments')
    container_id = fields.Many2one('crate.container.configuration', string='Container')
    container_partition = fields.Integer(related='container_id.crate_container_partition', string='Container Partition')
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

    @api.constrains('pallet_barcode', 'crate_barcode')
    def _check_unique_barcode(self):
        """Ensure that the same pallet and crate barcode are not used in an in-progress record."""
        for record in self:
            if record.state == 'in_progress':
                existing_record = self.search([
                    ('pallet_barcode', '=', record.pallet_barcode),
                    ('crate_barcode', '=', record.crate_barcode),
                    ('state', '=', 'in_progress'),
                    ('id', '!=', record.id)  # Exclude the current record
                ], limit=1)

                if existing_record:
                    raise ValidationError(
                        f"A record with the same License Plate Barcode '{record.pallet_barcode}' and "
                        f"Crate Barcode '{record.crate_barcode}' is already in progress. "
                        "Please complete or close the existing record before creating a new one."
                    )

    @api.onchange('pallet_barcode')
    def _onchange_pallet_barcode(self):
        """Allow only closed license plates for pallet_barcode."""
        if self.pallet_barcode:
            # Search for the license plate barcode in license.plate.orders model
            license_plate = self.env['license.plate.orders'].search([
                ('name', '=', self.pallet_barcode),
                ('state', '=', 'closed'),
                ('automation_manual', '=', 'automation')
            ], limit=1)

            # If license plate is not found or not closed, raise a ValidationError
            if not license_plate:
                raise ValidationError(
                    f"The License Plate Barcode '{self.pallet_barcode}' is not available or its status is not 'closed'. Please select a valid, closed license plate.")

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

    @api.depends('automation_decanting_process_id.pallet_barcode')
    def _compute_available_products(self):
        """Compute available products based on the selected pallet_barcode."""
        for line in self:
            if line.automation_decanting_process_id:
                license_plate = self.env['license.plate.orders'].search([
                    ('name', '=', line.automation_decanting_process_id.pallet_barcode),
                    ('state', '=', 'closed'),
                    ('automation_manual', '=', 'automation')
                ], limit=1)

                if license_plate:
                    # Get product IDs from the license plate lines
                    line.available_product_ids = [(6, 0, license_plate.license_plate_order_line_ids.mapped('product_id').ids)]
                else:
                    line.available_product_ids = [(5,)]

    @api.depends('automation_decanting_process_id.crate_barcode', 'partition_code')
    def _compute_bin_code(self):
        """Compute the bin_code as a combination of crate_barcode and partition_code."""
        for line in self:
            crate_barcode = line.automation_decanting_process_id.crate_barcode
            partition_code = line.partition_code
            if crate_barcode and partition_code:
                line.bin_code = f"{crate_barcode}_{partition_code}"
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
            if line.automation_decanting_process_id:
                license_plate = self.env['license.plate.orders'].search([
                    ('name', '=', line.automation_decanting_process_id.pallet_barcode),
                    ('state', '=', 'closed'),
                    ('automation_manual', '=', 'automation')
                ], limit=1)

                if license_plate:
                    # Calculate total quantity in license plate orders
                    total_quantity = sum(license_plate.license_plate_order_line_ids.filtered(lambda l: l.product_id == line.product_id).mapped('quantity'))
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
