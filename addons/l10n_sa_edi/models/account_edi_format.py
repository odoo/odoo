import logging

from markupsafe import Markup
from hashlib import sha256
from base64 import b64decode, b64encode
from lxml import etree
from datetime import datetime
from odoo import models, fields, _, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    """
        Once the journal has been successfully onboarded, we can clear/report invoices through the ZATCA API:
            A) STANDARD Invoice:
                Make a call to the Clearance API '/invoices/clearance/single'.
                This will validate the invoice, sign it and apply a QR code then return the result.
            B) SIMPLIFIED Invoice:
                Make a call to the Reporting API '/invoices/reporting/single'.
                This will validate the invoice then return the result.
        The X509 Certificate and password from the PCSID API need to be provided in the request headers.
    """

    # ====== Helper Functions =======

    def _l10n_sa_get_zatca_datetime(self, timestamp):
        return fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), timestamp)

    def _l10n_sa_xml_node_content(self, root, xpath, namespaces=None):
        namespaces = namespaces or self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_get_namespaces()
        return etree.tostring(root.xpath(xpath, namespaces=namespaces)[0], with_tail=False,
                              encoding='utf-8', method='xml')

    # ====== Xades Signing =======

    @api.model
    def _l10n_sa_get_digital_signature(self, company_id, invoice_hash):
        """
            Generate an ECDSA SHA256 digital signature for the XML eInvoice
        """
        decoded_hash = b64decode(invoice_hash).decode()
        return company_id.sudo().l10n_sa_private_key_id._sign(decoded_hash, formatting='base64')

    def _l10n_sa_calculate_signed_properties_hash(self, issuer_name, serial_number, signing_time, public_key):
        """
            Calculate the SHA256 value of the SignedProperties XML node. The algorithm used by ZATCA expects the indentation
            of the nodes to start with 40 spaces, except for the root SignedProperties node.
        """
        signed_properties = etree.fromstring(self.env['ir.qweb']._render('l10n_sa_edi.export_sa_zatca_ubl_signed_properties', {
            'issuer_name': issuer_name,
            'serial_number': serial_number,
            'signing_time': signing_time,
            'public_key_hashing': public_key,
        }))
        etree.indent(signed_properties, space='    ')
        signed_properties_split = etree.tostring(signed_properties).decode().split('\n')
        signed_properties_final = ""
        for index, line in enumerate(signed_properties_split):
            if index == 0:
                signed_properties_final += line
            else:
                signed_properties_final += (' ' * 36) + line
            if index != len(signed_properties_final) - 1:
                signed_properties_final += '\n'
        signed_properties_final = etree.tostring(etree.fromstring(signed_properties_final))
        return b64encode(sha256(signed_properties_final).hexdigest().encode()).decode()

    def _l10n_sa_sign_xml(self, xml_content, certificate, signature):
        """
            Function that signs XML content of a UBL document with a provided B64 encoded X509 certificate
        """
        root = etree.fromstring(xml_content)
        etree.indent(root, space='    ')

        def _set_content(xpath, content):
            node = root.xpath(xpath)[0]
            node.text = content

        der_cert = certificate._get_der_certificate_bytes(formatting='base64')

        issuer_name = certificate._l10n_sa_get_issuer_name()
        serial_number = certificate.serial_number
        signing_time = self._l10n_sa_get_zatca_datetime(datetime.now()).strftime('%Y-%m-%dT%H:%M:%SZ')
        public_key_hashing = b64encode(sha256(der_cert).hexdigest().encode()).decode()

        signed_properties_hash = self._l10n_sa_calculate_signed_properties_hash(issuer_name, serial_number,
                                                                                signing_time, public_key_hashing)

        _set_content("//*[local-name()='X509IssuerName']", issuer_name)
        _set_content("//*[local-name()='X509SerialNumber']", serial_number)
        _set_content("//*[local-name()='SignedSignatureProperties']/*[local-name()='SigningTime']", signing_time)
        _set_content("//*[local-name()='SignedSignatureProperties']//*[local-name()='DigestValue']", public_key_hashing)

        prehash_content = etree.tostring(root)
        invoice_hash = self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_generate_invoice_xml_hash(prehash_content,
                                                                                                   'digest')

        _set_content("//*[local-name()='SignatureValue']", signature)
        _set_content("//*[local-name()='X509Certificate']", der_cert.decode())
        _set_content("//*[local-name()='SignatureInformation']//*[local-name()='DigestValue']", invoice_hash)
        _set_content("//*[@URI='#xadesSignedProperties']/*[local-name()='DigestValue']", signed_properties_hash)

        return etree.tostring(root, with_tail=False)

    def _l10n_sa_assert_clearance_status(self, invoice, clearance_data):
        """
            Assert Clearance status. To be overridden in case there are any other cases to be accounted for
        """
        mode = 'reporting' if invoice._l10n_sa_is_simplified() else 'clearance'
        if mode == 'clearance' and clearance_data.get('clearanceStatus', '') != 'CLEARED':
            return {'error': _("Invoice could not be cleared:\n%s", clearance_data), 'blocking_level': 'error'}
        elif mode == 'reporting' and clearance_data.get('reportingStatus', '') != 'REPORTED':
            return {'error': _("Invoice could not be reported:\n%s", clearance_data), 'blocking_level': 'error'}
        return clearance_data

    # ====== UBL Document Rendering & Submission =======

    def _l10n_sa_postprocess_zatca_template(self, xml_content):
        """
            Post-process xml content generated according to the ZATCA UBL specifications. Specifically, this entails:
                -   Force the xmlns:ext namespace on the root element (Invoice). This is required, since, by default
                    the generated UBL file does not have any ext namespaced element, so the namespace is removed
                    since it is unused.
        """

        # Append UBLExtensions to the XML content
        ubl_extensions = etree.fromstring(self.env['ir.qweb']._render('l10n_sa_edi.export_sa_zatca_ubl_extensions'))
        root = etree.fromstring(xml_content)
        root.insert(0, ubl_extensions)

        # Force xmlns:ext namespace on UBl file
        ns_map = {'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'}
        etree.cleanup_namespaces(root, top_nsmap=ns_map, keep_ns_prefixes=['ext'])

        return etree.tostring(root, with_tail=False).decode()

    def _l10n_sa_generate_zatca_template(self, invoice):
        """
            Render the ZATCA UBL file
        """
        xml_content, errors = self.env['account.edi.xml.ubl_21.zatca']._export_invoice(invoice)
        if errors:
            return {
                'error': _("Could not generate Invoice UBL content: %s", ", \n".join(errors)),
                'blocking_level': 'error'
            }
        return self._l10n_sa_postprocess_zatca_template(xml_content)

    def _l10n_sa_submit_einvoice(self, invoice, signed_xml, PCSID_data):
        """
            Submit a generated Invoice UBL file by making calls to the following APIs:
                -   A. Clearance API: Submit a standard Invoice to ZATCA for validation, returns signed UBL
                -   B. Reporting API: Submit a simplified Invoice to ZATCA for validation
        """
        clearance_data = invoice.journal_id._l10n_sa_api_clearance(invoice, signed_xml.decode(), PCSID_data)
        if error := clearance_data.get('json_errors'):
            error_msg = ''
            if status_code := error.get('status_code'):
                error_msg = Markup("<b>[%s] </b>") % status_code

            is_warning = True
            validation_results = error.get('validationResults', {})
            for err in validation_results.get('warningMessages', []):
                error_msg += Markup('<b>%s</b> : %s <br/>') % (err['code'], err['message'])
            for err in validation_results.get('errorMessages', []):
                is_warning = False
                error_msg += Markup('<b>%s</b> : %s <br/>') % (err['code'], err['message'])
            return {
                'error': error_msg,
                'rejected': not is_warning,
                'response': signed_xml.decode(),
                'blocking_level': 'warning' if is_warning else 'error',
                'status_code': status_code,
            }
        if not clearance_data.get('error'):
            return self._l10n_sa_assert_clearance_status(invoice, clearance_data)
        return clearance_data

    def _l10n_sa_postprocess_einvoice_submission(self, invoice, signed_xml, clearance_data):
        """
            Once an invoice has been successfully submitted, it is returned as a Cleared invoice, on which data
            from ZATCA was applied. To be overridden to account for other cases, such as Reporting.
        """
        if invoice._l10n_sa_is_simplified():
            # if invoice is B2C, it is a SIMPLIFIED invoice, and thus it is only reported and returns
            # no signed invoice. In this case, we just return the original content
            return signed_xml.decode()
        return b64decode(clearance_data['clearedInvoice']).decode()

    def _l10n_sa_apply_qr_code(self, invoice, xml_content):
        """
            Apply QR code on Invoice UBL content
        """
        root = etree.fromstring(xml_content)
        qr_code = invoice.l10n_sa_qr_code_str
        qr_node = root.xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
        qr_node.text = qr_code
        return etree.tostring(root, with_tail=False)

    def _l10n_sa_get_signed_xml(self, invoice, unsigned_xml, certificate):
        """
            Helper method to sign the provided XML, apply the QR code in the case if Simplified invoices (B2C), then
            return the signed XML
        """
        signed_xml = self._l10n_sa_sign_xml(unsigned_xml, certificate, invoice.l10n_sa_invoice_signature)
        if invoice._l10n_sa_is_simplified():
            # Applying with_prefetch() to set the _prefetch_ids = _ids,
            # preventing premature QR code computation for other invoices.
            invoice = invoice.with_prefetch()
            return self._l10n_sa_apply_qr_code(invoice, signed_xml)
        return signed_xml

    def _l10n_sa_export_zatca_invoice(self, invoice, xml_content=None):
        """
            Generate a ZATCA compliant UBL file, make API calls to authenticate, sign and include QR Code and
            Cryptographic Stamp, then create an attachment with the final contents of the UBL file
        """
        self.ensure_one()

        # Prepare UBL invoice values and render XML file
        unsigned_xml = xml_content or self._l10n_sa_generate_zatca_template(invoice)

        # Load PCISD data and certificate
        try:
            PCSID_data, certificate = invoice.journal_id._l10n_sa_api_get_pcsid()
        except UserError as e:
            return ({
                'error': e.args[0],
                'blocking_level': 'error',
                'response': unsigned_xml
            }, unsigned_xml)

        certificate_sudo = self.env['certificate.certificate'].sudo().browse(certificate)

        # Apply Signature/QR code on the generated XML document
        try:
            signed_xml = self._l10n_sa_get_signed_xml(invoice, unsigned_xml, certificate_sudo)
        except UserError:
            return ({
                'error': _("Something went wrong. Please retry, and if that does not work, then onboard the journal again."),
                'blocking_level': 'error',
                'response': unsigned_xml
            }, unsigned_xml)

        # Once the XML content has been generated and signed, we submit it to ZATCA
        return self._l10n_sa_submit_einvoice(invoice, signed_xml, PCSID_data), signed_xml

    def _l10n_sa_check_seller_missing_info(self, invoice):
        """
            Helper function to check if ZATCA mandated partner fields are missing for the seller
        """
        partner_id = invoice.company_id.partner_id.commercial_partner_id
        missing_fields = []
        if not partner_id.state_id:
            missing_fields.append(_('State'))
        if not partner_id.city:
            missing_fields.append(_('City'))
        return missing_fields

    def _l10n_sa_check_buyer_missing_info(self, invoice):
        """
            Helper function to check if ZATCA mandated partner fields are missing for the buyer
        """
        partner_id = invoice.commercial_partner_id
        missing = []
        identification_scheme = partner_id.l10n_sa_edi_additional_identification_scheme
        if (
            any(
                tax.l10n_sa_exemption_reason_code in ('VATEX-SA-HEA', 'VATEX-SA-EDU')
                for tax in invoice.invoice_line_ids.filtered(
                    lambda line: line.display_type == 'product'
                ).tax_ids
            )
            and (
                identification_scheme != 'NAT'
                or not partner_id.l10n_sa_edi_additional_identification_number
            )
        ):
            missing.append(_("""
                Please set the Identification Scheme as National ID and Identification Number as the respective
                number on the Customer, as the Tax Exemption Reason is set either as VATEX-SA-HEA or VATEX-SA-EDU
            """))
        if identification_scheme == 'TIN' and not partner_id.vat:
            missing.append(_("Please set the VAT Number as the Identification Scheme is Tax Identification Number"))
        return missing

    def _l10n_sa_post_zatca_edi(self, invoice):  # no batch ensure that there is only one invoice
        """
            Post invoice to ZATCA and return a dict of invoices and their success/attachment
        """

        # Chain integrity check: chain head must have been REALLY posted, and did not time out
        # When a submission times out, we reset the chain index of the invoice to False, so it has to be submitted again
        # According to ZATCA, if we end up submitting the same invoice more than once, they will directly reach out
        # to the taxpayer for clarifications
        chain_head = invoice.journal_id._l10n_sa_get_last_posted_invoice()
        if chain_head and chain_head != invoice and not chain_head._l10n_sa_is_in_chain():
            invoice.l10n_sa_edi_chain_head_id = chain_head
            return {invoice: {
                'error': _("Error: This invoice is blocked due to %s. Please check it.", chain_head.name),
                'blocking_level': 'error',
                'response': None,
            }}

        xml_content = None
        if not invoice.l10n_sa_chain_index:
            # If the Invoice doesn't have a chain index, it means it either has not been submitted before,
            # or it was submitted and rejected. Either way, we need to assign it a new Chain Index and regenerate
            # the data that depends on it before submitting (UUID, XML content, signature)
            invoice.l10n_sa_chain_index = invoice.journal_id._l10n_sa_edi_get_next_chain_index()
            xml_content = invoice._l10n_sa_generate_unsigned_data()

        # Generate Invoice name for attachment
        attachment_name = self.env['account.edi.xml.ubl_21.zatca']._export_invoice_filename(invoice)

        # Generate XML, sign it, then submit it to ZATCA
        response_data, submitted_xml = self._l10n_sa_export_zatca_invoice(invoice, xml_content)

        # Check for submission errors
        if response_data.get('error'):

            # If the request was rejected, we save the signed xml content as an attachment
            if response_data.get('rejected'):
                invoice._l10n_sa_log_results(submitted_xml, response_data, error=True)

            # If the request returned an exception (Timeout, ValueError... etc.) it means we're not sure if the
            # invoice was successfully cleared/reported, and thus we keep the Index Chain.
            # Else, we recalculate the submission Index (ICV), UUID, XML content and Signature
            if not response_data.get('excepted'):
                invoice.l10n_sa_chain_index = False

            return {
                invoice: {
                    **response_data,
                    'response': submitted_xml
                }
            }

        # Once submission is done with no errors, check submission status
        cleared_xml = self._l10n_sa_postprocess_einvoice_submission(invoice, submitted_xml, response_data)

        # Set 'l10n_sa_edi_is_production' to True upon the first invoice submission in Production mode
        if not invoice.company_id.l10n_sa_edi_is_production:
            invoice.company_id.l10n_sa_edi_is_production = invoice.company_id.l10n_sa_api_mode == 'prod'

        # Save the submitted/returned invoice XML content once the submission has been completed successfully
        invoice._l10n_sa_log_results(cleared_xml.encode(), response_data)
        invoice.journal_id._l10n_sa_reset_chain_head_error()
        return {
            invoice: {
                'success': True,
                'response': cleared_xml,
                'message': '',
                'attachment': self.env['ir.attachment'].create({
                    'name': attachment_name,
                    'raw': cleared_xml.encode(),
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'mimetype': 'application/xml'
                })
            }
        }

    # ====== EDI Format Overrides =======

    def _is_required_for_invoice(self, invoice):
        """
            Override to add ZATCA edi checks on required invoices
        """
        self.ensure_one()
        if self.code != 'sa_zatca':
            return super()._is_required_for_invoice(invoice)

        return invoice.is_sale_document() and invoice.country_code == 'SA'

    def _check_move_configuration(self, invoice):
        """
            Override to add ZATCA compliance checks on the Invoice
        """

        journal = invoice.journal_id
        company = invoice.company_id

        errors = super()._check_move_configuration(invoice)
        if self.code != 'sa_zatca' or company.country_id.code != 'SA':
            return errors

        if invoice.commercial_partner_id == invoice.company_id.partner_id.commercial_partner_id:
            errors.append(_("- Invoice cannot be posted as the Supplier and Buyer are the same."))

        if not all(line.tax_ids for line in invoice.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and line._check_edi_line_tax_required())):
            errors.append(_("- Invoice lines need at least one tax. Please input it and try again."))

        if not journal._l10n_sa_ready_to_submit_einvoices():
            errors.append(_("- The Journal (%s) is not onboarded yet. Please onboard it and try again.", journal.name))

        if not company._l10n_sa_check_organization_unit():
            errors.append(_("- Please set the VAT Number on the Company to be 15 digits, with first and last digits being 3."))
        if not company.sudo().l10n_sa_private_key_id:
            errors.append(_("- Something went wrong. Please onboard the journal again."))

        supplier_missing_info = self._l10n_sa_check_seller_missing_info(invoice)
        customer_missing_info = self._l10n_sa_check_buyer_missing_info(invoice)

        if supplier_missing_info:
            errors.append(
                _(
                    "- Please set the following fields on the %(company_name)s: %(missing_fields)s",
                    company_name=company.name,
                    missing_fields=", ".join(supplier_missing_info),
                )
            )
        if customer_missing_info:
            errors.append(
                _(
                    "- %(missing_info)s",
                    missing_info=", ".join(customer_missing_info),
                )
            )
        if invoice.invoice_date > fields.Date.context_today(self.with_context(tz='Asia/Riyadh')):
            errors.append(_("- Please set the Invoice Date to be either less than or equal to today."))

        if invoice.l10n_sa_show_reason and not invoice.l10n_sa_reason:
            errors.append(_("- Please make sure the 'ZATCA Reason' for the issuance of the Credit/Debit Note is specified."))
        if invoice.l10n_sa_show_reason and not invoice._l10n_sa_check_billing_reference():
            errors.append(_("- Please make sure the 'Customer Reference' contains the sequential number of the original invoice(s) that the Credit/Debit Note is related to."))
        return errors

    def _needs_web_services(self):
        """
            Override to add a check on edi document format code
        """
        self.ensure_one()
        return self.code == 'sa_zatca' or super()._needs_web_services()

    def _is_compatible_with_journal(self, journal):
        """
            Override to add a check on journal type & country code (SA)
        """
        self.ensure_one()
        if self.code != 'sa_zatca':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'SA'

    def _l10n_sa_get_invoice_content_edi(self, invoice):
        """
            Return contents of the submitted UBL file or generate it if the invoice has not been submitted yet
        """
        doc = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'sa_zatca' and d.state == 'sent')
        return doc.attachment_id.raw or self._l10n_sa_generate_zatca_template(invoice).encode()

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != 'sa_zatca' or move.country_code != 'SA' or move.move_type not in ('out_invoice', 'out_refund'):
            return super()._get_move_applicability(move)

        return {
            'post': self._l10n_sa_post_zatca_edi,
            'edi_content': self._l10n_sa_get_invoice_content_edi,
        }

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        """
        Prepare invoice report to be printed.
        :param pdf_writer: The pdf writer with the invoice pdf content loaded.
        :param edi_document: The edi document to be added to the pdf file.
        """
        self.ensure_one()
        super()._prepare_invoice_report(pdf_writer, edi_document)
        if self.code != 'sa_zatca' or edi_document.move_id.country_code != 'SA':
            return

        attachment = edi_document.sudo().attachment_id
        if not attachment or not attachment.datas:
            _logger.warning("No attachment found for invoice %s", edi_document.move_id.name)
            return

        xml_content = attachment.raw
        file_name = attachment.name

        pdf_writer.addAttachment(file_name, xml_content, subtype='text/xml')
        if not pdf_writer.is_pdfa:
            try:
                pdf_writer.convert_to_pdfa()
            except Exception:
                _logger.exception("Error while converting to PDF/A")
            content = self.env['ir.qweb']._render(
                'account_edi_ubl_cii.account_invoice_pdfa_3_facturx_metadata',
                {
                    'title': edi_document.move_id.name,
                    'date': fields.Date.context_today(self),
                },
            )
            pdf_writer.add_file_metadata(content.encode())
