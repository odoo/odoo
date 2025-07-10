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
import threading
import asyncio
from odoo.tools.safe_eval import safe_eval


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


def _tote_codes(wizard):
    print("\n\n\n tote codes====", wizard.pc_container_code_ids.mapped("name"))
    return wizard.pc_container_code_ids.mapped("name")

def _split_codes(codes):
    """
    Takes a list of code strings (could be comma-separated), splits, strips, and returns set of codes.
    E.g., ['Pc01,Pc02', 'Pc03'] → {'Pc01', 'Pc02', 'Pc03'}
    """
    result = set()
    for code in codes:
        for part in (code or '').split(','):
            part = part.strip()
            if part:
                result.add(part)
    return result

class PackDeliveryReceiptWizard(models.TransientModel):
    _name = 'custom.pack.app.wizard'
    _description = 'Pack Delivery Receipt Wizard'
    _inherit = ['mail.thread']

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
    show_message = fields.Boolean(string="Show Message", default=False)
    message_text = fields.Text(string="Display Message")
    sale_order_ids = fields.Many2many(
        'sale.order',
        string='Sale Order Numbers',
        compute='_compute_sale_order_ids',
        store=False,
        help="Auto-fetched from selected pickings."
    )

    @api.depends('picking_ids')
    def _compute_sale_order_ids(self):
        for wizard in self:
            wizard.sale_order_ids = wizard.picking_ids.mapped('sale_id')

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

        tote_codes = _split_codes(self.pc_container_code_ids.mapped("name"))
        if not tote_codes:
            return

        # Find all pickings for this site and assigned and not packed (possible merged)
        all_pickings = self.env["stock.picking"].search([
            ("site_code_id", "=", self.site_code_id.id),
            ("state", "=", "assigned"),
            ("current_state", "!=", "pack"),
        ])

        # Step 1: Find all SOs involved in scanned totes (just like before)
        sale_ids = set()
        for picking in all_pickings:
            for mv in picking.move_ids_without_package:
                if bool(_split_codes([(mv.pc_container_code or "")]) & tote_codes):
                    if picking.sale_id:
                        sale_ids.add(picking.sale_id.id)

        # Step 2: For those SOs, get ALL pickings with operation_process_type == 'pick'
        if not sale_ids:
            raise ValidationError(
                (
                    "No picking found for scanned tote(s): %s at this site with state='Ready'. Please check the tote code or picking state.")
                % ', '.join(sorted(tote_codes))
            )

        relevant_pickings = self.env["stock.picking"].search([
            ("site_code_id", "=", self.site_code_id.id),
            ("state", "=", "assigned"),
            ("current_state", "!=", "pack"),
            ("operation_process_type", "=", "pick"),
            ("sale_id", "in", list(sale_ids)),
        ])
        if not relevant_pickings:
            raise ValidationError(
                ("No pickings found for involved Sale Orders at this site with state='Ready'.")
            )

        # Step 3: Gather ALL required totes for these picks (including "-")
        required_totes = set()
        for picking in relevant_pickings:
            for mv in picking.move_ids_without_package:
                tote = (mv.pc_container_code or "").strip()
                required_totes.update(_split_codes([tote]))
                if not tote:
                    required_totes.add("-")

        # Step 4: Raise error if not all are scanned (shows all pick numbers and their totes)
        missing = required_totes - tote_codes
        if missing:
            picks_and_totes = []
            for picking in relevant_pickings:
                pick_totes = []
                for mv in picking.move_ids_without_package:
                    code = (mv.pc_container_code or "").strip()
                    pick_totes.append(code if code else "-")
                picks_and_totes.append(
                    f"Pick: {picking.name} - Tote(s): {', '.join(pick_totes) if pick_totes else '-'}"
                )
            missing_display = [m or '-' for m in missing]
            raise ValidationError((
                    f"You must scan ALL totes before packing!\n"
                    f"Missing tote(s): {', '.join(missing_display)}\n"
                    "Picks for this order:\n" +
                    "\n".join(picks_and_totes)
            ))

        # All required totes are now scanned, proceed: only create lines for the actual scanned pickings
        # (Still only pickings with a move that matches a scanned tote)
        pickings_to_load = relevant_pickings.filtered(
            lambda p: any(
                bool(_split_codes([(mv.pc_container_code or "")]) & tote_codes)
                for mv in p.move_ids_without_package
            )
        )
        self.picking_ids = [(6, 0, pickings_to_load.ids)]

        vals_list = []
        for picking in pickings_to_load:
            incoterm = picking.sale_id.packaging_source_type if picking.sale_id else False
            pkg_id = self._get_package_box_id(
                picking.tenant_code_id.id,
                picking.site_code_id.id,
                incoterm
            )
            moves = picking.move_ids_without_package.filtered(
                lambda mv: bool(_split_codes([(mv.pc_container_code or "")]) & tote_codes)
            )
            for mv in moves:
                qty_to_create = int(round(mv.remaining_qty or 0))
                for _ in range(qty_to_create):
                    vals_list.append({
                        "wizard_id": self.id,
                        "product_id": mv.product_id.id,
                        "picking_id": picking.id,
                        "quantity": 0,
                        "available_quantity": 1,
                        "weight": mv.product_id.weight or 0.4,
                        "tenant_code_id": picking.tenant_code_id.id,
                        "site_code_id": picking.site_code_id.id,
                        "sale_order_id": picking.sale_id.id,
                        "package_box_type_id": pkg_id,
                    })
        if vals_list:
            self.line_ids = [(0, 0, v) for v in vals_list]

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

        raise ValidationError(_(
            "No package-box configuration found for this tenant/site. "
            "Please create a default package type before continuing."
        ))

    @api.onchange("scanned_sku")
    def _onchange_scanned_sku(self):
        self.ensure_one()
        self.message_text = False
        self.show_message = False
        scanned_input = (self.scanned_sku or "").strip()
        if not scanned_input:
            return

        tenant = self.tenant_code_id.name
        pick_ids = self.picking_ids.ids
        if not tenant or not pick_ids:
            raise ValidationError(_("Tenant and Picking must be selected before scanning."))

        # Find all valid product_ids used in selected pickings
        valid_move_products = self.env['stock.move'].search([
            ('picking_id', 'in', pick_ids)
        ]).mapped('product_id')
        valid_product_ids = set(valid_move_products.ids)

        # 1. Search product by barcode or default_code WITH tenant match
        product = self.env['product.product'].search([
            ('tenant_id', '=', tenant),
             '|',
            ('barcode', '=', scanned_input),
            ('default_code', '=', scanned_input)
        ], limit=1)

        # 2. If not found, search in product.barcode.multi
        if not product:
            multi_barcode = self.env['product.barcode.multi'].search([
                ('name', '=', scanned_input),
                ('product_id.tenant_id', '=', tenant)
            ], limit=1)
            if multi_barcode:
                product = multi_barcode.product_id

        if not product:
            _logger.warning(f"No product found for scanned code: {scanned_input}")
            raise ValidationError(_("No product found for scanned code: %s") % scanned_input)

        if product.id not in valid_product_ids:
            _logger.warning(f"Scanned product '{product.display_name}' is not part of the selected pickings.")
            raise ValidationError(_(
                "Scanned product '%s' is not included in the current picking(s).") % product.display_name)

        sku = product.default_code
        # --- FIX: Define matching_lines here ---
        matching_lines = self.line_ids.filtered(lambda l: l.product_id == product)
        if not matching_lines:
            _logger.warning(f"Scanned SKU '{sku}' does not match any line in this wizard.")
            raise ValidationError(_("Scanned SKU '%s' is not in this tote.") % sku)

        line = matching_lines.filtered(lambda l: l.quantity == 0 and not l.line_added).sorted(
            key=lambda l: not l.product_package_number
        )
        if not line:
            raise ValidationError(_("All units of SKU '%s' have already been scanned.") % sku)
        line = line[0]

        if line.api_payload_attempted:
            _logger.warning(f"[SKIP] Payload already attempted for SKU {sku}. Skipping resend.")
            return

        if not line.product_package_number:
            line.product_package_number = self.next_package_number

        # ====== BRANCH ON SALES ORDER COUNT ======
        so_count = len(set(self.line_ids.mapped('sale_order_id.id')))
        sale = line.picking_id.sale_id

        # --- MESSAGE DISPLAY (Both Single and Multi-Pick) ---
        if sale and sale.message_code and not self.show_message:
            msg = self.env['custom.message.configuration'].search([
                ('message_code', '=', sale.message_code)
            ], limit=1)
            if msg:
                self.show_message = True
                self.message_text = "Sale Order Number: %s\nMessage: %s" % (sale.name, msg.description)

        if so_count > 1:
            # Multi-pick: legacy logic for Stonehive/SHIPEROOALTONA
            if self.site_code_id.name == "SHIPEROOALTONA" and self.tenant_code_id.name == "STONEHIVE":
                _logger.info("[LEGACY] Triggering legacy multi-pick payload...")
                if any(l.api_payload_success for l in self.line_ids):
                    _logger.info("[LEGACY] Payload already sent — skipping.")
                    return

                line.scanned = True
                line.quantity = 1
                line.remaining_quantity = 0
                line.available_quantity = 1
                line.line_added = True

                try:
                    payload = self._prepare_old_logic_payload_multi_picks()
                    is_prod = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
                    api_url = (
                        "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/orders"
                        if is_prod else
                        "https://int-shiperooconnect-dev.automation.shiperoo.com/api/orders"
                    )
                    self.send_payload_to_api(api_url, payload)

                    for l in self.line_ids:
                        l.api_payload_success = True
                        l.line_added = True
                        l.scanned = True
                        l.quantity = 1
                        l.remaining_quantity = 0

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

            print("\n\n\n\ multi pick before auspost====", line.picking_id.sale_id.carrier,
                  line.picking_id.sale_id.items, line.picking_id.sale_id.shipmentid)
            if (line.picking_id.sale_id.carrier or '').upper() == 'AUSPOST':
                _logger.info("[LEGACY] Triggering legacy multi-pick payload...")
                if any(l.api_payload_success for l in self.line_ids):
                    _logger.info("[LEGACY] Payload already sent — skipping.")
                    return

                line.scanned = True
                line.quantity = 1
                line.remaining_quantity = 0
                line.available_quantity = 1
                line.line_added = True

                try:
                    payload = self._prepare_old_logic_payload_multi_picks()
                    is_prod = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
                    api_url = "https://shiperoo-connect-shopify.uat.automation.shiperoo.com/auspost/shipment" if is_prod == 'True' \
                        else "https://shiperoo-connect-shopify.uat.automation.shiperoo.com/auspost/shipment"

                    self.send_payload_to_api(api_url, payload)

                    for l in self.line_ids:
                        l.api_payload_success = True
                        l.line_added = True
                        l.scanned = True
                        l.quantity = 1
                        l.remaining_quantity = 0

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

            # MULTI-PICK - OneTraker
            else:
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
                except Exception as e:
                    raise UserError(_("Error while sending label for Order %s:\n%s") % (sale.name, str(e)))
        else:
            # SINGLE PICK LOGIC (all lines are for one SO)
            line.quantity = 1
            line.available_quantity = 1
            line.remaining_quantity = 0
            line.line_added = True
            line.scanned = True
            # Don't send the payload immediately here (unless that's your single-pick flow)
            # For single pick, payload usually sent on 'Pack' button or final scan

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

        #  Log config source
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
            record.show_package_box_in_lines = len(record.sale_order_ids) > 1

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
            partner = picking.partner_id
            country_code = partner.country_id.code if partner and partner.country_id else "AU"
            international_flag = 1 if country_code.upper() != "AU" else 0
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
                "business_name": line.picking_id.partner_id.business_name or "",
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
                "shipmentid": line.picking_id.sale_id.shipmentid or "",
                "items": line.picking_id.sale_id.items or "",
                "international":international_flag,
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

        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        if self.site_code_id.name != "SHIPEROOALTONA" or self.tenant_code_id.name != "STONEHIVE":
            api_url = "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/orders" if is_production == 'True' \
                else "https://shiperooconnect-dev.automation.shiperoo.com/api/orders"
        if (line.picking_id.sale_id.carrier or '').upper() == 'AUSPOST':
            api_url = "https://shiperoo-connect-shopify.uat.automation.shiperoo.com/auspost/shipment" if is_production == 'True' \
                else "https://shiperoo-connect-shopify.uat.automation.shiperoo.com/auspost/shipment"
        print("\n\n\n old logic Aup[opst payload single pick=====", api_url)
        _logger.info(f"[OLD LOGIC] Sending legacy payload:\n{json.dumps(payload, indent=4)}")
        self.send_payload_to_api(api_url, payload)
        #
        # # Optional: update state after sending
        # picking.write({'current_state': 'pack'})
        # picking.sale_id.write({
        #     'pick_status': 'packed',
        #     'delivery_status': 'partial',
        #     'tracking_url': 'https://auspost.com.au/mypost/track/details/placeholder'
        # })

        return payload

    def _prepare_old_logic_payload_multi_picks(self):
        """
        Prepares and returns the old format payload for multiple picks for:
        Site Code: SHIPEROOALTONA
        Tenant Code: STONEHIVE

        This method groups lines per product and builds a flat payload list as required by
        the old Shiperoo API.
        """
        # if self.site_code_id.name != "SHIPEROOALTONA" or self.tenant_code_id.name != "STONEHIVE":
        #     raise ValidationError("This method should only be called for SHIPEROOALTONA and STONEHIVE.")
        product_lines = []

        scanned_lines = self.line_ids.filtered(lambda l: l.scanned)
        if not scanned_lines:
            raise UserError(
                _("No scanned lines found to build legacy multi-pick payload. Please scan at least one SKU."))

        for line in scanned_lines:
            partner = scanned_lines[0].picking_id.partner_id if scanned_lines else False
            country_code = partner.country_id.code if partner and partner.country_id else "AU"
            international_flag = 1 if country_code.upper() != "AU" else 0
            product_lines.append({
                "sku_code": line.product_id.default_code,
                "name": line.product_id.name,
                "quantity": line.quantity,
                "remaining_quantity": line.remaining_quantity,
                "weight": line.weight or 0.4,
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
                "business_name": line.picking_id.partner_id.business_name or "",
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
                "shipmentid": line.picking_id.sale_id.shipmentid or "",
                "items":line.picking_id.sale_id.items or "",
                "international": international_flag,
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

        _logger.info(f"[OLD LOGIC MULTI-PICK PAYLOAD] {json.dumps(payload, indent=4)}")
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
        if self.single_pick_payload_sent:
            _logger.info(f"[SINGLE PICK] Payload already sent for wizard {self.id}, skipping re-send.")
            return
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
        sale_order_ids = set(self.picking_ids.mapped('sale_id.id'))
        if len(sale_order_ids) == 1:
            if self.single_pick_payload_sent:
                _logger.warning(f"[SKIP] Single-pick payload already sent for wizard {self.id}")
                raise UserError(_("Payload already sent for this pick. Please refresh."))

            payload = self.process_single_pick()

            # Only call OneTraker if not using legacy logic
            # if not (self.site_code_id.name == "SHIPEROOALTONA" and self.tenant_code_id.name == "STONEHIVE"):
            #     config = self.get_onetraker_config()
            #     api_url = config["ONETRAKER_CREATE_ORDER_URL"]
            #     self.send_payload_to_api(api_url, payload)

            self.write({'single_pick_payload_sent': True})
            self.env.cr.flush()
            _logger.info(f"[PRE-FLAG] Wizard {self.id} marked as payload sent before API call.")
            # self.update_remaining_packed_qty()

        # Release container(s)
        # self.update_remaining_packed_qty()
        self.release_container()

        return {'type': 'ir.actions.act_window_close'}

    def process_single_pick(self):
        """
        Builds and sends OneTraker payload for single-pick based on all scanned lines.
        Validates ALL pickings for the sale order (handles discrete SOs).
        Validates picking only after successful label generation & printing.
        """
        self.ensure_one()
        if self.single_pick_payload_sent:
            _logger.info(f"[SINGLE PICK] Payload already sent for wizard {self.id}, skipping re-send.")
        self.single_pick_payload_sent = True
        self.env.cr.flush()
        pickings = self.picking_ids
        if not pickings:
            raise ValidationError("No picking records found to pack.")

        scanned_lines = self.line_ids.filtered(lambda l: l.scanned)
        if not scanned_lines:
            raise ValidationError("No scanned lines found to pack for this picking.")

        main_picking = pickings[0]
        sale = main_picking.sale_id
        partner = main_picking.partner_id

        # Handle legacy site/tenant logic (STONEHIVE/SHIPEROOALTONA)
        if self.site_code_id.name == "SHIPEROOALTONA" and self.tenant_code_id.name == "STONEHIVE":
            return self._process_single_pick_old_logic(main_picking, scanned_lines)
        #Handle for Auspost if Carrier Auspost any tenant or site send old payload
        if sale and (sale.carrier or "").upper() == "AUSPOST":
            self._process_single_pick_old_logic(main_picking, scanned_lines)
            return {'type': 'ir.actions.act_window_close'}
        if sale and sale.service_type and sale.service_type.strip().upper() == "MANUAL WB":
            _logger.info("[MANUAL WB] Detected Manual WB order – skipping label generation.")

            sale.write({
                'consignment_number': "Manual WB",
                'pick_status': 'packed',
                # 'delivery_status': 'partial',
                'tracking_url': 'https://auspost.com.au/mypost/track/details/Manual WB',
            })

            self.send_tracking_update_to_ot_orders(
                so_number=sale.name,
                con_id="Manual WB",
                carrier="Manual",
                origin=sale.origin or main_picking.origin or "N/A",
                tenant_code=sale.tenant_code_id.name if sale.tenant_code_id else "N/A"
            )
            # Validate all picks for this SO
            for picking in pickings:
                picking.write({'current_state': 'pack'})
                picking.button_validate()

            return {
                "message": "Manual WB order processed successfully – no label generated.",
                "manual_wb": True
            }

        if not partner or not partner.email:
            raise ValidationError("Missing or invalid customer email.")

        if not re.match(r"[^@]+@[^@]+\.[^@]+", partner.email):
            raise ValidationError("Invalid email for customer: %s" % partner.name)

        config = self.get_onetraker_config()
        order_number = sale.name or main_picking.name
        customer_ref = sale.client_order_ref or "NA"
        country = partner.country_id.name or "Australia"
        country_code = partner.country_id.code or "AU"
        carrier = sale.carrier

        to_address = {
            "google_formated_address": None,
            "business_name": partner.name,
            "address1": partner.street or "",
            "address2": partner.street2 or None,
            "city": partner.city or "",
            "province": partner.state_id.name if partner.state_id else "",
            "zip": partner.zip or "",
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
                "mobile_number": partner.mobile or "00000000",
                "email": partner.email
            }
        }

        grouped_items = {}
        declared_value = 0.0

        for line in scanned_lines:
            pkg_num = line.product_package_number
            total_weight = sum(
                l.weight or 0.4
                for l in scanned_lines
                if l.product_package_number == pkg_num
            )
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
                        {"category": "weight", "unit": "KG", "value": round(total_weight, 2)}
                    ]
                }

            grouped_items[pkg_num]["products"].append({
                "product_id": line.product_id.default_code,
                "name": (line.product_id.name or "")[:40],
                "weight": line.weight or 0.4,
                "description": (line.product_id.name or "")[:40],
                "quantity": line.quantity or 1.0,
                "hs_code": line.product_id.hs_code or "",
                "declared_value": round(line.product_id.list_price or 10.0, 2),
                "item_contents_reference": ""
            })
            declared_value += (line.product_id.list_price or 10.0) * (line.quantity or 1.0)
        if (sale.carrier).upper() == "COURIERSPLEASE" and self.tenant_code_id.name == 'MYDEAL':
            merchant_code_mydeal = 'MYD'
        else:
            merchant_code_mydeal = 'MYDEAL'
        payload = {
            "merchant_code": (
                merchant_code_mydeal
                if (self.tenant_code_id.name or '').upper() == "MYDEAL"
                else config["DEFAULT_MERCHANT_CODE"]
            ),
            "service_type": sale.service_type or "STANDARD",
            "carrier_code":sale.carrier or "AUSPOST",
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

        #  Send to OneTraker and print label
        label_url, con_id = self.send_payload_and_print_label(payload, main_picking.name)

        # Print all docs attached to the sale order, if any, after OneTraker success
        if getattr(sale, "docs", None):
            self.print_all_docs_from_sale_order(sale)

        if (sale.carrier).upper() == "COURIERSPLEASE":
            tracking_url = f'https://www.couriersplease.com.au/tools-track?no={con_id}'
        else:
            tracking_url = f'https://auspost.com.au/mypost/track/details/{con_id}'
        # Only need to write sale order fields once (they're shared for all picks)
        sale.write({
            'carrier': carrier,
            'pick_status': 'packed',
            'consignment_number': con_id,
            'status': label_url,
            'tracking_url': tracking_url,
        })

        self.send_tracking_update_to_ot_orders(
            so_number=sale.name,
            con_id=con_id,
            carrier=carrier,
            origin=sale.origin or main_picking.origin or "N/A",
            tenant_code=sale.tenant_code_id.name if sale.tenant_code_id else "N/A"
        )
        #  Validate all picks for this SO (this is the fix)
        for picking in pickings:
            picking.write({'current_state': 'pack'})
            # picking.button_validate()
        return payload

    def release_container(self):
        """Releases the container(s) using fire-and-forget logic. Errors are logged but not raised."""
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
            return  # No raise, just exit silently

        # Fetch URLs dynamically from system parameters based on Warehouse Code
        dev_url = self.env['ir.config_parameter'].sudo().get_param('dev_container_release_url')
        prod_url = self.env['ir.config_parameter'].sudo().get_param('prod_container_release_url')

        if not dev_url or not prod_url:
            _logger.error(f"Missing API URL configuration for warehouse {warehouse_code}")
            return  # No raise, just exit silently

        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
        release_container_api_url = prod_url if is_production else dev_url

        _logger.info(f"Releasing container(s) {container_codes} via API: {release_container_api_url}")

        def _release_async(url, payload, code):
            try:
                requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload), timeout=15)
                _logger.info(f"[RELEASE] Sent async release for {code}")
            except Exception as e:
                _logger.warning(f"[RELEASE] failed for {code}: {str(e)}")

        for container_code in self.pc_container_code_ids.mapped("name"):
            release_payload = {
                "is_release_container": True,
                "container_code": container_code,
                "site_code": site_code,
                "tenant_code": owner_code,
                "warehouse_code": warehouse_code
            }

            _logger.info(f"Container Release Payload: {json.dumps(release_payload, indent=4)}")

            threading.Thread(
                target=_release_async,
                args=(release_container_api_url, release_payload, container_code),
                daemon=True
            ).start()

        return True

    def send_payload_to_api(self, api_url, payload):
        """
        Send the final JSON payload to OneTraker using credentials/config from the config model.
        """
        # config = self.get_onetraker_config()
        headers = {
            'Content-Type': 'application/json'
        }
        if "onetraker" in api_url:
            config = self.get_onetraker_config()
            headers['Authorization'] = config["BEARER"]
        try:
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                _logger.info(f"[ONETRAKER][SIMPLE API] Label created. Response:\n{response.text}")
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
        self.ensure_one()

        config = self.get_onetraker_config()
        api_url = config.get("ONETRAKER_CREATE_ORDER_URL")
        bearer_token = config.get("BEARER")
        bench_ip = self.pack_bench_id.printer_ip

        if not bench_ip:
            raise UserError(_("Pack Bench is missing printer IP."))

        headers = {
            'Content-Type': 'application/json',
            'Authorization': bearer_token
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=50)
            response.raise_for_status()
            response_json = response.json()

            _logger.info(f"[ONETRAKER][SINGLE PICK RESPONSE] {json.dumps(response_json, indent=4)}")

            generic = response_json.get("genericResponse", {})
            status_code = generic.get("apiStatusCode")
            status_message = generic.get("apiStatusMessage", "").lower()
            status_error_code = generic.get("apiStatusErrorCode", "")

            label_url = response_json.get("order", {}).get("shipment", {}).get("documents", {}).get("shipping_label",
                                                                                                    {}).get("url")
            con_id = response_json.get("order", {}).get("shipment", {}).get("carrier_details", {}).get("con_id")

            picking_id = self.picking_ids[0].id if self.picking_ids else False
            sale_order_id = self.picking_ids[0].sale_id.id if self.picking_ids and self.picking_ids[
                0].sale_id else False
            order_number = self.picking_ids[0].sale_id.name if self.picking_ids and self.picking_ids[
                0].sale_id else pick_name
            carrier = self.picking_ids[0].sale_id.carrier if self.picking_ids and self.picking_ids[0].sale_id else ''
            origin = self.picking_ids[0].sale_id.origin if self.picking_ids and self.picking_ids[0].sale_id else ''
            tracking_url = (f'https://www.couriersplease.com.au/tools-track?no={con_id}'
                            if (carrier or '').upper() == "COURIERSPLEASE"
                            else f'https://auspost.com.au/mypost/track/details/{con_id}')

            # LOG ONLY ON SUCCESS
            if status_code == 200 and generic.get("apiSuccessStatus") == "True":
                self.env['shipping.integration.log'].sudo().create({
                    'picking_id': picking_id,
                    'sale_order_id': sale_order_id,
                    'order_number': order_number,
                    'payload_json': json.dumps(payload),
                    'response_json': json.dumps(response_json),
                    'status': 'success',
                    'consignment_number': con_id,
                    'tracking_url': tracking_url,
                    'label_url': label_url,
                    'attempted_at': fields.Datetime.now(),
                    'carrier': carrier,
                    'is_synced': False,
                    'origin':origin,
                })
            elif (
                    status_code == 400
                    and "order already present with order number" in status_message
                    and status_error_code == "order_insert_failed"
            ):
                _logger.warning(f"[ONETRAKER] Order already present: {status_message}. Skipping log.")
            else:
                raise UserError(_(generic.get("apiStatusMessage", "Unknown error from OneTraker")))

            # Print the label (background)
            if label_url:
                def _background_print(label_url_inner, printer_id_inner):
                    try:
                        self._send_label_to_print_api(label_url_inner)
                    except Exception as e:
                        _logger.warning(
                            f"[PRINT API][FAIL] Could not send label to print API for printer {printer_id_inner}: {str(e)}"
                        )

                threading.Thread(
                    target=_background_print,
                    args=(label_url, self.pack_bench_id.printer_name),
                    daemon=True
                ).start()
            else:
                _logger.warning(f"[PRINT API] No label_url to print for order {order_number}")

            return label_url, con_id

        except Exception as e:
            _logger.error(f"[ONETRAKER][FAILURE] {str(e)}")
            raise UserError(_("Failed to process label:\n%s") % str(e))

    def _send_label_to_print_api(self, label_url):
        """
        Sends the label URL to the new print API endpoint for the given printerId.
        Chooses UAT or PROD based on is_production_env config parameter.
        """
        printer_id = self.pack_bench_id.printer_name
        if not printer_id:
            raise UserError("Pack Bench is missing printer name (printerId). Please configure it.")
        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
        if is_production:
            api_url = f"https://shiperoo-wes.prod.automation.shiperoo.com/printers/printUrl/{printer_id}"
        else:
            api_url = f"https://shiperoo-wes.prod.automation.shiperoo.com/printers/printUrl/{printer_id}"
        payload = {"url": label_url}
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            _logger.info(
                f"[PRINT API] Label sent to print API for printer {printer_id}: {label_url} (env: {'PROD' if is_production else 'UAT'})")
        except Exception as e:
            _logger.error(f"[PRINT API][FAIL] Could not send label to print API for printer {printer_id}: {str(e)}")
            # raise UserError(_(f"Failed to send label to print API: {str(e)}"))



    def print_label_via_pack_bench(self, label_url):
        self.ensure_one()

        # if not label_url:
        #     raise UserError(_("No label URL provided to print."))

        bench_ip = self.pack_bench_id.printer_ip
        if not bench_ip:
            raise UserError(_("Pack Bench is missing IP address. Please configure it."))

        try:
            #  Fast label fetch with short timeout
            response = requests.get(label_url, timeout=20)
            if response.status_code != 200 or not response.text.strip():
                raise UserError(_("Failed to download label or label content is empty."))

            zpl_data = response.text.strip()

            #  Instant socket print (raw, no buffer delay)
            with socket.create_connection((bench_ip, 9100), timeout=20) as sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # disable Nagle
                sock.sendall(zpl_data.encode('utf-8'))

            _logger.info(f"[ZEBRA][FAST] Label printed instantly to {bench_ip}:9100")

        except (requests.exceptions.RequestException, socket.timeout) as e:
            _logger.error(f"[ZEBRA][TIMEOUT] {str(e)}")
            raise UserError(_("Timeout during label printing:\n%s") % str(e))

        except socket.error as e:
            _logger.error(f"[ZEBRA][SOCKET ERROR] {str(e)}")
            raise UserError(_("Printer socket error:\n%s") % str(e))

    def send_payload_to_onetraker(self, env, picking, lines, config):
        if not picking:
            raise ValidationError("Picking is required to send OneTraker payload.")

        partner = picking.partner_id
        sale = picking.sale_id
        # Manual WB Handling for Multi-Pick
        if sale and sale.service_type and sale.service_type.strip().upper() == "MANUAL WB":
            _logger.info(f"[MANUAL WB MULTI] Skipping label generation for multi-pick: {picking.name}")

            sale.write({
                'consignment_number': "Manual WB",
                'pick_status': 'packed',
                'tracking_url': 'https://auspost.com.au/mypost/track/details/Manual WB',
            })
            picking.write({'current_state': 'pack'})
            picking.button_validate()

            self.send_tracking_update_to_ot_orders(
                so_number=sale.name,
                con_id="Manual WB",
                carrier="Manual",
                origin=sale.origin or "N/A",
                tenant_code=sale.tenant_code_id.name if sale.tenant_code_id else "N/A"
            )

            return True  # Skip API and treat as success

        if not partner or not partner.email:
            raise ValidationError("Missing or invalid customer email.")
        if not re.match(r"[^@]+@[^@]+\.[^@]+", partner.email):
            raise ValidationError("Invalid email format.")

        order_number = sale.name or picking.name
        customer_ref = sale.client_order_ref or "NA"
        country_code = partner.country_id.code or "AU"
        carrier = sale.carrier

        to_address = {
            "google_formated_address": None,
            "business_name": partner.name,
            "address1": partner.street or "",
            "address2": partner.street2 or None,
            "city": partner.city or "",
            "province": partner.state_id.name if partner.state_id else "",
            "zip": partner.zip or "",
            "country": partner.country_id.name or "Australia",
            "country_code": country_code,
            "contact": {
                "name": partner.name,
                "mobile_number": partner.mobile or "00000000",
                "email": partner.email
            }
        }

        grouped_items, declared_value = {}, 0.0
        for line in lines:
            pkg = line.product_package_number
            grouped_items.setdefault(pkg, {
                "type": None,
                "quantity": 1,
                "products": [],
                "authority_to_leave": True,
                "attributes": [
                    {"category": "length", "unit": "m", "value": 0.1},
                    {"category": "width", "unit": "m", "value": 0.2},
                    {"category": "height", "unit": "m", "value": 0.3},
                    {"category": "weight", "unit": "KG", "value": round(line.weight or 0.4, 2)}
                ]
            })

            grouped_items[pkg]["products"].append({
                "product_id": line.product_id.default_code,
                "name": (line.product_id.name or "")[:40],
                "weight": line.weight or 0.4,
                "description": (line.product_id.name or "")[:40],
                "quantity": line.quantity or 1.0,
                "hs_code": line.product_id.hs_code or "",
                "declared_value": round(line.product_id.list_price or 10.0, 2),
                "item_contents_reference": ""
            })
            declared_value += (line.product_id.list_price or 10.0) * (line.quantity or 1.0)

        if (sale.carrier).upper() == "COURIERSPLEASE" and self.tenant_code_id.name == 'MYDEAL':
            merchant_code_mydeal = 'MYD'
        else:
            merchant_code_mydeal = 'MYDEAL'
        payload = {
            "merchant_code": (
                merchant_code_mydeal
                if (self.tenant_code_id.name or '').upper() == "MYDEAL"
                else config["DEFAULT_MERCHANT_CODE"]
            ),
            "service_type": sale.service_type or "STANDARD",
            "carrier_code": sale.carrier or "AUSPOST",
            "order_number": order_number,
            "tags": {"external_order_id": customer_ref},
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

        headers = {
            'Content-Type': 'application/json',
            'Authorization': config["BEARER"]
        }

        api_url = config["ONETRAKER_CREATE_ORDER_URL"]

        try:
            _logger.info(f"[ONETRAKER] Sending payload to {api_url} for order {order_number}")
            _logger.info(json.dumps(payload, indent=4))
            response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            resp_data = response.json()

            _logger.info(f"[ONETRAKER][MULTI-PICK RESPONSE] {json.dumps(resp_data, indent=4)}")
            generic = resp_data.get("genericResponse", {})
            status_code = generic.get("apiStatusCode")
            status_message = generic.get("apiStatusMessage", "").lower()
            status_error_code = generic.get("apiStatusErrorCode", "")

            if (
                    status_code == 400
                    and "order already present with order number" in status_message
                    and status_error_code == "order_insert_failed"
            ):
                _logger.warning(
                    f"[ONETRAKER][MULTI] Order already present: {status_message}. Allowing process to continue.")
                order_number = status_message.split("order number")[-1].strip()
                label_url = None
                con_id = ''
                # continue with post-label processing: update pick, update SO, release container
                picking.write({'current_state': 'pack'})
                # sale.write({
                #     'carrier': carrier,
                #     'pick_status': 'packed',
                #     'consignment_number': con_id,
                #     'status': label_url,
                #     'tracking_url': f'https://auspost.com.au/mypost/track/details/{con_id}',
                # })
                # self.send_tracking_update_to_ot_orders(
                #     so_number=sale.name,
                #     con_id=con_id,
                #     carrier=carrier,
                #     origin=sale.origin or "N/A",
                #     tenant_code=sale.tenant_code_id.name if sale.tenant_code_id else "N/A"
                # )
                picking.button_validate()
                return True

            if generic.get("apiSuccessStatus") != "True":
                raise ValidationError(generic.get("apiStatusMessage", "Unknown error"))

            label_url = resp_data.get("order", {}).get("shipment", {}).get("documents", {}).get("shipping_label",
                                                                                                {}).get("url")
            con_id = resp_data.get("order", {}).get("shipment", {}).get("carrier_details", {}).get("con_id")

            #  Fire-and-forget label printing
            if label_url:
                self._send_label_to_print_api(label_url)
            else:
                _logger.warning(f"[PRINT API] No label_url found in response for multi-pick: {order_number}")
            # Update DB
            if (sale.carrier).upper() == "COURIERSPLEASE":
                tracking_url = f'https://www.couriersplease.com.au/tools-track?no={con_id}'
            else:
                tracking_url = f'https://auspost.com.au/mypost/track/details/{con_id}'
            picking.write({'current_state': 'pack'})
            # --- Print all attached docs, if present ---
            if getattr(sale, "docs", None):
                self.print_all_docs_from_sale_order(sale)
            sale.write({
                'carrier': carrier,
                'pick_status': 'packed',
                # 'delivery_status': 'partial',
                'consignment_number': con_id,
                'status': label_url,
                'tracking_url': tracking_url,
            })

            self.send_tracking_update_to_ot_orders(
                so_number=sale.name,
                con_id=con_id,
                carrier=carrier,
                origin=sale.origin or "N/A",
                tenant_code=sale.tenant_code_id.name if sale.tenant_code_id else "N/A"
            )
            self.env['shipping.integration.log'].sudo().create({
                'picking_id': picking.id if picking else False,
                'sale_order_id': sale.id if sale else False,
                'order_number': sale.name if sale else picking.name,
                'payload_json': json.dumps(payload),
                'response_json': json.dumps(resp_data),
                'status': 'success',
                'consignment_number': con_id,
                'tracking_url': (f'https://www.couriersplease.com.au/tools-track?no={con_id}' if (sale.carrier or '').upper() == "COURIERSPLEASE"
                                 else f'https://auspost.com.au/mypost/track/details/{con_id}'),
                'label_url': label_url,
                'attempted_at': fields.Datetime.now(),
                'carrier': sale.carrier if sale else '',
                'is_synced': False,
                'origin':sale.origin,
            })
            # picking.button_validate()
            return True

        except Exception as e:
            _logger.error(f"[ONETRAKER][FAILURE] {str(e)}")
            raise UserError(f"Failed to send payload:\n{str(e)}")

    def send_tracking_update_to_ot_orders(self, so_number, con_id, carrier, origin, tenant_code):
            is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
            ot_orders_url = (
                "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/ot_orders"
                if is_production else
                "https://int-shiperooconnect-dev.automation.shiperoo.com/api/ot_orders"
            )

            payload = {
                "so_number": so_number,
                "carrier_con_id": con_id,
                "carrier": carrier,
                "cin_id": origin,
                "tenant_code": tenant_code,
            }

            headers = {"Content-Type": "application/json"}

            _logger.info(f"[OT_ORDERS] Fire-and-forget tracking update to {ot_orders_url}:\n{json.dumps(payload)}")

            try:
                # Non-blocking, fast attempt with short timeout
                requests.post(
                    url=ot_orders_url,
                    headers=headers,
                    json=payload,
                    timeout=15
                )
            except requests.exceptions.RequestException as e:
                _logger.warning(f"[OT_ORDERS] Tracking update skipped due to network issue: {str(e)}")

    def _fire_and_forget_label_print(self, zpl_data, printer_ip):
        try:
            with socket.create_connection((printer_ip, 9100), timeout=10) as sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.sendall(zpl_data)
            _logger.info(f"[ZEBRA][ASYNC] Label sent successfully to printer {printer_ip}")
        except Exception as e:
            _logger.warning(f"[ZEBRA][ASYNC FAIL] Could not send label to {printer_ip}: {str(e)}")

    def print_all_docs_from_sale_order(self, sale_order):
        """
        For each doc URL attached to the sale order,
        send the URL directly to the print API (bench/printer) and do nothing else.
        """
        import json

        if not sale_order.docs:
            _logger.info(f"No docs found for sale order {sale_order.name}")
            #return
        try:
            # Try to load as JSON list or string
            urls = json.loads(sale_order.docs)
            if isinstance(urls, str):
                urls = [urls]
            elif not isinstance(urls, list):
                urls = []
        except Exception:
            # fallback: treat as single URL string
            urls = [sale_order.docs]

        printer_id = self.pack_bench_id.printer_name
        if not printer_id:
            raise UserError("Pack Bench is missing printer name (printerId). Please configure it.")

        is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env') == 'True'
        api_url = (
            f"https://shiperoo-wes.prod.automation.shiperoo.com/printers/printUrl/{printer_id}"
            # if is_production
            # else f"https://shiperoo-wes.prod.automation.shiperoo.com/printers/printUrl/{printer_id}"
        )
        headers = {"Content-Type": "application/json"}

        for url in urls:
            url = url.strip()
            if not url:
                continue
            try:
                payload = {"url": url}
                # Fire-and-forget POST to print API
                requests.post(api_url, headers=headers, json=payload, timeout=8)
                _logger.info(f"[PRINT API] Sent doc label URL to {printer_id}: {url}")
            except Exception as e:
                _logger.warning(
                    f"[PRINT API][FAIL] Could not send doc label URL to printer {printer_id}: {url} :: {str(e)}"
                )


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
    manual_pick_number_id = fields.Many2one(
        'stock.picking',
        string='Manual Pick Number',
        domain="[('id', 'in', picking_ids)]",  # Only show available picks
        help="Assign to a specific pick when consolidating discrete picks.",
    )

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

        if (sale_order.carrier).upper() == "COURIERSPLEASE":
            tracking_url = f'https://www.couriersplease.com.au/tools-track?no={tracking_number}'
        else:
            tracking_url = f'https://auspost.com.au/mypost/track/details/{tracking_number}'
        sale_order.write({
            'consignment_number': tracking_number,
            'tracking_url': tracking_url,
            'carrier': carrier_name,
            'pick_status': "packed",
            'delivery_status': "partial",
        })
        picking.write({'current_state': "pack"})
        # Ensure move lines are correctly updated before validation
        # picking.action_assign()
        # for move in picking.move_ids:
        #     for line in move.move_line_ids:
        #         _logger.info(
        #             f"[VALIDATION DEBUG] MoveLine: {line.id}, qty_done: {line.qty_done}, reserved: {line.reserved_uom_qty}")
        #         if line.qty_done == 0:
        #             line.qty_done = line.product_uom_qty or 1.0

        # Validate the picking after setting qty_done
        # picking.button_validate()
        # Ensure move lines are correctly updated before validation
        # picking.action_assign()
        # for move in picking.move_ids:
        #     for line in move.move_line_ids:
        #         _logger.info(
        #             f"[VALIDATION DEBUG] MoveLine: {line.id}, qty_done: {line.qty_done}, reserved: {line.reserved_uom_qty}")
        #         if line.qty_done == 0:
        #             line.qty_done = line.product_uom_qty or 1.0

        # Validate the picking after setting qty_done
        # picking.button_validate()
        self.send_tracking_update_to_ot_orders(
            so_number=sale_order.name,
            con_id=tracking_number,
            carrier=carrier_name,
            origin=sale_order.origin or "N/A",
            tenant_code=sale_order.tenant_code_id.name if sale_order.tenant_code_id else "N/A"
        )

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
        # picking.button_validate()
        # Ensure move lines are correctly updated before validation
        # picking.action_assign()
        # for move in picking.move_ids:
        #     for line in move.move_line_ids:
        #         _logger.info(
        #             f"[VALIDATION DEBUG] MoveLine: {line.id}, qty_done: {line.qty_done}, reserved: {line.reserved_uom_qty}")
        #         if line.qty_done == 0:
        #             line.qty_done = line.product_uom_qty or 1.0

        # Validate the picking after setting qty_done
        picking.button_validate()

        self.send_tracking_update_to_ot_orders(
            so_number=sale_order.name,
            con_id="Manual WB",
            carrier="Manual",
            origin=sale_order.origin or "N/A",
            tenant_code=sale_order.tenant_code_id.name if sale_order.tenant_code_id else "N/A"
        )
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
            self.weight = 0.4
            _logger.warning(f"Weight was missing or zero; defaulted to 0.5 for product {self.product_id.name}")

        # Save to product if not already set
        if not self.product_id.weight or self.product_id.weight == 0.0:
            self.product_id.write({'weight': self.weight})
            _logger.info(f"Saved defaulted weight {self.weight} to product {self.product_id.name}")

        # Propagate to other lines with same product in same wizard
        same_product_lines = self.wizard_id.line_ids.filtered(
            lambda l: l.product_id.id == self.product_id.id and l.id != self.id
        )
        for line in same_product_lines:
            if not line.weight or line.weight == 0.0:
                line.weight = self.weight
                _logger.info(f"Updated weight to {self.weight} for product {line.product_id.name} on line ID {line.id}")

        # Re-trigger package box selection logic if needed
        # self.wizard_id._auto_select_package_box_type()

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