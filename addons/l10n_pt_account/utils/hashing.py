import base64
import binascii
import logging
import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo.exceptions import UserError
from odoo.tools import float_repr
from odoo import _

_logger = logging.getLogger(__name__)


class L10nPtHashingUtils:
    L10N_PT_SIGN_DEFAULT_ENDPOINT = 'http://l10n-pt.api.odoo.com/iap/l10n_pt_account'

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
                raise Exception(result['error'])
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
                raise Exception(result['error'])
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
        date = date.isoformat()
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
        private_key_string = env['ir.config_parameter'].sudo().get_param(f'l10n_pt_account.private_key')
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
