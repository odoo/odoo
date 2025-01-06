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
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, default=lambda self: _('New'))
    barcode_option = fields.Selection([('pallet', 'Pallet'),
                                       ('Box', 'Box'),
                                       ('crate', 'Crate'),])
    pallet_barcode = fields.Char(string='License Plate Barcode',  track_visibility="always")
    hu_barcode = fields.Char(string='Handling Unit Barcode')
    crate_barcode = fields.Char(string='Crate Barcode',  track_visibility="always")
    container_id = fields.Many2one('crate.container.configuration', string='Container')
    container_partition = fields.Integer(related='container_id.crate_container_partition', string='Container Partition')
    container_code = fields.Char(related='container_id.crate_code', string='Container Code')
    automation_decanting_process_line_ids = fields.One2many('automation.decanting.orders.process.line',
                            'automation_decanting_process_id', string='Items', tracking=True)
    crate_status = fields.Selection([('open', 'Open'),
                                     ('closed', 'Closed'),
                                     ('partially_filled', 'Partially Filled'),
                                     ('fully_filled', 'Fully Filled')],
                                    string='Crate Status', default='open', track_visibility="always")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
    ], string='State', default='draft', track_visibility="always")
    license_plate_ids = fields.Many2many('license.plate.orders', string='License Plate Barcodes',  track_visibility="always")
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Receipt Order'
    )
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
    location_dest_id = fields.Many2one(related='picking_id.location_dest_id', string='Destination location')
    count_lines = fields.Integer(string='Count Lines')
    source_document = fields.Char(related='picking_id.origin', store=True)

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
                'default_picking_id': self.picking_id.id,
                'default_updated_count_lines': self.count_lines,
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
                if license_plate.automation_manual != 'automation':
                    raise ValidationError(
                        _("License Plate '%s' is not of type 'automation'. Please select only automation type license plates." % license_plate.name)
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
                ('site_code_id', '=', self.site_code_id.id)
            ], limit=1)

            # If crate not found or not available, raise a ValidationError
            if not crate:
                raise ValidationError(
                    f"The scanned Crate Barcode '{self.crate_barcode}' is not available for use. Please check the barcode and try again.")

    def action_button_close(self):
        """ Action button close method to update status, move stock, and close crate status."""
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

        stock_move_obj = self.env['stock.move']
        stock_quant_obj = self.env['stock.quant']

        # Loop through decanting process lines to handle stock movement
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
                # "batch_property07": 'yyy',  # Assuming Color is stored here
                "batch_property07": self.source_document,  # Assuming Color is stored here
                "batch_property08": 'zzz',
            })
            # Comment out this code because stock is updating through Receipt Wizard
            # stock_quant_obj._update_available_quantity(
            #     product_id=line.product_id,
            #     location_id=line.location_dest_id,
            #     quantity=line.quantity,
            #     # lot_id=line.lot_id,
            #     # package_id=line.package_id,
            #     # owner_id=line.owner_id
            # )
        # Add the receipt entry (for external systems or integration purposes)
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

        # Log the generated data
        _logger.info(f"Generated data for crate close: {json_data}")

        # Define the URLs for Shiperoo Connect
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')

        url_automation_putaway = (
            "https://shiperooconnect-prod.automation.shiperoo.com/api/interface/automationputaway"
            if is_production == 'True'
            else "https://shiperooconnect.automation.shiperoo.com/api/interface/automationputaway"
        )
        headers = {
            'Content-Type': 'application/json'
        }
        try:
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
        return super().create(vals_list)



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
    picking_id = fields.Many2one(
        string='Receipt Order',
        related = 'automation_decanting_process_id.picking_id',
        store=True
    )
    location_dest_id = fields.Many2one(related='picking_id.location_dest_id', string='Destination location')


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

    @api.depends('automation_decanting_process_id.crate_barcode', 'partition_code',
                 'automation_decanting_process_id.site_code_id')
    def _compute_bin_code(self):
        """Compute the bin_code based on site_code_id and other factors."""
        for line in self:
            process = line.automation_decanting_process_id
            crate_barcode = process.crate_barcode
            partition_code = line.partition_code
            site_code = process.site_code_id.name

            if crate_barcode and partition_code:
                if site_code == 'FC3':  # Special logic for site_code_id == 'FC3'
                    line.bin_code = f"{crate_barcode}F0{partition_code}"
                else:  # Default logic for other site codes
                    line.bin_code = f"{crate_barcode}F{partition_code}"
            else:
                line.bin_code = False


    def _generate_partition_code(self, line_index, container_partition):
        """Generate partition code based on line index and container partition."""
        # Calculate half of the container partition to determine how many items are in each group ('A' or 'B')
        half_partition = container_partition // 2

        if container_partition == 1:
            # Only 1 partition, return 1A
            return "1A"

        if container_partition == 2:
            # Two partitions, return 1A, 2A
            return f"{line_index + 1}A"

        # For 4 or 8 partitions
        partition_letter = 'A' if line_index < half_partition else 'B'  # First half 'A', second half 'B'
        partition_number = (line_index % half_partition) + 1  # Cycle through numbers up to half_partition
        return f"{partition_number}{partition_letter}"

    # def action_open_update_quantity_wizard(self):
    #     """
    #     Open the update quantity wizard.
    #     """
    #     return {
    #         'name': _('Update Quantity'),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'automation.decanting.update.quantity.wizard',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_decanting_line_id': self.id,
    #             'default_quantity': self.quantity,
    #             'default_product_id':self.product_id.id,
    #             'default_license_plate_order_id': self.automation_decanting_process_id.license_plate_ids.ids,
    #         }
    #     }

