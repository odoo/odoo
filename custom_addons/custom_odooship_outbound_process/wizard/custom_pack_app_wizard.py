# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
import requests
import xml.etree.ElementTree as ET
import urllib


_logger = logging.getLogger(__name__)


class PackDeliveryReceiptWizard(models.TransientModel):
    _name = 'custom.pack.app.wizard'
    _description = 'Pack Delivery Receipt Wizard'

    # Field to store the scanned PC container barcode
    pc_container_code_id = fields.Many2one(
        'pc.container.barcode.configuration', string='Scan Barcode', required=True
    )
    warehouse_id = fields.Many2one(related='pc_container_code_id.warehouse_id', store=True)
    site_code_id = fields.Many2one(related='pc_container_code_id.site_code_id', store=True)
    picking_ids = fields.Many2many('stock.picking', string='Pick Numbers', store=True)
    line_ids = fields.One2many('custom.pack.app.wizard.line', 'wizard_id', string='Product Lines')
    pack_bench_id = fields.Many2one('pack.bench.configuration', string='Pack Bench', required=True)
    package_box_type_id = fields.Many2one(
        'package.box.configuration', string='Package Box Type',
        help="Select packaging box for single picking.",
        required=True
    )
    show_package_box_in_lines = fields.Boolean(compute="_compute_show_package_box_in_lines", store=True)
    picking_id = fields.Many2one('stock.picking', string='Select Receipt')
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        compute='_compute_tenant_code',
        store=True
    )
    line_count = fields.Integer(string="Line Count", compute="_compute_fields_based_on_picking_ids", store=True)
    updated_line_count = fields.Integer(
        string="Updated Line Count", compute='_compute_updated_line_count', store=True
    )

    @api.depends('line_ids')
    def _compute_updated_line_count(self):
        """
        Compute the number of lines each time the line items are updated.
        """
        for wizard in self:
            wizard.updated_line_count = len(wizard.line_ids)
            _logger.info(f"Computed updated line count: {wizard.updated_line_count}")

    @api.depends('updated_line_count')
    def check_and_pack_products(self):
        """
        Checks if the conditions are met to pack products and then packs them.
        """
        for wizard in self:
            if wizard.line_count == wizard.updated_line_count:
                _logger.info(f"Conditions met for packing products in wizard {wizard.id}. Executing pack_products.")
                return wizard.pack_products()
            else:
                _logger.info(
                    f"Conditions not met for packing products in wizard {wizard.id}. Line count: {wizard.line_count}, Updated line count: {wizard.updated_line_count}")
        return {}

    # def write(self, vals):
    #     result = super(PackDeliveryReceiptWizard, self).write(vals)
    #     if 'line_ids' in vals:
    #         self.check_and_pack_products()
    #     return result


    @api.depends('picking_ids')
    def _compute_fields_based_on_picking_ids(self):
        """
        Computes both the tenant code and the total line count based on the picking IDs.
        """
        for wizard in self:
            if wizard.picking_ids:
                # Set the tenant code from the first picking
                wizard.tenant_code_id = wizard.picking_ids[0].tenant_code_id
                # Calculate the total line count from all pickings
                wizard.line_count = sum(len(picking.move_ids_without_package) for picking in wizard.picking_ids)
            else:
                # If there are no pickings, reset the tenant code and line count
                wizard.tenant_code_id = False
                wizard.line_count = 0

    @api.onchange('pc_container_code_id')
    def _onchange_pc_container_code_id(self):
        if self.pc_container_code_id:
            pickings = self.env['stock.picking'].search([
                ('move_ids_without_package.pc_container_code', '=', self.pc_container_code_id.name),
                ('state', '=', 'done')
            ])

            if not pickings:
                raise ValidationError(_("No completed pickings found for this PC container code."))

            self.picking_ids = [(6, 0, pickings.ids)]
            self._auto_select_package_box_type()
            self._compute_fields_based_on_picking_ids()


    @api.depends('picking_ids')
    def _compute_show_package_box_in_lines(self):
        """
        Determines if the package_box_type_id should be displayed in line items
        instead of the wizard header.
        """
        for record in self:
            record.show_package_box_in_lines = len(record.picking_ids) > 1

    def _auto_select_package_box_type(self):
        """
        Automatically selects the package box type based on the Incoterm location field in the sales order.
        """
        if len(self.picking_ids) == 1:
            picking = self.picking_ids[0]
            incoterm_location = picking.sale_id.packaging_source_type
            if incoterm_location:
                package_box = self.env['package.box.configuration'].search(
                    [('name', '=', incoterm_location)], limit=1)
                if package_box:
                    self.package_box_type_id = package_box.id  # Set package type for single pick

        else:  # Multiple picks scenario
            for line in self.line_ids:
                if line.picking_id.sale_id:
                    incoterm_location = line.picking_id.sale_id.packaging_source_type
                    package_box = self.env['package.box.configuration'].search(
                        [('name', '=', incoterm_location)], limit=1)
                    if package_box:
                        line.package_box_type_id = package_box.id  # Set package type in line items for multiple picks


    def pack_products(self):
        """
        Main method to validate and process the pack operation.
        Calls appropriate processing methods based on the number of pick numbers.
        """
        if not self.picking_ids:
            raise ValidationError(_("No pickings are linked to this operation. Please check your container code."))

        # Ensure Product is added on line items
        for line in self.line_ids:
            if not line.product_id:
                raise ValidationError(_("Please ensure all line items have a product selected before proceeding."))

            if not line.weight or line.weight <= 0.0:
                raise ValidationError(_(
                    "The product '%s' (SKU: %s) does not have a weight. Please add weight before proceeding."
                ) % (line.product_id.name, line.product_id.default_code or "N/A"))

        active_id = self.env.context.get('active_id')
        pack_app_order = self.env['custom.pack.app'].browse(active_id)
        section_name = self.pc_container_code_id.name

        # Create a section line for the license plate
        self.env['custom.pack.app.line'].create({
            'pack_app_line_id': pack_app_order.id,
            'product_id': False,
            'name': section_name,
            'quantity': 0,
            'sku_code': '',
            'available_quantity': 0,
            'remaining_quantity': 0,
            'display_type': 'line_section',
            'picking_id': False,
            'tenant_code_id': False,
            'site_code_id': False,
        })

        # Organize picking orders
        picking_orders = {}
        for line in self.line_ids:
            self.env['custom.pack.app.line'].create({
                'pack_app_line_id': pack_app_order.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'sku_code': line.product_id.default_code,
                'quantity': 1.0,
                'available_quantity': line.available_quantity,
                'remaining_quantity': line.remaining_quantity,
                'picking_id': line.picking_id.id,
                'tenant_code_id': line.tenant_code_id.id,
                'site_code_id': line.site_code_id.id,
            })

            if line.picking_id.id not in picking_orders:
                picking_orders[line.picking_id.id] = []
            picking_orders[line.picking_id.id].append(line)

        # Determine API endpoint
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        if self.site_code_id.name == "FC3":
            api_url = "https://shiperooconnect-prod.automation.shiperoo.com/api/ot_orders" if is_production == 'True' else "https://shiperooconnect.automation.shiperoo.com/api/ot_orders"
        elif self.site_code_id.name == "SHIPEROOALTONA":
            api_url = "https://shiperooconnect-prod.automation.shiperoo.com/api/ot_orders" if is_production == 'True' else "https://shiperooconnect.automation.shiperoo.com/api/ot_orders"
        else:
            raise ValidationError(_("Unknown warehouse. Cannot determine API endpoint."))

        # Process based on the number of pick numbers
        if not len(self.picking_ids) > 1:
            payloads = [self.process_single_pick()]

        # Send payloads to API
            for payload in payloads:
                self.send_payload_to_api(api_url, payload)
        # self.release_container()
        return {'type': 'ir.actions.act_window_close'}

    def release_container(self):
        """ Releases the container only if packing was successful. """
        container_code = self.pc_container_code_id.name
        warehouse_code = self.warehouse_id.name
        owner_code = self.tenant_code_id.name if self.tenant_code_id else ""

        if not container_code or not warehouse_code or not owner_code:
            _logger.error("Missing container, warehouse, or owner code.")
            raise UserError(_("Missing required data to release container."))

        # Fetch URLs dynamically from system parameters based on Warehouse Code
        dev_url = self.env['ir.config_parameter'].sudo().get_param(f'{warehouse_code.lower()}_geekplus_dev_url')
        prod_url = self.env['ir.config_parameter'].sudo().get_param(f'{warehouse_code.lower()}_geekplus_prod_url')

        if not dev_url or not prod_url:
            _logger.error(f"Missing API URL configuration for warehouse {warehouse_code}")
            raise UserError(_("API URL configuration is missing for warehouse: %s") % warehouse_code)

        # Select the correct API URL based on the environment
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
        geek_api_url = prod_url if is_production else dev_url

        full_api_url = f"{geek_api_url}?warehouse_code={warehouse_code}&owner_code={owner_code}"

        _logger.info(f"Releasing container {container_code} via API: {full_api_url}")

        payload = {
            "header": {
                "warehouse_code": warehouse_code,
                "user_id": "admin",
                "user_key": "Geekplus_2020"
            },
            "body": {
                "container_amount": 1,
                "container_list": [
                    {
                        "container_code": container_code,
                        "operation_type": 1,
                        "type": 10
                    }
                ]
            }
        }

        _logger.info(f"Container Release Payload: {json.dumps(payload, indent=4)}")

        try:
            response = requests.post(full_api_url, headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload))
            response.raise_for_status()
            _logger.info(f"Container {container_code} successfully released.")
            return True

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error releasing container {container_code}: {str(e)}")
            raise UserError(_("Error releasing container: %s") % str(e))

    def process_single_pick(self):
        """
        Processes the pack operation when there is only one pick number.
        Returns the formatted payload.
        """
        grouped_lines = {}
        total_weight = 0

        for line in self.line_ids:
            sku_code = line.product_id.default_code
            product_weight = line.weight  # Default weight to 1 if not defined

            if sku_code not in grouped_lines:
                grouped_lines[sku_code] = {
                    "sku_code": sku_code,
                    "name": line.product_id.name,
                    "quantity": 0,
                    "remaining_quantity": 0,
                    "weight": 0,
                    "picking_id": line.picking_id.name if line.picking_id else "",
                    "customer_name": line.picking_id.partner_id.name or "",
                    "shipping_address": f"{line.picking_id.partner_id.name},{line.picking_id.partner_id.street or ''}",
                    "tenant_code": line.tenant_code_id.name if line.tenant_code_id else "",
                    "site_code": line.site_code_id.name if line.site_code_id else "",
                    "receipt_number": line.picking_id.name,
                    "partner_id": line.picking_id.partner_id.name,
                    "origin": line.picking_id.origin or "N/A",
                    "package_name": line.package_box_type_id.name,
                    "length": line.package_box_type_id.length or "NA",
                    "width": line.package_box_type_id.width or "NA",
                    "height": line.package_box_type_id.height or "NA",
                    "sales_order_number": line.picking_id.sale_id.name if line.picking_id.sale_id else "N/A",
                    "sales_order_carrier": line.picking_id.sale_id.service_type if line.picking_id.sale_id else "N/A",
                    "sales_order_origin": line.picking_id.sale_id.origin if line.picking_id.sale_id else "N/A",
                    "incoterm_location": line.incoterm_location or "N/A",
                    "status": line.picking_id.sale_id.post_category if line.picking_id.sale_id else "N/A",
                    "carrier":line.picking_id.sale_id.carrier or "N/A",
                }

            grouped_lines[sku_code]["quantity"] += line.quantity
            grouped_lines[sku_code]["remaining_quantity"] += line.remaining_quantity
            grouped_lines[sku_code]["weight"] += product_weight * line.quantity
            total_weight += product_weight * line.quantity

        return {
            "header": {"user_id": "system", "user_key": "system", "warehouse_code": self.warehouse_id.name},
            "body": {
                "receipt_list": [{
                    "product_lines": list(grouped_lines.values()),
                    "pack_bench_number": self.pack_bench_id.name,
                    "pack_bench_ip": self.pack_bench_id.printer_ip,
                }]
            }
        }

    # Old Code Commented
    # def process_multiple_picks(self, picking_orders):
    #     """
    #     Processes multiple pick numbers and returns a list of formatted payloads.
    #     Each pick number has its own payload, and products are NOT grouped across different pick numbers.
    #     """
    #     payloads = []
    #     for picking_id, lines in picking_orders.items():
    #         product_lines = []
    #
    #         for line in lines:
    #             product_weight = line.weight  # Default weight to 1 if not defined
    #
    #             product_lines.append({
    #                 "sku_code": line.product_id.default_code,
    #                 "name": line.product_id.name,
    #                 "quantity": line.quantity,
    #                 "remaining_quantity": line.remaining_quantity,
    #                 "weight": product_weight * line.quantity,  # Weight per product line
    #                 "picking_id": line.picking_id.name if line.picking_id else "",
    #                 "customer_name": line.picking_id.partner_id.name or "",
    #                 "shipping_address": f"{line.picking_id.partner_id.name},{line.picking_id.partner_id.street or ''}",
    #                 "tenant_code": line.tenant_code_id.name if line.tenant_code_id else "",
    #                 "site_code": line.site_code_id.name if line.site_code_id else "",
    #                 "receipt_number": line.picking_id.name,
    #                 "origin": line.picking_id.origin or "N/A",
    #                 "package_name": line.package_box_type_id.name,
    #                 "length": line.package_box_type_id.length or "NA",
    #                 "width": line.package_box_type_id.width or "NA",
    #                 "height": line.package_box_type_id.height or "NA",
    #                 "sales_order_number": line.picking_id.sale_id.name if line.picking_id.sale_id else "N/A",
    #                 "sales_order_carrier": line.picking_id.sale_id.service_type if line.picking_id.sale_id else "N/A",
    #                 "sales_order_origin": line.picking_id.sale_id.origin if line.picking_id.sale_id else "N/A",
    #                 "incoterm_location": line.incoterm_location or "N/A",
    #                 "status": line.picking_id.sale_id.post_category if line.picking_id.sale_id else "N/A",
    #                 "carrier": line.picking_id.sale_id.carrier or "N/A",
    #             })
    #
    #         payloads.append({
    #             "header": {"user_id": "system", "user_key": "system", "warehouse_code": self.warehouse_id.name},
    #             "body": {
    #                 "receipt_list": [{
    #                     "product_lines": product_lines,
    #                     "pack_bench_number": self.pack_bench_id.name,
    #                     "pack_bench_ip": self.pack_bench_id.printer_ip,
    #                 }]
    #             }
    #         })
    #
    #     return payloads



    def prepare_payload_for_individual_line(self, line):
        """
        Prepares a payload for a single line.
        """
        payloads = []
        product_weight = line.weight  # Default weight to 1 if not defined
        product_line = {
            "sku_code": line.product_id.default_code,
            "name": line.product_id.name,
            "quantity": line.quantity,
            "remaining_quantity": line.remaining_quantity,
            "weight": product_weight * line.quantity,  # Weight per product line
            "picking_id": line.picking_id.name if line.picking_id else "",
            "customer_name": line.picking_id.partner_id.name or "",
            "shipping_address": f"{line.picking_id.partner_id.name},{line.picking_id.partner_id.street or ''}",
            "tenant_code": line.tenant_code_id.name if line.tenant_code_id else "",
            "site_code": line.site_code_id.name if line.site_code_id else "",
            "receipt_number": line.picking_id.name,
            "origin": line.picking_id.origin or "N/A",
            "package_name": line.package_box_type_id.name,
            "length": line.package_box_type_id.length or "NA",
            "width": line.package_box_type_id.width or "NA",
            "height": line.package_box_type_id.height or "NA",
            "sales_order_number": line.picking_id.sale_id.name if line.picking_id.sale_id else "N/A",
            "sales_order_carrier": line.picking_id.sale_id.service_type if line.picking_id.sale_id else "N/A",
            "sales_order_origin": line.picking_id.sale_id.origin if line.picking_id.sale_id else "N/A",
            "incoterm_location": line.incoterm_location or "N/A",
            "status": line.picking_id.sale_id.post_category if line.picking_id.sale_id else "N/A",
            "carrier": line.picking_id.sale_id.carrier or "N/A",
        }
        payloads.append({
            "header": {"user_id": "system", "user_key": "system", "warehouse_code": self.warehouse_id.name},
            "body": {
                "receipt_list": [{
                    "product_lines": product_line,
                    "pack_bench_number": self.pack_bench_id.name,
                    "pack_bench_ip": self.pack_bench_id.printer_ip,
                }]
            }
        })
        # Convert the payload to JSON
        json_payload = json.dumps(payloads, indent=4)
        _logger.info(f"Sending payload to API: {json_payload}")
        # api_url = self.determine_api_url(line.site_code_id.name)
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        if self.site_code_id.name == "FC3":
            api_url = "https://shiperooconnect-prod.automation.shiperoo.com/api/ot_orders" if is_production == 'True' else "https://shiperooconnect.automation.shiperoo.com/api/ot_orders"
        elif self.site_code_id.name == "SHIPEROOALTONA":
            api_url = "https://shiperooconnect-prod.automation.shiperoo.com/api/orders" if is_production == 'True' else "https://shiperooconnect.automation.shiperoo.com/api/orders"
        else:
            raise ValidationError(_("Unknown warehouse. Cannot determine API endpoint."))
        # Send the payload to the API
        try:
            response = requests.post(api_url, headers={'Content-Type': 'application/json'}, data=json_payload)
            response.raise_for_status()
            _logger.info(f"Payload successfully sent to {api_url}")
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error sending payload: {str(e)}")
            raise UserError(f"Error sending payload: {str(e)}")


    def send_payload_to_api(self, api_url, payload):
        """
        Sends the given payload to the provided API URL.
        """
        json_payload = json.dumps(payload, indent=4)
        _logger.info(f"Sending payload to API: {json_payload}")

        try:
            response = requests.post(api_url, headers={'Content-Type': 'application/json'}, data=json_payload)
            response.raise_for_status()
            _logger.info(f"Payload successfully sent to {api_url}")
        except requests.exceptions.RequestException as e:
            _logger.error(f"Error sending payload: {str(e)}")
            raise UserError(f"Error sending payload: {str(e)}")


class PackDeliveryReceiptWizardLine(models.TransientModel):
    _name = 'custom.pack.app.wizard.line'
    _description = 'Pack Delivery Receipt Wizard Line'

    wizard_id = fields.Many2one('custom.pack.app.wizard', string='Wizard Reference', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('id', 'in', available_product_ids)]")
    default_code = fields.Char(related='product_id.default_code', string='SKU Code')
    available_quantity = fields.Float(string='Expected Quantity', compute='_compute_available_quantity', store=True)
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity', store=True)
    quantity = fields.Float(string='Quantity', store=True)
    available_product_ids = fields.Many2many('product.product', string='Available Products',
                                             compute='_compute_available_products')
    picking_id = fields.Many2one('stock.picking', string='Picking Number', compute='_compute_picking_id', store=True)
    tenant_code_id = fields.Many2one(related='picking_id.tenant_code_id', string='Tenant ID')
    site_code_id = fields.Many2one(related='picking_id.site_code_id', string='Site Code')
    package_box_type_id = fields.Many2one('package.box.configuration', string='Package Box Type',
                                          help="Select packaging box for each product line.")
    sale_order_id = fields.Many2one(related='picking_id.sale_id', string='Sale Order', store=True)
    incoterm_location = fields.Char(related='sale_order_id.packaging_source_type', string='Incoterm location')
    weight = fields.Float(string="Weight", help="If product weight is missing, enter weight here.", required=True)
    line_added = fields.Boolean(string='line Added', default=False)

    @api.onchange('product_id', 'package_box_type_id')
    def _compute_add_line_boolean(self):
        for line in self:
            if line.product_id and line.package_box_type_id and line.weight:
                try:
                    # Attempt to prepare the payload only if all conditions are met
                    payload = line.wizard_id.prepare_payload_for_individual_line(line)
                    line.line_added = True
                    _logger.info(f"Payload prepared successfully for line: {payload}")
                except Exception as e:
                    line.line_added = False
                    _logger.error(f"Failed to prepare payload for line due to: {str(e)}")
                    # Optionally, raise a UserError or ValidationError to inform the user if necessary
                    # raise UserError(_("Failed to prepare payload: ") + str(e))
            else:
                line.line_added = False
                _logger.debug("Product, package box type, or weight not properly set, skipping payload preparation.")

    @api.depends('wizard_id.picking_ids', 'product_id')
    def _compute_picking_id(self):
        """
        Compute the picking number based on the product.
        """
        for line in self:
            picking = line.wizard_id.picking_ids.filtered(
                lambda p: line.product_id in p.move_ids_without_package.mapped('product_id'))[:1]
            line.picking_id = picking.id if picking else False

    @api.depends('wizard_id.picking_ids')
    def _compute_available_products(self):
        """
        Compute the available products based on the selected picking and match the PC barcode.
        """
        for line in self:
            if line.wizard_id and line.wizard_id.picking_ids:
                # Fetch products linked to the picking and PC container code
                product_ids = line.wizard_id.picking_ids.mapped('move_ids_without_package').filtered(lambda m: m.pc_container_code == line.wizard_id.pc_container_code_id.name).mapped('product_id.id')

                _logger.info(
                    f"Filtered product IDs for PC barcode {line.wizard_id.pc_container_code_id.name}: {product_ids}")

                if not product_ids:
                    _logger.warning(
                        f"No products found for PC barcode {line.wizard_id.pc_container_code_id.name} in pickings {line.wizard_id.picking_ids.ids}")

                line.available_product_ids = [(6, 0, product_ids)]
            else:
                _logger.warning("No picking IDs found, clearing available products")
                line.available_product_ids = [(5,)]

    @api.depends('wizard_id.picking_ids', 'product_id')
    def _compute_available_quantity(self):
        """
        Computes the expected quantity by summing the product's quantity in relevant stock moves.
        """
        for line in self:
            if line.wizard_id.picking_ids:
                moves = self.env['stock.move'].search([
                    ('picking_id', 'in', line.wizard_id.picking_ids.ids),
                    ('product_id', '=', line.product_id.id),
                    ('pc_container_code', '=', line.wizard_id.pc_container_code_id.name)
                ])
                line.available_quantity = sum(moves.mapped('product_uom_qty'))
                _logger.info(f"Available quantity for product {line.product_id.id}: {line.available_quantity}")
            else:
                line.available_quantity = 0.0

    @api.depends('product_id', 'quantity')
    def _compute_remaining_quantity(self):
        for line in self:
            if line.wizard_id and line.wizard_id.picking_id:
                total_quantity_selected = sum(
                    l.quantity for l in line.wizard_id.line_ids if l.product_id == line.product_id)
                move_lines = line.wizard_id.picking_id.move_ids_without_package.filtered(
                    lambda m: m.product_id == line.product_id)
                available_qty = sum(move_lines.mapped('product_uom_qty'))
                line.remaining_quantity = move_lines.remaining_qty - total_quantity_selected
            else:
                line.remaining_quantity = 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        When a product is selected:
        - If weight exists on the product, fetch and assign it.
        - If weight does NOT exist, prompt the user to enter it manually.
        - Once entered, update the product's weight permanently for future use.
        """
        if self.product_id:
            self.quantity = 1  # Set default quantity per scan
            if not self.wizard_id.pack_bench_id:
                raise ValidationError("Please select a Pack Bench first before proceeding with packing.")
            if not self.product_id.weight or self.product_id.weight <= 0.0:
                return {
                    'warning': {
                        'title': _("Missing Weight"),
                        'message': _("The selected product '%s' does not have a weight. "
                                     "Please enter the weight manually.") % self.product_id.name
                    }
                }
            else:
                # If weight exists, fetch it from the product and assign it
                self.weight = self.product_id.weight

        self.wizard_id._auto_select_package_box_type()

    @api.onchange('weight')
    def _onchange_weight(self):
        """
        When the user manually enters a weight:
        - Validate the weight input (must be greater than 0).
        - Save it to the product record so it is available next time.
        """
        if self.product_id:
            if self.weight and self.weight > 0:
                if self.product_id and (not self.product_id.weight or self.product_id.weight == 0.0):
                    self.product_id.weight = self.weight  # Update the product record
                    _logger.info(f"Updated weight for product {self.product_id.name} to {self.weight}")
            elif self.weight == 0:
                return {
                    'warning': {
                        'title': _("Invalid Weight"),
                        'message': _("Weight must be greater than 0. Please enter a valid weight."),
                    }
                }
            elif self.weight == 0 and self.package_box_type_id:
                return {
                    'warning': {
                        'title': _("Invalid Weight"),
                        'message': _("Weight must be greater than 0. Please enter a valid weight."),
                    }
                }

