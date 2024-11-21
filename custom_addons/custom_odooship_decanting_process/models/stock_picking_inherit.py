# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json
import requests
import logging
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

    def button_manual_pack(self):
        """
        This method manually packs line items marked as 'Packed'
        and sends them to the external Flask API in a consolidated format.
        """

        for picking in self:
            packed_lines = picking.move_ids_without_package.filtered(lambda line: line.packed)
            if not packed_lines:
                raise UserError("No packed items found in this picking.")

            sku_list = []

            # Loop through each packed line to build the SKU list
            for line in packed_lines:
                sku_list.append({
                    "sku_code": line.product_id.default_code,  # Product code (SKU)
                    "sku_amount": line.product_uom_qty,  # Quantity (expected)
                    "amount": line.quantity_done,  # Quantity (actual)
                    "out_batch_code": "ECOM",  # Batch code
                    "owner_code": picking.tenant_code_id.name,  # Tenant code
                })

            # Prepare payload with consolidated SKU list
            data = {
                "body": {
                    "warehouse_code": picking.site_code_id.name,  # Site Code
                    "receipt_code": picking.name,  # Picking name as receipt code
                    "sku_list": sku_list
                },
                "header": {
                    "user_id": "system",
                    "user_key": "system",
                    "warehouse_code": picking.site_code_id.name  # Site Code
                }
            }

            # Convert data to JSON format
            json_data = json.dumps(data, indent=4)
            _logger.info(f"Generated data Pack: {json_data}")

            # Determine environment-specific URL
            is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
            url_manual_packing = (
                "https://shiperooconnect-prod.automation.shiperoo.com/receive_payload"
                if is_production == 'True'
                else "https://shiperooconnect.automation.shiperoo.com/receive_payload"
            )

            headers = {
                'Content-Type': 'application/json'
            }

            try:
                # Send POST request to the external Flask API
                response = requests.post(url_manual_packing, data=json_data, headers=headers)
                if response.status_code == 200:
                    api_response = response.json()
                    if api_response.get('success'):
                        for line in packed_lines:
                            line.released_manual = True  # Mark the line as released
                        self.env.cr.commit()  # Commit changes immediately to avoid conflicts
                    else:
                        raise UserError(
                            f"Failed to send data to Pack App {picking.name}: {api_response.get('message')}")
                else:
                    raise UserError(f"Flask API error ({response.status_code}): {response.text}")
            except requests.RequestException as e:
                raise UserError(f"Error communicating with Flask API: {str(e)}")

        return True

    def button_validate(self):
        """
        Overrides the button_validate method to handle special cases for incoming pickings.
        If the picking_type_code is 'incoming', and the state is 'ready', it directly sets the state to 'done'.
        If the state is 'draft', it raises a validation error.
        """
        for picking in self:
            # Check if this is an incoming receipt
            if picking.picking_type_code == 'incoming':
                if picking.state == 'draft':
                    # Raise an error if the user tries to validate from draft state
                    raise UserError("You cannot validate an incoming receipt from the 'Draft' state.")
                elif picking.state == 'ready':
                    # If in ready state, directly mark as done
                    picking.state = 'done'
                    return

        # Call the super method for other cases
        return super(StockPicking, self).button_validate()