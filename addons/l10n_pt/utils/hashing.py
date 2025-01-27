import base64
import binascii
import re
import requests
import stdnum.pt.nif
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER
from odoo.exceptions import UserError
from odoo.tools import float_repr, format_date
from odoo import _lt


SIGN_DEFAULT_ENDPOINT = 'http://l10n-pt.api.odoo.com/api/l10n_pt/1'
ERROR_MESSAGES = {
    "error_connecting_iap": _lt("Unable to connect to the IAP endpoint to sign the documents. Please try later. If the problem persists, please contact Odoo support."),
    "error_db_unknown": _lt("This database is not known by Odoo. Please contact Odoo support."),
    "error_db_no_subscription": _lt("This database does not have a valid subscription. Please contact Odoo support."),
    "error_db_not_production": _lt("This database is not a production database. Please contact Odoo support."),
    "error_db_not_activated": _lt("This database is not activated. Please activate it first."),
    "error_documents_not_provided": _lt("No documents were provided to sign."),
    "error_documents_wrong_format": _lt("The documents provided are not in the correct format. Please contact Odoo support."),
}


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
            raise UserError(str(ERROR_MESSAGES.get(error, _lt("Unknown error %s while contacting IAP. Please contact Odoo support.", error))))
        return result
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        raise UserError(str(ERROR_MESSAGES.get("error_connecting_iap")))


def get_message_to_hash(date, l10n_pt_hashed_on, amount_total, l10n_pt_document_number, previous_hash):
    date = date.strftime('%Y-%m-%d')
    system_entry_date = l10n_pt_hashed_on.isoformat(timespec='seconds')
    gross_total = float_repr(amount_total, 2)
    return f"{date};{system_entry_date};{l10n_pt_document_number};{gross_total};{previous_hash}"


def sign_records(env, docs_to_sign, model):
    result = call_iap(env, "sign_documents", {"documents": docs_to_sign})
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
        error_msg = _lt("Some fields required for the generation of the document are missing or invalid. Please verify them:\n")
        error_msg += _lt('- The `VAT` of your company should be defined and match the following format: PT123456789\n') if not company_vat_ok else ""
        error_msg += _lt("- The `ATCUD` is not defined. Please verify the  AT series") if not atcud else ""
        error_msg += _lt("- The `hash` is not defined. You can contact the support.") if not hash_value else ""
        raise UserError(error_msg)


def l10n_pt_common_qr_code_str(record, env, date):
    """
    Generate the partial values needed to construct the QR code for Portugal.
    These are values that are common to l10n_pt, l10n_pt_pos and l10n_pt_stock.

    :param record: The account_move, pos_order or stock_picking for which the QR code is generated
    :param env: Environment
    :param date: The date required in the QR code, can be move.date, pos.date_order or picking.date_done
    :return: Dictionary containing some of the values needed for the QR code string, and the correct tax_letter per record
    """
    company_vat = re.sub(r'\D', '', record.company_id.vat)
    partner_vat = re.sub(r'\D', '', record.partner_id.vat or '999999990')

    tax_letter = 'I'
    if record.company_id.l10n_pt_region_code == 'PT-AC':
        tax_letter = 'J'
    elif record.company_id.l10n_pt_region_code == 'PT-MA':
        tax_letter = 'K'

    qr_code_dict = {}
    qr_code_dict['A:'] = f"{company_vat}*"
    qr_code_dict['B:'] = f"{partner_vat}*"
    qr_code_dict['C:'] = f"{record.partner_id.country_id.code if record.partner_id and record.partner_id.country_id else 'Desconhecido'}*"
    qr_code_dict['E:'] = f"{'A' if record.state == 'cancel' else 'N'}*"
    qr_code_dict['F:'] = f"{format_date(env, date, date_format='yyyyMMdd')}*"
    qr_code_dict[f'{tax_letter}1:'] = f"{record.company_id.l10n_pt_region_code}*"
    qr_code_dict['R:'] = f"{PT_CERTIFICATION_NUMBER}"

    return qr_code_dict, tax_letter
