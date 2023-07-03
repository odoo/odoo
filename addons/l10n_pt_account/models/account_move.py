import base64
import binascii
import logging
import re

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo import models, _, api, fields
from odoo.exceptions import UserError
from odoo.tools import float_repr, groupby

_logger = logging.getLogger(__name__)
DEFAULT_ENDPOINT = 'http://l10n-pt.api.odoo.com/iap/l10n_pt'


class AccountMove(models.Model):
    _inherit = "account.move"
    l10n_pt_document_number = fields.Char(string='Document Number', compute='_compute_l10n_pt_document_number')

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------
    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._get_integrity_hash_fields()
        return ['invoice_date', 'create_date', 'amount_total', 'l10n_pt_document_number', 'move_type', 'sequence_prefix', 'sequence_number']

    @api.depends('move_type', 'sequence_prefix', 'sequence_number')
    def _compute_l10n_pt_document_number(self):
        for move in self:
            move.l10n_pt_document_number = f"{move.move_type} {re.sub(r'[^A-Za-z0-9]+', '_', move.sequence_prefix).rstrip('_') }/{move.sequence_number}"

    def _hash_compute(self, previous_hash=None):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return super()._hash_compute(previous_hash=previous_hash)
        if not self._context.get('l10n_pt_force_compute_signature'):
            return {}
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', DEFAULT_ENDPOINT)
        if endpoint == 'demo':
            return self._l10n_pt_sign_records_using_demo_key(previous_hash)  # sign locally with the demo key provided by the government
        return self._l10n_pt_sign_records_using_iap(previous_hash, endpoint)  # sign the records using Odoo's IAP (or a custom endpoint)

    def _l10n_pt_sign_records_using_iap(self, previous_hash, endpoint):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        docs_to_sign = [{
            'id': move.id,
            'date': move.date.isoformat(),
            'system_entry_date': move.create_date.isoformat(timespec='seconds'),
            'l10n_pt_document_number': self._l10n_pt_document_number_compute(move.move_type, move.sequence_prefix, move.sequence_number),
            'gross_total': float_repr(move.amount_total, 2),
            'previous_signature': previous_hash
        } for move in self]
        res = {}
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
                res[self.browse(int(record_id))] = f"${record_info['signature_version']}${record_info['signature']}"
        except ConnectionError as e:
            _logger.error("Error while contacting the IAP endpoint: %s", e)
            raise UserError(_("Unable to connect to the IAP endpoint to sign the documents. Please check your internet connection."))
        except Exception as e:
            _logger.error("An error occurred when signing the document: %s", e)
            raise UserError(_("An error occurred when signing the document: %s", e))
        return res

    def _l10n_pt_account_get_message_to_hash(self, previous_hash):
        self.ensure_one()
        date = self.date.isoformat()
        system_entry_date = self.create_date.isoformat(timespec='seconds')
        gross_total = float_repr(self.amount_total, 2)
        return f"{date};{system_entry_date};{self.l10n_pt_document_number};{gross_total};{previous_hash}"

    def _l10n_pt_sign_records_using_demo_key(self, previous_hash):
        """
        Technical requirements from the Portuguese tax authority can be found at page 13 of the following document:
        https://info.portaldasfinancas.gov.pt/pt/docs/Portug_tax_system/Documents/Order_No_8632_2014_of_the_3rd_July.pdf
        """
        current_key_version = self.env['ir.config_parameter'].sudo().get_param('l10n_pt.current_key_version')
        private_key_string = self.env['ir.config_parameter'].sudo().get_param(f'l10n_pt.private_key_v{current_key_version}')
        if not private_key_string:
            raise UserError(_("The private key for the local hash generation in Portugal is not set."))
        private_key = serialization.load_pem_private_key(str.encode(private_key_string), password=None)
        res = {}
        for move in self:
            if not previous_hash:
                previous_move = move.sudo().search([
                    ('journal_id', '=', move.journal_id.id),
                    ('state', '=', 'posted'),
                    ('sequence_prefix', '=', move.sequence_prefix),
                    ('sequence_number', '=', move.sequence_number - 1),
                    ('inalterable_hash', '!=', False),
                ], limit=1)
                previous_hash = previous_move.inalterable_hash if previous_move else ""
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            message = move._l10n_pt_account_get_message_to_hash(previous_hash)
            signature = private_key.sign(
                message.encode(),
                padding.PKCS1v15(),
                hashes.SHA1(),
            )
            res[move] = f"${current_key_version}${base64.b64encode(signature).decode()}"
            previous_hash = res[move]
        return res

    def _l10n_pt_verify_integrity(self, previous_hash):
        """
        :return: True if the hash of the record is valid, False otherwise
        """
        self.ensure_one()
        try:
            hash_version, inalterable_hash = self.inalterable_hash.split("$")[1:]
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            public_key_string = self.env['ir.config_parameter'].sudo().get_param(f'l10n_pt.public_key_v{hash_version}')
            if not public_key_string:
                raise UserError(_("The public key (version %s) for the local hash verification in Portugal is not set.", hash_version))
            public_key = serialization.load_pem_public_key(str.encode(public_key_string))
            public_key.verify(
                base64.b64decode(inalterable_hash),
                self._l10n_pt_account_get_message_to_hash(previous_hash).encode(),
                padding.PKCS1v15(),
                hashes.SHA1(),
            )
            return True
        except (InvalidSignature, binascii.Error, ValueError):
            # InvalidSignature: the hash is not valid
            # binascii.Error: the hash is not base64 encoded
            # ValueError: the hash does not have the correct format (with $)
            return False

    def l10n_pt_compute_missing_hashes(self, company_id):
        """
        Compute the hash for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        all_moves = self.search([
            ('company_id', '=', company_id),
            ('restrict_mode_hash_table', '=', True),
            ('state', '=', 'posted'),
            ('inalterable_hash', '=', False),
        ], order='sequence_prefix,sequence_number')
        grouped = groupby(all_moves.filtered(lambda m: m.restrict_mode_hash_table and not m.inalterable_hash), key=lambda m: m.sequence_prefix)
        for prefix, moves in grouped:
            moves = sorted(moves, key=lambda m: m.sequence_number)
            moves_hashes = self.env['account.move'].browse([m.id for m in moves]).with_context(l10n_pt_force_compute_signature=True)._hash_compute()
            for move, inalterable_hash in moves_hashes.items():
                super(AccountMove, move).write({'inalterable_hash': inalterable_hash})

    def preview_invoice(self):
        self.l10n_pt_compute_missing_hashes(self.company_id.id)
        return super().preview_invoice()

    def action_send_and_print(self):
        self.l10n_pt_compute_missing_hashes(self.company_id.id)
        return super().action_send_and_print()

    def action_invoice_sent(self):
        self.l10n_pt_compute_missing_hashes(self.company_id.id)
        return super().action_invoice_sent()
