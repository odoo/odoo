import binascii
import requests

from werkzeug.urls import url_encode

from odoo import _, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools.urls import urljoin as url_join


URL_ANAF_AUTHORIZE = 'https://logincert.anaf.ro/anaf-oauth2/v1/authorize'
URL_ANAF_TOKEN = 'https://logincert.anaf.ro/anaf-oauth2/v1/token'


class L10nRoEdiController(http.Controller):

    @http.route('/l10n_ro_edi/authorize/<int:company_id>', auth="user")
    def authorize(self, company_id, **kw):
        """ Generate Authorization Token to acquire access_key for requesting Access Token """
        company = http.request.env['res.company'].browse(company_id)
        if not company.l10n_ro_edi_client_id or not company.l10n_ro_edi_client_secret:
            raise UserError(_("Client ID and Client Secret field must be filled."))

        auth_url_params = url_encode({
            'response_type': 'code',
            'client_id': company.l10n_ro_edi_client_id,
            'redirect_uri': company.l10n_ro_edi_callback_url,
            'token_content_type': 'jwt',
        })
        auth_url = f'{URL_ANAF_AUTHORIZE}?{auth_url_params}'
        return request.redirect(auth_url, code=302, local=False)

    @http.route('/l10n_ro_edi/callback/<int:company_id>', type='http', auth="user")
    def callback(self, company_id, **kw):
        """ Use the acquired access_key to request access & refresh token from ANAF """
        company = http.request.env['res.company'].browse(company_id)
        access_key = kw.get('code')

        def log_and_raise_error(message: str):
            message += '\n' + _("Received access key: %s", access_key)
            company._l10n_ro_edi_log_message(message, 'callback')
            raise UserError(message)

        # Without certificate, ANAF won't give any access key in the callback URL's "code" parameter
        if not access_key:
            log_and_raise_error(_("Access key not found. Please try again.\nResponse: %s", kw))

        try:
            response = requests.post(
                url=URL_ANAF_TOKEN,
                data={
                    'grant_type': 'authorization_code',
                    'client_id': company.l10n_ro_edi_client_id,
                    'client_secret': company.l10n_ro_edi_client_secret,
                    'code': access_key,
                    'access_key': access_key,
                    'redirect_uri': company.l10n_ro_edi_callback_url,
                    'token_content_type': 'jwt',
                },
                headers={
                    'accept': 'application/json',
                    'user-agent': 'Odoo (http://www.odoo.com/contactus)',
                },
                timeout=10,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            log_and_raise_error(f"Request to {URL_ANAF_TOKEN} failed: {e}")

        response_to_log = _("Response (code=%(status_code)s) to %(url)s failed:\n%(text)s",
                            status_code=response.status_code,
                            url=response.url,
                            text=response.text)
        try:
            response_json = response.json()
        except requests.exceptions.RequestException as e:
            error_cause = _("Error when converting response to json: %s", e)
            log_and_raise_error(f"{error_cause}\n{response_to_log}")

        try:
            company._l10n_ro_edi_process_token_response(response_json)
        except ValidationError as e:
            log_and_raise_error(f"{e}\n{response_to_log}")
        except binascii.Error as e:
            error_cause = _("Error when decoding the access token payload: %s", e)
            log_and_raise_error(f"{error_cause}\n{response_to_log}")
        except Exception as e:
            error_cause = _("Error when processing the response: %s", e)
            log_and_raise_error(f"{error_cause}\n{response_to_log}")

        return request.redirect(url_join(request.httprequest.url_root, 'web'))
