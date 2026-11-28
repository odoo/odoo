import base64
import binascii
import json

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo.exceptions import UserError
from odoo.tools import LazyTranslate, float_repr, split_every

_lt = LazyTranslate(__name__)


SIGN_DEFAULT_ENDPOINT = 'https://l10n-pt.api.odoo.com/api/l10n_pt/1'
# The most documents the signing service signs in one request.
SIGN_MAX_DOCUMENTS = 1000
ERROR_MESSAGES = {
    "error_connecting_iap": _lt("Unable to connect to the IAP endpoint to sign the documents. Please try later. If the problem persists, please contact Odoo support."),
    "error_db_unknown": _lt("This database is not known by Odoo. Please contact Odoo support."),
    "error_db_no_subscription": _lt("This database does not have a valid subscription. Please contact Odoo support."),
    "error_db_not_production": _lt("This database is not a production database. Please contact Odoo support."),
    "error_db_not_activated": _lt("This database is not activated. Please activate it first."),
    "error_documents_not_provided": _lt("No documents were provided to sign."),
    "error_documents_wrong_format": _lt("The documents provided are not in the correct format. Please contact Odoo support."),
    "error_documents_too_many": _lt("Too many documents were sent to be signed at once. Please contact Odoo support."),
    "error_internal": _lt("The signing service could not sign the documents. Please try later. If the problem persists, please contact Odoo support."),
}


def split_inalterable_hash(inalterable_hash):
    """
    The ``(version, signature)`` of a stored ``$version$signature`` hash: empty strings when there is
    none, and the signature ``'invalid_hash'``, which matches no message, when the stored value was
    altered out of that shape. The signature alone is what the next document of the chain signs over.
    """
    if not inalterable_hash:
        return '', ''
    parts = inalterable_hash.split('$')
    if len(parts) != 3 or parts[0]:
        return '', 'invalid_hash'
    return parts[1], parts[2]


def signing_unavailable_error(env, error):
    """
    The error telling that the signing service could not be reached or failed: signing may succeed when
    tried again later. A plain ``UserError``, so that every client shows it as one, flagged with
    ``l10n_pt_retry_later`` for the callers that would otherwise try other documents.

    :param error: ``error_connecting_iap`` or ``error_internal``
    """
    exception = UserError(env._(ERROR_MESSAGES[error]))  # pylint: disable=gettext-variable
    exception.l10n_pt_retry_later = True
    return exception


def call_iap(env, route, params=None):
    try:
        params = {**(params or {}), 'db_uuid': env['ir.config_parameter'].sudo().get_param('database.uuid')}
        endpoint = env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', SIGN_DEFAULT_ENDPOINT)
        response = requests.post(f"{endpoint}/{route}", json={"params": params}, timeout=60)
        response.raise_for_status()
        result = response.json().get("result")
        if result is None:
            # A JSON-RPC error: the service failed while handling the request.
            raise signing_unavailable_error(env, "error_internal")
        error = result.get("error")
        if error in ("error_connecting_iap", "error_internal"):
            raise signing_unavailable_error(env, error)
        if error:
            if error in ERROR_MESSAGES:
                raise UserError(env._(ERROR_MESSAGES[error]))  # pylint: disable=gettext-variable
            raise UserError(env._("Unknown error %s while contacting IAP. Please contact Odoo support.", error))
        return result
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError,
        # An answer that is not JSON, e.g. a proxy's error page (requests' own error subclasses it).
        json.JSONDecodeError,
    ):
        raise signing_unavailable_error(env, "error_connecting_iap")


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
    """
    Sign one chain of documents, in requests of at most ``SIGN_MAX_DOCUMENTS``, each chained after the
    last signature of the one before.

    :return: {record: '$version$signature'}
    """
    res = {}
    docs_to_sign = sorted(docs_to_sign, key=lambda doc: doc['sorting_key'])
    previous_signature = docs_to_sign[0]['previous_signature'] if docs_to_sign else ''
    for chunk in split_every(SIGN_MAX_DOCUMENTS, docs_to_sign):
        result = call_iap(env, "sign_documents", {
            "documents": [{**doc, 'previous_signature': previous_signature} for doc in chunk],
            "model": model,
        })
        if set(result) != {str(doc['id']) for doc in chunk}:
            raise signing_unavailable_error(env, "error_internal")
        for record_id, record_info in result.items():
            res[env[model].browse(int(record_id))] = f"${record_info['signature_version']}${record_info['signature']}"
        previous_signature = result[str(chunk[-1]['id'])]['signature']
    return res


def get_public_keys(env):
    result = call_iap(env, "get_public_keys")
    res = {}
    for public_key_version, public_key_str in result.items():
        res[int(public_key_version)] = public_key_str
    return res


def get_public_key(public_keys, inalterable_hash):
    """
    The public key that verifies ``inalterable_hash``: the one of the key version stored in it.

    :param public_keys: {key version: public key}, as ``get_public_keys`` returns them
    :return: the public key, or None when the hash names no known version
    """
    version, __ = split_inalterable_hash(inalterable_hash)
    return public_keys.get(int(version)) if version.isdigit() else None


def verify_integrity(message, inalterable_hash, public_key_string):
    """
    :param message: The message (string) to verify
    :param inalterable_hash: The hash to verify against
    :param public_key_string: The public key to use to verify the hash
    :return: True if the hash of the record is valid, False otherwise
    """
    try:
        __, signature = split_inalterable_hash(inalterable_hash)
        public_key = serialization.load_pem_public_key(str.encode(public_key_string))
        public_key.verify(
            base64.b64decode(signature),
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
        return True
    except (InvalidSignature, binascii.Error, ValueError, IndexError):
        # InvalidSignature: the hash is not valid
        # binascii.Error: the hash is not base64 encoded
        # ValueError/IndexError: the key or the signature is not of the expected form
        return False
