# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AutomationDecantingProductProcess(models.TransientModel):
    _name = 'automation.decanting.product.process.wizard'
    _description = 'Automation Decanting Product Wizard'

    # Decanting process fields
    automation_decanting_process_id = fields.Many2one('automation.decanting.orders.process', string='Decanting Process')

    # License plates associated with this decanting process
    license_plate_ids = fields.Many2many(
        'license.plate.orders',
        string='License Plate Barcodes',
        relation='decanting_product_process_license_plate_rel'  # Shorten the table name
    )

    # Container-related fields
    container_id = fields.Many2one('crate.container.configuration', string='Container')
    container_partition = fields.Integer(related='container_id.crate_container_partition', string='Container Partition',
                                         readonly=True)
    crate_barcode = fields.Char(string='Crate Barcode')
    crate_status = fields.Selection([
        ('open', 'Open'),
        ('partially_filled', 'Partially Filled'),
        ('fully_filled', 'Fully Filled')
    ], string='Crate Status', default='open')
    count_lines = fields.Integer(string='Count Lines', default=0,compute='_compute_count_lines',store=True)
    # Product lines
    line_ids = fields.One2many('automation.decanting.product.process.wizard.line', 'wizard_id', string='Product Lines')

    @api.depends('line_ids')
    def _compute_count_lines(self):
        """
        Compute the count of lines based on the number of product lines in the wizard.
        """
        for wizard in self:
            wizard.count_lines = len(wizard.line_ids.filtered(lambda line: line.product_id))

    @api.depends('line_ids', 'container_partition')
    def _compute_crate_status(self):
        """
        Compute the crate status based on the number of lines and the container partition.
        """
        for wizard in self:
            line_count = len(wizard.line_ids)
            if line_count == 0:
                wizard.crate_status = 'open'
            elif line_count >= wizard.container_partition:
                wizard.crate_status = 'fully_filled'
            else:
                wizard.crate_status = 'partially_filled'

    @api.depends('line_ids', 'container_partition')
    def _compute_crate_status(self):
        """
        Compute the crate status based on the number of lines and the container partition.
        """
        for wizard in self:
            line_count = len(wizard.line_ids)
            if line_count == 0:
                wizard.crate_status = 'open'
            elif line_count >= wizard.container_partition:
                wizard.crate_status = 'fully_filled'
            else:
                wizard.crate_status = 'partially_filled'

    def action_confirm(self):
        """
        Confirm the decanting process by updating the license plate lines and decanting process
        with the entered quantities, and updating the remaining quantities in the license plate order lines.
        """
        for line in self.line_ids:
            # Raise ValidationError if no product line items are added
            if not self.line_ids:
                raise ValidationError(_("Please add at least one product line before proceeding."))

            # Ensure that each line item has a product selected
            for line in self.line_ids:
                if not line.product_id:
                    raise ValidationError(_("Please ensure all line items have a product selected before proceeding."))

            # Validate if the number of lines exceeds the container partition limit
            if self.count_lines > self.container_partition:
                raise ValidationError(
                    _("You cannot confirm this decanting process because the number of lines (%s) exceeds the allowed partition limit (%s).")
                    % (self.count_lines, self.container_partition)
                )
            # Create a new decanting process line
            self.env['automation.decanting.orders.process.line'].create({
                'automation_decanting_process_id': self.automation_decanting_process_id.id,
                'product_id': line.product_id.id,
                'quantity':line.quantity,
                'available_quantity': line.available_quantity,
                'remaining_quantity': line.remaining_quantity,
                'barcode': line.barcode,
                'partition_code': line.partition_code,
                'bin_code': line.bin_code,
            })

            # Update remaining quantities in license plate order lines
            total_qty_to_decant = line.quantity  # Quantity entered by the user

            # Loop through license plate orders to find the corresponding product and update remaining quantity
            for license_plate in self.license_plate_ids:
                product_lines = license_plate.license_plate_order_line_ids.filtered(
                    lambda l: l.product_id == line.product_id)

                for lp_line in product_lines:
                    if total_qty_to_decant <= 0:
                        break  # Exit the loop if the entire quantity has been decanted

                    if lp_line.remaining_qty >= total_qty_to_decant:
                        # Deduct the quantity from the license plate line's remaining quantity
                        lp_line.remaining_qty -= total_qty_to_decant
                        total_qty_to_decant = 0  # All quantity has been decanted
                    else:
                        # Deduct the available quantity and continue decanting from the next license plate
                        total_qty_to_decant -= lp_line.remaining_qty
                        lp_line.remaining_qty = 0  # This license plate line is fully decanted

                    # Mark is_remaining_qty as True if remaining_qty is 0
                    lp_line.is_remaining_qty = (lp_line.remaining_qty == 0)

            if total_qty_to_decant > 0:
                raise ValidationError(_("Insufficient remaining quantity for product %s. Only %d quantity left." % (
                    line.product_id.display_name, line.available_quantity)))
        self._compute_crate_status()
        self.automation_decanting_process_id.crate_status = self.crate_status
        self.automation_decanting_process_id.count_lines = self.count_lines
        return {'type': 'ir.actions.act_window_close'}


class AutomationDecantingProductProcessLine(models.TransientModel):
    _name = 'automation.decanting.product.process.wizard.line'
    _description = 'Decanting Product Line for Wizard'

    wizard_id = fields.Many2one('automation.decanting.product.process.wizard', string='Wizard Reference', required=True)
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        domain="[('id', 'in', available_product_ids)]",  # Domain to filter products
    )
    sku_code = fields.Char(related='product_id.default_code', string='SKU')
    quantity = fields.Float(string='Quantity', required=True)
    barcode = fields.Char(string='Item Barcode')
    automation_decanting_process_id = fields.Many2one('automation.decanting.orders.process', string='Decanting Process')
    section = fields.Integer(string='Section')
    partition_code = fields.Char(string='Partition Code')
    bin_code = fields.Char(string='Bin Code')
    available_product_ids = fields.Many2many('product.product', string='Available Products',
                                             compute='_compute_available_products')
    available_quantity = fields.Float(string='Available Quantity', compute='_compute_available_quantity')
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity', store=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        Update the count of lines and validate against the container partition.
        """
        if self.wizard_id:
            process = self.wizard_id.automation_decanting_process_id
            if process:
                current_line_count = len(process.automation_decanting_process_line_ids)
                # Check partition limit before adding a new line
                partition_limit = process.container_partition
                if self.wizard_id.count_lines > partition_limit:
                    raise ValidationError(
                        _("You cannot add more than %s items to the container.") % partition_limit)

    @api.depends('wizard_id.license_plate_ids')
    def _compute_available_products(self):
        """Compute available products based on the selected license plates in the wizard."""
        for line in self:
            if line.wizard_id:
                license_plates = line.wizard_id.license_plate_ids
                if license_plates:
                    # Loop through the license plates and check for the 'closed' state
                    closed_license_plates = license_plates.filtered(lambda lp: lp.state == 'closed')
                    if closed_license_plates:
                        # Fetch all products from the closed license plates
                        available_products = closed_license_plates.mapped('license_plate_order_line_ids.product_id')
                        # Set available products
                        line.available_product_ids = [(6, 0, available_products.ids)]
                    else:
                        line.available_product_ids = [(5,)]  # Clear the field if no valid license plates are found
                else:
                    line.available_product_ids = [(5,)]  # Clear the field if no license plates are available

    @api.depends('product_id', 'wizard_id.license_plate_ids')
    def _compute_available_quantity(self):
        """
        Compute the available quantity for the product by summing up the quantities from all selected license plates in the wizard.
        """
        for line in self:
            if line.wizard_id and line.wizard_id.license_plate_ids:
                move_lines = line.wizard_id.license_plate_ids.mapped(
                    'license_plate_order_line_ids').filtered(lambda m: m.product_id == line.product_id)
                line.available_quantity = sum(move_lines.mapped('quantity'))
            else:
                line.available_quantity = 0.0

    @api.depends('product_id', 'wizard_id.license_plate_ids')
    def _compute_remaining_quantity(self):
        """
        Compute the remaining quantity for the product by subtracting the total quantity already selected
        from the available quantity across multiple license plates.
        """
        for line in self:
            if line.wizard_id and line.wizard_id.license_plate_ids:
                # Total quantity that has already been selected for this product across all lines in the wizard
                total_quantity_selected = sum(
                    l.quantity for l in line.wizard_id.line_ids if l.product_id == line.product_id)

                # Get all the license plate lines for the product across all selected license plates
                move_lines = line.wizard_id.license_plate_ids.mapped(
                    'license_plate_order_line_ids').filtered(lambda m: m.product_id == line.product_id)

                # Sum of remaining quantities available across license plates
                available_qty = sum(move_lines.mapped('remaining_qty'))

                # Calculate remaining quantity
                remaining_qty = available_qty - total_quantity_selected

                # Assign remaining quantity, ensuring it doesn't go below zero
                line.remaining_quantity = max(remaining_qty, 0)
            else:
                line.remaining_quantity = 0.0

    @api.depends('wizard_id.crate_barcode', 'partition_code')
    def _compute_bin_code(self):
        """Compute the bin_code as a combination of crate_barcode and partition_code in the wizard."""
        for line in self:
            crate_barcode = line.wizard_id.crate_barcode
            partition_code = line.partition_code
            if crate_barcode and partition_code:
                line.bin_code = f"{crate_barcode}F{partition_code}"
            else:
                line.bin_code = False

    @api.onchange('automation_decanting_process_id')
    def _onchange_process_id(self):
        """Ensure the line limit is checked when changing the process in the wizard."""
        if self.automation_decanting_process_id:
            current_line_count = len(self.line_ids)  # Use the wizard's line_ids
            if current_line_count > self.automation_decanting_process_id.container_partition:
                raise ValidationError(
                    "You are not allowed to add more than {} items.".format(
                        self.automation_decanting_process_id.container_partition)
                )

    @api.onchange('quantity')
    def onchange_quantity(self):
        """Ensure that the entered quantity does not exceed the remaining quantity in the wizard."""
        for line in self:
            # Recompute the remaining quantity based on the current data in the wizard
            line._compute_remaining_quantity()

            # Check if the entered quantity exceeds the remaining quantity
            if line.remaining_quantity < 0:
                if line.remaining_quantity < line.quantity:
                    return {
                        'warning': {
                            'title': _("Invalid Quantity"),
                            'message': _(
                                "The selected quantity (%s) is greater than the actual remaining quantity (%s)." % (
                                line.quantity, line.remaining_quantity)),
                        }
                    }

    @api.onchange('wizard_id', 'product_id')
    def _onchange_assign_partition_code(self):
        """
        Assign partition code when a new product line is added or modified.
        This uses the current line count and container partition from the wizard.
        """
        if self.wizard_id:
            wizard = self.wizard_id
            decanting_process = wizard.automation_decanting_process_id

            if decanting_process:
                # Get the current line count
                current_line_count = len(decanting_process.automation_decanting_process_line_ids)

                # Calculate partition code based on current line count and container partition
                container_partition = decanting_process.container_partition
                partition_code = self._generate_partition_code(current_line_count, container_partition)

                # Assign partition code to the line
                self.partition_code = partition_code

    def _generate_partition_code(self, line_index, container_partition):
        """
        Generate partition code based on line index and container partition.
        For the wizard, this ensures that partition codes are dynamically generated.
        """
        partition_group = (line_index // 2) + 1  # Determine the group number (1A, 1B, etc.)
        partition_letter = chr(65 + (line_index % 2))  # 65 is the ASCII for 'A'
        return "{}{}".format(partition_group, partition_letter)

    # @api.model
    # def create(self, vals):
    #     """
    #     Override the create method to assign partition codes, check quantity,
    #     and validate partition limits before creation.
    #     """
    #     process_id = vals.get('automation_decanting_process_id')
    #     if process_id:
    #         process = self.env['automation.decanting.orders.process'].browse(process_id)
    #         current_line_count = len(process.automation_decanting_process_line_ids)
    #
    #         # Check partition limit before adding a new line
    #         partition_limit = process.container_partition
    #         if current_line_count >= partition_limit:
    #             raise ValidationError(
    #                 _("You cannot add more than %s items to the container.") % partition_limit)
    #
    #         # Calculate partition_code based on current line count and container_partition
    #         partition_code = self._generate_partition_code(current_line_count, partition_limit)
    #         vals['partition_code'] = partition_code
    #
    #     # Call the original create method
    #     new_record = super(AutomationDecantingProductProcessLine, self).create(vals)
    #     # Check the quantity after creation
    #     # new_record.onchange_quantity()
    #     return new_record



