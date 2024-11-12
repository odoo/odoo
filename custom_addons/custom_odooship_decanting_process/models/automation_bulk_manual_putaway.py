# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
import json
import requests
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
class AutomationBulkManual(models.Model):
    _name = "automation.bulk.manual.putaway"
    _description = "Automation Bulk and Manual Putaway"

    name = fields.Char(string='Reference', required=True, default=lambda self: _('New'))
    license_plate_ids = fields.Many2many('license.plate.orders', string='License Plate Barcodes', track_visibility="always")
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Receipt Order')
    partner_id = fields.Many2one(related='picking_id.partner_id', string='Customer', store=True)
    tenant_code_id = fields.Many2one('tenant.code.configuration', string='Tenant Code', related='partner_id.tenant_code_id', store=True)
    site_code_id = fields.Many2one('site.code.configuration', related='picking_id.site_code_id', string='Site Code', store=True)
    location_dest_id = fields.Many2one(related='picking_id.location_dest_id', string='Destination location')
    source_document = fields.Char(related='picking_id.origin', store=True)
    box_pallet = fields.Selection([('box', 'Box'), ('pallet', 'Pallet')], string="Box/Pallet")
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', string="State")
    automation_manual = fields.Selection([('automation', 'Automation'), ('automation_bulk', 'Automation Bulk'), ('manual', 'Manual')], string='Automation Manual')
    delivery_receipt_order_id = fields.Many2one('delivery.receipt.orders', string='Delivery Receipt Order')
    automation_bulk_manual_putaway_line_ids = fields.One2many('automation.bulk.manual.putaway.line', 'automation_bulk_manual_id', string="Product Lines")


    @api.model
    def create(self, vals):
        # Check the type of automation_manual and assign the correct sequence
        if vals.get('automation_manual') == 'automation_bulk':
            # Retrieve the sequence for automation bulk
            vals['name'] = self.env['ir.sequence'].next_by_code('automation.bulk.putaway') or _('New')
        else:
            # Retrieve the sequence for manual
            vals['name'] = self.env['ir.sequence'].next_by_code('manual.putaway') or _('New')

        return super(AutomationBulkManual, self).create(vals)


    def send_message_to_automation(self):
        """Send data to external system with exact payload structure."""
        receipt_list = []
        sku_list = []
        stock_quant_obj = self.env['stock.quant']
        for line in self.automation_bulk_manual_putaway_line_ids:
            sku_list.append({
                "sku_code": line.product_id.default_code,  # Assuming SKU is stored in `default_code`
                "owner_code": self.tenant_code_id.name,
                "sku_level": 0,
                "amount": line.quantity,
                "out_batch_code": "ECOM",
                "batch_property07": "yyy",
                "batch_property08": "zzz"
            })
            stock_quant_obj._update_available_quantity(
                product_id=line.product_id,
                location_id=line.location_dest_id,
                quantity=line.quantity,
            )
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

        # Define URL based on environment settings
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        # url_automation_putaway = (
        #     "https://shiperooconnect-prod.automation.shiperoo.com/api/interface/automationputaway"
        #     if is_production == 'True'
        #     else "https://shiperooconnect.automation.shiperoo.com/api/interface/automationputaway"
        # )
        headers = {'Content-Type': 'application/json'}

        # Convert data to JSON and send it to the API
        json_data = json.dumps(data, indent=4)
        _logger.info(f"Generated data for automation putaway: {json_data}")

        try:
            response = requests.post(url_automation_putaway, headers=headers, data=json_data)
            if response.status_code == 200:
                self.state = 'done'
            else:
                self.state = 'draft'
                raise UserError(f"Failed to send message: {response.status_code} - {response.content.decode()}")

        except requests.exceptions.RequestException as e:
            self.state = 'draft'
            raise UserError(f"Error sending message: {str(e)}")

        return {'type': 'ir.actions.act_window_close'}


    # def assign_to_free_location(self):
    #     free_location = self.env['stock.location'].search([('is_free', '=', True)], limit=1)
    #     if free_location:
    #         self.location_id = free_location

    @api.onchange('license_plate_ids')
    def _onchange_license_plate_ids(self):
        """
        Ensure all selected license plates belong to the same picking_id and DRD.
        Set picking_id and other fields based on the first license plate scanned.
        Validate if subsequent plates match the picking_id, DRD, and selection type.
        """
        if self.license_plate_ids:
            # Clear automation_bulk_manual_putaway_line_ids to prevent duplication
            self.automation_bulk_manual_putaway_line_ids = [(5, 0, 0)]

            # Get picking_id and DRD from the first license plate
            first_picking_id = self.license_plate_ids[0].picking_id
            first_drd = self.license_plate_ids[0].delivery_receipt_order_id  # Assuming DRD is stored in this field
            first_selection_type = self.license_plate_ids[0].automation_manual

            # Check each license plate for matching picking_id, DRD, and selection type
            for license_plate in self.license_plate_ids:
                if license_plate.picking_id != first_picking_id or license_plate.delivery_receipt_order_id != first_drd:
                    # Clear license_plate_ids field and raise validation error if picking or DRD mismatches
                    self.license_plate_ids = False
                    raise ValidationError(
                        _("All selected License Plates must belong to the same Picking Order and DRD. "
                          "License Plate '%s' does not match." % license_plate.name)
                    )

                if license_plate.automation_manual != first_selection_type:
                    # Clear license_plate_ids field and raise a warning if selection types mismatch
                    self.license_plate_ids = False
                    raise ValidationError(
                        _("All selected License Plates must be of the same type (Automation Bulk or Manual Bulk). "
                          "License Plate '%s' has a different type." % license_plate.name)
                    )

            # Set fields based on the first license plate’s picking_id and DRD
            self.picking_id = first_picking_id
            self.delivery_receipt_order_id = first_drd  # Set DRD to the matched DRD
            self.automation_manual = first_selection_type

            # Populate product lines based on selected license plates
            product_lines = []
            for license_plate in self.license_plate_ids:
                for line in license_plate.license_plate_order_line_ids:
                    product_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        # Additional fields can be set here if needed
                    }))
            self.automation_bulk_manual_putaway_line_ids = product_lines
        else:
            # Clear fields if no license plates are selected
            self.picking_id = False
            self.delivery_receipt_order_id = False
            self.automation_bulk_manual_putaway_line_ids = False


class AutomationBulkManualPutawayLine(models.Model):
    _name = 'automation.bulk.manual.putaway.line'
    _description = 'Automation Bulk Manual Putaway Line'

    automation_bulk_manual_id = fields.Many2one('automation.bulk.manual.putaway', string="Putaway Process")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    sku_code = fields.Char(related='product_id.default_code', string='SKU', store=True)
    quantity = fields.Float(string='Quantity', required=True)
    barcode = fields.Char(string='Item Barcode')
    section = fields.Integer(string='Section')
    picking_id = fields.Many2one('stock.picking', string='Receipt Order', related='automation_bulk_manual_id.picking_id', store=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', related='picking_id.location_dest_id', store=True)
