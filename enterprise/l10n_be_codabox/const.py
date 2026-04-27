from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)

PROXY_ERROR_CODES = {
    "error_codabox_not_configured": _lt("CodaBox is not configured. Please check your configuration."),
    "error_connecting_iap": _lt("An error occurred while connecting to the IAP server. Please contact Odoo support."),
    "error_connecting_codabox": _lt("An error occurred while connecting to CodaBox. Please contact Odoo support."),
    "error_connection_not_found": _lt("No connection exists with these VAT/Company ID number(s). Please check your configuration."),
    "error_consent_not_valid": _lt("It seems that your CodaBox connection is not valid anymore.  Please connect again."),
    "error_invalid_fidu_password": _lt("The provided password is not valid for this VAT/Company ID number."),
    "error_deprecated": _lt("Please upgrade the module CodaBox."),
}

CODABOX_ERROR_CODES = {
    "notFound": _lt("No files were found. Please check your configuration."),
    "validationError": _lt("It seems that the VAT/Company ID number you provided is not valid. Please check your configuration."),
    "unknownAccountingOffice": _lt("It seems that the VAT/Company ID number you provided does not exist in CodaBox. Please check your configuration."),
    "alreadyRegistered": _lt("It seems you have already created a connection to CodaBox with this account. To create a new connection, you must first revoke the old one on myCodaBox portal."),
    "timeout": _lt("CodaBox is not responding. Please try again later."),
}

DEFAULT_IAP_ENDPOINT = "https://l10n-be-codabox.api.odoo.com/api/l10n_be_codabox/2"


def get_error_msg(error):
    error_type = error.get("type")
    codabox_error_code = error.get("codabox_error_code")
    if error_type == 'error_connecting_codabox' and codabox_error_code:
        return CODABOX_ERROR_CODES.get(codabox_error_code, _lt("Unknown error %s while contacting CodaBox. Please contact Odoo support.", codabox_error_code))
    return PROXY_ERROR_CODES.get(error_type, _lt("Unknown error %s while contacting CodaBox. Please contact Odoo support.", error_type))


def get_iap_endpoint(env):
    return env["ir.config_parameter"].sudo().get_param("l10n_be_codabox.iap_endpoint", DEFAULT_IAP_ENDPOINT).strip()
