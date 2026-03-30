from odoo import models, fields, api
from odoo.exceptions import UserError
from .graph_client import GraphClient
from datetime import datetime, date, timedelta
import requests
from odoo.models import BaseModel
from .msal_helper import acquire_token
import logging
import time

_logger = logging.getLogger(__name__)

def serialize_value(val):
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, BaseModel):
        if not val:
            return ""
        return val.display_name
    return val

class ExcelExportTask(models.Model):
    _name = 'excel.export.task'
    _description = 'Excel Online Export Task'

    name = fields.Char(string="Task Name", required=True, default="New Export")
    model_id = fields.Many2one(
        'ir.model', string="Model to Export", ondelete='cascade',
        domain=[('transient', '=', False)], required=True
    )
    fields_to_export = fields.Many2many(
        'ir.model.fields',
        string="Fields to Export"
    )
    file_id = fields.Char(
        string="Workbook File ID", required=True,
        help="Paste the GUID from your OneDrive URL"
    )
    sheet_name = fields.Char(
        string="Sheet Name", required=True, default="Sheet1"
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')],
        default='draft', readonly=True
    )

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.fields_to_export = [(5, 0, 0)]
        if self.model_id:
            return {
                'domain': {
                    'fields_to_export': [
                        ('model_id', '=', self.model_id.id),
                        ('store', '=', True),
                        ('ttype', 'not in', ['one2many', 'many2many'])
                    ]
                }
            }
        else:
            return {'domain': {'fields_to_export': []}}

    def _ensure_token_and_drive(self):
        """Ensure token and drive are valid, refresh if needed."""
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('excel_export.access_token')
        drive_id = params.get_param('excel_export.drive_id')
        token_expiry = params.get_param('excel_export.token_expiry')
        now = int(time.time())

        # If token/drive missing or expired (with 2 min buffer), refresh
        if (not token or not drive_id or not token_expiry or now > int(token_expiry) - 120):
            _logger.info("Token or Drive ID missing or expired, generating new ones…")
            # Call your msal_helper and get expiry info
            msal_result = acquire_token(self.env, return_full_result=True)  # We'll update acquire_token below
            token = msal_result["access_token"]
            expires_in = msal_result.get("expires_in", 3600)
            expiry_timestamp = now + int(expires_in)
            params.set_param('excel_export.access_token', token)
            params.set_param('excel_export.token_expiry', str(expiry_timestamp))

            upn = params.get_param('excel_export.user_upn')
            if not upn:
                raise UserError("Excel Export User UPN is not configured. Please set it in Settings.")
            _logger.info("Fetching Drive for user %s", upn)
            resp = requests.get(
                f"https://graph.microsoft.com/v1.0/users/{upn}/drive",
                headers={"Authorization": f"Bearer {token}"}
            )
            _logger.info("Graph /drive response: %s %s", resp.status_code, resp.text)
            if not resp.ok:
                raise UserError(f"Could not fetch Drive ID:\n{resp.json()}")
            drive_id = resp.json().get('id')
            params.set_param('excel_export.drive_id', drive_id)
        else:
            _logger.info("Using cached token and drive id.")

        return token, drive_id

    def action_send(self):
        # Ensure token and drive are available and valid
        self._ensure_token_and_drive()

        # Proceed with export
        client = GraphClient(self.env, file_id=self.file_id, sheet_name=self.sheet_name)
        client.clear_sheet()
        rows = self._get_export_data()
        client.write_values(rows)
        self.state = 'done'

    def _get_export_data(self):
        Model = self.env[self.model_id.model]
        records = Model.search([])
        field_objs = self.fields_to_export
        if not field_objs:
            raise UserError("Please select at least one field to export.")
        header = [f.field_description for f in field_objs]
        rows = [header]
        for rec in records:
            row = [serialize_value(rec[f.name]) for f in field_objs]
            rows.append(row)
        return rows
