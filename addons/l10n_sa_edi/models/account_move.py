import uuid
import json

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_repr
from datetime import datetime
from base64 import b64decode, b64encode
from lxml import etree

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sa_reversal_reason = fields.Char("Reversal Reason", help="Reason for which the original invoice was reversed")

    l10n_sa_uuid = fields.Char(string='Document UUID', copy=False, help="Universally unique identifier of the Invoice")

    l10n_sa_submission_state = fields.Selection([('to_send', 'To Send'), ('sent', 'Sent'), ('to_cancel', 'To Cancel'),
                                                 ('cancelled', 'Cancelled')], string="Submission State",
                                                compute="_l10n_sa_compute_submission_state", store=True)

    l10n_sa_unsigned_xml_data = fields.Text("Unsigned XML", copy=False)
    l10n_sa_unsigned_xml_signature = fields.Char("Unsigned XML Signature", copy=False)

    @api.depends('edi_document_ids', 'edi_document_ids.state')
    def _l10n_sa_compute_submission_state(self):
        for move in self:
            sa_document = next((d for d in move.edi_document_ids if d.edi_format_id.code == 'sa_zatca'), None)
            move.l10n_sa_submission_state = sa_document.state if sa_document else 'to_send'

    @api.depends('amount_total_signed', 'amount_tax_signed', 'l10n_sa_confirmation_datetime', 'company_id',
                 'company_id.vat', 'journal_id', 'journal_id.l10n_sa_production_csid_json')
    def _compute_qr_code_str(self):
        """ Override to update QR code generation in accordance with ZATCA Phase 2"""
        for move in self:
            move.l10n_sa_qr_code_str = ''
            if move.country_code == 'SA' and move.move_type == 'out_invoice' and move.l10n_sa_unsigned_xml_data:
                x509_cert = json.loads(move.journal_id.l10n_sa_production_csid_json)['binarySecurityToken']
                qr_code_str = move._l10n_sa_get_qr_code(move.journal_id, move.l10n_sa_unsigned_xml_data, b64decode(x509_cert), move.l10n_sa_unsigned_xml_signature)
                move.l10n_sa_qr_code_str = b64encode(qr_code_str).decode()

    def _l10n_sa_get_qr_code_encoding(self, tag, field, int_length=1):
        """
            Helper function to encode strings for the QR code generation according to ZATCA specs
        """
        company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
        company_name_length_encoding = len(field).to_bytes(length=int_length, byteorder='big')
        return company_name_tag_encoding + company_name_length_encoding + field

    @api.model
    def _l10n_sa_get_qr_code(self, journal_id, unsigned_xml, x509_cert, signature):
        """
            Generate QR code string based on XML content of the Invoice UBL file, X509 Production Certificate
            and company info.

            :return b64 encoded QR code string
        """

        def xpath_ns(expr):
            return root.xpath(expr, namespaces=edi_format._l10n_sa_get_namespaces())[0].text.strip()

        qr_code_str = ''
        root = etree.fromstring(unsigned_xml)
        edi_format = self.env.ref('l10n_sa_edi.edi_sa_zatca')

        # Indent XML content to avoid indentation mismatches
        etree.indent(root, space='    ')

        invoice_date = xpath_ns('//cbc:IssueDate')
        invoice_time = xpath_ns('//cbc:IssueTime')
        invoice_datetime = datetime.strptime(invoice_date + ' ' + invoice_time, '%Y-%m-%d %H:%M:%S')

        if invoice_datetime and journal_id.company_id.vat and x509_cert:

            prehash_content = etree.tostring(root)
            invoice_hash = edi_format._l10n_sa_generate_invoice_xml_hash(prehash_content, 'digest')

            amount_total = float(xpath_ns('//cbc:TaxInclusiveAmount'))
            amount_tax = float(xpath_ns('//cac:TaxTotal/cbc:TaxAmount'))
            x509_certificate = load_der_x509_certificate(b64decode(x509_cert), default_backend())
            seller_name_enc = self._l10n_sa_get_qr_code_encoding(1, journal_id.company_id.display_name.encode())
            seller_vat_enc = self._l10n_sa_get_qr_code_encoding(2, journal_id.company_id.vat.encode())
            timestamp_enc = self._l10n_sa_get_qr_code_encoding(3,
                                                               invoice_datetime.strftime("%Y-%m-%dT%H:%M:%SZ").encode())
            amount_total_enc = self._l10n_sa_get_qr_code_encoding(4, float_repr(abs(amount_total), 2).encode())
            amount_tax_enc = self._l10n_sa_get_qr_code_encoding(5, float_repr(abs(amount_tax), 2).encode())
            invoice_hash_enc = self._l10n_sa_get_qr_code_encoding(6, invoice_hash)
            signature_enc = self._l10n_sa_get_qr_code_encoding(7, signature.encode())
            public_key_enc = self._l10n_sa_get_qr_code_encoding(8,
                                                                x509_certificate.public_key().public_bytes(Encoding.DER,
                                                                                                           PublicFormat.SubjectPublicKeyInfo))
            qr_code_str = (seller_name_enc + seller_vat_enc + timestamp_enc + amount_total_enc +
                           amount_tax_enc + invoice_hash_enc + signature_enc + public_key_enc)
        return qr_code_str

    def _l10n_sa_get_previous_invoice(self):
        """
            Search for the previous invoice relating to the current record. We use the l10n_sa_confirmation_datetime
            field to figure out which invoice comes before which.
        :return: Previous invoice record
        :rtype: recordset
        """
        self.ensure_one()
        return self.search(
            [('move_type', 'in', self.get_invoice_types()), ('id', '!=', self.id), ('state', '=', 'posted'),
             ('l10n_sa_confirmation_datetime', '<', self.l10n_sa_confirmation_datetime),
             ('l10n_sa_submission_state', '=', 'sent')], limit=1, order='l10n_sa_confirmation_datetime desc')

    @api.model_create_multi
    def create(self, vals_list):
        """
            Override to add a UUID on the invoice whenever it is created
        """
        for vals in vals_list:
            if 'l10n_sa_uuid' not in vals:
                vals['l10n_sa_uuid'] = uuid.uuid1()
        return super(AccountMove, self).create(vals_list)

    def button_cancel_posted_moves(self):
        """
            Override to prohibit the cancellation of invoices submitted to ZATCA
        """
        for move in self:
            if move.edi_document_ids.filtered(lambda doc: doc.edi_format_id.code == "sa_zatca"):
                raise UserError(_("Cannot cancel eInvoices submitted to ZATCA. Please, issue a Credit Note instead"))
        return super(AccountMove, self).button_cancel_posted_moves()

    def _l10n_sa_generate_unsigned_xml(self):
        """
            Generate Unsigned XML content & digital signature to be used during both Signing and QR code generation.
            It is necessary to save the signature as it changes everytime it is generated and both the signing and the
            QR code expect to have the same, identical signature.
        """
        self.ensure_one()
        edi_format = self.env.ref('l10n_sa_edi.edi_sa_zatca')
        # Build the dict of values to be used for generating the Invoice XML content
        invoice_values = edi_format._l10n_sa_prepare_values(self)
        self.l10n_sa_unsigned_xml_data = edi_format._l10n_sa_generate_zatca_template(self, invoice_values)
        # Once the XML content is generated, we hash it, then use the hexadecimal hash to generate a Signature
        invoice_hash_hex = edi_format._l10n_sa_generate_invoice_xml_hash(self.l10n_sa_unsigned_xml_data).decode()
        self.l10n_sa_unsigned_xml_signature = edi_format._l10n_sa_get_digital_signature(self.journal_id.company_id, invoice_hash_hex).decode()

    def _post(self, soft=True):
        to_post = super()._post(soft)
        for move in to_post.filtered(lambda m: m.country_code == 'SA' and m.move_type in ('out_invoice', 'out_refund')):
            move._l10n_sa_generate_unsigned_xml()
        return to_post