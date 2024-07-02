import requests
import base64

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import json
from werkzeug.urls import url_join, url_encode


ENDPOINT_AUTHORIZE = 'https://logincert.anaf.ro/anaf-oauth2/v1/authorize'
ENDPOINT_TOKEN = 'https://logincert.anaf.ro/anaf-oauth2/v1/token'


class EFacturaOAuthController(http.Controller):

    @http.route('/l10n_ro_edi/authorize/<int:company_id>', auth="user")
    def authorize(self, company_id, **kw):
        """ Generate Authorization Token to acquire access_key for requesting Access Token """
        company = http.request.env['res.company'].sudo().browse(company_id)
        if not company.l10n_ro_edi_client_id or not company.l10n_ro_edi_client_secret:
            raise UserError(_("Client ID and Client Secret field must be filled."))

        auth_url = url_join(ENDPOINT_AUTHORIZE, '?' + url_encode({
            'response_type': 'code',
            'client_id': company.l10n_ro_edi_client_id,
            'redirect_uri': company.l10n_ro_edi_callback_url,
            'token_content_type': 'jwt',
        }))
        return request.redirect(auth_url, code=302, local=False)

    @http.route('/l10n_ro_edi/callback/<int:company_id>', type='http', auth="user")
    def callback(self, company_id, **kw):
        """ Use the acquired access_key to request access & refresh token from ANAF """
        company = http.request.env['res.company'].sudo().browse(company_id)
        access_key = kw.get('code')
        # Without certificate, ANAF won't give any access key in the callback URL's "code" parameter
        if not access_key:
            error_message = _("Access key not found. Please try again.\nResponse: %s", kw)
            company.l10n_ro_edi_oauth_error = error_message
            company.env.cr.commit()
            raise UserError(error_message)

        response = requests.post(
            url=ENDPOINT_TOKEN,
            data={
                "grant_type": "authorization_code",
                "client_id": company.l10n_ro_edi_client_id,
                "client_secret": company.l10n_ro_edi_client_secret,
                "code": access_key,
                "access_key": access_key,
                "redirect_uri": company.l10n_ro_edi_callback_url,
                "token_content_type": "jwt",
            },
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "accept": "application/json",
                "user-agent": "PostmanRuntime/7.29.2",
            },
            timeout=10,
        )
        response_json = response.json()
        company._l10n_ro_edi_process_token_response(response_json)
        return request.redirect(f"{company.get_base_url()}/web")
