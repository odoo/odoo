# addons/excel_export_connector/models/res_config_settings.py
import logging
import requests
from odoo import models, fields


_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    excel_export_tenant_id     = fields.Char(string="Tenant ID",         config_parameter='excel_export.tenant_id')
    excel_export_client_id     = fields.Char(string="Client ID",         config_parameter='excel_export.client_id')
    excel_export_client_secret = fields.Char(string="Client Secret",     config_parameter='excel_export.client_secret')
    excel_export_user_upn      = fields.Char(string="OneDrive User (UPN)", config_parameter='excel_export.user_upn')
    excel_export_access_token  = fields.Char(string="Access Token",      readonly=True)
    excel_export_drive_id      = fields.Char(string="Drive ID",          readonly=True)

    # def action_generate_token_and_drive(self):
    #     _logger.info("Starting token acquisition for Excel connector…")
    #     token = acquire_token(self.env)
    #     _logger.info("Got token: %s", token)
    #     # persist token
    #     self.env['ir.config_parameter'].sudo().set_param('excel_export.access_token', token)

    #     upn = self.excel_export_user_upn
    #     _logger.info("Fetching Drive for user %s", upn)
    #     resp = requests.get(
    #         f"https://graph.microsoft.com/v1.0/users/{upn}/drive",
    #         headers={"Authorization": f"Bearer {token}"}
    #     )
    #     _logger.info("Graph /drive response: %s %s", resp.status_code, resp.text)
    #     if not resp.ok:
    #         raise UserError(f"Could not fetch Drive ID:\n{resp.json()}")
    #     drive_id = resp.json().get('id')
    #     _logger.info("Storing Drive ID %s", drive_id)
    #     self.env['ir.config_parameter'].sudo().set_param('excel_export.drive_id', drive_id)

    #     # reload so the readonly fields refresh
    #     return {'type': 'ir.actions.client', 'tag': 'reload'}
