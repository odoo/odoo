# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import requests
import logging


_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'


    duplicate_pack_count = fields.Integer(string='Pack Counting', default=1)




    def button_manual_pack(self):
        """
        This method manually packs line items marked as 'Packed'
        and sends them to the external Flask API in a consolidated format.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pack Bench Wizard',
            'res_model': 'pack.delivery.receipt.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                # 'default_automation_decanting_process_id': self.id,
                # 'default_license_plate_ids': self.license_plate_ids.ids,
                # 'default_container_id': self.container_id.id,
                # 'default_crate_barcode': self.crate_barcode,
                # 'default_picking_id': self.picking_id.id,
                # 'default_updated_count_lines': self.count_lines,
            }
        }
        # for picking in self:
        #     packed_lines = picking.move_ids_without_package.filtered(lambda line: line.packed and not line.released_manual)
        #     if not packed_lines:
        #         raise UserError("No packed items found in this picking.")
        #
        #     sku_list = []
        #     total_sku_amount = 0  # To calculate the total quantity
        #     sku_type_amount = 0  # To count unique SKUs
        #
        #     # Loop through each packed line to build the SKU list
        #     for line in packed_lines:
        #         total_sku_amount += line.quantity  # Accumulate total quantity
        #         sku_list.append({
        #             "sku_code": line.product_id.default_code,  # Product code (SKU)
        #             "sku_amount": line.quantity,  # Quantity
        #             "amount": line.quantity,  # Quantity
        #             "out_batch_code": "ECOM",  # Batch code
        #             "owner_code": picking.tenant_code_id.name,  # Tenant code
        #             "out_order_code": picking.name,  # Picking name as the order code
        #         })
        #
        #     sku_type_amount = len(sku_list)  # Count unique SKUs
        #
        #     # Prepare payload with consolidated SKU list
        #     data = {
        #         "header": {
        #             "user_id": "admin",  # Replace as needed
        #             "user_key": "admin",
        #             "warehouse_code": picking.site_code_id.name,  # Site Code
        #             # "interface_code": "feedback_outbound_container"  # Interface Code
        #         },
        #         "body": {
        #             "container_list": [
        #                 {
        #                     "container_code": picking.name,  # Receipt number
        #                     "sku_type_amount": sku_type_amount,  # Unique SKU count
        #                     "sku_amount": total_sku_amount,  # Total quantities of all SKUs
        #                     "sku_list": sku_list,  # Consolidated SKU list
        #                 }
        #             ],
        #             "warehouse_code": picking.site_code_id.name,  # Warehouse code
        #         }
        #     }
        #
        #     # Convert data to JSON format
        #     json_data = json.dumps(data, indent=4)
        #     _logger.info(f"Generated data Pack: {json_data}")
        #
        #     # Determine environment-specific URL
        #     is_production = self.env['ir.config_parameter'].sudo().get_param('is_production_env')
        #     url_manual_packing = (
        #         "https://shiperooconnect-prod.automation.shiperoo.com/receive_payload"
        #         if is_production == 'True'
        #         else "https://shiperooconnect.automation.shiperoo.com/receive_payload"
        #     )
        #
        #     headers = {
        #         'Content-Type': 'application/json'
        #     }
        #
        #     try:
        #         # Send POST request to the external Flask API
        #         response = requests.post(url_manual_packing, data=json_data, headers=headers)
        #         if response.status_code == 200:
        #             api_response = response.json()
        #             if api_response.get('success'):
        #                 for line in packed_lines:
        #                     line.released_manual = True  # Mark the line as released
        #                 self.env.cr.commit()  # Commit changes immediately to avoid conflicts
        #             else:
        #                 raise UserError(
        #                     f"Failed to send data to Pack App {picking.name}: {api_response.get('message')}")
        #         else:
        #             raise UserError(f"Flask API error ({response.status_code}): {response.text}")
        #     except requests.RequestException as e:
        #         raise UserError(f"Error communicating with Flask API: {str(e)}")
        #
        # return True

