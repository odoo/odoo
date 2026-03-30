# addons/excel_export_connector/msal_helper.py
import msal
from odoo.exceptions import UserError

def acquire_token(env, return_full_result=False):
    params        = env['ir.config_parameter'].sudo()
    tenant_id     = params.get_param('excel_export.tenant_id')
    client_id     = params.get_param('excel_export.client_id')
    client_secret = params.get_param('excel_export.client_secret')
    if not (tenant_id and client_id and client_secret):
        raise UserError(
            "Please configure your Azure Tenant ID, Client ID and Client Secret "
            "in Settings → Excel Online Connector."
        )
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=authority,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        err  = result.get("error")
        desc = result.get("error_description")
        raise UserError(f"Could not acquire token: {err}\n{desc}")
    if return_full_result:
        return result
    return result["access_token"]
