import base64
import binascii
import logging
import requests
import stdnum.pt.nif
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo.exceptions import UserError
from odoo.tools import float_repr
from odoo import _

_logger = logging.getLogger(__name__)


class L10nPtHashingUtils:
    L10N_PT_SIGN_DEFAULT_ENDPOINT = 'http://l10n-pt.api.odoo.com/iap/l10n_pt'

    @staticmethod
    def _l10n_pt_get_short_hash(inalterable_hash):
        if not inalterable_hash:
            return False
        hash_str = inalterable_hash.split("$")[2]
        return hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]

    @staticmethod
    def _l10n_pt_verify_qr_code_prerequisites(company, atcud):
        company_vat_ok = company.vat and stdnum.pt.nif.is_valid(company.vat)
        if not company_vat_ok or not atcud:
            error_msg = _("Some fields required for the generation of the document are missing or invalid. Please verify them:\n")
            error_msg += _('- The `VAT` of your company should be defined and match the following format: PT123456789\n') if not company_vat_ok else ""
            error_msg += _("- The `ATCUD` is not defined. Please verify the operation type's official series") if not atcud else ""
            raise UserError(error_msg)

    @staticmethod
    def _l10n_pt_sign_records_using_demo_key(records, previous_hash, hash_field, get_last_record_function, get_message_to_hash_function):
        res = {}
        if not previous_hash:
            previous_move = get_last_record_function(records[0])
            previous_hash = previous_move[hash_field] if previous_move else ""
        for record in records:
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            message = get_message_to_hash_function(record, previous_hash)
            res[record.id] = L10nPtHashingUtils._l10n_pt_sign_using_demo_key(record.env, message)
            previous_hash = res[record.id]
        return res

    @staticmethod
    def _l10n_pt_get_iap_error(error_code):
        return {
            'error_db_unknown': _("Your database uuid does not exist. Please contact Odoo support."),
            'error_db_subscription_verification': _("An error has occurred when trying to verify your subscription. Please contact Odoo support."),
            'error_db_no_subscription': _("You do not have an Odoo enterprise subscription."),
            'error_db_not_production': _("Your database is not used for a production environment."),
            'error_db_not_activated': _("Your database is not yet activated."),
            'error_contact_support': _("An error has occurred. Please contact Odoo support."),
            'error_documents_not_provided': _("No documents to sign."),
            'error_documents_wrong_format': _("The submitted documents are not in the correct format."),
        }.get(error_code, _("An error has occurred. Please contact Odoo support."))

    @staticmethod
    def _l10n_pt_get_public_keys(env):
        endpoint = env['ir.config_parameter'].sudo().get_param('l10n_pt_account.iap_endpoint', L10nPtHashingUtils.L10N_PT_SIGN_DEFAULT_ENDPOINT)
        res = {}
        try:
            params = {'db_uuid': env['ir.config_parameter'].sudo().get_param('database.uuid')}
            response = requests.post(f'{endpoint}/get_public_keys', json={'params': params}, timeout=5000)
            if not response.ok:
                raise ConnectionError
            result = response.json().get('result')
            if result.get('error'):
                raise Exception(L10nPtHashingUtils._l10n_pt_get_iap_error(result['error']))
            for public_key_version, public_key_str in result.items():
                res[int(public_key_version)] = public_key_str
        except ConnectionError as e:
            _logger.error("Error while contacting the IAP endpoint: %s", e)
            raise UserError(_("Unable to connect to the IAP endpoint to sign the documents. Please check your internet connection."))
        except Exception as e:
            _logger.error("An error occurred when signing the document: %s", e)
            raise UserError(_("An error occurred when signing the document: %s", e))
        return res

    @staticmethod
    def _l10n_pt_get_last_public_key(env):
        if env['ir.config_parameter'].sudo().get_param('l10n_pt_account.iap_endpoint') == 'demo':
            public_key_string = env['ir.config_parameter'].sudo().get_param('l10n_pt_account.public_key')
        else:
            public_keys = L10nPtHashingUtils._l10n_pt_get_public_keys(env)
            public_key_string = public_keys[max(public_keys, key=int)]
        if not public_key_string:
            raise UserError(_("The public key for the local hash verification in Portugal is not set."))
        return public_key_string

    @staticmethod
    def _l10n_pt_sign_records_using_iap(env, docs_to_sign):
        """
        Sign the documents given by IAP. Instead of signing the documents one
        by one which requires multiple RPC calls, we batch them all
        with the needed info for signing and get the computed
        signature for each of the documents in a single RPC call.
        :param env: the environment
        :param docs_to_sign is a list of dictionaries in the form of [{
            'id': 123,
            'sorting_key': 123,
            'date': '2020-01-01',
            'system_entry_date': '2020-01-01T00:00:00',
            'l10n_pt_document_number': 'doc_number_123',
            'gross_total': 100.0,
            'previous_signature': 'Au7ynj1',  # mandatory for the first document, useless for the others
        }, {...}, ...]
        :returns: a dictionary in the form of {
            123 : {
                'signature': 'P!W8Au7ynj1',
                'signature_version': '1',
            },
            ...
        }
        """
        endpoint = env['ir.config_parameter'].sudo().get_param('l10n_pt_account.iap_endpoint', L10nPtHashingUtils.L10N_PT_SIGN_DEFAULT_ENDPOINT)
        res = {}
        try:
            params = {
                'db_uuid': env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'documents': docs_to_sign,
            }
            response = requests.post(f'{endpoint}/sign_documents', json={'params': params}, timeout=5000)
            if not response.ok:
                raise ConnectionError
            result = response.json().get('result')
            if result.get('error'):
                raise Exception(L10nPtHashingUtils._l10n_pt_get_iap_error(result['error']))
            for record_id, record_info in result.items():
                res[int(record_id)] = f"${record_info['signature_version']}${record_info['signature']}"
        except ConnectionError as e:
            _logger.error("Error while contacting the IAP endpoint: %s", e)
            raise UserError(_("Currently unable to connect to the IAP endpoint to sign the documents"))
        except Exception as e:
            _logger.error("An error occurred when signing the document: %s", e)
            raise UserError(_("An error occurred when signing the document: %s", e))
        return res

    @staticmethod
    def _l10n_pt_get_message_to_hash(date, create_date, amount_total, l10n_pt_document_number, previous_hash):
        date = date.strftime('%Y-%m-%d')
        system_entry_date = create_date.isoformat(timespec='seconds')
        gross_total = float_repr(amount_total, 2)
        return f"{date};{system_entry_date};{l10n_pt_document_number};{gross_total};{previous_hash}"

    @staticmethod
    def _l10n_pt_sign_using_demo_key(env, message):
        """
        Technical requirements from the Portuguese tax authority can be found at page 13 of the following document:
        https://info.portaldasfinancas.gov.pt/pt/docs/Portug_tax_system/Documents/Order_No_8632_2014_of_the_3rd_July.pdf
        """
        current_key_version = env['ir.config_parameter'].sudo().get_param('l10n_pt_account.key_version')
        private_key_string = env['ir.config_parameter'].sudo().get_param('l10n_pt_account.private_key')
        if not private_key_string:
            raise UserError(_("The private key for the local hash generation in Portugal is not set."))
        private_key = serialization.load_pem_private_key(str.encode(private_key_string), password=None)
        signature = private_key.sign(
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
        return f"${current_key_version}${base64.b64encode(signature).decode()}"

    @staticmethod
    def _l10n_pt_verify_integrity(message, inalterable_hash, public_key_string):
        """
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
        except (InvalidSignature, binascii.Error, ValueError):
            # InvalidSignature: the hash is not valid
            # binascii.Error: the hash is not base64 encoded
            # ValueError: the hash does not have the correct format (with $)
            return False
