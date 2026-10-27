import base64
import binascii
import re

import requests
import stdnum.pt.nif
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo.exceptions import UserError
from odoo.tools import LazyTranslate, float_repr, format_date

from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER

_lt = LazyTranslate(__name__)


SIGN_DEFAULT_ENDPOINT = 'https://l10n-pt.api.odoo.com/api/l10n_pt/1'
ERROR_MESSAGES = {
    "error_connecting_iap": _lt("Unable to connect to the IAP endpoint to sign the documents. Please try later. If the problem persists, please contact Odoo support."),
    "error_db_unknown": _lt("This database is not known by Odoo. Please contact Odoo support."),
    "error_db_no_subscription": _lt("This database does not have a valid subscription. Please contact Odoo support."),
    "error_db_not_production": _lt("This database is not a production database. Please contact Odoo support."),
    "error_db_not_activated": _lt("This database is not activated. Please activate it first."),
    "error_documents_not_provided": _lt("No documents were provided to sign."),
    "error_documents_wrong_format": _lt("The documents provided are not in the correct format. Please contact Odoo support."),
}


class L10nPtSigningUnavailable(UserError):
    """The signing service could not be reached: signing may succeed when tried again later."""


def call_iap(env, route, params=None):
    try:
        params = params or {}
        params['db_uuid'] = env['ir.config_parameter'].sudo().get_param('database.uuid')
        endpoint = env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', SIGN_DEFAULT_ENDPOINT)
        response = requests.post(f"{endpoint}/{route}", json={"params": params}, timeout=60)
        response.raise_for_status()
        result = response.json().get("result", {})
        error = result.get("error")
        if error:
            if error in ERROR_MESSAGES:
                raise UserError(env._(ERROR_MESSAGES[error]))  # pylint: disable=gettext-variable
            raise UserError(env._("Unknown error %s while contacting IAP. Please contact Odoo support.", error))
        return result
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.HTTPError):
        raise L10nPtSigningUnavailable(env._(ERROR_MESSAGES["error_connecting_iap"]))  # pylint: disable=gettext-variable


def format_hash_values(hash_values):
    """
    Format the values a document is signed over, exactly as the AT expects them in the message.

    Takes the raw values returned by ``_l10n_pt_get_hash_values`` and renders them. Signing
    (``_calculate_hashes``) and verification (``get_message_to_hash``) both go through here, so
    the two sides cannot render the same values differently.

    :param hash_values: the ``_l10n_pt_get_hash_values`` dict of the record
    :return: the formatted components, keyed as the IAP signing service expects them
    """
    return {
        'date': hash_values['date'].strftime('%Y-%m-%d'),
        'system_entry_date': hash_values['system_entry_date'].isoformat(timespec='seconds'),
        'name': hash_values['document_number'],
        'gross_total': float_repr(hash_values['gross_total'], 2),
    }


def get_message_to_hash(hash_values, previous_hash):
    """
    The signed message of a document, rebuilt for verification.

    :param hash_values: the ``_l10n_pt_get_hash_values`` dict of the record
    :param previous_hash: the bare signature of the previous document in the chain
    """
    values = format_hash_values(hash_values)
    return f"{values['date']};{values['system_entry_date']};{values['name']};{values['gross_total']};{previous_hash}"


def sign_records(env, docs_to_sign, model):
    result = call_iap(env, "sign_documents", {"documents": docs_to_sign, "model": model})
    res = {}
    for record_id, record_info in result.items():
        res[env[model].browse(int(record_id))] = f"${record_info['signature_version']}${record_info['signature']}"
    return res


def get_public_keys(env):
    result = call_iap(env, "get_public_keys")
    res = {}
    for public_key_version, public_key_str in result.items():
        res[int(public_key_version)] = public_key_str
    return res


def verify_integrity(message, inalterable_hash, public_key_string):
    """
    :param message: The message (string) to verify
    :param inalterable_hash: The hash to verify against
    :param public_key_string: The public key to use to verify the hash
    :return: True if the hash of the record is valid, False otherwise
    """
    try:
        inalterable_hash = inalterable_hash.split('$')[2]
        public_key = serialization.load_pem_public_key(str.encode(public_key_string))
        public_key.verify(
            base64.b64decode(inalterable_hash),
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
        return True
    except (InvalidSignature, binascii.Error, ValueError, IndexError):
        # InvalidSignature: the hash is not valid
        # binascii.Error: the hash is not base64 encoded
        # ValueError/IndexError: the hash does not have the correct format (with $)
        return False


def verify_prerequisites_qr_code(record, hash_value, atcud):
    company_vat_ok = record.company_id.vat and stdnum.pt.nif.is_valid(record.company_id.vat)
    if not company_vat_ok or not hash_value or not atcud:
        error_msg = record.env._("Some fields required for the generation of the document are missing or invalid. Please verify them:") + "\n"
        error_msg += record.env._("- The `VAT` of your company should be defined and match the following format: PT123456789") + "\n" if not company_vat_ok else ""
        error_msg += record.env._("- The `ATCUD` is not defined. Please verify the AT series") + "\n" if not atcud else ""
        error_msg += record.env._("- The `hash` is not defined. You can contact the support") if not hash_value else ""
        raise UserError(error_msg)


def l10n_pt_common_qr_code_str(record, env, date):
    """
    Generate the partial values needed to construct the QR code for Portugal.
    These are values that are common to l10n_pt, l10n_pt_pos, l10n_pt_sale and l10n_pt_stock.

    :param record: The record for which the QR code is generated
    :param env: Environment
    :param date: The date required in the QR code, can be move.date, pos.date_order or picking.date_done
    :return: Dictionary containing some of the values needed for the QR code string
    """
    company_vat = re.sub(r'\D', '', record.company_id.vat)
    partner_vat = record.partner_id and record.partner_id._l10n_pt_get_vat() or '999999990'

    qr_code_dict = {}
    qr_code_dict['A:'] = f"{company_vat}*"
    qr_code_dict['B:'] = f"{partner_vat}*"
    qr_code_dict['C:'] = f"{record.partner_id.country_id.code if record.partner_id and record.partner_id.country_id else 'Desconhecido'}*"
    qr_code_dict['E:'] = f"{'A' if record._l10n_pt_is_cancelled() else 'N'}*"
    qr_code_dict['F:'] = f"{format_date(env, date, date_format='yyyyMMdd')}*"
    qr_code_dict['G:'] = f"{record.l10n_pt_document_number}*"
    qr_code_dict['R:'] = f"{PT_CERTIFICATION_NUMBER}"

    return qr_code_dict
