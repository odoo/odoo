# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError
import json
import requests
import logging
from datetime import date


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

    # def button_manual_pack(self):
    #     """
    #     This method manually packs line items marked as 'Packed'
    #     and sends them to the external Flask API in a consolidated format.
    #     """
    #
    #     for picking in self:
    #         packed_lines = picking.move_ids_without_package.filtered(lambda line: line.packed and not line.released_manual)
    #         if not packed_lines:
    #             raise UserError("No packed items found in this picking.")
    #
    #         sku_list = []
    #         total_sku_amount = 0  # To calculate the total quantity
    #         sku_type_amount = 0  # To count unique SKUs
    #
    #         # Loop through each packed line to build the SKU list
    #         for line in packed_lines:
    #             total_sku_amount += line.quantity  # Accumulate total quantity
    #             sku_list.append({
    #                 "sku_code": line.product_id.default_code,  # Product code (SKU)
    #                 "sku_amount": line.quantity,  # Quantity
    #                 "amount": line.quantity,  # Quantity
    #                 "out_batch_code": "ECOM",  # Batch code
    #                 "owner_code": picking.tenant_code_id.name,  # Tenant code
    #                 "out_order_code": picking.name,  # Picking name as the order code
    #             })
    #
    #         sku_type_amount = len(sku_list)  # Count unique SKUs
    #
    #         # Prepare payload with consolidated SKU list
    #         data = {
    #             "header": {
    #                 "user_id": "admin",  # Replace as needed
    #                 "user_key": "admin",
    #                 "warehouse_code": picking.site_code_id.name,  # Site Code
    #                 # "interface_code": "feedback_outbound_container"  # Interface Code
    #             },
    #             "body": {
    #                 "container_list": [
    #                     {
    #                         "container_code": picking.name,  # Receipt number
    #                         "sku_type_amount": sku_type_amount,  # Unique SKU count
    #                         "sku_amount": total_sku_amount,  # Total quantities of all SKUs
    #                         "sku_list": sku_list,  # Consolidated SKU list
    #                     }
    #                 ],
    #                 "warehouse_code": picking.site_code_id.name,  # Warehouse code
    #             }
    #         }
    #
    #         # Convert data to JSON format
    #         json_data = json.dumps(data, indent=4)
    #         _logger.info(f"Generated data Pack: {json_data}")
    #
    #         # Determine environment-specific URL
    #         is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
    #         url_manual_packing = (
    #             "https://shiperooconnect-prod.automation.shiperoo.com/receive_payload"
    #             if is_production == 'True'
    #             else "https://shiperooconnect.automation.shiperoo.com/receive_payload"
    #         )
    #
    #         headers = {
    #             'Content-Type': 'application/json'
    #         }
    #
    #         try:
    #             # Send POST request to the external Flask API
    #             response = requests.post(url_manual_packing, data=json_data, headers=headers)
    #             if response.status_code == 200:
    #                 api_response = response.json()
    #                 if api_response.get('success'):
    #                     for line in packed_lines:
    #                         line.released_manual = True  # Mark the line as released
    #                     self.env.cr.commit()  # Commit changes immediately to avoid conflicts
    #                 else:
    #                     raise UserError(
    #                         f"Failed to send data to Pack App {picking.name}: {api_response.get('message')}")
    #             else:
    #                 raise UserError(f"Flask API error ({response.status_code}): {response.text}")
    #         except requests.RequestException as e:
    #             raise UserError(f"Error communicating with Flask API: {str(e)}")
    #
    #     return True

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
            }
            # Define the URLs for Shiperoo Connect
            is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
            api_url = (
                "https://shiperooconnect-prod.automation.shiperoo.com/api/discrepency_receiver"
                if is_production == 'True'
                else "https://shiperooconnect.automation.shiperoo.com/api/discrepency_receiver"
            )
            json_data = json.dumps(payload, indent=4)
            _logger.info(f"Sending payload to {api_url}: {json_data}")

            # Send the payload to the API
            headers = {'Content-Type': 'application/json'}
            try:
                response = requests.post(api_url, headers=headers, data=json_data)
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