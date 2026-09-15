import base64
import io
import logging

from lxml import etree

from odoo import SUPERUSER_ID, _, api, fields, models, tools
from odoo.tools import cleanup_xml_node
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter
from odoo.tools.xml_utils import dict_to_xml

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import (
    SUPPORTED_FILE_TYPES,
)

_logger = logging.getLogger(__name__)

# Factur-X PDF/A extension schema, as a self-contained <rdf:RDF> block.
# WeasyPrint appends xmp_metadata fragments inside its own <x:xmpmeta> AFTER its
# generated PDF/A identification (pdfaid part/conformance), so this fragment must
# be a complete rdf:RDF of its own — NOT a full <?xml?><x:xmpmeta> packet (that
# would nest and break XMP well-formedness) and NOT bare <rdf:Description>
# elements (they would land outside rdf:RDF). See odoo/tools/pdf and the
# WeasyPrint metadata assembly (pdf/metadata.py). The pdfa identification and
# output intent are emitted natively by WeasyPrint's pdf/a-3b variant.
FACTURX_PDFA_XMP_RDF = b"""<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:about="" xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/" xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#" xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#"><pdfaExtension:schemas><rdf:Bag><rdf:li rdf:parseType="Resource"><pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema><pdfaSchema:namespaceURI>urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#</pdfaSchema:namespaceURI><pdfaSchema:prefix>fx</pdfaSchema:prefix><pdfaSchema:property><rdf:Seq><rdf:li rdf:parseType="Resource"><pdfaProperty:name>DocumentFileName</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>name of the embedded XML invoice file</pdfaProperty:description></rdf:li><rdf:li rdf:parseType="Resource"><pdfaProperty:name>DocumentType</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>INVOICE</pdfaProperty:description></rdf:li><rdf:li rdf:parseType="Resource"><pdfaProperty:name>Version</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>The actual version of the Factur-X XML schema</pdfaProperty:description></rdf:li><rdf:li rdf:parseType="Resource"><pdfaProperty:name>ConformanceLevel</pdfaProperty:name><pdfaProperty:valueType>Text</pdfaProperty:valueType><pdfaProperty:category>external</pdfaProperty:category><pdfaProperty:description>The conformance level of the embedded Factur-X data</pdfaProperty:description></rdf:li></rdf:Seq></pdfaSchema:property></rdf:li></rdf:Bag></pdfaExtension:schemas></rdf:Description><rdf:Description rdf:about="" xmlns:fx="urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#"><fx:ConformanceLevel>EN 16931</fx:ConformanceLevel><fx:DocumentFileName>factur-x.xml</fx:DocumentFileName><fx:DocumentType>INVOICE</fx:DocumentType><fx:Version>1.0</fx:Version></rdf:Description></rdf:RDF>"""


class MixinAccountMoveSend(models.AbstractModel):
    _inherit = "mixin.account.move.send"

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)

        peppol_formats = set(self.env["res.partner"]._get_peppol_formats())
        if peppol_format_moves := moves.filtered(
            lambda m: moves_data[m]["invoice_edi_format"] in peppol_formats
        ):
            not_configured_company_partners = (
                peppol_format_moves.company_id.partner_id.filtered(
                    lambda partner: not (partner.peppol_eas and partner.peppol_endpoint)
                )
            )
            if not_configured_company_partners:
                alerts["account_edi_ubl_cii_configure_company"] = {
                    "message": _(
                        "Please fill in your company's VAT or Peppol Address to generate a complete XML file."
                    ),
                    "level": "info",
                    "action_text": _("Configure"),
                    "action": not_configured_company_partners._get_records_action(),
                }
            not_configured_partners = (
                peppol_format_moves.partner_id.commercial_partner_id.filtered(
                    lambda partner: not (partner.peppol_eas and partner.peppol_endpoint)
                )
            )
            if not_configured_partners:
                alerts["account_edi_ubl_cii_configure_partner"] = {
                    "message": _("Please fill in partner's VAT or Peppol Address."),
                    "level": "info",
                    "action_text": _("View Partner(s)"),
                    "action": not_configured_partners._get_records_action(
                        name=_("Check Partner(s)")
                    ),
                }

            if any(
                self.env["account.edi.xml.ubl_bis3"]._is_customer_behind_chorus_pro(
                    partner
                )
                for partner in peppol_format_moves.partner_id.commercial_partner_id
            ):
                chorus_pro = (
                    self.env["ir.module.module"]
                    .sudo()
                    .search([("name", "=", "l10n_fr_facturx_chorus_pro")], limit=1)
                )
                if chorus_pro and chorus_pro.state != "installed":
                    alerts["account_edi_ubl_cii_chorus_pro_install"] = {
                        "message": _(
                            "Please install the french Chorus pro module to have all the specific rules."
                        ),
                        "level": "info",
                        "action": chorus_pro._get_records_action(),
                        "action_text": _("Install Chorus Pro"),
                    }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.ubl_cii_xml_id

    def _prepare_mail_attachment_placeholders(
        self, move, invoice_edi_format=None, extra_edis=None, pdf_report=None
    ):
        # EXTENDS 'account'
        results = super()._prepare_mail_attachment_placeholders(
            move,
            invoice_edi_format=invoice_edi_format,
            extra_edis=extra_edis,
            pdf_report=pdf_report,
        )
        if move._is_ubl_cii_xml_required(invoice_edi_format):
            builder = move.partner_id.commercial_partner_id._get_edi_builder(
                invoice_edi_format
            )
            filename = builder._export_invoice_filename(move)
            results.append(
                {
                    "id": f"placeholder_{filename}",
                    "name": filename,
                    "mimetype": "application/xml",
                    "placeholder": True,
                }
            )
        return results

    @api.model
    def _display_attachments_widget(self, edi_format, sending_methods):
        ubl_format_info = self.env["res.partner"]._get_ubl_cii_formats_info()
        return super()._display_attachments_widget(
            edi_format, sending_methods
        ) or ubl_format_info.get(edi_format, {}).get("embed_attachments")

    @api.model
    def _get_ubl_available_attachments(
        self, mail_attachments_widget, invoice_edi_format
    ):
        if not invoice_edi_format or not mail_attachments_widget:
            return self.env["ir.attachment"], self.env["ir.attachment"]
        attachment_ids = [
            values["id"] for values in mail_attachments_widget if values.get("manual")
        ]
        attachments = self.env["ir.attachment"].browse(attachment_ids)

        ubl_format_info = (
            self.env["res.partner"]
            ._get_ubl_cii_formats_info()
            .get(invoice_edi_format, {})
        )
        if not ubl_format_info.get("embed_attachments"):
            return self.env["ir.attachment"], attachments

        accepted_attachments = attachments.filtered(
            lambda attachment: attachment.mimetype in SUPPORTED_FILE_TYPES
        )
        return accepted_attachments, attachments - accepted_attachments

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if invoice._is_ubl_cii_xml_required(invoice_data["invoice_edi_format"]):
            builder = invoice.partner_id.commercial_partner_id._get_edi_builder(
                invoice_data["invoice_edi_format"]
            )
            xml_content, errors = builder.with_context(
                from_peppol="peppol" in invoice_data["sending_methods"]
            )._export_invoice(invoice)
            filename = builder._export_invoice_filename(invoice)

            # Failed.
            if errors:
                invoice_data["error"] = {
                    "error_title": _(
                        "Errors occurred while creating the EDI document (format: %s):",
                        builder._description,
                    ),
                    "errors": errors,
                }
                invoice_data["error_but_continue"] = True
            else:
                invoice_data["ubl_cii_xml_attachment_values"] = {
                    "name": filename,
                    "raw": xml_content,
                    "mimetype": "application/xml",
                    "res_model": invoice._name,
                    "res_id": invoice.id,
                    "res_field": "ubl_cii_xml_file",  # Binary field
                }
                invoice_data["ubl_cii_xml_options"] = {
                    "ubl_cii_format": invoice_data["invoice_edi_format"],
                    "builder": builder,
                }

    def _get_invoice_pdf_render_options(self, invoice, invoice_data):
        # EXTENDS 'account'
        # For Factur-X, render the invoice PDF natively as PDF/A-3b with the CII
        # XML embedded (relationship "Data") and the Factur-X XMP extension
        # schema, in one WeasyPrint pass. This replaces the old post-processing
        # (pypdf attach + convert_to_pdfa), which produced invalid PDF/A on
        # WeasyPrint output.
        options = super()._get_invoice_pdf_render_options(invoice, invoice_data)
        xml_options = invoice_data.get("ubl_cii_xml_options") or {}
        # Under test_enable the PDF path is normally stubbed, so skip the native
        # PDF/A render unless a test explicitly forces real rendering.
        renders_pdf = not tools.config["test_enable"] or self.env.context.get(
            "force_report_rendering"
        )
        if (
            renders_pdf
            and xml_options.get("ubl_cii_format") == "facturx"
            and invoice_data.get("ubl_cii_xml_attachment_values")
        ):
            invoice_data["facturx_pdfa_native"] = True
            options = {
                **options,
                "pdf_variant": "pdf/a-3b",
                "attachments": [
                    {
                        "content": invoice_data["ubl_cii_xml_attachment_values"]["raw"],
                        "name": "factur-x.xml",
                        "description": "Factur-X invoice",
                        "relationship": "Data",
                    }
                ],
                "xmp_metadata": [FACTURX_PDFA_XMP_RDF],
            }
        return options

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)

        # Add PDF to XML
        if (
            "ubl_cii_xml_options" in invoice_data
            and invoice_data["ubl_cii_xml_options"]["ubl_cii_format"] != "facturx"
        ):
            self._postprocess_invoice_ubl_xml(invoice, invoice_data)

        # Always silently generate a Factur-X and embed it inside the PDF for inter-portability
        if (
            invoice_data.get("ubl_cii_xml_options", {}).get("ubl_cii_format")
            == "facturx"
        ):
            xml_facturx = invoice_data["ubl_cii_xml_attachment_values"]["raw"]
        else:
            xml_facturx = self.env["account.edi.xml.cii"]._export_invoice(invoice)[0]

        # during tests, PDF rendering is skipped — create the attachment directly
        if tools.config["test_enable"]:
            self.env["ir.attachment"].sudo().create(
                {
                    "name": "factur-x.xml",
                    "raw": xml_facturx,
                    "res_id": invoice.id,
                    "res_model": "account.move",
                }
            )
            return

        # Factur-X invoices are rendered natively as PDF/A-3b with the CII XML
        # already embedded and the Factur-X XMP schema in place (see
        # _get_invoice_pdf_render_options). The pypdf attach + convert_to_pdfa
        # post-processing below is then unnecessary AND unsafe: a pypdf
        # round-trip strips the PDF/A output intent, trailer ID and XMP,
        # invalidating conformance.
        if invoice_data.pop("facturx_pdfa_native", False):
            return

        # Read pdf content.
        pdf_values = (
            (
                not self.env.context.get("custom_template_facturx")
                and invoice.invoice_pdf_report_id
            )
            or invoice_data.get("pdf_attachment_values")
            or invoice_data["proforma_pdf_attachment_values"]
        )
        reader_buffer = io.BytesIO(pdf_values["raw"])
        reader = OdooPdfFileReader(reader_buffer, strict=False)

        # Post-process.
        writer = OdooPdfFileWriter()
        writer.clone_reader_document_root(reader)

        writer.add_attachment("factur-x.xml", xml_facturx, subtype="text/xml")

        # PDF-A.
        if (
            invoice_data.get("ubl_cii_xml_options", {}).get("ubl_cii_format")
            == "facturx"
            and not writer.is_pdfa
        ):
            try:
                writer.convert_to_pdfa()
            except Exception:
                _logger.exception("Error while converting to PDF/A")

            # Extra metadata to be Factur-x PDF-A compliant.
            content = self.env["ir.qweb"]._render(
                "account_edi_ubl_cii.account_invoice_pdfa_3_facturx_metadata",
                {
                    "title": invoice.name,
                    "date": fields.Date.context_today(self),
                },
            )
            if "<pdfaid:conformance>B</pdfaid:conformance>" in content:
                content.replace(
                    "<pdfaid:conformance>B</pdfaid:conformance>",
                    "<pdfaid:conformance>A</pdfaid:conformance>",
                )
            writer.add_file_metadata(content.encode())

        # Replace the current content.
        writer_buffer = io.BytesIO()
        writer.write(writer_buffer)
        pdf_values["raw"] = writer_buffer.getvalue()
        reader_buffer.close()
        writer_buffer.close()

    @api.model
    def _postprocess_invoice_ubl_xml(self, invoice, invoice_data):
        """
        Include the PDF in the UBL as an AdditionalDocumentReference element.

        According to UBL 2.1 standard, the AdditionalDocumentReference element should be
        placed above ProjectReference which isn't usually in xml files.
        So usually it's set above AccountingSupplierParty. Here, we try to find a suitable anchor point among
        the available element to insert our PDF attachment. If none of these are found, we
        skip adding the attachment to avoid breaking the XML structure.
        Inside CreditNote, the ProjectReference element is not used in xml.
        So we look for OriginatorDocumentReference instead.
        """
        tree = etree.fromstring(invoice_data["ubl_cii_xml_attachment_values"]["raw"])

        localname = etree.QName(tree).localname
        anchor_xpath = {
            "Invoice": "//*[local-name()='ProjectReference' or local-name()='Signature' or local-name()='AccountingSupplierParty']",
            "CreditNote": "//*[local-name()='StatementDocumentReference' or local-name()='OriginatorDocumentReference' or local-name()='Signature' or local-name()='AccountingSupplierParty']",
            "DebitNote": "//*[local-name()='Signature' or local-name()='AccountingSupplierParty']",
        }.get(localname)

        anchor_elements = tree.xpath(anchor_xpath)

        if not anchor_elements:
            return

        anchor_index = tree.index(anchor_elements[0])
        pdf_values = (
            invoice.invoice_pdf_report_id
            or invoice_data.get("pdf_attachment_values")
            or invoice_data["proforma_pdf_attachment_values"]
        )

        edi_model = invoice_data["ubl_cii_xml_options"]["builder"]
        doc_type_code_node = edi_model._get_document_type_code_node(
            invoice, invoice_data
        )
        vals = {"invoice": invoice}
        edi_model._add_invoice_config_vals(vals)
        nsmap = edi_model._get_document_nsmap(vals)

        attachments_to_embed = (
            [
                {
                    "filename": attachment.name,
                    "raw": attachment.raw,
                    "mimetype": attachment.mimetype,
                }
                for attachment in self._get_ubl_available_attachments(
                    invoice_data["mail_attachments_widget"],
                    invoice_data["invoice_edi_format"],
                )[0]
            ]
            if invoice_data.get("mail_attachments_widget")
            else []
        )
        attachments_to_embed.append(
            {
                "filename": pdf_values["name"],
                "raw": pdf_values["raw"],
                "mimetype": pdf_values["mimetype"],
                "document_type_node": doc_type_code_node,
            }
        )

        for attachment_values in attachments_to_embed:
            additional_document_reference_node = {
                "_tag": "cac:AdditionalDocumentReference",
                "cbc:ID": {"_text": attachment_values["filename"]},
                "cbc:DocumentTypeCode": attachment_values.get("document_type_node"),
                "cac:Attachment": {
                    "cbc:EmbeddedDocumentBinaryObject": {
                        "_text": base64.b64encode(attachment_values["raw"]).decode(),
                        "mimeCode": attachment_values["mimetype"],
                        "filename": attachment_values["filename"],
                    }
                },
            }
            tree.insert(
                anchor_index,
                dict_to_xml(additional_document_reference_node, nsmap=nsmap),
            )

        invoice_data["ubl_cii_xml_attachment_values"]["raw"] = etree.tostring(
            cleanup_xml_node(tree), xml_declaration=True, encoding="UTF-8"
        )

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        attachments_vals = [
            invoice_data.get("ubl_cii_xml_attachment_values")
            for invoice_data in invoices_data.values()
            if invoice_data.get("ubl_cii_xml_attachment_values")
        ]
        if attachments_vals:
            attachments = (
                self.env["ir.attachment"]
                .with_user(SUPERUSER_ID)
                .create(attachments_vals)
            )
            res_ids = attachments.mapped("res_id")
            self.env["account.move"].browse(res_ids).invalidate_recordset(
                fnames=["ubl_cii_xml_id", "ubl_cii_xml_file"]
            )
