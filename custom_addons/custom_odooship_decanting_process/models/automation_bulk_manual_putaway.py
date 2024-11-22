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
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Receipt Order', store=True)
    partner_id = fields.Many2one(related='picking_id.partner_id', string='Customer', store=True)
    tenant_code_id = fields.Many2one('tenant.code.configuration', string='Tenant Code', related='partner_id.tenant_code_id', store=True)
    site_code_id = fields.Many2one('site.code.configuration', related='picking_id.site_code_id', string='Site Code', store=True)
    parent_location_id = fields.Many2one('stock.location',string='Source location')
    location_dest_id = fields.Many2one('stock.location',string='Destination location',domain="[('location_id', '=', parent_location_id)]")
    source_document = fields.Char(store=True)
    box_pallet = fields.Selection([('box', 'Box'), ('pallet', 'Pallet')], string="Box/Pallet")
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', string="State")
    automation_manual = fields.Selection([('automation', 'Automation'), ('automation_bulk', 'Automation Bulk'), ('manual', 'Manual')], string='Automation Manual')
    delivery_receipt_order_id = fields.Many2one('delivery.receipt.orders', string='Delivery Receipt Order')
    automation_bulk_manual_putaway_line_ids = fields.One2many('automation.bulk.manual.putaway.line', 'automation_bulk_manual_id', string="Product Lines")

    @api.onchange('location_dest_id')
    def _onchange_location_dest_id(self):
        """
            Check empty location
        """
        if self.location_dest_id.filled == True:
            raise ValidationError(
                "The selected location is already in use and cannot be assigned. Please choose a different available location.")
    @api.onchange('parent_location_id')
    def _onchange_parent_location_id(self):
        """
        Dynamically filter location_dest_id based on parent_location_id.
        """
        if self.parent_location_id:
            return {
                'domain': {
                    'location_dest_id': [('location_id', '=', self.parent_location_id.id),
                                         ('filled', '=',False)]
                }
            }
        return {
            'domain': {
                'location_dest_id': []
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Check if name should be generated based on the selection field
            if not vals.get('name') or vals['name'] == _('New'):
                if vals.get('automation_manual') == 'automation_bulk':
                    # Generate sequence for automation bulk
                    vals['name'] = self.env['ir.sequence'].next_by_code('automation.bulk.putaway') or _('New')
                elif vals.get('automation_manual') == 'manual':
                    # Generate sequence for manual putaway
                    vals['name'] = self.env['ir.sequence'].next_by_code('manual.putaway') or _('New')
        return super(AutomationBulkManual, self).create(vals_list)

    def _get_next_available_location(self):
        """
        Finds the next available manual location under the parent location.
        Filters locations where location_id matches the parent_location_id.
        """
        if not self.parent_location_id:
            raise ValidationError(
                _("The source location (parent location) is not defined. Please set the source location for this operation.")
            )

        parent_location = self.parent_location_id

        # Fetch child locations under the parent location
        free_locations = self.env['stock.location'].search([
            ('location_id', '=', parent_location.id),  # Filter locations with location_id matching parent_location_id
            ('filled', '=', False)  # Ensure the location is not filled
        ], order='name')

        if not free_locations:
            raise ValidationError(_("No available manual locations under '%s'." % parent_location.name))

        # Return the first available location
        return free_locations[0]

    @api.onchange('license_plate_ids')
    def _onchange_license_plate_ids(self):
        """
        Ensure all selected license plates belong to the same picking_id and DRD.
        Assign the next free location for each product if manual is selected.
        """
        if self.license_plate_ids:
            # Clear automation_bulk_manual_putaway_line_ids to prevent duplication
            self.automation_bulk_manual_putaway_line_ids = [(5, 0, 0)]

            first_picking_id = self.license_plate_ids[0].picking_id
            first_drd = self.license_plate_ids[0].delivery_receipt_order_id
            first_selection_type = self.license_plate_ids[0].automation_manual
            first_location_dest_id = self.license_plate_ids[0].location_dest_id
            first_source_document = self.picking_id.origin

            # Validation for license plates
            for license_plate in self.license_plate_ids:
                if license_plate.picking_id != first_picking_id or license_plate.delivery_receipt_order_id != first_drd:
                    self.license_plate_ids = [(5,0,0)]
                    self.picking_id = False
                    self.delivery_receipt_order_id = False
                    self.parent_location_id = False
                    self.location_dest_id = False
                    self.automation_bulk_manual_putaway_line_ids = [(5, 0, 0)]
                    return {
                        'warning': {
                            'title': _("Invalid Operation"),
                            'message': _("All selected License Plates must belong to the same Picking Order and DRD. "
                              "License Plate '%s' does not match." % license_plate.name),
                        }
                    }

                if license_plate.automation_manual != first_selection_type:
                    self.license_plate_ids = [(5, 0, 0)]
                    self.picking_id = False
                    self.delivery_receipt_order_id = False
                    self.parent_location_id = False
                    self.location_dest_id = False
                    self.automation_bulk_manual_putaway_line_ids = [(5, 0, 0)]
                    return {
                        'warning': {
                            'title': _("Invalid Operation"),
                            'message': _("All selected License Plates must be of the same type (Automation Bulk or Manual Bulk). "
                  "License Plate '%s' has a different type." % license_plate.name),
                        }
                    }
                if license_plate.automation_manual not in  ['automation_bulk', 'manual']:
                    self.license_plate_ids = [(5, 0, 0)]
                    self.picking_id = False
                    self.delivery_receipt_order_id = False
                    self.parent_location_id = False
                    self.location_dest_id = False
                    self.automation_bulk_manual_putaway_line_ids = [(5, 0, 0)]
                    return {
                        'warning': {
                            'title': _("Invalid Selection"),
                            'message': _(
                                "Invalid selection: The automation_manual type must be either 'Manual' or 'Automation Bulk', not 'Automation'."),
                            'sticky':False,
                        }
                    }
            # Set fields based on the first license plate
            self.picking_id = first_picking_id
            self.delivery_receipt_order_id = first_drd
            self.automation_manual = first_selection_type
            self.parent_location_id = first_location_dest_id
            self.source_document = first_source_document

            product_lines = []
            for license_plate in self.license_plate_ids:
                for line in license_plate.license_plate_order_line_ids:
                    location_dest_id = False
                    if self.automation_manual == 'manual':
                        # Find the next available manual location
                        current_location = self.parent_location_id
                        # location_dest = self._get_next_available_location(current_location)
                        # self.location_dest_id = location_dest_id.id

                        # Mark the location as filled
                        self.location_dest_id.filled = True
                    if self.automation_manual == 'automation_bulk':
                        self.location_dest_id = self.parent_location_id

                    product_lines.append((0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'location_dest_id': location_dest_id,
                    }))
            self.automation_bulk_manual_putaway_line_ids = product_lines
        else:
            self.picking_id = False
            self.delivery_receipt_order_id = False
            self.parent_location_id= False
            self.location_dest_id = False
            self.automation_bulk_manual_putaway_line_ids = False

    def update_manual_bulk_location(self):
        """
        Updates the location of manual products to location_dest_id by creating and validating
        a new internal transfer.
        """
        stock_picking_obj = self.env['stock.picking']

        if not self.automation_bulk_manual_putaway_line_ids:
            raise ValidationError(_("No product lines found to update inventory."))

        if self.automation_manual != 'manual':
            raise ValidationError(_("This operation is only allowed for manual putaways."))

        # Create an internal transfer (Picking Type: Internal Transfer)
        internal_transfer_vals = {
            'picking_type_id': self.env.ref('stock.picking_type_internal').id,  # Internal Transfer Type
            'location_id': self.parent_location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'origin': self.name,
            'move_ids_without_package': [],
        }

        # Prepare move lines
        move_lines = []
        for line in self.automation_bulk_manual_putaway_line_ids:
            move_vals = {
                'product_id': line.product_id.id,
                'name': line.product_id.display_name,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'location_id': self.parent_location_id.id,
                'location_dest_id': self.location_dest_id.id,
            }
            move_lines.append((0, 0, move_vals))

        internal_transfer_vals['move_ids_without_package'] = move_lines

        # Create the internal transfer
        internal_transfer = stock_picking_obj.create(internal_transfer_vals)

        # Confirm and reserve quantities
        internal_transfer.action_confirm()
        for move in internal_transfer.move_ids_without_package:
            move._action_assign()  # Ensure quantities are reserved
            for move_line in move.move_line_ids:
                move_line.quantity = line.quantity  # Set the quantities as done

        # Validate the transfer
        # try:
        #     internal_transfer.button_validate()
        # except ValidationError as e:
        #     raise ValidationError(_("Transfer validation failed: %s. Please ensure quantities are reserved." % str(e)))

        # Update the state to 'done'
        self.state = 'done'
        self.location_dest_id.filled = True
        _logger.info(f"Internal transfer {internal_transfer.name} created and validated for putaway process.")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': internal_transfer.id,
            'target': 'new',
        }

    def send_message_to_automation(self):
        """Send data to external system with exact payload structure."""
        receipt_list = []
        sku_list = []
        stock_quant_obj = self.env['stock.quant']
        # self.location_dest_id.filled=True
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
        #Define URL based on environment settings
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        url_automation_putaway = (
            "https://shiperooconnect-prod.automation.shiperoo.com/api/interface/automationputaway"
            if is_production == 'True'
            else "https://shiperooconnect.automation.shiperoo.com/api/interface/automationputaway"
        )
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
