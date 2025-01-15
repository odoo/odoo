# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
import requests
import xml.etree.ElementTree as ET
import base64
import urllib
import pyodbc

_logger = logging.getLogger(__name__)


class PackDeliveryReceiptWizard(models.TransientModel):
    _name = 'pack.delivery.receipt.wizard'
    _description = 'Pack Delivery Receipt Wizard'

    line_ids = fields.One2many('pack.delivery.receipt.wizard.line', 'wizard_id', string='Product Lines')
    pack_bench_id = fields.Many2one('pack.bench.configuration', string='Pack Bench')
    package_box_type_id = fields.Many2one('package.box.configuration', string='Package Box Type')
    picking_id = fields.Many2one('stock.picking', string='Select Receipt')
    state = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], string='State', default='open')
    package_id = fields.Many2one('package.configuration', string='Select Package Type')
    pack_count = fields.Integer('Pack Count')

    def _split_address(self):
        """
        Splits the full address into components (Street, City, State, Postal Code).
        This assumes that the address is in a single string format (e.g., "U 1 19 Ascot St, Doncaster East, VIC, 3109").
        """
        address = self.picking_id.partner_id.street or ""
        # Split the address by commas
        address_parts = [part.strip() for part in address.split(',')]

        # Define default values for address components
        add1 = address_parts[0] if len(address_parts) > 0 else ""
        add2 = address_parts[1] if len(address_parts) > 1 else ""
        add3 = address_parts[2] if len(address_parts) > 2 else ""
        add4 = address_parts[3] if len(address_parts) > 3 else ""
        add5 = address_parts[4] if len(address_parts) > 4 else ""
        add6 = ""  # Empty by default
        return add1, add2, add3, add4, add5, add6

    def _generate_xml(self):
        """
        Generates a complete XML representation of the wizard data.
        """
        root = ET.Element("ConnoteObject")
        connote = ET.SubElement(root, "Connote")

        # Add general details
        ET.SubElement(connote, "ConDate").text = self.picking_id.scheduled_date.strftime(
            '%d/%m/%Y') if self.picking_id.scheduled_date else ""
        ET.SubElement(connote, "Printer").text = "S3"  # Workstation ID assigned in SmartFreight
        ET.SubElement(connote, "Reference").text = ""  # Blank
        ET.SubElement(connote, "RecAccNo").text = "SHO005"
        ET.SubElement(connote, "RecName").text = self.picking_id.partner_id.name[
                                                 :50] if self.picking_id.partner_id.name else ""
        ET.SubElement(connote, "RecPh").text = self.picking_id.partner_id.phone or ""
        ET.SubElement(connote, "RecContact").text = self.picking_id.partner_id.name[
                                                    :30] if self.picking_id.partner_id.name else ""
        ET.SubElement(connote, "RecEmail").text = self.picking_id.partner_id.email or ""

        # Add recipient address
        rec_addr = ET.SubElement(connote, "RecAddr")
        # Split the address properly
        add1, add2, add3, add4, add5, add6 = self._split_address()

        # Assign the split address parts to the XML elements
        ET.SubElement(rec_addr, "add1").text = add1
        ET.SubElement(rec_addr, "add2").text = add2
        ET.SubElement(rec_addr, "add3").text = add3
        ET.SubElement(rec_addr, "add4").text = add4
        ET.SubElement(rec_addr, "add5").text = add5
        ET.SubElement(rec_addr, "add6").text = add6

        # Add sender details
        ET.SubElement(connote,"sendaccno").text ="NSW"
        ET.SubElement(connote,"matchsendertoaccountno").text ="YES"
        # ET.SubElement(connote, "SendName").text = "TSCO Pty Ltd"  # Always the same value
        # ET.SubElement(connote, "SendPh").text = ""
        # ET.SubElement(connote, "SendEmail").text = "customer.service@jbswear.com.au"
        #
        # send_addr = ET.SubElement(connote, "SendAddr")
        # ET.SubElement(send_addr, "add1").text = "Cnr Grieve Pde and Taras Ave"
        # ET.SubElement(send_addr, "add2").text = ""
        # ET.SubElement(send_addr, "add3").text = "Altona North"
        # ET.SubElement(send_addr, "add4").text = "Vic"
        # ET.SubElement(send_addr, "add5").text = "3025"
        # ET.SubElement(send_addr, "add6").text = ""

        # Add processing details
        # Add processing details with modified logic
        if self.picking_id.sale_id.carrier == 'Premium Satchel':
            ET.SubElement(connote, "ChargeTo").text = "S"  # Always the same value
            ET.SubElement(connote, "CarrierName").text = "Startracker EXP"  # Updated carrier name for Premium Satchel
            ET.SubElement(connote, "AccNo").text = "10151511"  # Account number for Premium Satchel
            ET.SubElement(connote, "Service").text = "FP PREMIUM"  # Service type for Premium Satchel
            ET.SubElement(connote, "autoconsolidate").text = "a"  # Always the same value

        elif self.picking_id.sale_id.carrier == 'PICKUP':
            ET.SubElement(connote, "ChargeTo").text = "S"  # Always the same value
            ET.SubElement(connote, "CarrierName").text = "PICK-UP"  # Carrier name for Pickup
            ET.SubElement(connote, "AccNo").text = "PICK-UP"  # Account number for Pickup
            ET.SubElement(connote, "Service").text = "PICK-UP"  # Service type for Pickup
            ET.SubElement(connote, "autoconsolidate").text = "a"  # Always the same value

        else:  # Default to Standard Courier/cheapest logic
            ET.SubElement(connote, "ChargeTo").text = "S"  # Always the same value
            ET.SubElement(connote, "ApplyLeastCost").text = "Yes"  # Apply least cost logic for Standard Courier
            ET.SubElement(connote, "autoconsolidate").text = "a"  # Always the same value

        # Add additional references
        additional_refs = ET.SubElement(connote, "AdditionalReferences")
        ET.SubElement(additional_refs, "ReferenceNo").text = self.picking_id.origin or ""
        ET.SubElement(additional_refs, "ReferenceNo").text = ""  # Blank

        # Add freight line details
        for line in self.line_ids:
            freight_line = ET.SubElement(connote, "FreightLineDetails")
            ET.SubElement(freight_line, "Ref").text = self.picking_id.sale_id.origin or ""
            ET.SubElement(freight_line, "Desc").text = "CTN"  # Or SAT based on logic
            ET.SubElement(freight_line, "Wgt").text = f"{line.weight * line.quantity:.2f}" or "1" # Rounded to 2 decimals
            ET.SubElement(freight_line, "Amt").text = str(line.quantity)  # Converted to string

            # Safely retrieve dimensions with default values of 0 if not set
            length = self.package_box_type_id.length or 0
            width = self.package_box_type_id.width or 0
            height = self.package_box_type_id.height or 0

            # Add dimensions to the XML with formatted values
            ET.SubElement(freight_line, "len").text = f"{length:.2f}"
            ET.SubElement(freight_line, "wdt").text = f"{width:.2f}"
            ET.SubElement(freight_line, "hgt").text = f"{height:.2f}"

            # Calculate and add cube value
            cube = (length * width * height) / 1_000_000  # Convert mm³ to m³
            ET.SubElement(freight_line, "Cube").text = f"{cube:.5f}"

        # Convert XML to string
        xml_data = ET.tostring(root, encoding='utf-8', method='xml')
        return xml_data

    def send_xml_to_jb_receiver(self, xml_data=None, payload=None):
        """
        Sends the payload (in JSON format) or XML data to the jb_xml_receiver API.
        """
        # Prepare the product line details as part of the payload if it's not provided
        if payload is None:
            product_lines = []
            for line in self.line_ids:
                product_lines.append({
                    "sku_code": line.product_id.default_code,
                    "name": line.product_id.name,
                    "quantity": line.quantity,
                    "remaining_quantity": line.remaining_quantity,
                    "product_packaging_id": line.product_packaging_id.name,
                    "product_packaging_qty": line.product_packaging_qty,
                })

            # Prepare the receipt list as required
            receipt_list = [{
                "receipt_number": self.picking_id.name,
                "partner_id": self.picking_id.partner_id.name,
                "tenant_code": self.picking_id.tenant_code_id.name,
                "site_code": self.picking_id.site_code_id.name,
                "origin": self.picking_id.origin or "N/A",
                "sales_order_number": self.picking_id.sale_id.name or "N/A",
                "sales_order_carrier": self.picking_id.sale_id.carrier or "N/A",
                "sales_order_origin": self.picking_id.sale_id.origin or "N/A",
                "product_lines": product_lines,  # Add the product lines
            }]

            # Prepare the final data structure
            data = {
                "body": {
                    "receipt_list": receipt_list
                },
                "header": {
                    "user_id": "system",
                    "user_key": "system",
                    "warehouse_code": self.picking_id.site_code_id.name  # Site Code
                }
            }
        else:
            data = payload

        # Convert data to JSON format
        json_data = json.dumps(data, indent=4)

        # Log the generated data
        _logger.info(f"Generated data for API request: {json_data}")

        # Define the API URL based on the environment
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        api_url = (
            "https://shiperooconnect-prod.automation.shiperoo.com/api/process_so"
            if is_production == 'True'
            else "https://shiperooconnect.automation.shiperoo.com/api/process_so"
        )

        # Prepare headers for the request
        headers = {
            'Content-Type': 'application/json',  # Set content type as JSON
        }

        try:
            # Send the payload to the API
            response = requests.post(api_url, headers=headers, data=json_data)
            response.raise_for_status()  # Will raise an exception for HTTP errors
            _logger.info(f"Payload sent successfully to {api_url}: {json_data}")

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error sending payload to jb_xml_receiver: {str(e)}")
            raise UserError(f"Error sending payload to jb_xml_receiver: {str(e)}")

    @api.model
    def default_get(self, fields):
        """
        Override the default_get method to automatically set the picking_id
        based on the active_id in the context when the wizard is opened.
        """
        res = super(PackDeliveryReceiptWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            picking_order = self.env['stock.picking'].browse(active_id)
            res['picking_id'] = picking_order.id  # Automatically set the picking_id
            res['pack_count'] = picking_order.duplicate_pack_count
        return res

    def delivery_package_done(self):
        """
        Delivers the package, generates XML, and sends it to jb_xml_receiver.
        """
        xml_data = self._generate_xml()
        if self.picking_id.tenant_code_id.name == 'JB1':
            # Create the attachment
            attachment_vals = {
                'name': f"JB_XML_{self.picking_id.origin}.xml",  # The name of the file
                'type': 'binary',  # File type
                'datas': base64.b64encode(xml_data),  # Encode the XML data to base64
                'res_model': 'stock.picking',  # The model to which the attachment will be linked
                'res_id': self.picking_id.id,  # The ID of the picking record
                'mimetype': 'application/xml',  # MIME type for XML file
            }

            try:
                attachment = self.env['ir.attachment'].create(attachment_vals)  # Create the attachment record
                _logger.info(f"XML data saved as attachment with ID: {attachment.id}")
            except Exception as e:
                _logger.error(f"Error creating attachment: {str(e)}")
                raise UserError(f"Error creating attachment: {str(e)}")

        # Send XML data to jb_xml_receiver API
        self.send_xml_to_jb_receiver(xml_data)
        #
        # # Update state and pack count
        # self.state = 'closed'
        self.pack_count += 1
        self.picking_id.duplicate_pack_count = self.pack_count

        # Feedback to the user
        return {
            'type': 'ir.actions.act_window_close',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'XML data successfully saved as attachment!',
                'type': 'success',
            },
        }


class PackageDeliveryReceiptWizardLine(models.TransientModel):
    _name = 'pack.delivery.receipt.wizard.line'
    _description = 'Delivery Receipt Wizard Line'

    wizard_id = fields.Many2one('pack.delivery.receipt.wizard', string='Wizard Reference', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 domain="[('id', 'in', available_product_ids)]")
    quantity = fields.Float(string='Quantity', required=True)
    available_quantity = fields.Float(string='Expected Quantity', compute='_compute_quantity', store=True)
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity', store=True)
    available_product_ids = fields.Many2many('product.product', string='Available Products',
                                             compute='_compute_available_products')
    location_dest_id = fields.Many2one('stock.location', string='Destination location')
    picking_id = fields.Many2one('stock.picking', string='Receipt')
    product_packaging_id = fields.Many2one('stock.move', string='Packaging')
    product_packaging_qty = fields.Float(string='Packaging Quantity')
    weight = fields.Float(string='Weight', required=True)

    @api.depends('wizard_id.picking_id')
    def _compute_available_products(self):
        """
        Compute the available products based on the selected picking.
        """
        for line in self:
            picking = line.wizard_id.picking_id
            if picking:
                product_ids = picking.move_ids_without_package.mapped('product_id.id')
                line.available_product_ids = [(6, 0, product_ids)]
            else:
                line.available_product_ids = [(6, 0, [])]

    @api.depends('wizard_id.picking_id', 'product_id')
    def _compute_quantity(self):
        """
        Automatically fetch the quantity from the picking for the selected product.
        """
        for line in self:
            picking = line.wizard_id.picking_id
            if picking and line.product_id:
                move = picking.move_ids_without_package.filtered(lambda m: m.product_id == line.product_id)
                line.available_quantity = sum(move.mapped('product_uom_qty'))
                line.weight = line.product_id.weight
            else:
                line.available_quantity = 0

    @api.depends('quantity', 'available_quantity')
    def _compute_remaining_quantity(self):
        """
        Compute remaining quantity as the difference between available quantity and entered quantity.
        """
        for line in self:
            picking = line.wizard_id.picking_id
            move = picking.move_ids_without_package.filtered(lambda m: m.product_id == line.product_id)
            line.remaining_quantity = sum(move.mapped('remaining_packed_qty'))
            line.remaining_quantity = line.remaining_quantity - line.quantity

    @api.constrains('quantity', 'available_quantity')
    def _check_quantity(self):
        """
        Validate that the entered quantity does not exceed the available quantity.
        """
        for line in self:
            if line.quantity > line.available_quantity:
                raise ValidationError(_(
                    f"The entered quantity ({line.quantity}) for product {line.product_id.name} exceeds the available quantity ({line.available_quantity})."
                ))
