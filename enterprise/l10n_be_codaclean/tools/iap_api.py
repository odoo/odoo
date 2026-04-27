import logging

from odoo import _, modules, release
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import exception_to_unicode

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "https://l10n-be-codaclean.api.odoo.com"


def get_contact_url(env, route=None):
    endpoint = env["ir.config_parameter"].sudo().get_param("l10n_be_codaclean.iap_endpoint", _DEFAULT_ENDPOINT).strip()
    suffix = f"/api/l10n_be_codaclean/1/{route}" if route else ""
    return f'{endpoint.removesuffix("/")}{suffix}'


def get_error_message(error):
    error_type = error.get("type", "")
    error_message = error.get("message", "")
    return {
        "jsonrpc": error_message,
        "iap_error_server": _("An internal error occurred on the IAP server. Please contact Odoo support."),
        "iap_error_connecting": _("An error occurred while connecting to the IAP server. If the error persists please contact Odoo support."),
        "iap_error_connection_not_found": _("Connection not found. Please check your configuration."),
        "codaclean_error_connecting": _("An error occurred while connecting to Codaclean. %s", error_message),
        "codaclean_error_auth": _("An error occurred while trying to authenticate with Codaclean. %s", error_message),
        "codaclean_error_file_download": _("An error occurred while trying to download a Coda file / PDF from Codaclean. %s", error_message),
    }.get(error_type, _("Unknown error '%s' while contacting IAP / Codaclean. Please contact Odoo support.", error_type))


def contact(env, action, params, timeout=15):
    """This function does not raise (except in test mode)"""
    if modules.module.current_test:
        raise ValidationError(_('Test mode'))
    params = {
        **params,
        'db_uuid': env['ir.config_parameter'].sudo().get_param('database.uuid'),
        'db_version': release.version,
        'db_lang': env.lang,
    }
    url = get_contact_url(env, action)
    try:
        result = iap_tools.iap_jsonrpc(url, params=params, timeout=timeout)
    except AccessError as e:
        result = {
            'error': {
                'type': 'jsonrpc',
                'message': exception_to_unicode(e),
            },
        }
    return result
