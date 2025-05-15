# -*- coding: utf-8 -*-
import logging
import json
import requests
import xml.etree.ElementTree as ET
import urllib
import socket
import httpx
import time
import datetime
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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
        help="Scan SKU or barcode. The system will match the product automatically.",
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
    total_line_items = fields.Integer(
        string="Total Line Items",
        compute="_compute_total_line_items",
        store=True
    )
    confirm_pack_warning = fields.Boolean(string="User Confirmed Pack Warning", default=False)

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

    @api.depends('line_ids')
    def _compute_total_line_items(self):
        for wizard in self:
            wizard.total_line_items = len(wizard.line_ids)

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
            raise ValidationError("No pickings found for the scanned tote(s).")

        self.picking_ids = [(6, 0, pickings.ids)]

        #  Validate all totes per picking are scanned
        for picking in pickings:
            all_totes_in_pick = picking.move_ids_without_package.mapped('pc_container_code')
            scanned_totes = set(tote_codes)
            expected_totes = set(all_totes_in_pick)

            missing_totes = expected_totes - scanned_totes
            if missing_totes:
                raise ValidationError((
                    "You must scan all tote(s) for Picking '%s'.\n\n"
                    "Missing tote(s): %s\n\n"
                    "Please scan them before continuing."
                ) % (picking.name, ", ".join(missing_totes)))

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

                # Always create one line per unit, regardless of single/multi pick
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
            "Please create a default package type before continuing."
        ))

    @api.onchange("scanned_sku")
    def _onchange_scanned_sku(self):
        """Handle scanned barcode or SKU (multi-barcode aware)."""
        self.ensure_one()

        scanned_input = (self.scanned_sku or "").strip()
        if not scanned_input:
            return

        # Try barcode or default_code match
        product = self.env['product.product'].search([
            '|',
            ('barcode', '=', scanned_input),
            ('default_code', '=', scanned_input)
        ], limit=1)

        # Try multi-barcode if not found
        if not product:
            multi_barcode = self.env['product.barcode.multi'].search([('name', '=', scanned_input)], limit=1)
            product = multi_barcode.product_id if multi_barcode else None

        if not product:
            _logger.warning(f"No product found for scanned code: {scanned_input}")
            raise ValidationError(_("No product found for scanned code: %s") % scanned_input)

        sku = product.default_code
        matching_lines = self.line_ids.filtered(lambda l: l.product_id == product)
        if not matching_lines:
            raise ValidationError(_("Scanned SKU '%s' is not in this tote.") % sku)

        # Find the next unscanned line
        unscanned_line = matching_lines.filtered(lambda l: l.quantity == 0 and not l.line_added).sorted(
            key=lambda l: not l.product_package_number)
        if not unscanned_line:
            raise ValidationError(_("All units of SKU '%s' have already been scanned.") % sku)

        line = unscanned_line[0]
        if line.api_payload_attempted:
            _logger.warning(f"[SKIP] Payload already attempted for SKU {sku}. Skipping resend.")
            return

        if not line.product_package_number:
            line.product_package_number = self.next_package_number

        is_multi_pick = len(self.picking_ids) > 1

        # Set basic scanned values
        line.update({
            'scanned': True,
            'quantity': 1,
            'remaining_quantity': 0,
            'available_quantity': 1,
            'line_added': True
        })

        if is_multi_pick:
            if any(l.api_payload_success for l in self.line_ids):
                _logger.info("[LEGACY] Payload already sent — skipping.")
                return

            try:
                payload = self._prepare_old_logic_payload_multi_picks()
                is_prod = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
                use_orders_endpoint = self.site_code_id.name == "SHIPEROOALTONA" and self.tenant_code_id.name == "STONEHIVE"
                api_url = (
                    "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/orders" if is_prod else
                    "https://shiperooconnect-dev.automation.shiperoo.com/api/orders"
                ) if use_orders_endpoint else (
                    "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/ot_orders" if is_prod else
                    "https://shiperooconnect-dev.automation.shiperoo.com/api/ot_orders"
                )

                self.send_payload_to_api(api_url, payload)

                for l in self.line_ids:
                    l.update({
                        'api_payload_success': True,
                        'line_added': True,
                        'scanned': True,
                        'quantity': 1,
                        'remaining_quantity': 0
                    })

                return {
                    'warning': {
                        'title': _("Success"),
                        'message': _("Legacy label printed successfully."),
                        'type': 'notification'
                    }
                }
            except Exception as e:
                _logger.error(f"[LEGACY] Payload failed: {str(e)}")
                raise UserError(_("Legacy label failed:\n%s") % str(e))

        # Single pick: no API call here
        self.last_scanned_line_id = line
        self.scanned_sku = False

    def increment_package_number(self):
        self.ensure_one()
        self.next_package_number += 1
        _logger.info(f"Package number incremented to {self.next_package_number}")

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',  # Keeps the wizard open
        }

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

    def _process_single_pick_old_logic(self, picking, scanned_lines):
        product_lines = []
        for line in scanned_lines:
            product_lines.append({
                "sku_code": line.product_id.default_code,
                "name": line.product_id.name,
                "quantity": line.quantity,
                "remaining_quantity": line.remaining_quantity,
                "weight": line.weight,
                "picking_id": line.picking_id.name,
                "customer_name": line.picking_id.partner_id.name or "",
                 "shipping_address": f"{line.picking_id.partner_id.name or ''}, {line.picking_id.partner_id.street or ''}, "
                                     f"{line.picking_id.partner_id.street2 or ''}, {line.picking_id.partner_id.city or ''}, "
                                     f"{line.picking_id.partner_id.state_id.name if line.picking_id.partner_id.state_id else ''}, "
                                     f"{line.picking_id.partner_id.country_id.name if line.picking_id.partner_id.country_id else ''}, "
                                     f"{line.picking_id.partner_id.zip or ''}",
                "customer_email": line.picking_id.partner_id.email,
                "tenant_code": line.tenant_code_id.name if line.tenant_code_id else "",
                "site_code": line.site_code_id.name if line.site_code_id else "",
                "receipt_number": line.picking_id.name,
                "partner_id": line.picking_id.partner_id.name,
                "origin": line.picking_id.origin or "N/A",
                "package_name": (line.package_box_type_id.name if line.package_box_type_id else "NoBox") + '_' + str(
                    line.product_package_number),
                "length": line.package_box_type_id.length or "NA",
                "width": line.package_box_type_id.width or "NA",
                "height": line.package_box_type_id.height or "NA",
                "sales_order_number": line.picking_id.sale_id.name if line.picking_id.sale_id else "N/A",
                "sales_order_carrier": line.picking_id.sale_id.service_type if line.picking_id.sale_id else "N/A",
                "sales_order_origin": line.picking_id.sale_id.origin if line.picking_id.sale_id else "N/A",
                "customer_reference": line.picking_id.sale_id.client_order_ref if line.picking_id.sale_id else "N/A",
                "incoterm_location": line.incoterm_location or "N/A",
                "status": line.picking_id.sale_id.post_category if line.picking_id.sale_id else "N/A",
                "carrier": line.picking_id.sale_id.carrier or "N/A",
                "hs_code": line.product_id.hs_code or "",
                "cost_price": line.product_id.standard_price or "0.0",
                "sale_price": line.product_id.list_price or "0.0",
            })

        payload = {
            "header": {
                "user_id": "system",
                "user_key": "system",
                "warehouse_code": self.warehouse_id.name
            },
            "body": {
                "receipt_list": [{
                    "product_lines": product_lines,
                    "pack_bench_number": self.pack_bench_id.name,
                    "pack_bench_ip": self.pack_bench_id.printer_ip,
                }]
            }
        }

        # is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        # api_url = "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/orders" if is_production == 'True' else "https://shiperooconnect-dev.automation.shiperoo.com/api/orders"

        _logger.info(f"[OLD LOGIC] Sending legacy payload:\n{json.dumps(payload, indent=4)}")
        # self.send_payload_to_api(api_url, payload)
        return payload

    def _prepare_old_logic_payload_multi_picks(self):
        """
        Prepares and returns the old format payload for multiple picks for:

        This method groups lines per product and builds a flat payload list as required by
        the  Shiperoo API.
        """

        product_lines = []

        scanned_lines = self.line_ids.filtered(lambda l: l.scanned)
        if not scanned_lines:
            raise UserError(
                _("No scanned lines found to build legacy multi-pick payload. Please scan at least one SKU."))

        for line in scanned_lines:
            product_lines.append({
                "sku_code": line.product_id.default_code,
                "name": line.product_id.name,
                "quantity": line.quantity,
                "remaining_quantity": line.remaining_quantity,
                "weight": line.weight or 0.5,
                "picking_id": line.picking_id.name if line.picking_id else "",
                "customer_name": line.picking_id.partner_id.name or "",
                "shipping_address": f"{line.picking_id.partner_id.name or ''}, {line.picking_id.partner_id.street or ''}, "
                                     f"{line.picking_id.partner_id.street2 or ''}, {line.picking_id.partner_id.city or ''}, "
                                     f"{line.picking_id.partner_id.state_id.name if line.picking_id.partner_id.state_id else ''}, "
                                     f"{line.picking_id.partner_id.country_id.name if line.picking_id.partner_id.country_id else ''}, "
                                     f"{line.picking_id.partner_id.zip or ''}",
                "customer_email": line.picking_id.partner_id.email,
                "tenant_code": line.tenant_code_id.name if line.tenant_code_id else "",
                "site_code": line.site_code_id.name if line.site_code_id else "",
                "receipt_number": line.picking_id.name,
                "partner_id": line.picking_id.partner_id.name,
                "origin": line.picking_id.origin or "N/A",
                "package_name": (line.package_box_type_id.name if line.package_box_type_id else "NoBox") + '_' + str(
                    line.product_package_number),
                "length": line.package_box_type_id.length or "NA",
                "width": line.package_box_type_id.width or "NA",
                "height": line.package_box_type_id.height or "NA",
                "sales_order_number": line.picking_id.sale_id.name if line.picking_id.sale_id else "N/A",
                "sales_order_carrier": line.picking_id.sale_id.service_type if line.picking_id.sale_id else "N/A",
                "sales_order_origin": line.picking_id.sale_id.origin if line.picking_id.sale_id else "N/A",
                "customer_reference": line.picking_id.sale_id.client_order_ref if line.picking_id.sale_id else "N/A",
                "incoterm_location": line.sale_order_id.packaging_source_type if line.sale_order_id else "N/A",
                "status": line.picking_id.sale_id.post_category if line.picking_id.sale_id else "N/A",
                "carrier": line.picking_id.sale_id.carrier if line.picking_id.sale_id else "N/A",
                "hs_code": line.product_id.hs_code or "",
                "so_reference": line.picking_id.sale_id.client_order_ref or "N/A",
                "cost_price": line.product_id.standard_price or "0.0",
                "sale_price": line.product_id.list_price or "0.0",
            })

        payload = {
            "header": {
                "user_id": "system",
                "user_key": "system",
                "warehouse_code": self.warehouse_id.name
            },
            "body": {
                "receipt_list": [
                    {
                        "product_lines": product_lines,
                        "pack_bench_number": self.pack_bench_id.name,
                        "pack_bench_ip": self.pack_bench_id.printer_ip
                    }
                ]
            }
        }

        _logger.info(f"[LOGIC MULTI-PICK PAYLOAD] {json.dumps(payload, indent=4)}")
        return payload

    def pack_products(self):
        """
        Main method to validate and process the pack operation.
        - Shows a warning if unscanned lines exist (with 2-step confirmation).
        - Sends payloads for scanned lines.
        - Handles both single-pick and multi-pick scenarios.
        - Releases containers after successful pack.
        """
        self.ensure_one()

        if not self.picking_ids or not self.picking_ids.ids:
            _logger.warning("[PACK_PRODUCTS] picking_ids is empty or not properly set. Value: %s", self.picking_ids)
            raise ValidationError(_("No pickings are linked to this operation. Please check your container code."))

        # Check for unscanned lines
        unscanned_lines = self.line_ids.filtered(lambda l: not l.scanned)
        if unscanned_lines:
            missing_skus = ", ".join(unscanned_lines.mapped("product_id.default_code"))

            # Show warning only on first click
            if not self.confirm_pack_warning:
                self.confirm_pack_warning = True
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Unscanned Items Detected'),
                        'message': _(
                            'You have not scanned the following SKU(s):\n%s\n\nClick "Pack" again to continue anyway.') % missing_skus,
                        'type': 'warning',
                        'sticky': False,
                    }
                }
            else:
                _logger.warning("[PACK_PRODUCTS] User acknowledged unscanned lines. Proceeding anyway.")

        # Reset warning flag before proceeding
        self.confirm_pack_warning = False

        # Get scanned lines only
        scanned_lines = self.line_ids.filtered(lambda l: l.scanned)
        if not scanned_lines:
            raise ValidationError(_("No scanned products found to pack."))

        # Validate scanned lines
        for line in scanned_lines:
            if not line.product_id:
                raise ValidationError(_("All line items must have a product selected."))
            if not line.weight or line.weight <= 0.0:
                raise ValidationError(
                    _("Product '%s' (SKU: %s) has missing weight. Please update it before proceeding.")
                    % (line.product_id.name, line.product_id.default_code or "N/A"))

        # Add section header for tote(s)
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
            picking_orders.setdefault(line.picking_id.id, []).append(line)

        # Handle single pick separately
        if len(self.picking_ids) <= 1:
            if self.single_pick_payload_sent:
                _logger.warning(f"[SKIP] Single-pick payload already sent for wizard {self.id}")
                raise UserError(_("Payload already sent for this pick. Please refresh."))

            payload = self.process_single_pick()
            _logger.info(f"[PRE-FLAG] Wizard {self.id} marked as payload sent before API call.")

        # Release container(s)
        # self.release_container()

        return {'type': 'ir.actions.act_window_close'}


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
        # config = self.get_onetraker_config()
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                _logger.info(f"[PALOAD] Label created. Response:\n{response.text}")
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
    quantity = fields.Float(string='Quantity', store=True)
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
            is_multi_pick = len(wizard.picking_ids) > 1
            is_serial_required = line.product_id.is_serial_number
            has_serial = bool(line.serial_number)
            is_fragile = line.product_id.is_fragile

            ready_for_payload = (
                    line.product_id and
                    line.package_box_type_id and
                    line.weight > 0 and
                    line.product_package_number and
                    is_multi_pick and
                    (not is_serial_required or has_serial)
            )

            # Show appropriate warnings
            if not ready_for_payload:
                if is_serial_required and not has_serial:
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
                if is_fragile:
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

            # Skip if any payload already sent
            if any(l.api_payload_success for l in wizard.line_ids):
                _logger.warning("[OLD LOGIC] Legacy payload already triggered — skipping resend.")
                return

            try:
                payload = wizard._prepare_old_logic_payload_multi_picks()
                is_prod = wizard.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
                use_orders = wizard.site_code_id.name == "SHIPEROOALTONA" and wizard.tenant_code_id.name == "STONEHIVE"

                api_url = (
                    "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/orders" if is_prod else
                    "https://shiperooconnect-dev.automation.shiperoo.com/api/orders"
                ) if use_orders else (
                    "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/ot_orders" if is_prod else
                    "https://shiperooconnect-dev.automation.shiperoo.com/api/ot_orders"
                )

                _logger.info("[OLD LOGIC] Triggering legacy payload to: %s", api_url)
                wizard.send_payload_to_api(api_url, payload)

                for l in wizard.line_ids:
                    l.update({
                        'api_payload_success': True,
                        'line_added': True,
                        'scanned': True,
                        'quantity': 1,
                        'remaining_quantity': 0
                    })

                return {
                    'warning': {
                        'title': _("Success"),
                        'message': _("Legacy label printed successfully for multi-pick."),
                        'type': 'notification'
                    }
                }

            except Exception as e:
                _logger.error(f"[MULTI-PICK] Failed to send legacy payload: {str(e)}")
                raise UserError(_("Legacy multi-pick label failed:\n%s") % str(e))

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

    @api.depends("wizard_id.line_ids.scanned")
    def _compute_remaining_quantity(self):
        for line in self:
            if not line.picking_id or not line.product_id:
                line.remaining_quantity = 0
                continue

            same_lines = line.wizard_id.line_ids.filtered(
                lambda l: l.product_id.id == line.product_id.id and l.picking_id.id == line.picking_id.id
            )

            total_units = len(same_lines)

            # Count scanned units and fix quantity if scanned but 0
            scanned_units = 0
            for l in same_lines:
                if l.scanned or l.line_added:
                    scanned_units += 1
                    if l.quantity == 0:
                        l.quantity = 1  # Fix quantity to 1 for already scanned line

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
        When the user enters a weight:
        - If weight is 0 or missing, assign default value of 0.5.
        - Save to product if not already set.
        - Propagate weight to all other lines with the same product in the wizard.
        """
        if not self.product_id or not self.wizard_id:
            return

        # Default to 0.5 if not set
        if not self.weight or self.weight == 0.0 and len(self.picking_ids) != 1:
            self.weight = 0.5
            _logger.warning(f"Weight was missing or zero; defaulted to 0.5 for product {self.product_id.name}")

        # Save to product if not already set
        if not self.product_id.weight or self.product_id.weight == 0.0:
            self.product_id.write({'weight': self.weight})
            _logger.info(f"Saved defaulted weight {self.weight} to product {self.product_id.name}")
        if not self.weight or self.weight == 0.0 and len(self.picking_ids) != 1:
            self.weight = 0.5
            _logger.warning(f"Weight was missing or zero; defaulted to 0.5 for product {self.product_id.name}")

        # Propagate to other lines with same product in same wizard
        same_product_lines = self.wizard_id.line_ids.filtered(
            lambda l: l.product_id.id == self.product_id.id and l.id != self.id
        )
        for line in same_product_lines:
            if not line.weight or line.weight == 0.0:
                line.weight = self.weight
                _logger.info(f"Updated weight to {self.weight} for product {line.product_id.name} on line ID {line.id}")

        # Re-trigger package box selection logic if needed
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
