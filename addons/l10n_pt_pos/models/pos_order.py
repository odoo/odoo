import base64
import binascii
import logging
import re

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_repr

_logger = logging.getLogger(__name__)
DEFAULT_ENDPOINT = 'http://l10n-pt.api.odoo.com/iap/l10n_pt'


class PosOrder(models.Model):
    _inherit = "pos.order"

    l10n_pt_pos_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)

    # -------------------------------------------------------------------------
    # HASH
    # -------------------------------------------------------------------------
    def _get_integrity_hash_fields(self):
        if self.company_id.country_id.code != 'PT':
            return []
        return ['date_order', 'create_date', 'amount_total', 'name']

    def _get_l10n_pt_document_number(self):
        self.ensure_one()
        sequence_prefix = re.sub(r'[^A-Za-z0-9]+', '_', '_'.join(self.name.split('/')[:-1])).rstrip('_')
        sequence_postfix = self.name.split('/')[-1]
        return f"pos_order {sequence_prefix}/{sequence_postfix}"

    def _hash_compute(self, previous_hash=None):
        if self.company_id.country_id.code != 'PT' or not self._context.get('l10n_pt_force_compute_signature'):
            return {}
        endpoint = self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', DEFAULT_ENDPOINT)
        if endpoint == 'demo':
            return self._l10n_pt_sign_records_using_demo_key(previous_hash)  # sign locally with the demo key provided by the government
        return self._l10n_pt_sign_records_using_iap(previous_hash, endpoint)  # sign the records using Odoo's IAP (or a custom endpoint)

    def _l10n_pt_sign_records_using_iap(self, previous_hash, endpoint):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        docs_to_sign = [{
            'id': order.id,
            'date': order.date.isoformat(),
            'system_entry_date': order.create_date.isoformat(timespec='seconds'),
            'l10n_pt_document_number': order._get_l10n_pt_document_number(),
            'gross_total': float_repr(order.amount_total, 2),
            'previous_signature': previous_hash,
        } for order in self]
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
                res[int(record_id)] = f"${record_info['signature_version']}${record_info['signature']}"
        except ConnectionError as e:
            _logger.error("Error while contacting the IAP endpoint: %s", e)
            raise UserError(_("Unable to connect to the IAP endpoint to sign the documents. Please check your internet connection."))
        except Exception as e:
            _logger.error("An error occurred when signing the document: %s", e)
            raise UserError(_("An error occurred when signing the document: %s", e))
        return res

    def _l10n_pt_get_message_to_hash(self, previous_hash):
        self.ensure_one()
        date = self.date_order.isoformat()
        system_entry_date = self.create_date.isoformat(timespec='seconds')
        gross_total = float_repr(self.amount_total, 2)
        return f"{date};{system_entry_date};{self._get_l10n_pt_document_number()};{gross_total};{previous_hash}"

    def _l10n_pt_get_last_record(self):
        self.ensure_one()
        return self.sudo().search([
            ('config_id', '=', self.config_id.id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('l10n_pt_pos_inalterable_hash', '!=', False),
        ], order="id DESC", limit=1)

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
        for order in self:
            if not previous_hash:
                previous = order._l10n_pt_get_last_record()
                previous_hash = previous.l10n_pt_pos_inalterable_hash if previous else ""
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            message = order._l10n_pt_get_message_to_hash(previous_hash)
            signature = private_key.sign(
                message.encode(),
                padding.PKCS1v15(),
                hashes.SHA1(),
            )
            res[order.id] = f"${current_key_version}${base64.b64encode(signature).decode()}"
            previous_hash = res[order.id]
        return res

    def _l10n_pt_verify_integrity(self, previous_hash):
        """
        :return: True if the hash of the record is valid, False otherwise
        """
        self.ensure_one()
        try:
            hash_version, inalterable_hash = self.l10n_pt_pos_inalterable_hash.split("$")[1:]
            previous_hash = previous_hash.split("$")[2] if previous_hash else ""
            public_key_string = self.env['ir.config_parameter'].sudo().get_param(f'l10n_pt.public_key_v{hash_version}')
            if not public_key_string:
                raise UserError(_("The public key (version %s) for the local hash verification in Portugal is not set.", hash_version))
            public_key = serialization.load_pem_public_key(str.encode(public_key_string))
            public_key.verify(
                base64.b64decode(inalterable_hash),
                self._l10n_pt_get_message_to_hash(previous_hash).encode(),
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
        orders = self.search([
            ('company_id', '=', company_id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('l10n_pt_pos_inalterable_hash', '=', False),
        ], order='id')
        orders_hashes = self.env['pos.order'].browse([o.id for o in orders]).with_context(l10n_pt_force_compute_signature=True)._hash_compute()
        for order, l10n_pt_pos_inalterable_hash in orders_hashes.items():
            super(PosOrder, order).write({'l10n_pt_pos_inalterable_hash': l10n_pt_pos_inalterable_hash})
        return orders[-1].l10n_pt_pos_inalterable_hash

    def write(self, vals):
        if not vals:
            return True
        for order in self:
            violated_fields = set(vals).intersection(order._get_integrity_hash_fields() + ['l10n_pt_pos_inalterable_hash'])
            if (
                order.company_id.country_id.code == 'PT'
                and order.state in ['paid', 'done', 'invoiced']
                and violated_fields
                and order.l10n_pt_pos_inalterable_hash
               ):
                raise UserError(_("You cannot edit the following fields: %s", ', '.join(violated_fields)))
        return super(PosOrder, self).write(vals)
