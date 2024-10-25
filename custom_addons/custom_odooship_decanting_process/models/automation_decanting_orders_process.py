# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import requests

from odoo.tools.populate import compute

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
    crate_status = fields.Selection([('open', 'Open'),
                                     ('closed', 'Closed'),
                                     ('partially_filled', 'Partially Filled'),
                                     ('fully_filled', 'Fully Filled')],
                                    string='Crate Status', default='open')
    state = fields.Selection([
        ('draft', 'draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='State', default='draft')
    license_plate_ids = fields.Many2many('license.plate.orders', string='License Plate Barcodes')
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
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
    location_dest_id = fields.Many2one(related='picking_id.location_dest_id', string='Destination location')
    count_lines = fields.Integer(string='Count Lines')

    def action_open_decanting_wizard(self):
        """
        Opens the decanting product process wizard.
        """
        # Raise validation error if crate barcode is missing
        if not self.crate_barcode:
            raise ValidationError(_("Crate Barcode is required to process decanting."))

        # Raise validation error if no license plates are selected
        if not self.license_plate_ids:
            raise ValidationError(_("At least one License Plate must be selected to process decanting."))

        # Raise validation error if no container is selected
        if not self.container_id:
            raise ValidationError(_("Container is required to process decanting."))
        if self.count_lines == self.container_partition:
            raise ValidationError(_("No partition left."))
        self.state = 'in_progress'
        return {
            'type': 'ir.actions.act_window',
            'name': 'Decanting Product Process Wizard',
            'res_model': 'automation.decanting.product.process.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_automation_decanting_process_id': self.id,
                'default_license_plate_ids': self.license_plate_ids.ids,
                'default_container_id': self.container_id.id,
                'default_crate_barcode': self.crate_barcode,
            }
        }

    @api.onchange('license_plate_ids')
    def _onchange_license_plate_ids(self):
        """
        Ensure all selected license plates belong to the same picking_id.
        Set picking_id based on the first license plate scanned, and validate
        if subsequent plates match the picking_id.
        """
        if self.license_plate_ids:
            # Get the picking_id from the first license plate
            first_picking_id = self.license_plate_ids[0].picking_id

            # Check if all license plates belong to the same picking_id
            for license_plate in self.license_plate_ids:
                if license_plate.picking_id != first_picking_id:
                    raise ValidationError(
                        _("All selected License Plates must belong to the same Picking Order. "
                          "License Plate '%s' does not belong to the same picking order." % license_plate.name)
                    )

            # Set picking_id based on the first license plate
            self.picking_id = first_picking_id
        else:
            self.picking_id = False

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

    # @api.onchange('license_plate_ids')
    # def _onchange_license_plate_ids(self):
    #     """Allow only closed license plates with done delivery receipt order."""
    #     for license_plate in self.license_plate_ids:
    #         if license_plate.state != 'closed' or license_plate.automation_manual != 'automation':
    #             raise ValidationError(
    #                 f"The selected License Plate '{license_plate.name}' is not available or its status is not 'closed'."
    #             )
            # Check the related delivery receipt order
            # delivery_order = self.license_plate_id.delivery_receipt_order_id
            # if delivery_order and delivery_order.state != 'done':
            #     raise ValidationError(
            #         f"The related Delivery Receipt Order '{delivery_order.name}' is still in progress. "
            #         "Please complete the order (Manual/Automation Order Process) before proceeding."
            #     )


    def check_crate_status(self):
        """
        Checks the crate status to determine if it is 'fully_filled' or 'partially_filled' based on the container partition.
        """
        for record in self:
            total_lines = len(record.automation_decanting_process_line_ids)
            if record.count_lines >= record.container_partition:
                record.crate_status = 'fully_filled'
            elif record.count_lines > 0:
                record.crate_status = 'partially_filled'
            else:
                record.crate_status = 'open'

    def write(self, vals):
        # If crate is closed, do not allow any modifications
        for record in self:
            # if record.state == 'done' or record.crate_status == 'closed':
            #     raise ValidationError(_("You cannot modify a closed or completed crate."))

            if 'automation_decanting_process_line_ids' in vals:
                # Check if crate is fully filled
                if record.crate_status == 'fully_filled':
                    raise ValidationError(_("The crate is fully filled. You cannot add new product lines."))

        result = super(AutomationDecantingOrdersProcess, self).write(vals)
        # self.check_crate_status()  # Update the crate status after changes
        return result

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
        stock_quant_obj = self.env['stock.quant']
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
            # Create stock move to update inventory location
            quant = stock_quant_obj.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', self.picking_id.location_dest_id.id)
            ], limit=1)

            if quant:
                # If the quant exists, adjust the quantity
                quant.sudo().quantity -= line.quantity  # Reduce the quantity from the current location
            else:
                raise UserError(f"No quant found for product '{line.product_id.name}' in the current location.")

            # Now update the destination location with the new quantity
            destination_quant = stock_quant_obj.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', self.location_dest_id.id)
            ], limit=1)

            if destination_quant:
                # If quant exists in the destination, increase the quantity
                destination_quant.sudo().quantity += line.quantity
            else:
                # If no quant exists, create a new one in the destination location
                stock_quant_obj.sudo().create({
                    'product_id': line.product_id.id,
                    'location_id': self.location_dest_id.id,
                    'quantity': line.quantity,
                    'in_date': fields.Datetime.now(),  # Optional: to track the update time
                })

        # Add the receipt entry
        receipt_list.append({
            "warehouse_code": self.site_code_id.name,  # Site Code
            "receipt_code": self.name,  # Decanting Order Name as Receipt Code
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
        #
        # # Log the generated data
        _logger.info(f"Generated data for crate close: {json_data}")
        #
        # # Define the URLs for Shiperoo Connect
        # # url_geekplus = "https://shiperooconnect.automation.shiperoo.com/api/interface/geekplus/"
        url_automation_putaway = "https://shiperooconnect.automation.shiperoo.com/api/interface/automationputaway"
        #
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
        records = super(AutomationDecantingOrdersProcess, self).create(vals_list)
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('automation.decanting.orders.process') or _('New')

        return records



class AutomationDecantingOrdersProcessLine(models.Model):
    _name = 'automation.decanting.orders.process.line'
    _description = 'Decanting Orders process line'

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
    )
    sku_code = fields.Char(related='product_id.default_code', string='SKU')
    quantity = fields.Float(string='Quantity')
    barcode = fields.Char(string='Item Barcode')
    automation_decanting_process_id = fields.Many2one('automation.decanting.orders.process', string='Decanting Process')
    section = fields.Integer(string='Section')
    partition_code = fields.Char(string='Partition Code')
    bin_code = fields.Char(string='Bin Code', compute='_compute_bin_code')
    available_product_ids = fields.Many2many('product.product', string='Available Products')
    available_quantity = fields.Float(string='Available Quantity')
    remaining_quantity = fields.Float(string='Remaining Quantity')


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
        # new_record.onchange_quantity()
        return new_record

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

    def _generate_partition_code(self, line_index, container_partition):
        """Generate partition code based on line index and container partition."""
        partition_group = (line_index // 2) + 1  # Determine the group number (1A, 1B, etc.)
        partition_letter = chr(65 + (line_index % 2))  # 65 is the ASCII for 'A'
        return "{}{}".format(partition_group, partition_letter)
