# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""e-Tax Invoice & e-Receipt documents (ขมธอ.3-2560).

An ``od19.etax.document`` is the legal, signed representation of a posted
journal entry.  The lifecycle is:

    Draft -> Generated (unsigned XML) -> Signed (XAdES-BES) -> PDF

The XML is validated against the official ETDA XSD before it is signed, so a
document can never be issued in a non conformant shape.
"""

import base64
import hashlib
import logging
import re

from lxml import etree

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..lib import namespaces, qr, signer, validator, xml_builder

_logger = logging.getLogger(__name__)

_ALLOWED_MOVE_TYPES = ("out_invoice", "out_refund", "out_receipt")


class Od19EtaxDocument(models.Model):
    _name = "od19.etax.document"
    _description = "e-Tax Invoice / e-Receipt Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "issue_datetime desc, id desc"

    name = fields.Char(
        string="Document Reference",
        required=True,
        copy=False,
        tracking=True,
        help="Reference reported in ExchangedDocument/ID (max 35 characters).",
    )
    document_type = fields.Selection(
        namespaces.DOCUMENT_TYPE_SELECTION,
        string="Document Type",
        required=True,
        default="tax_invoice",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="move_id.currency_id",
        store=True,
        readonly=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        required=True,
        ondelete="cascade",
        tracking=True,
        domain="[('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt'))]",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="move_id.commercial_partner_id",
        store=True,
        readonly=True,
    )
    source_document_id = fields.Many2one(
        "od19.etax.document",
        string="Corrected Document",
        ondelete="set null",
        copy=False,
        help="Original e-Tax document referenced by a debit/credit note or a "
        "cancellation note.",
    )
    certificate_id = fields.Many2one(
        "od19.etax.certificate",
        string="Signing Certificate",
        help="Leave empty to use the certificate configured on the company.",
    )
    od19_etax_enabled = fields.Boolean(
        related="company_id.od19_etax_enabled",
        string="e-Tax Invoice Enabled",
        readonly=True,
    )

    issue_datetime = fields.Datetime(
        string="Issue Date Time",
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    type_code = fields.Char(
        string="Document Type Code",
        compute="_compute_type_code",
        store=True,
        readonly=False,
    )
    purpose_code = fields.Char(
        string="Purpose Code",
        compute="_compute_type_code",
        store=True,
        readonly=False,
    )
    global_id = fields.Char(
        string="Global ID",
        copy=False,
        help="Optional globally unique identifier (OID) of the document.",
    )
    note = fields.Text(string="Note")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("generated", "XML Generated"),
            ("signed", "Signed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )

    xml_file = fields.Binary(string="Unsigned XML", attachment=True, copy=False)
    xml_filename = fields.Char(copy=False)
    signed_xml_file = fields.Binary(string="Signed XML", attachment=True, copy=False)
    signed_xml_filename = fields.Char(copy=False)
    pdf_file = fields.Binary(string="e-Tax PDF", attachment=True, copy=False)
    pdf_filename = fields.Char(copy=False)

    digest = fields.Char(
        string="XML Fingerprint",
        readonly=True,
        copy=False,
        help="SHA-512 digest of the signed XML, printed on the paper copy.",
    )
    signed_at = fields.Datetime(string="Signed On", readonly=True, copy=False)
    signer_subject = fields.Char(readonly=True, copy=False)
    signer_serial = fields.Char(readonly=True, copy=False)

    _name_document_type_uniq = models.Constraint(
        "unique(name, document_type, company_id)",
        "The document reference must be unique per document type and company.",
    )

    # ------------------------------------------------------------------
    # Defaults and constraints
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        Company = self.env["res.company"]
        for vals in vals_list:
            company = (
                Company.browse(vals["company_id"])
                if vals.get("company_id")
                else self.env.company
            )
            company._od19_etax_check_enabled()
            if not vals.get("name"):
                move = self.env["account.move"].browse(vals.get("move_id"))
                vals["name"] = (move.name if move else False) or self.env._("e-Tax")
        return super().create(vals_list)

    def _ensure_etax_enabled(self):
        """Raise when any record belongs to a company without the feature."""
        for record in self:
            record.company_id._od19_etax_check_enabled()

    @api.depends("document_type", "move_id.dncn")
    def _compute_type_code(self):
        for record in self:
            spec = namespaces.DOCUMENT_TYPES.get(record.document_type, {})
            record.type_code = namespaces.document_type_code(
                record.document_type, record.move_id.dncn
            )
            record.purpose_code = spec.get("purpose_code", False)

    @api.constrains("move_id")
    def _check_move(self):
        for record in self:
            if record.move_id and record.move_id.move_type not in _ALLOWED_MOVE_TYPES:
                raise ValidationError(
                    self.env._(
                        "An e-Tax document can only be issued for a customer "
                        "invoice, credit note or receipt."
                    )
                )

    # ------------------------------------------------------------------
    # Data exposed to the XML builder
    # ------------------------------------------------------------------
    def get_note_text(self):
        """Return the free text reported in ``ExchangedDocument/IncludedNote``."""
        self.ensure_one()
        return self.note or ""

    def _document_lines(self):
        """Return the billable lines of the journal entry."""
        self.ensure_one()
        return self.move_id.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line.quantity
        )

    def _compute_gross_line_total(self):
        """Sum of ``price_unit * quantity`` in document currency."""
        self.ensure_one()
        return sum(
            line.price_unit * line.quantity for line in self._document_lines()
        )

    def _compute_header_allowance(self):
        """Total line discount, i.e. gross line total minus net line total."""
        self.ensure_one()
        lines = self._document_lines()
        gross = sum(line.price_unit * line.quantity for line in lines)
        net = sum(line.price_subtotal for line in lines)
        return max(gross - net, 0.0)

    def _get_certificate(self):
        """Return the certificate to sign with."""
        self.ensure_one()
        certificate = self.certificate_id or self.company_id.od19_etax_certificate_id
        if not certificate:
            raise UserError(
                self.env._(
                    "Please configure an e-Tax signing certificate on company %s "
                    "or on the document.",
                    self.company_id.display_name,
                )
            )
        return certificate

    def _xml_filename(self):
        self.ensure_one()
        return "%s.xml" % re.sub(r"[^A-Za-z0-9._-]+", "_", self.name or "etax")

    def _pdf_filename(self):
        self.ensure_one()
        return "%s.pdf" % re.sub(r"[^A-Za-z0-9._-]+", "_", self.name or "etax")

    # ------------------------------------------------------------------
    # XML generation
    # ------------------------------------------------------------------
    def _build_unsigned_tree(self):
        """Build and validate the unsigned XML tree."""
        self.ensure_one()
        tree = xml_builder.build_unsigned_tree(self)
        try:
            validator.assert_valid(tree, self.document_type)
        except validator.ValidationError as error:
            raise UserError(
                self.env._(
                    "ไฟล์ XML e-Tax ไม่ผ่านการตรวจสอบตาม Schema ของ ETDA "
                    "(ขมธอ.3-2560)\n%s",
                    error,
                )
            ) from error
        return tree

    def action_generate_xml(self):
        """Build the unsigned XML and store it as an attachment."""
        self._ensure_etax_enabled()
        for record in self:
            if record.state == "signed":
                raise UserError(
                    self.env._(
                        "A signed e-Tax document cannot be regenerated. "
                        "It is legally issued; issue a cancellation note "
                        "instead."
                    )
                )
            if record.state == "cancelled":
                raise UserError(
                    self.env._(
                        "A cancelled e-Tax document cannot be regenerated."
                    )
                )
            tree = record._build_unsigned_tree()
            content = etree.tostring(
                tree, xml_declaration=True, encoding="UTF-8", pretty_print=True
            )
            record.write({
                "xml_file": base64.b64encode(content),
                "xml_filename": record._xml_filename(),
                "state": "generated",
            })
        return True

    def action_sign(self):
        """Validate and sign the XML with the configured certificate."""
        self._ensure_etax_enabled()
        for record in self:
            if record.move_id.state != "posted":
                raise UserError(
                    self.env._(
                        "Journal entry %s must be posted before the e-Tax "
                        "document can be signed.",
                        record.move_id.display_name,
                    )
                )
            certificate = record._get_certificate()
            certificate._check_usable()
            tree = record._build_unsigned_tree()
            signed_tree = signer.sign_tree(
                tree,
                certificate._get_signing_key_pem(),
                certificate._get_signing_cert_pem(),
            )
            signed = etree.tostring(
                signed_tree, xml_declaration=True, encoding="UTF-8", pretty_print=True
            )
            errors = validator.validate(signed_tree, record.document_type)
            if errors:
                # The signature is an optional trailing element of the root, so
                # a failure here points at the XAdES extension rather than at
                # the invoice content.  Keep the document but surface it.
                _logger.warning(
                    "Signed e-Tax document %s does not validate: %s",
                    record.name,
                    "; ".join(errors),
                )
            record.write({
                "signed_xml_file": base64.b64encode(signed),
                "signed_xml_filename": record._xml_filename(),
                "digest": hashlib.sha512(signed).hexdigest(),
                "signed_at": fields.Datetime.now(),
                "signer_subject": certificate.subject,
                "signer_serial": certificate.serial_number,
                "state": "signed",
            })
            record.message_post(
                body=self.env._(
                    "Document signed with certificate %s.", certificate.name
                )
            )
        return True

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def _get_report(self):
        self.ensure_one()
        return self.env.ref("od19_etax_invoice.action_report_etax_document")

    def action_generate_pdf(self):
        """Render the printable PDF carrying the signed XML."""
        self._ensure_etax_enabled()
        for record in self:
            report = record._get_report()
            content, report_type = report._render_qweb_pdf(report, record.ids)
            if report_type != "pdf":
                raise UserError(
                    self.env._("The e-Tax report did not produce a PDF document.")
                )
            record.write({
                "pdf_file": base64.b64encode(content),
                "pdf_filename": record._pdf_filename(),
            })
        return True

    def action_print(self):
        """Open the printable e-Tax document."""
        self.ensure_one()
        self._ensure_etax_enabled()
        return self._get_report().report_action(self.ids)

    # ------------------------------------------------------------------
    # RD submission
    # ------------------------------------------------------------------
    def action_submit_to_rd(self):
        """Create a submission for this document and send it to the RD."""
        self.ensure_one()
        self._ensure_etax_enabled()
        if self.state != "signed":
            raise UserError(
                self.env._(
                    "เอกสาร %s ต้องอยู่ในสถานะลงนามแล้วก่อนนำส่งไปยังสรรพากร",
                    self.name,
                )
            )
        submission = self.env["od19.etax.submission"].create({
            "company_id": self.company_id.id,
            "document_ids": [Command.set(self.ids)],
        })
        submission.action_submit()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("RD Submission"),
            "res_model": "od19.etax.submission",
            "res_id": submission.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_cancel(self):
        for record in self:
            if record.state == "signed":
                raise UserError(
                    self.env._(
                        "A signed e-Tax document cannot be cancelled. Issue a "
                        "cancellation note instead."
                    )
                )
            record.state = "cancelled"
        return True

    def action_reset_to_draft(self):
        for record in self:
            if record.state == "signed":
                raise UserError(
                    self.env._("A signed e-Tax document cannot be reset to draft.")
                )
            record.write({
                "state": "draft",
                "xml_file": False,
                "xml_filename": False,
                "signed_xml_file": False,
                "signed_xml_filename": False,
                "digest": False,
            })
        return True

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def get_document_type_label(self):
        """Return the translated label of :attr:`document_type`."""
        self.ensure_one()
        return dict(self._fields["document_type"].selection).get(
            self.document_type, ""
        )

    def get_header_allowance(self):
        """Public wrapper used by the printed report."""
        self.ensure_one()
        return self._compute_header_allowance()

    def _format_local_datetime(self, value):
        """Render a naive UTC datetime in the current user's time zone."""
        if not value:
            return ""
        return fields.Datetime.context_timestamp(self, value).strftime(
            "%d/%m/%Y %H:%M"
        )

    def get_issue_datetime_label(self):
        """Issue date time formatted for the printed report."""
        self.ensure_one()
        return self._format_local_datetime(self.issue_datetime)

    def get_signed_at_label(self):
        """Signing date time formatted for the printed report."""
        self.ensure_one()
        return self._format_local_datetime(self.signed_at)

    def get_qr_payload(self):
        """Compact verification payload encoded in the printed QR code."""
        self.ensure_one()
        partner = self.move_id.commercial_partner_id
        return "|".join(filter(None, [
            self.name or "",
            self.company_id.vat or "",
            partner.vat or "",
            self.move_id.invoice_date.isoformat() if self.move_id.invoice_date else "",
            "%.2f %s" % (self.move_id.amount_total, self.move_id.currency_id.name or ""),
            (self.digest or "")[:32],
        ]))

    def get_qr_data_uri(self):
        """Return the QR code of :meth:`get_qr_payload` as a data URI."""
        self.ensure_one()
        return qr.generate_data_uri(self.get_qr_payload())

    def get_tax_summary(self):
        """Return the VAT breakdown shown on the printed document."""
        self.ensure_one()
        return xml_builder.EtaxXmlBuilder(self)._tax_groups()
