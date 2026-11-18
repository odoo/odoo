from datetime import date

import requests

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import format_datetime

from odoo.addons.l10n_pt_at_webservice.utils import series_ws
from odoo.addons.l10n_pt_certification.utils.hashing import ERROR_MESSAGES, SIGN_DEFAULT_ENDPOINT

# Odoo's proxy calls the AT with a 30-second timeout: the database waits a little longer.
PT_AT_WS_PROXY_TIMEOUT = 60

# The proxy's route of each operation of the AT's series webservice, and the AT's result codes meaning
# it succeeded: registarSerie, consultarSeries (4048: no series found), anularSerie, finalizarSerie.
PT_AT_WS_SUCCESS_CODES = {
    'register': (2001,),
    'query': (2002, 4048),
    'annul': (2003,),
    'finalize': (2004,),
}


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pt_at_ws_env = fields.Selection(
        selection=[
            ('prod', 'Production'),
            ('test', 'Test'),
            ('offline', 'Offline (no connection)'),
        ],
        string="AT Webservice Environment",
        default='offline',
    )
    l10n_pt_at_ws_username = fields.Char(
        string='AT Webservice Username',
        groups='base.group_system',
        help="Username (NIF/sub-user ID) for the Autoridade Tributária Series webservice.",
    )
    l10n_pt_at_ws_password = fields.Char(
        string='AT Webservice Password',
        groups='base.group_system',
        help="Password for the Autoridade Tributária Series webservice.",
    )

    def _l10n_pt_at_ws_check_configuration(self):
        """Raise when the company lacks what a call to the AT webservice needs."""
        self.ensure_one()
        if not self.l10n_pt_at_ws_username or not self.l10n_pt_at_ws_password:
            raise UserError(self.env._(
                "The AT webservice credentials are not configured for company %(company)s. "
                "Please configure them in the Accounting Settings.",
                company=self.name,
            ))
        public_cert = series_ws.get_at_public_certificate()
        if hasattr(public_cert, 'not_valid_after_utc'):
            public_cert_end = public_cert.not_valid_after_utc.replace(tzinfo=None)
        else:
            public_cert_end = public_cert.not_valid_after
        if public_cert_end < fields.Datetime.now():
            raise UserError(self.env._(
                "The AT public key certificate shipped with Odoo expired on %(date)s. "
                "Update Odoo to get the certificate the AT currently uses.",
                date=format_datetime(self.env, public_cert_end),
            ))

    def _l10n_pt_at_ws_call(self, operation, params, accept=()):
        """
        Call an operation of the AT's series webservice through Odoo's IAP proxy, which presents Odoo's
        client certificate to the AT. The company's credentials are sealed with the AT's public key.

        :param operation: ``register``, ``query``, ``annul`` or ``finalize``
        :param params: the operation's parameters, as named in the AT's WSDL
        :param accept: the AT's refusal codes the caller handles: their answer is returned, not raised
        :return: the AT's answer, ``{'codResultOper', 'msgResultOper', 'infoSerie': [...]}``
        :raises UserError: when the configuration is incomplete, the proxy or the AT gave no usable
            answer, or the AT refused the operation
        """
        self.ensure_one()
        self._l10n_pt_at_ws_check_configuration()
        ICP = self.env['ir.config_parameter'].sudo()
        endpoint = ICP.get_param('l10n_pt.iap_endpoint', SIGN_DEFAULT_ENDPOINT)
        payload = {
            'db_uuid': ICP.get_param('database.uuid'),
            'environment': self.l10n_pt_at_ws_env,
            'token': series_ws.seal_username_token(self.l10n_pt_at_ws_username, self.l10n_pt_at_ws_password),
            'params': {key: value.isoformat() if isinstance(value, date) else value for key, value in params.items()},
        }
        try:
            response = requests.post(f"{endpoint}/series/{operation}", json={'params': payload}, timeout=PT_AT_WS_PROXY_TIMEOUT)
            response.raise_for_status()
            answer = response.json().get('result')
        except requests.exceptions.Timeout as e:
            raise UserError(self.env._("The AT webservice did not answer in time: %(error)s. Please try again later.", error=e)) from e
        except (requests.exceptions.RequestException, ValueError) as e:
            raise UserError(self.env._(
                "Could not connect to Odoo's AT webservice service: %(error)s. Please try again later.", error=e,
            )) from e
        if not isinstance(answer, dict):
            # A JSON-RPC error: the proxy failed while handling the request.
            answer = {'error': 'error_internal'}
        if 'error' in answer:
            raise UserError(self._l10n_pt_at_ws_proxy_error_message(answer))
        if answer['codResultOper'] not in (*PT_AT_WS_SUCCESS_CODES[operation], *accept):
            raise self._l10n_pt_at_ws_refusal(answer)
        return answer

    def _l10n_pt_at_ws_refusal(self, answer):
        """The error telling the user that the AT refused the request, with its result code and message."""
        return UserError(self.env._(
            "The AT refused the request (%(code)s): %(message)s", code=answer['codResultOper'], message=answer['msgResultOper'] or '',
        ))

    def _l10n_pt_at_ws_proxy_error_message(self, answer):
        """The sentence telling the user why the proxy refused the call, or why the AT gave no usable answer."""
        error = answer['error']
        if error.startswith('error_db_') and error in ERROR_MESSAGES:
            return self.env._(ERROR_MESSAGES[error])  # pylint: disable=gettext-variable
        if error == 'error_at_http' and answer.get('status') in (401, 403):
            return self.env._("The AT webservice refused the connection (HTTP %(status)s). Please contact Odoo support.", status=answer['status'])
        messages = {
            'error_at_fault': self.env._("The AT webservice refused the request: %(error)s", error=answer.get('message') or ''),
            'error_at_http': self.env._("The AT webservice answered with an HTTP error (%(status)s).", status=answer.get('status')),
            'error_at_timeout': self.env._("The AT webservice did not answer in time. Please try again later."),
            'error_at_unreachable': self.env._("Could not connect to the AT webservice. Please try again later."),
            'error_at_tls': self.env._("The secure connection to the AT webservice failed. Please contact Odoo support."),
            'error_at_no_certificate': self.env._("Odoo's connection to this AT webservice environment is not set up. Please contact Odoo support."),
            'error_at_unreadable': self.env._("The answer of the AT webservice could not be read. Please try again later."),
            'error_params_wrong_format': self.env._("The request to the AT webservice was not in the expected form. Please contact Odoo support."),
        }
        return messages.get(error) or self.env._(
            "Odoo's AT webservice service could not handle the request. Please try again later. "
            "If the problem persists, please contact Odoo support."
        )
