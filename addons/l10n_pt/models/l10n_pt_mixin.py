# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_repr
import logging
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
import base64


_logger = logging.getLogger(__name__)
DEFAULT_ENDPOINT = 'http://l10n-pt.api.odoo.com/iap/l10n_pt'


class L10nPtMixin(models.AbstractModel):
    _name = 'l10n_pt.mixin'
    _description = "Portugal Mixin - Contains common things between Portuguese apps"

    l10n_pt_signature_version = fields.Integer(string="Signature Version")
    l10n_pt_document_number = fields.Char(string='Document number', compute='_compute_l10n_pt_document_number', store=True)
    l10n_pt_date = fields.Date()  # To be defined in the inheriting model using related/compute
    l10n_pt_gross_total = fields.Float()  # To be defined in the inheriting model using related/compute

    @api.model
    def _l10n_pt_get_sanitized_sequence_info(self, prefix, name=None, number=None):
        """
        l10n_pt_document_number must be in the format [^ ]+ [^/^ ]+/[0-9]+
        Therefore we must sanitize the sequence prefix in case it contains spaces or "/"
        If the sequence number is not provided, we'll use the name and the prefix to determine it
        :param prefix: the sequence prefix which may contain spaces or "/"
        :param name: the name of the record
        :param number: the sequence number of the record
        :returns: the formatted and sanitized sequence prefix and number
        """
        seq_prefix = prefix.replace(" ", "_").replace("/", "_")
        seq_prefix = seq_prefix[:-1] if seq_prefix.endswith('_') else seq_prefix
        assert name is not None or number is not None, "Either the name or the number must be defined"
        seq_number = number if number is not None else name.replace(prefix, '')
        return f"{seq_prefix}/{seq_number}"

    def _compute_l10n_pt_document_number(self):
        raise NotImplementedError("'_compute_l10n_pt_document_number' must be overriden by the inheriting class"
                                  "that uses the following '_l10n_pt_get_blockchain_record_hash_string' method")

    def _l10n_pt_compute_blockchain_inalterable_hash(self):
        """
        Regroup all records that need a hash and send them all at once to the IAP endpoint
        such that we only perform one request instead of one request per record.
        """
        if not self._context.get('l10n_pt_force_compute_signature'):
            return
        self = self.filtered(lambda r: not r.blockchain_inalterable_hash and r.blockchain_must_hash).sorted("blockchain_secure_sequence_number")
        if not self:
            return
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', DEFAULT_ENDPOINT)
        if endpoint == 'demo':
            self._l10n_pt_sign_records_using_demo_key()  # sign locally with the demo key provided by the government
        else:
            self._l10n_pt_sign_records_using_iap(endpoint)  # sign the records using Odoo's IAP (or a custom endpoint)

    def l10n_pt_compute_missing_hashes(self, company_id):
        """
        Compute the hash for all records that do not have one yet
        (because they were not printed/previewed yet)
        :return: the last computed hash
        """
        records = self.search([
            ('company_id', '=', company_id),
            ('blockchain_secure_sequence_number', '!=', False),
            ('blockchain_inalterable_hash', '=', False),
        ], order='blockchain_secure_sequence_number')
        records.with_context(l10n_pt_force_compute_signature=True)._l10n_pt_compute_blockchain_inalterable_hash()
        return records[-1].blockchain_inalterable_hash if records else ""

    def _l10n_pt_sign_records_using_iap(self, endpoint):
        """
        Sign the records using Odoo's IAP (or a custom endpoint)
        To avoid multiple RPC calls, we send all the needed data of all the records at once
        such that the IAP endpoint can sign all the records at once and return simply
        the signature and the signature key version for each record.
        """
        docs_to_sign = [
            {
                'id': record.id,
                'secure_sequence_number': record.blockchain_secure_sequence_number,
                'date': record.l10n_pt_date.strftime('%Y-%m-%d'),
                'system_entry_date': record.create_date.strftime("%Y-%m-%dT%H:%M:%S"),
                'l10n_pt_document_number': record.l10n_pt_document_number,
                'gross_total': float_repr(record.l10n_pt_gross_total, 2),
                'previous_signature': record._get_blockchain_record_previous_hash() if record == self[0] else '',
            }
            for record in self
        ]
        try:
            params = {
                'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'documents': docs_to_sign,
            }
            response = requests.post(f'{endpoint}/sign_documents', json={'params': params}, timeout=5000)
            if not response.ok:
                raise ConnectionError
            result = response.json().get('result')
            if result.get('error'):
                raise Exception(result['error'])
            for record_id, record_info in result.items():
                record = self.browse(int(record_id))
                record.blockchain_inalterable_hash = record_info['signature']
                record.l10n_pt_signature_version = int(record_info['signature_version'])
        except ConnectionError as e:
            _logger.error("Error while contacting the IAP endpoint: %s", e)
            raise UserError(_("Unable to connect to the IAP endpoint to sign the documents. Please check your internet connection."))
        except Exception as e:
            _logger.error("An error occurred when signing the document: %s", e)
            raise UserError(_("An error occurred when signing the document: %s", e))

    # Methods to sign locally with the demo key provided by the government

    def _l10n_pt_sign_records_using_demo_key(self):
        for record in self:
            record.blockchain_inalterable_hash = record._l10n_pt_get_blockchain_record_hash_string()
            record.flush_recordset()  # Make sure the hash is stored in the database before computing the next one (which depends on this one)

    def _l10n_pt_get_blockchain_record_hash_string(self, previous_hash=None):
        self.ensure_one()
        date = self.l10n_pt_date.strftime('%Y-%m-%d')
        system_entry_date = self.create_date.strftime("%Y-%m-%dT%H:%M:%S")
        gross_total = float_repr(self.l10n_pt_gross_total, 2)
        previous_hash = previous_hash or self._get_blockchain_record_previous_hash()
        message = f"{date};{system_entry_date};{self.l10n_pt_document_number};{gross_total};{previous_hash}"
        return self._l10n_pt_sign_message(message)

    @api.model
    def _l10n_pt_get_private_key(self):
        """
        :rtype: str
        :return: the private key used to sign Portuguese documents.
        This key is detained by the company which produces this software, not the company that uses this software.
        More info can be found on the following link
        https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Faturacao/Paginas/certificacao-de-software.aspx
        """
        private_key = self.env['ir.config_parameter'].sudo().get_param('l10n_pt.private_key')
        if not private_key:
            raise UserError(_("The private key for the hash generation in Portugal is not set."))
        return private_key

    @api.model
    def _l10n_pt_sign_message(self, message):
        """
        Technical requirements from the Portuguese tax authority can be found at page 13 of the following document:
        https://info.portaldasfinancas.gov.pt/pt/docs/Portug_tax_system/Documents/Order_No_8632_2014_of_the_3rd_July.pdf
        """
        private_key_string = self._l10n_pt_get_private_key()
        private_key = serialization.load_pem_private_key(str.encode(private_key_string), password=None)
        signature = private_key.sign(
            message.encode(),
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        return base64.b64encode(signature).decode()
