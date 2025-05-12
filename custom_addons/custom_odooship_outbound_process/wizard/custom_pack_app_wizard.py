# -*- coding: utf-8 -*-
from email.policy import default

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
import requests
import xml.etree.ElementTree as ET
import urllib

_logger = logging.getLogger(__name__)


def _tote_codes(wizard):
    return wizard.pc_container_code_ids.mapped("name")


class PackDeliveryReceiptWizard(models.TransientModel):
    _name = 'custom.pack.app.wizard'
    _description = 'Pack Delivery Receipt Wizard'

    pc_container_code_ids = fields.Many2many(
        "pc.container.barcode.configuration",
        "custom_pack_pc_container_rel",
        "wizard_id",
        "container_id",
        string="Scan PC Tote Barcodes",
        domain="[('site_code_id', '=', site_code_id)]",
        help="Scan one or more tote barcodes",
    )
    scanned_sku = fields.Char(
        string="Scan Product SKU",
        help="Scan each SKU barcode.  The wizard updates the corresponding line automatically.",
    )
    picking_id = fields.Many2one('stock.picking', string='Dummy Picking')
    site_code_id = fields.Many2one('site.code.configuration', string='Site Code', store=True)
    warehouse_id = fields.Many2one(related='site_code_id.warehouse_id', store=True)
    picking_ids = fields.Many2many('stock.picking', string='Pick Numbers', store=True)
    line_ids = fields.One2many('custom.pack.app.wizard.line', 'wizard_id', string='Product Lines')
    pack_bench_id = fields.Many2one(
        'pack.bench.configuration',
        string='Pack Bench',
        required=True,
        domain="[('site_code_id', '=', site_code_id)]"
    )
    show_package_box_in_lines = fields.Boolean(compute="_compute_show_package_box_in_lines",
                                               default=False,
                                               store=True)
    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        store=True
    )
    line_count = fields.Integer(string="Line Count", compute="_compute_fields_based_on_picking_ids", store=True)
    updated_line_count = fields.Integer(
        string="Updated Line Count", compute='_compute_updated_line_count', store=True
    )
    next_package_number = fields.Integer(string='Next Package Number', default=1)
    confirm_increment = fields.Boolean(string="Confirm Increment")
    pack_app_id = fields.Many2one(
        'custom.pack.app',
        string='Pack App Reference',
        readonly=True,
    )
    single_pick_payload_sent = fields.Boolean(string="Single Pick Payload Sent", default=False)
    single_pick_payload_attempted = fields.Boolean(string="Payload Attempted for Single Pick", default=False)
    last_scanned_line_id = fields.Many2one(
        'custom.pack.app.wizard.line',
        string="Last Scanned Line",
        help="Tracks the last scanned line for controlled package number assignment"
    )

    @api.model
    def default_get(self, fields):
        res = super(PackDeliveryReceiptWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            pack_app = self.env['custom.pack.app'].browse(active_id)
            if not pack_app.exists():
                raise ValidationError(_("The related Pack App record no longer exists."))
            if 'site_code_id' in fields and pack_app.site_code_id:
                res['site_code_id'] = pack_app.site_code_id.id
            if 'pack_bench_id' in fields and pack_app.pack_bench_id:
                res['pack_bench_id'] = pack_app.pack_bench_id.id
            res['pack_app_id'] = pack_app.id
        else:
            raise ValidationError(_("No active Pack App record found. Please open this wizard from the Pack App."))
        return res

    @api.onchange("pc_container_code_ids")
    def _onchange_pc_container_code_ids(self):
        self.ensure_one()

        self.picking_ids = [(5, 0, 0)]
        self.line_ids = [(5, 0, 0)]

        if not self.pc_container_code_ids or not self.site_code_id:
            return

        tote_codes = _tote_codes(self)

        pickings = self.env["stock.picking"].search([
            ("current_state", "=", "pick"),
            ("move_ids_without_package.pc_container_code", "in", tote_codes),
            ("site_code_id", "=", self.site_code_id.id),
        ])
        if not pickings:
            raise ValidationError(_("No pickings found for the scanned tote(s)."))

        self.picking_ids = [(6, 0, pickings.ids)]

        vals_list = []
        for picking in pickings:
            incoterm = picking.sale_id.packaging_source_type if picking.sale_id else False
            pkg_id = self._get_package_box_id(
                picking.tenant_code_id.id,
                picking.site_code_id.id,
                incoterm
            )

            for mv in picking.move_ids_without_package.filtered(lambda m: m.pc_container_code in tote_codes):
                qty_to_create = int(round(mv.remaining_qty or 0))

                #  Always create one line per unit, regardless of single/multi pick
                for _ in range(qty_to_create):
                    vals_list.append({
                        "wizard_id": self.id,
                        "product_id": mv.product_id.id,
                        "picking_id": picking.id,
                        "quantity": 0,
                        "available_quantity": 1,
                        "weight": mv.product_id.weight or 0.0,
                        "tenant_code_id": picking.tenant_code_id.id,
                        "site_code_id": picking.site_code_id.id,
                        "sale_order_id": picking.sale_id.id,
                        "package_box_type_id": pkg_id,
                    })

        if vals_list:
            self.line_ids = [(0, 0, v) for v in vals_list]

        # recalc counters / tenant
        self._compute_fields_based_on_picking_ids()

    def _get_package_box_id(self, tenant_id, site_id, incoterm):
        """
        Decide which package.box.configuration to use.

        • If the Incoterm (packaging_source_type) is provided
          → look for an exact match first.
        • Otherwise (or if no exact match exists)
          → fall back to the tenant+site 'default' box (is_default_package).
        • If nothing is found at all
          → raise a ValidationError telling the user to configure a default box.
        """
        Box = self.env["package.box.configuration"]

        if incoterm:
            box = Box.search(
                [
                    ("name", "=", incoterm),
                    ("tenant_code_id", "=", tenant_id),
                    ("site_code_id", "=", site_id),
                ],
                limit=1,
            )
            if box:
                return box.id

        default_box = Box.search(
            [
                ("is_default_package", "=", True),
                ("tenant_code_id", "=", tenant_id),
                ("site_code_id", "=", site_id),
            ],
            limit=1,
        )
        if default_box:
            return default_box.id

        # 3) nothing found → stop the process
        raise ValidationError(_(
            "No package-box configuration found for this tenant/site. "
            "Please create a *default* package type before continuing."
        ))

    @api.onchange("scanned_sku")
    def _onchange_scanned_sku(self):
        """Handle every product-barcode scan."""
        self.ensure_one()
        sku = (self.scanned_sku or "").strip()
        if not sku:
            return

        matching_lines = self.line_ids.filtered(lambda l: l.product_id.default_code == sku)
        if not matching_lines:
            raise ValidationError(_("Scanned SKU '%s' is not in this tote.") % sku)

        line = matching_lines.filtered(lambda l: l.quantity == 0 and not l.line_added).sorted(
            key=lambda l: not l.product_package_number
        )

        if not line:
            raise ValidationError(_("All units of SKU '%s' have already been scanned.") % sku)

        line = line[0]

        # Prevent reprocessing
        if line.api_payload_attempted:
            _logger.warning(f"[SKIP] Payload already attempted for SKU {sku}. Skipping resend.")
            return

        if not line.product_package_number:
            line.product_package_number = self.next_package_number

        if len(self.picking_ids) > 1:  # MULTI-PICK
            config = self.get_onetraker_config()
            try:
                success = self.send_payload_to_onetraker(self.env, line.picking_id, [line], config)
                line.api_payload_attempted = True
                if success:
                    line.update({
                        "api_payload_success": True,
                        "line_added": True,
                        "quantity": 1,
                        "available_quantity": 1,
                        "remaining_quantity": 0,
                        "scanned": True,
                        "product_package_number": line.product_package_number or self.next_package_number
                    })
                else:
                    raise UserError(_("Failed to send label for SKU %s.") % sku)
            except Exception as e:
                raise UserError(_("Error while sending label for SKU %s:\n%s") % (sku, str(e)))
        else:  # SINGLE PICK
            line.quantity = 1
            line.available_quantity = 1
            line.remaining_quantity = 0
            line.line_added = True
            line.scanned = True

        # Track last scanned line
        self.last_scanned_line_id = line
        self.scanned_sku = False

    def get_onetraker_config(self):
        is_prod = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
        config_model = self.env['onetracker.connection.config'].sudo()
        tenant_id = self.tenant_code_id.id
        site_id = self.site_code_id.id

        config = config_model.search([
            ('tenant_code_id', '=', tenant_id),
            ('site_code_id', '=', site_id),
            ('is_production', '=', is_prod)
        ], limit=1)

        if not config:
            raise UserError(_("No OneTraker configuration found for this tenant and site for the current environment."))

        # 📝 Log config source
        _logger.info(f"[ONETRAKER][CONFIG] Using {'PRODUCTION' if is_prod else 'DEVELOPMENT'} environment.")
        _logger.info(f"[ONETRAKER][CONFIG] Tenant: {self.tenant_code_id.name}, Site: {self.site_code_id.name}")
        _logger.info(f"[ONETRAKER][CONFIG] URL: {config.onetraker_order_url}")
        _logger.info(f"[ONETRAKER][CONFIG] From Location ID: {config.default_from_location_id}")

        return {
            "ONETRAKER_CREATE_ORDER_URL": config.onetraker_order_url,
            "DEFAULT_MERCHANT_CODE": config.merchant_code,
            "DEFAULT_FROM_LOCATION_ID": config.default_from_location_id,
            "DEFAULT_AUTO_GENERATE_LABEL": config.default_auto_generate_label,
            "BEARER": config.bearer_token
        }

    # def increment_package_number(self):
    #     self.ensure_one()
    #     self.next_package_number += 1
    #     _logger.info(f"Package number incremented to {self.next_package_number}")
    #
    #     if self.last_scanned_line_id:
    #         line = self.last_scanned_line_id
    #
    #         line.product_package_number = self.next_package_number
    #         line.quantity = 1
    #         line.scanned = True
    #         line.line_added = True
    #
    #         line.available_quantity = 1
    #         line.remaining_quantity = 0
    #
    #         _logger.info(
    #             f"[Package Assigned] Product: {line.product_id.display_name}, Pkg#: {line.product_package_number}, Qty: {line.quantity}")
    #
    #         self.last_scanned_line_id = False
    #     else:
    #         _logger.warning("No last scanned line found to assign package number.")
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'custom.pack.app.wizard',
    #         'res_id': self.id,
    #         'view_mode': 'form',
    #         'target': 'new',
    #     }

    def increment_package_number(self):
        self.ensure_one()
        self.next_package_number += 1
        _logger.info(f"Package number incremented to {self.next_package_number}")

        if self.last_scanned_line_id:
            line = self.last_scanned_line_id

            # ✅ Only assign if not already scanned or added
            if not line.scanned and not line.line_added:
                line.product_package_number = self.next_package_number
                line.quantity = 1
                line.available_quantity = 1
                line.remaining_quantity = 0
                line.line_added = True
                line.scanned = True

                _logger.info(
                    f"[Package Assigned] Product: {line.product_id.display_name}, "
                    f"Pkg#: {line.product_package_number}"
                )
            else:
                _logger.warning(
                    f"[SKIP] Line already scanned or added for {line.product_id.display_name}. "
                    f"Package number not reassigned."
                )

            # ✅ Do NOT reset last_scanned_line_id if line wasn't updated
            if not line.api_payload_attempted:
                self.last_scanned_line_id = line
            else:
                self.last_scanned_line_id = False
        else:
            _logger.warning("No last scanned line found to assign package number.")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'custom.pack.app.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('confirm_increment')
    def _onchange_confirm_increment(self):
        for wizard in self:
            if wizard.confirm_increment:
                wizard.next_package_number += 1
                wizard.confirm_increment = False
                _logger.info(f"Package number incremented to {wizard.next_package_number}")

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
                # return wizard.pack_products()
            else:
                _logger.info(
                    f"Conditions not met for packing products in wizard {wizard.id}. Line count: {wizard.line_count}, Updated line count: {wizard.updated_line_count}")
        return {}

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
        - If a single pick, assigns package box at the wizard level.
        - If multiple picks, assigns package box at the line level.
        - If no exact match for `incoterm_location`, selects the default package box.
        - Ensures package box selection is based on matching `site_code` and `tenant_code`.
        """
        for line in self.line_ids:
            picking = line.picking_id
            if not picking:
                continue  # no picking yet → skip

            incoterm = picking.sale_id.packaging_source_type or False
            try:
                box_id = self._get_package_box_id(
                    self.tenant_code_id.id,
                    self.site_code_id.id,
                    incoterm
                )
                line.package_box_type_id = box_id
            except ValidationError as err:
                # bubble the message up so the user sees it immediately
                raise err


    def pack_products(self):
        """
        Main method to validate and process the pack operation.
        - Checks for unscanned lines.
        - Raises warning with missing SKU codes.
        - Sends payloads only for lines where 'scanned' is True.
        - Preserves existing single/multi pick logic and container release.
        """
        self.ensure_one()

        if not self.picking_ids or not self.picking_ids.ids:
            _logger.warning("[PACK_PRODUCTS] picking_ids is empty or not properly set. Value: %s", self.picking_ids)
            raise ValidationError(_("No pickings are linked to this operation. Please check your container code."))

        #  Check for unscanned lines
        unscanned_lines = self.line_ids.filtered(lambda l: not l.scanned)
        # if unscanned_lines:
        #     missing_skus = ", ".join(unscanned_lines.mapped("product_id.default_code"))
        #     return {
        #         'warning': {
        #             'title': _('Unscanned Items Detected'),
        #             'message': _(
        #                 'You have not scanned the following SKU(s):\n\n%s\n\nPlease scan them before proceeding to pack.') % missing_skus,
        #             'type': 'notification'
        #         }
        #     }

        #  Only use scanned lines for processing
        scanned_lines = self.line_ids.filtered(lambda l: l.scanned)

        #  Safety check
        if not scanned_lines:
            raise ValidationError(_("No scanned products found to pack."))

        #  Validate scanned lines
        for line in scanned_lines:
            if not line.product_id:
                raise ValidationError(_("Please ensure all line items have a product selected before proceeding."))
            if not line.weight or line.weight <= 0.0:
                raise ValidationError(_(
                    "The product '%s' (SKU: %s) does not have a weight. Please add weight before proceeding."
                ) % (line.product_id.name, line.product_id.default_code or "N/A"))

        #  Add section header for the tote
        pack_app_order = self.pack_app_id
        section_name = ', '.join(self.pc_container_code_ids.mapped('name'))

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
            'sale_order_id': False,
            'tenant_code_id': False,
            'site_code_id': False,
        })

        #  Create app lines only for scanned lines
        picking_orders = {}
        for line in scanned_lines:
            self.env['custom.pack.app.line'].create({
                'pack_app_line_id': pack_app_order.id,
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'sku_code': line.product_id.default_code,
                'quantity': 1.0,
                'available_quantity': line.available_quantity,
                'remaining_quantity': line.remaining_quantity,
                'picking_id': line.picking_id.id,
                'sale_order_id': line.sale_order_id.id,
                'tenant_code_id': line.tenant_code_id.id,
                'site_code_id': line.site_code_id.id,
            })

            if line.picking_id.id not in picking_orders:
                picking_orders[line.picking_id.id] = []
            picking_orders[line.picking_id.id].append(line)

        #  Prepare for OneTraker payload
        config = self.get_onetraker_config()
        api_url = config["ONETRAKER_CREATE_ORDER_URL"]

        #  Single Pick Logic
        if len(self.picking_ids) <= 1:
            if self.single_pick_payload_sent:
                _logger.warning(f"[SKIP] Single-pick payload already sent for wizard {self.id}")
                raise UserError(_("Payload already sent for this pick. Please refresh."))

            payload = self.process_single_pick()  # should use all relevant scanned_lines internally
            self.send_payload_to_api(api_url, payload)
            self.write({'single_pick_payload_sent': True})
            self.env.cr.flush()
            _logger.info(f"[PRE-FLAG] Wizard {self.id} marked as payload sent before API call.")

        #  Release container in both cases
        self.release_container()

        return {'type': 'ir.actions.act_window_close'}

    def process_single_pick(self):
        """
        Builds and sends OneTraker payload for single-pick based on all scanned lines.
        """
        self.ensure_one()

        if not self.picking_ids or len(self.picking_ids) != 1:
            raise ValidationError("This method should only be called for a single picking.")

        picking = self.picking_ids[0]
        scanned_lines = self.line_ids.filtered(lambda l: l.scanned)

        if not scanned_lines:
            raise ValidationError("No scanned lines found to pack for this picking.")

        sale = picking.sale_id
        partner = picking.partner_id

        if not partner or not partner.email:
            raise ValidationError("Missing or invalid customer email.")

        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", partner.email):
            raise ValidationError("Invalid email for customer: %s" % partner.name)

        config = self.get_onetraker_config()
        order_number = sale.name or picking.name
        customer_ref = sale.client_order_ref or "NA"
        country = partner.country_id.name or "Australia"
        country_code = partner.country_id.code or "AU"
        carrier = sale.carrier or 'AUSPOST'

        to_address = {
            "google_formated_address": None,
            "business_name": partner.name,
            "address1": partner.street or "",
            "address2": partner.street2 or None,
            "city": partner.city or "",
            "province": partner.state_id.name if partner.state_id else "",
            "province_code": partner.zip or "",
            "country": country,
            "country_code": country_code,
            "street_address": None,
            "area_name": None,
            "locality": None,
            "unit_floor": None,
            "landmark": None,
            "google_place_id": None,
            "contact": {
                "name": partner.name,
                "mobile_number": "+61412345678" or "0000000000",
                "email": partner.email or "support@shiperoo.com"
            }
        }

        grouped_items = {}
        declared_value = 0.0

        for line in scanned_lines:
            pkg_num = line.product_package_number
            if pkg_num not in grouped_items:
                grouped_items[pkg_num] = {
                    "type": None,
                    "quantity": 1,
                    "products": [],
                    "authority_to_leave": True,
                    "attributes": [
                        {"category": "length", "unit": "m", "value": 0.1},
                        {"category": "width", "unit": "m", "value": 0.2},
                        {"category": "height", "unit": "m", "value": 0.3},
                        {"category": "weight", "unit": "KG", "value": line.weight or 0.5}
                    ]
                }

            grouped_items[pkg_num]["products"].append({
                "product_id": line.product_id.default_code,
                "name": line.product_id.name,
                "weight": line.weight or 0.5,
                "description": line.product_id.name,
                "quantity": line.quantity or 1.0,
                "hs_code": line.product_id.hs_code or "999999",
                "declared_value": round(line.product_id.list_price or 10.0, 2),
                "item_contents_reference": ""
            })
            declared_value += (line.product_id.list_price or 10.0) * (line.quantity or 1.0)

        payload = {
            "merchant_code": config["DEFAULT_MERCHANT_CODE"],
            "service_type": sale.service_type or "STANDARD",
            "order_number": order_number,
            "tags": {"external_order_id": customer_ref},
            "tu_id": None,
            "tu_type": "",
            "auto_generate_label": config["DEFAULT_AUTO_GENERATE_LABEL"],
            "shipment": {
                "from_location_id": config["DEFAULT_FROM_LOCATION_ID"],
                "to_address": to_address,
                "items": list(grouped_items.values()),
                "instruction": {"note": sale.note or ""}
            }
        }

        if country_code.upper() != "AU":
            payload["shipment"]["international"] = {
                "incoterms": "DAP",
                "customs_declaration": {
                    "description": "Apparell",
                    "total_value": round(declared_value, 2),
                    "currency": "AUD",
                    "duty_paid_by": "receiver",
                    "export_declaration_number": ""
                }
            }

        _logger.info(f"[ONETRAKER][SINGLE PICK PAYLOAD] Sending payload:\n{json.dumps(payload, indent=4)}")
        self.send_payload_to_api(config["ONETRAKER_CREATE_ORDER_URL"], payload)

        # Mark picking and order as packed
        picking.write({'current_state': 'pack'})
        sale.write({
            'carrier': carrier,
            'pick_status': 'packed',
            'delivery_status': 'partial'
        })
        picking.button_validate()

        return payload

    def release_container(self):
        """ Releases the container only if packing was successful. """
        self.ensure_one()

        container_codes = ', '.join(self.pc_container_code_ids.mapped('name'))

        warehouse_code = self.warehouse_id.name
        owner_code = self.tenant_code_id.name if self.tenant_code_id else ""
        site_code = self.site_code_id.name if self.site_code_id else ""

        _logger.info("Raw values:")
        _logger.info("  container_codes: %s", container_codes)
        _logger.info("  warehouse_code: %s", warehouse_code)
        _logger.info("  tenant_code: %s", owner_code)
        _logger.info("  site_code: %s", site_code)

        if not container_codes or not warehouse_code or not owner_code or not site_code:
            _logger.error("Missing container, warehouse, site code or owner code.")
            raise UserError(_("Missing required data to release container(s)."))

        # Fetch URLs dynamically from system parameters based on Warehouse Code
        dev_url = self.env['ir.config_parameter'].sudo().get_param('dev_container_release_url')
        prod_url = self.env['ir.config_parameter'].sudo().get_param('prod_container_release_url')

        if not dev_url or not prod_url:
            _logger.error(f"Missing API URL configuration for warehouse {warehouse_code}")
            raise UserError(_("API URL configuration is missing for warehouse: %s") % warehouse_code)

        # Select the correct API URL based on the environment
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
        release_container_api_url = prod_url if is_production else dev_url

        _logger.info(f"Releasing container(s) {container_codes} via API: {release_container_api_url}")

        for container_code in self.pc_container_code_ids.mapped("name"):
            release_payload = {
                "is_release_container": True,
                "container_code": container_code,
                "site_code": site_code,
                "tenant_code": owner_code,
                "warehouse_code": warehouse_code
            }

            _logger.info(f"Container Release Payload: {json.dumps(release_payload, indent=4)}")

            try:
                response = requests.post(release_container_api_url, headers={'Content-Type': 'application/json'},
                                         data=json.dumps(release_payload))
                response.raise_for_status()
                _logger.info(f"Container {container_code} successfully released.")
            except requests.exceptions.RequestException as e:
                _logger.error(f"Error releasing container {container_code}: {str(e)}")
                raise UserError(_("Error releasing container: %s") % str(e))

        return True

    def send_payload_to_api(self, api_url, payload):
        """
        Send the final JSON payload to OneTraker using credentials/config from the config model.
        """
        config = self.get_onetraker_config()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': config["BEARER"]
        }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                _logger.info("Label sent successfully to OneTraker.")
                return {
                    'warning': {
                        'title': _("Success"),
                        'message': _("Label Printed Successfully."),
                        'type': 'notification'
                    }
                }
            else:
                _logger.error(f"OneTraker error {response.status_code}: {response.text}")
                raise UserError(f"Label sending failed. Error: {response.text}")
        except requests.exceptions.RequestException as e:
            _logger.error(f"OneTraker request exception: {e}")
            raise UserError(f"Request error: {str(e)}")

    def send_payload_and_print_label(self, payload, pick_name=None):
        """
        Full OneTraker Label Process:
        1. Send payload to OneTraker
        2. Extract label URL from response
        3. Trigger browser print for label
        """
        config = self.get_onetraker_config()
        api_url = config.get("ONETRAKER_CREATE_ORDER_URL")
        bearer_token = config.get("BEARER")

        headers = {
            'Content-Type': 'application/json',
            'Authorization': bearer_token
        }

        try:
            # Send payload to OneTraker
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            _logger.info(
                f"[ONETRAKER][SEND] Response ({response.status_code}) for {pick_name or 'N/A'}: {response.text}")

            if response.status_code != 200:
                raise UserError(
                    _("Label sending failed.\nStatus: %s\nResponse: %s") % (response.status_code, response.text))

            response_json = response.json()
            generic_response = response_json.get("genericResponse", {})

            if generic_response.get("apiStatusCode") != 200:
                raise UserError(
                    _("OneTraker API Error:\n%s") % generic_response.get("apiStatusMessage", "Unknown error"))

            label_url = generic_response.get("label_url")
            if not label_url:
                raise UserError(_("Label URL not found in the OneTraker response."))

            _logger.info(f"[ONETRAKER][LABEL] Retrieved label URL: {label_url}")

            # Open label in browser for printing
            # return {
            #     'type': 'ir.actions.act_url',
            #     'url': label_url,
            #     'target': 'new',
            # }
            # Enhanced: Send to Zebra printer
            self.print_label_via_pack_bench(label_url)
            return {'type': 'ir.actions.act_window_close'}


        except requests.exceptions.RequestException as e:
            _logger.error(f"[ONETRAKER][ERROR] Request failed: {str(e)}")
            raise UserError(_("Failed to send payload to OneTraker:\n%s") % str(e))

        except ValueError:
            _logger.error("[ONETRAKER][ERROR] Failed to parse JSON from response")
            raise UserError(_("Failed to decode OneTraker API response. Please check logs."))

    def print_label_via_pack_bench(self, label_url):
        """
        Downloads label (ZPL/PDF) and sends it to Zebra printer via Pack Bench IP.
        """
        self.ensure_one()

        if not label_url:
            raise UserError(_("No label URL provided to print."))

        bench_ip = self.pack_bench_id.printer_ip
        if not bench_ip:
            raise UserError(_("Pack Bench is missing IP address. Please configure it."))

        try:
            label_resp = requests.get(label_url)
            label_resp.raise_for_status()

            label_data = label_resp.content
            content_type = label_resp.headers.get('Content-Type')

            _logger.info(f"[ZEBRA] Downloaded label: {len(label_data)} bytes, type: {content_type}")

            printer_url = f"http://{bench_ip}:9100"  # RAW print port for Zebra

            send_resp = requests.post(
                printer_url,
                data=label_data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=5
            )
            send_resp.raise_for_status()

            _logger.info(f"[ZEBRA] Label sent to Zebra printer at {printer_url}")

        except requests.exceptions.RequestException as e:
            _logger.error(f"[ZEBRA ERROR] Failed to print label via {bench_ip}: {e}")
            raise UserError(_("Failed to print label via Pack Bench %s:\n%s") % (bench_ip, str(e)))

    def send_payload_to_onetraker(self, env, picking, lines, config):
        """
        Prepares and sends OneTraker payload for given picking and its associated lines.
        This works for both single-pick and multi-pick.
        """
        if not picking:
            raise ValidationError("Picking is required to send OneTraker payload.")

        partner = picking.partner_id
        sale = picking.sale_id

        if not partner or not partner.email:
            raise ValidationError("Missing or invalid customer email.")

        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", partner.email):
            raise ValidationError("Invalid email for customer: %s" % partner.name)

        order_number = sale.name or picking.name
        customer_ref = sale.client_order_ref or "NA"
        country = partner.country_id.name or "Australia"
        country_code = partner.country_id.code or "AU"

        # Carrier fallback
        carrier = sale.carrier or 'AUSPOST'

        to_address = {
            "google_formated_address": None,
            "business_name": partner.name,
            "address1": partner.street or "",
            "address2": partner.street2 or None,
            "city": partner.city or "",
            "province": partner.state_id.name if partner.state_id else "",
            "province_code": partner.zip or "",
            # "province_code": "VIC",
            "country": country,
            "country_code": country_code,
            "street_address": None,
            "area_name": None,
            "locality": None,
            "unit_floor": None,
            "landmark": None,
            "google_place_id": None,
            "contact": {
                "name": partner.name,
                "mobile_number": "+61412345678" or "0000000000",
                "email": partner.email or "support@shiperoo.com"
            }
        }

        grouped_items = {}
        declared_value = 0.0

        for line in lines:
            pkg_num = line.product_package_number
            box = line.package_box_type_id

            if pkg_num not in grouped_items:
                grouped_items[pkg_num] = {
                    "type": None,
                    "quantity": 1,
                    "products": [],
                    "authority_to_leave": True,
                    "attributes": [
                        {
                            "category": "length",
                            "unit": "m",
                            "value":0.1
                        },
                        {
                            "category": "width",
                            "unit": "m",
                            "value": 0.2
                        },
                        {
                            "category": "height",
                            "unit": "m",
                            "value": 0.3
                        },
                        {
                            "category": "weight",
                            "unit": "KG",
                            "value": line.weight or 0.5
                        }
                    ]
                }

            product_data = {
                "product_id": line.product_id.default_code,
                "name": line.product_id.name,
                "weight": line.weight or 0.5,
                "description": line.product_id.name,
                "quantity": line.quantity or 1.0,
                "hs_code": line.product_id.hs_code or "999999",
                "declared_value": round(line.product_id.list_price or 10.0, 2),
                "item_contents_reference": ""
            }

            grouped_items[pkg_num]["products"].append(product_data)
            declared_value += product_data["declared_value"] * product_data["quantity"]

        payload = {
            "merchant_code": config["DEFAULT_MERCHANT_CODE"],
            "service_type": sale.service_type or "STANDARD",
            "order_number": order_number,
            "tags": {"external_order_id": customer_ref},
            "tu_id": None,  # Fixed value per sample
            "tu_type": "",
            "auto_generate_label": config["DEFAULT_AUTO_GENERATE_LABEL"],
            "shipment": {
                "from_location_id": config["DEFAULT_FROM_LOCATION_ID"],
                "to_address": to_address,
                "items": list(grouped_items.values()),
                "instruction": {
                    "note": sale.note or ""
                }
            }
        }

        if country_code.upper() != "AU":
            payload["shipment"]["international"] = {
                "incoterms": "DAP",
                "customs_declaration": {
                    "description": "Apparell",
                    "total_value": round(declared_value, 2),
                    "currency": "AUD",
                    "duty_paid_by": "receiver",
                    "export_declaration_number": ""
                }
            }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': config["BEARER"]
        }

        api_url = config["ONETRAKER_CREATE_ORDER_URL"]
        _logger.info(f"[ONETRAKER] Sending payload to {api_url} for order {order_number}")
        _logger.info(json.dumps(payload, indent=4))

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            resp_data = response.json()
            generic = resp_data.get("genericResponse", {})
            _logger.error(json.dumps(resp_data, indent=4))

            if generic.get("apiStatusCode") != 200:
                raise UserError(generic.get("apiStatusMessage", "Unknown OneTraker API error."))

            # Print label URL (for multi-pick)
            label_url = generic.get("label_url")
            # if label_url:
            #     _logger.info(f"[ONETRAKER][LABEL] {label_url}")
            #     self.env['ir.actions.act_url'].create({
            #         'name': 'Print Label',
            #         'type': 'ir.actions.act_url',
            #         'url': label_url,
            #         'target': 'new',
            #     })
            if label_url:
                _logger.info(f"[ONETRAKER][LABEL] {label_url}")
                self.print_label_via_pack_bench(label_url)

            # Update Sale Order + Picking
            picking.write({'current_state': 'pack'})
            sale.write({
                'consignment_number': generic.get("carrier_con_id", ""),
                'tracking_url': label_url,
                'carrier': carrier,
                'pick_status': 'packed',
                'delivery_status': 'partial',
            })
            picking.button_validate()

            _logger.info("[ONETRAKER] Label sent successfully and records updated.")
            return True

        except requests.exceptions.RequestException as e:
            _logger.error(f"[ONETRAKER] Request failed: {str(e)}")
            raise UserError(f"Failed to send payload to OneTraker: {str(e)}")

        except ValueError:
            _logger.error("[ONETRAKER] Invalid JSON response from OneTraker.")
            raise UserError("Failed to decode OneTraker API response. Check the response format.")

    def send_onetraker_test_payload():
        api_url = "https://ext-api.onetraker.com/api/v1/shipping/order"  # Ensure your IP is allowed
        bearer_token = "YOUR_BEARER_TOKEN"  # 🔐 Replace with your actual token from OneTraker

        headers = {
            "Content-Type": "application/json",
            "Authorization": bearer_token
        }

        payload = {
            "merchant_code": "BNBFC3",
            "service_type": "STANDARD",
            "order_number": "S001507",
            "tags": {
                "external_order_id": "BNB#319371"
            },
            "tu_id": None,
            "tu_type": "",
            "auto_generate_label": True,
            "shipment": {
                "from_location_id": "67a02a3efa0a44ea2542b5c5",
                "to_address": {
                    "google_formated_address": None,
                    "business_name": "Julz Ferguson",
                    "address1": "995 Wanaka-Luggate Highway",
                    "address2": None,
                    "city": "Wānaka",
                    "province": "Otago",
                    "province_code": "9382",
                    "country": "New Zealand",
                    "country_code": "NZ",
                    "street_address": None,
                    "area_name": None,
                    "locality": None,
                    "unit_floor": None,
                    "landmark": None,
                    "google_place_id": None,
                    "contact": {
                        "name": "Julz Ferguson",
                        "mobile_number": "+64272758886",
                        "email": "julz.ferg@xtra.co.nz"
                    }
                },
                "items": [
                    {
                        "type": None,
                        "quantity": 1,
                        "products": [
                            {
                                "product_id": "OMM100BLK-XS-S",
                                "name": "On My Mind Wool Blend Cape - Black",
                                "weight": 1.35,
                                "description": "On My Mind Wool Blend Cape - Black",
                                "quantity": 1.0,
                                "hs_code": "620211",
                                "declared_value": 57.08,
                                "item_contents_reference": ""
                            }
                        ],
                        "authority_to_leave": True,
                        "attributes": [
                            {"category": "length", "unit": "m", "value": 0.2},
                            {"category": "width", "unit": "m", "value": 0.1},
                            {"category": "height", "unit": "m", "value": 0.1},
                            {"category": "weight", "unit": "KG", "value": 1.35}
                        ]
                    }
                ],
                "instruction": {
                    "note": ""
                },
                "international": {
                    "incoterms": "DAP",
                    "customs_declaration": {
                        "description": "Apparell",
                        "total_value": 57.08,
                        "currency": "AUD",
                        "duty_paid_by": "receiver",
                        "export_declaration_number": ""
                    }
                }
            }
        }

        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            print("Status Code:", response.status_code)
            print("Response:", response.text)
        except Exception as e:
            print("Request failed:", e)

class PackDeliveryReceiptWizardLine(models.TransientModel):
    _name = 'custom.pack.app.wizard.line'
    _description = 'Pack Delivery Receipt Wizard Line'

    wizard_id = fields.Many2one('custom.pack.app.wizard', string='Wizard Reference')
    product_id = fields.Many2one('product.product', string='Product',
                                 store=True, required=True,
                                 domain="[('id', 'in', available_product_ids)]")
    default_code = fields.Char(related='product_id.default_code', string='SKU Code')
    available_quantity = fields.Float(string='Expected Quantity', compute='_compute_available_quantity', store=True)
    remaining_quantity = fields.Float(string='Remaining Quantity', compute='_compute_remaining_quantity', store=True)
    quantity = fields.Float(string='Quantity', store=True, default=1)
    available_product_ids = fields.Many2many('product.product', string='Available Products',
                                             compute='_compute_available_products')
    picking_id = fields.Many2one('stock.picking', string='Picking Number', store=True)
    tenant_code_id = fields.Many2one(related='picking_id.tenant_code_id', string='Tenant ID')
    site_code_id = fields.Many2one(related='picking_id.site_code_id', string='Site Code')
    package_box_type_id = fields.Many2one('package.box.configuration', string='Package Box Type',
                                          domain="[('site_code_id', '=', site_code_id), ('tenant_code_id', '=', tenant_code_id)]",
                                          help="Select packaging box for each product line.")
    sale_order_id = fields.Many2one(related='picking_id.sale_id', string='Sale Order', store=True)
    incoterm_location = fields.Char(related='sale_order_id.packaging_source_type', string='Incoterm location')
    weight = fields.Float(string="Weight",
                          help="If product weight is missing, enter weight here.", required=True)
    line_added = fields.Boolean(string='Line Added', compute='_compute_line_added', store=True)
    current_state = fields.Selection([
        ('draft', 'Draft'),
        ('pick', 'Pick'),
        ('pack', 'Pack'),
        ('partially_pick', 'Partially Pick')
    ], default='draft')
    product_package_number = fields.Integer(string='Package Number', required=True, store=True)
    serial_number = fields.Char(string='Serial Number', store=True)
    show_serial_number = fields.Boolean(
        string="Show Serial?",
        compute="_compute_show_serial_number",
        store=False  # Not stored in DB, just used in view
    )
    api_payload_success = fields.Boolean(string="Payload Sent Successfully", default=False, store=True)
    api_payload_attempted = fields.Boolean(string="Payload Attempted", default=False, store=True)
    line_added = fields.Boolean(string='Line Added', compute='_compute_line_added', store=True)
    scanned = fields.Boolean(string="Scanned", default=False, store=True)

    @api.depends(
        "api_payload_success",  # multi-pick: payload sent
        "remaining_quantity",  # single-pick: reached zero
        "wizard_id.picking_ids"  # to catch mode change
    )
    def _compute_line_added(self):
        """
        * Multi-pick   → flagged as soon as the API payload succeeds
        * Single-pick  → flagged when remaining_quantity hits 0
        """
        for line in self:
            if len(line.wizard_id.picking_ids) > 1:
                line.line_added = bool(line.api_payload_success)
            else:
                line.line_added = line.remaining_quantity == 0

    @api.onchange('product_id', 'package_box_type_id', 'serial_number', 'weight', 'product_package_number')
    def _onchange_trigger_payload(self):
        for line in self:
            if not line.product_id or line.api_payload_success:
                return

            wizard = line.wizard_id
            multiple_picks = len(wizard.picking_ids) > 1
            serial_ok = not line.product_id.is_serial_number or bool(line.serial_number)

            all_ready = (
                    line.product_id and
                    line.package_box_type_id and
                    line.weight > 0 and
                    line.product_package_number and
                    multiple_picks and
                    serial_ok
            )

            if not all_ready:
                if line.product_id.is_serial_number and not line.serial_number:
                    return {
                        'warning': {
                            'title': _("Packing Information"),
                            'message': _("Serial number is required for product '%s'.") % line.product_id.display_name
                        }
                    }
                if not line.package_box_type_id and not line.api_payload_attempted:
                    return {
                        'warning': {
                            'title': _("Packing Information"),
                            'message': _("Please select a package type before proceeding.")
                        }
                    }
                if line.product_id.is_fragile:
                    return {
                        'warning': {
                            'title': _("Packing Information"),
                            'message': _("This item is fragile and must be packed with bubble wrap for protection.")
                        }
                    }
                return

            if line.api_payload_attempted:
                _logger.info(f"[SKIP] Payload already attempted for {line.product_id.display_name}")
                return

            _logger.info(f"[AUTO PAYLOAD] Sending for {line.product_id.display_name}")
            line.api_payload_attempted = True

            try:
                config = wizard.get_onetraker_config()
                success = wizard.send_payload_to_onetraker(wizard.env, line.picking_id, [line], config)
                if success:
                    line.api_payload_success = True
                    line.line_added = True
                api_url = config['ONETRAKER_CREATE_ORDER_URL']
                bearer_token = config['BEARER']

                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': bearer_token
                }

                response = requests.post(api_url, headers=headers, data=json.dumps(payload))
                if response.status_code == 200:
                    line.api_payload_success = True
                    line.line_added = True
                    _logger.info(f"[SUCCESS] Payload sent for {line.product_id.display_name}")
                    return {
                        'warning': {
                            'title': _("Success"),
                            'message': _("Label Printed Successfully."),
                            'type': 'notification'
                        }
                    }
                else:
                    try:
                        error_message = response.json().get('message', response.text)
                    except ValueError:
                        error_message = response.text

                    _logger.error(f"[FAILURE] API Error ({response.status_code}): {error_message}")
                    raise UserError(
                        _("Payload failed for order '%s'. Fix it before proceeding:\n%s") %
                        (line.sale_order_id.name, error_message)
                    )

            except requests.exceptions.RequestException as e:
                _logger.error(f"[EXCEPTION] during payload for {line.product_id.display_name}: {str(e)}")
                raise UserError(
                    _("API request failed for product '%s':\n%s") % (line.product_id.display_name, str(e))
                )

    def send_tracking_update_to_odoo(self, order_number, tracking_number, carrier_name, pick_number):
        """
        Mirrors the Flask behavior: Updates the sale order and stock picking with tracking info.
        """
        SaleOrder = self.env['sale.order'].sudo()
        Picking = self.env['stock.picking'].sudo()

        sale_order = SaleOrder.search([('name', '=', order_number)], limit=1)
        if not sale_order:
            raise UserError(_("Sale Order %s not found for tracking update.") % order_number)

        picking = Picking.search([('name', '=', pick_number)], limit=1)
        if not picking:
            raise UserError(_("Picking %s not found for tracking update.") % pick_number)

        track_url = f"https://auspost.com.au/mypost/track/details/{tracking_number}"
        sale_order.write({
            'consignment_number': tracking_number,
            'tracking_url': track_url,
            'carrier': carrier_name,
            'pick_status': "packed",
            'delivery_status': "partial",
        })
        picking.write({'current_state': "pack"})
        picking.button_validate()

        _logger.info(f"Tracking and pick state updated for Order: {order_number}, Pick: {pick_number}")

    def handle_manual_wb_update(self, order_number, pick_number):
        """
        Handles the special case where the order is Manual WB (skip label sending).
        """
        SaleOrder = self.env['sale.order'].sudo()
        Picking = self.env['stock.picking'].sudo()

        sale_order = SaleOrder.search([('name', '=', order_number)], limit=1)
        picking = Picking.search([('name', '=', pick_number)], limit=1)

        if not sale_order or not picking:
            raise UserError(_("Order or Picking not found for Manual WB handling."))

        sale_order.write({
            'consignment_number': "Manual WB",
            'pick_status': "packed",
        })
        picking.write({'current_state': "pack"})
        picking.button_validate()

        _logger.info(f"Manual WB tracking and pick state updated for Order: {order_number}")

    @api.depends("wizard_id.picking_ids")
    def _compute_available_products(self):
        for line in self:
            wiz = line.wizard_id
            if wiz and wiz.picking_ids:
                tote_codes = wiz.pc_container_code_ids.mapped("name")
                product_ids = (
                    wiz.picking_ids.mapped("move_ids_without_package")
                    .filtered(lambda m: m.pc_container_code in tote_codes)
                    .mapped("product_id")
                    .ids
                )
                line.available_product_ids = [(6, 0, product_ids)]
            else:
                line.available_product_ids = [(5,)]

    @api.depends("wizard_id.line_ids")
    def _compute_available_quantity(self):
        """Always equal to how many line-records were created for this SKU+pick."""
        for line in self:
            if not line.picking_id or not line.product_id:
                line.available_quantity = 0
                continue
            same = line.wizard_id.line_ids.filtered(
                lambda l: l.picking_id == line.picking_id and l.product_id == line.product_id
            )
            line.available_quantity = len(same)

    @api.depends("wizard_id.line_ids.quantity", "product_id", "picking_id")
    def _compute_remaining_quantity(self):
        for line in self:
            if not line.picking_id or not line.product_id:
                line.remaining_quantity = 0
                continue

            same_lines = line.wizard_id.line_ids.filtered(
                lambda l: l.product_id.id == line.product_id.id and l.picking_id.id == line.picking_id.id
            )

            # Total expected lines for this product
            total_units = len(same_lines)

            # Count only scanned or added lines (skip new blank ones)
            scanned_units = sum(
                1 for l in same_lines
                if l.scanned or l.line_added or l.quantity == 1
            )

            # Don't let it go negative
            line.remaining_quantity = max(total_units - scanned_units, 0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return

        wizard = self.wizard_id
        if not wizard.pack_bench_id:
            raise ValidationError("Please select a Pack Bench before proceeding.")

        self.weight = self.product_id.weight or 0.0

        if not self.weight:
            return {
                'warning': {
                    'title': _("Missing Weight"),
                    'message': _(
                        "The selected product '%s' does not have a weight. Please enter it manually.") % self.product_id.name
                }
            }

        # Auto-set package number
        if wizard.next_package_number:
            self.product_package_number = wizard.next_package_number

        # Auto-select package box based on incoterm
        if self.picking_id and self.picking_id.sale_id:
            sale = self.picking_id.sale_id
            incoterm = sale.packaging_source_type
            tenant = wizard.tenant_code_id
            site = wizard.site_code_id

            box = self.env['package.box.configuration'].search([
                ('name', '=', incoterm),
                ('tenant_code_id', '=', tenant.id),
                ('site_code_id', '=', site.id)
            ], limit=1)

            if box:
                self.package_box_type_id = box.id
                _logger.info(f"Auto-selected box '{box.name}' for product {self.product_id.name}")
            else:
                default_box = self.env['package.box.configuration'].search([
                    ('is_default_package', '=', True),
                    ('tenant_code_id', '=', tenant.id),
                    ('site_code_id', '=', site.id)
                ], limit=1)
                if default_box:
                    self.package_box_type_id = default_box.id
                    _logger.info(f"Assigned default box '{default_box.name}' for product {self.product_id.name}")

        if self.product_id.is_fragile:
            return {
                'warning': {
                    'title': _("Packing Information"),
                    'message': _("This item is fragile and must be packed with bubble wrap for protection.")
                }
            }


    @api.onchange('weight')
    def _onchange_weight(self):
        """
        When the user manually enters a weight or leaves it empty:
        - If weight is 0 or missing, assign default value of 0.5.
        - Save to product if not already set.
        """
        if self.product_id:
            if not self.weight or self.weight == 0.0:
                self.weight = 0.5  #  Default fallback
                _logger.warning(f"Weight was missing or zero; defaulted to 0.5 for product {self.product_id.name}")

            if not self.product_id.weight or self.product_id.weight == 0.0:
                self.product_id.write({'weight': self.weight})
                _logger.info(f"Saved defaulted weight {self.weight} to product {self.product_id.name}")

            # Re-trigger package box selection
            self.wizard_id._auto_select_package_box_type()

    @api.depends('product_id')
    def _compute_show_serial_number(self):
        for line in self:
            line.show_serial_number = line.product_id.is_serial_number if line.product_id else False

    @api.onchange('serial_number')
    def _onchange_serial_number(self):
        if self.product_id.is_serial_number:
            if not self.serial_number:
                return {
                    'warning': {
                        'title': _("Serial Number Required"),
                        'message': _("Please enter a serial number for product '%s'.") % self.product_id.name
                    },
                    'value': {
                        'serial_number': self.serial_number  # Preserve current input
                    }
                }

            #  Try to update the serial number in the matching sale order line
            sale_order = self.sale_order_id
            if sale_order:
                matching_line = sale_order.order_line.filtered(lambda l: l.product_id.id == self.product_id.id)

                if matching_line:
                    matching_line[0].serial_number = self.serial_number
                    _logger.info(
                        f"Serial number '{self.serial_number}' updated on sale order line for product {self.product_id.name}")
                else:
                    _logger.warning(
                        f"No matching sale order line found for product {self.product_id.name} in order {sale_order.name}")
