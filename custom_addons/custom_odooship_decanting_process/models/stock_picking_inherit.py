# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError
import json
import requests
import logging
from datetime import date
#import math


_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    tenant_code_id = fields.Many2one(
        'tenant.code.configuration',
        string='Tenant Code',
        related='partner_id.tenant_code_id',
        readonly=True,
        store=True
    )
    site_code_id = fields.Many2one(related='location_dest_id.site_code_id', string='Site Code', store=True)
    tenant_id = fields.Char(related='tenant_code_id.name',string='Tenant ID', store=True)
    site_code = fields.Char(related='site_code_id.name',string='Site Code', store=True)
    is_automation = fields.Boolean(string='Is Automation', default=False)
    is_error_found = fields.Boolean(string='Is Error Found', default=False)
    is_error_found_message = fields.Char(string='Error Found Message')
    reference_1 = fields.Char(string='Reference', store=False)
    container_number = fields.Char(string='Container Number', store=False)
    # tolerance_qty = fields.Integer(
    #     string="Tolerance Quantity", compute='_compute_tolerance_qty', store=True)
    # total_allowed_qty = fields.Float(
    #     string="Total Allowed Quantity", compute='_compute_tolerance_qty', store=True)

    # @api.depends('product_uom_qty', 'picking_id.tenant_code_id', 'picking_id.customer_number')
    # def _compute_tolerance_qty(self):
    #     """
    #     Compute:
    #     - tolerance_qty = ceil(5% of product_uom_qty)
    #     - total_allowed_qty = product_uom_qty + tolerance_qty
    #     - Use international tolerance if customer_number exists, else domestic
    #     """
    #     ToleranceConfig = self.env['shipment.tolerance.config']
    #     for move in self:
    #         move.tolerance_qty = 0
    #         move.total_allowed_qty = move.product_uom_qty
    #
    #         tenant = move.picking_id.tenant_code_id
    #         customer_number = move.picking_id.customer_number
    #         if not tenant:
    #             continue
    #
    #         config = ToleranceConfig.search([('tenant_id', '=', tenant.id)], limit=1)
    #         if not config:
    #             continue
    #
    #         tolerance_percent = config.international_tolerance if customer_number else config.domestic_tolerance
    #         tolerance_value = (tolerance_percent / 100.0) * move.product_uom_qty
    #
    #         move.tolerance_qty = math.ceil(tolerance_value)
    #         move.total_allowed_qty = move.product_uom_qty + move.tolerance_qty

    @api.onchange('is_error_found')
    def _onchange_is_error_found(self):
        """
        Onchange is error found display error message when boolean is True
        """
        if self.is_error_found:
            self.is_error_found_message = "<span style='color:red; font-weight:bold;'>Error message in Log</span>"
        else:
            self.is_error_found_message = ""


    def button_validate_picking(self):
        """
        Sends SKU details to the specified API endpoint for each product line in the picking.
        Updates the state to 'done' if the operation is successful.
        """

        for picking in self:
            # Validate that required fields are present
            if picking.picking_type_code == 'incoming':
                if picking.state == 'draft':
                    # Raise an error if the user tries to validate from draft state
                    raise UserError("You cannot validate an incoming receipt from the 'Draft' state.")
            if not picking.tenant_code_id or not picking.site_code_id:
                raise ValidationError(
                    _("Tenant Code and Site Code must be specified for this operation.")
                )

            if not picking.move_ids_without_package:
                raise ValidationError(_("No product lines found to send."))
            schedule_date = picking.scheduled_date.strftime("%d-%m-%Y") if picking.scheduled_date else "N/A"

            # Get today's date in "YYYY-MM-DD" format
            current_date = date.today().strftime("%d-%m-%Y")
            # Build the payload
            product_lines = []
            for line in picking.move_ids_without_package:
                product_lines.append({
                    "product_id": line.product_id.default_code,
                    "name": line.product_id.name,
                    "product_uom_qty": line.product_uom_qty,
                    "quantity": line.product_uom_qty,
                    "remaining_quantity": line.remaining_qty,
                    "delivery_receipt_state": line.delivery_receipt_state or "N/A",
                    "product_packaging_id":line.product_packaging_id.name,
                    "product_packaging_qty":line.product_packaging_qty,
                })

            payload = {
                "receipt_number": picking.name,
                "partner_id":picking.partner_id.name,
                "tenant_code": picking.tenant_code_id.name,
                "site_code": picking.site_code_id.name,
                "origin": picking.origin or "N/A",
                "product_lines": product_lines,
                "schedule_date":schedule_date,
                "current_date":current_date,
                "reference_1":picking.reference_1,
                "container_number":picking.container_number,
            }
            json_data = json.dumps(payload, indent=4)
            if picking.tenant_code_id.name == "MYSALE":
                is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
                if is_production == 'True':
                # Production 
                    api_url = (
                        "https://shiperoo-connect-fp.prod.automation.shiperoo.com/"
                        "sc-file-processor/api/receipt-completion"
                    )
                    auth = ('apiuser', 'd7oX8L3af6D4FDobC8AFsWRgLamvQs')
                else:
                    # UAT 
                    api_url = (
                        "https://shiperoo-connect.uat.automation.shiperoo.com/"
                        "sc-file-processor/api/receipt-completion"
                    )
                    auth = ('apiuser', 'apipass')
                    # api_url = "https://shiperoo-connect.uat.automation.shiperoo.com/sc-file-processor/api/receipt-completion"
                    # auth = ('apiuser', 'apipass')
            else:
                is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
                api_url = (
                "https://shiperoo-connect-int.prod.automation.shiperoo.com/api/discrepency_receiver"
                if is_production == 'True'
                else "https://shiperooconnect-dev.automation.shiperoo.com/api/discrepency_receiver"
            )
                auth = None
            # Define the URLs for Shiperoo Connect
            # is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
            # api_url = (
            #     "https://shiperooconnect-prod.automation.shiperoo.com/api/discrepency_receiver"
            #     if is_production == 'True'
            #     else "https://shiperooconnect-dev.automation.shiperoo.com/api/discrepency_receiver"
            # )
            # json_data = json.dumps(payload, indent=4)
            _logger.info(f"Sending payload to {api_url}: {json_data}")

             # Send the payload to the API
            headers = {'Content-Type': 'application/json'}
            try:
                if auth:
                    response = requests.post(api_url, headers=headers, data=json_data, auth=auth)
                else:
                    response = requests.post(api_url, headers=headers, data=json_data)
                # response = requests.post(api_url, headers=headers, data=json_data)
                _logger.info(f"Response Status Code: {response.status_code}, Response Body: {response.text}")

                if response.status_code != 200:
                    raise UserError(f"Failed to send data: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                _logger.error(f"Error communicating with API: {str(e)}")
                raise UserError(f"Error communicating with API: {str(e)}")

            # If no errors, update the state to 'done'
            picking.state = 'done'
            _logger.info(f"Picking {picking.name} has been successfully processed and marked as done.")

        return True

    def button_validate(self):
        """
        Overrides the button_validate method to handle special cases for incoming pickings.
        If the picking_type_code is 'incoming', and the state is 'draft', it raises a validation error.
        """
        for picking in self:
            # Check if this is an incoming receipt
            if picking.picking_type_code == 'incoming':  # Directly compare with 'incoming'
                if picking.state == 'draft':
                    # Raise an error if the user tries to validate from the draft state
                    raise UserError("You cannot validate an incoming receipt from the 'Draft' state.")

        # Call the super method for other cases
        return super(StockPicking, self).button_validate()
