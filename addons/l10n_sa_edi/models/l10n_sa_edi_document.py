from base64 import b64decode, b64encode
from datetime import datetime
from hashlib import sha256

from lxml import etree
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import LockError, UserError
from odoo.tools import float_repr
from odoo.tools.xml_utils import find_xml_value

L10N_SA_DOCUMENT_STATES = [
    ('to_send', "To Send"),
    ('accepted', "Accepted"),
    ('warning', "Accepted (warning(s))"),
    ('rejected', "Rejected"),
    ('error', "Error"),
    ('unknown', "Unknown"),
]


class L10nSaEdiDocument(models.Model):
    _name = 'l10n_sa_edi.document'
    _description = 'ZATCA Document'

    name = fields.Char(related='attachment_id.name')
    res_model = fields.Selection([
        ('account.move', "Journal Entry"),
        ('pos.order', "POS Order"),
    ], string="Invoice Type", readonly=True, required=True)
    res_id = fields.Many2oneReference(model_field="res_model", readonly=True, required=True)
    attachment_id = fields.Many2one(comodel_name='ir.attachment', readonly=True)
    state = fields.Selection(string="ZATCA State", readonly=True, selection=L10N_SA_DOCUMENT_STATES)
    message = fields.Html("ZATCA Errors/Warnings", translate=True, help="Detailed Errors/Warnings")
    content = fields.Binary(compute="_compute_content")
    l10n_sa_edi_chain_head_id = fields.Many2one(
        comodel_name='l10n_sa_edi.document',
        string="ZATCA chain stopping document",
        copy=False,
        readonly=True,
        help="Technical field to know if the chain has been stopped by a previous invoice",
    )
    l10n_sa_chain_index = fields.Integer(
        string="ZATCA chain index", copy=False, readonly=True,
        help="Invoice index in chain, set if and only if an in-chain XML was submitted and did not error",
    )
    l10n_sa_edi_log_ids = fields.One2many(comodel_name="l10n_sa_edi.log", inverse_name="l10n_sa_edi_document_id")
    company_id = fields.Many2one(comodel_name="res.company", required=True)
    journal_id = fields.Many2one(comodel_name="account.journal", required=True)
    account_move_id = fields.Many2one('account.move', compute='_compute_resource')

    _unique_record = models.Constraint(
        'unique(res_model, res_id)',
        "Only one ZATCA document can be linked to a record!",
    )

    def _l10n_sa_get_resource_field_mapping(self):
        return {
            'account.move': 'account_move_id',
        }

    def _compute_content(self):
        """contents of the submitted UBL file or generate it if the invoice has not been submitted yet"""
        for record in self:
            attachment_id = record.state in ('accepted', 'warning') and record.attachment_id
            record.content = attachment_id.raw if attachment_id else record.resource._l10n_sa_generate_zatca_template().encode()

    @api.depends('res_id', 'res_model')
    def _compute_resource(self):
        """
        Assign the field based on the res_model equivalent to:
        match record.res_model:
        case 'account_move':
            record.account_move_id = record.res_id
        case ...:
            ...
        record.write({
            'pos_order_id': False,
            ...
        })
        """
        for record in self:
            field = self._l10n_sa_get_resource_field_mapping()[record.res_model]
            other_fields = set(self._l10n_sa_get_resource_field_mapping().values()) - {field}
            record[field] = record.res_id
            for field in other_fields:
                record[field] = False

    @property
    def resource(self):
        return self[self._l10n_sa_get_resource_field_mapping()[self.res_model]]

    # ====== Helper Functions =======

    @api.model
    def _l10n_sa_get_zatca_datetime(self, timestamp):
        return fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), timestamp)

    # ====== Xades Signing =======

    @api.model
    def _l10n_sa_get_digital_signature(self, company_id, invoice_hash):
        """Generate an ECDSA SHA256 digital signature for the XML eInvoice"""
        decoded_hash = b64decode(invoice_hash).decode()
        return company_id.sudo().l10n_sa_private_key_id._sign(decoded_hash, formatting='base64')

    @api.model
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

    @api.model
    def _l10n_sa_sign_xml(self, xml_content, certificate, signature):
        """Function that signs XML content of a UBL document with a provided B64 encoded X509 certificate"""
        def _set_content(xpath, content):
            node = root.xpath(xpath)[0]
            node.text = content

        root = etree.fromstring(xml_content)
        etree.indent(root, space='    ')

        der_cert = certificate._get_der_certificate_bytes(formatting='base64')

        issuer_name = certificate._l10n_sa_get_issuer_name()
        serial_number = certificate.serial_number
        signing_time = self._l10n_sa_get_zatca_datetime(datetime.now()).strftime('%Y-%m-%dT%H:%M:%SZ')
        public_key_hashing = b64encode(sha256(der_cert).hexdigest().encode()).decode()

        signed_properties_hash = self._l10n_sa_calculate_signed_properties_hash(issuer_name, serial_number, signing_time, public_key_hashing)

        _set_content("//*[local-name()='X509IssuerName']", issuer_name)
        _set_content("//*[local-name()='X509SerialNumber']", serial_number)
        _set_content("//*[local-name()='SignedSignatureProperties']/*[local-name()='SigningTime']", signing_time)
        _set_content("//*[local-name()='SignedSignatureProperties']//*[local-name()='DigestValue']", public_key_hashing)

        prehash_content = etree.tostring(root)
        invoice_hash = self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_generate_invoice_xml_hash(prehash_content, 'digest')

        _set_content("//*[local-name()='SignatureValue']", signature)
        _set_content("//*[local-name()='X509Certificate']", der_cert.decode())
        _set_content("//*[local-name()='SignatureInformation']//*[local-name()='DigestValue']", invoice_hash)
        _set_content("//*[@URI='#xadesSignedProperties']/*[local-name()='DigestValue']", signed_properties_hash)

        return etree.tostring(root, with_tail=False)

    @api.model
    def _l10n_sa_assert_clearance_status(self, clearance_data):
        """Assert Clearance status. To be overridden in case there are any other cases to be accounted for"""
        self.ensure_one()
        mode = 'reporting' if self.resource._l10n_sa_is_simplified() else 'clearance'
        if mode == 'clearance' and clearance_data.get('clearanceStatus', '') != 'CLEARED':
            return {'error': self.env._("Invoice could not be cleared:\n%s", clearance_data), 'blocking_level': 'error'}
        if mode == 'reporting' and clearance_data.get('reportingStatus', '') != 'REPORTED':
            return {'error': self.env._("Invoice could not be reported:\n%s", clearance_data), 'blocking_level': 'error'}
        return clearance_data

    # ====== UBL Document Rendering & Submission =======

    def _l10n_sa_create_log(self, notify, attachment=False):
        self.ensure_one()
        attachment = attachment or self.attachment_id
        vals_list = [{
            'l10n_sa_edi_document_id': self.id,
            'state': self.state,
            'attachment_name': attachment.name,
            'is_test': self.resource.company_id.l10n_sa_api_mode != 'prod',
            'message': self.message,
        }]

        if notify:
            notif_type = 'success'
            msg = self.env._('Document successfully accepted!')
            if self.state in {'error', 'unknown', 'rejected'}:
                notif_type = 'danger'
                msg = self.env._('Document is blocked. Please check it and try again.')

            elif self.state == 'warning':
                notif_type = 'warning'
                msg = self.env._('Document accepted with warning(s). Please check it.')

            self.env.user._bus_send('simple_notification', {
                'type': notif_type,
                'message': msg,
            })

        return self.env['l10n_sa_edi.log'].create(vals_list)

    @api.model
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

    @api.model
    def _l10n_sa_submit_einvoice(self, signed_xml, PCSID_data):
        """
        Submit a generated Invoice UBL file by making calls to the following APIs:
            -   A. Clearance API: Submit a standard Invoice to ZATCA for validation, returns signed UBL
            -   B. Reporting API: Submit a simplified Invoice to ZATCA for validation
        """
        clearance_data = self.journal_id._l10n_sa_api_clearance(self.resource, signed_xml.decode(), PCSID_data)
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
        if not clearance_data.get('error') and clearance_data.get("status_code") != 409:
            return self._l10n_sa_assert_clearance_status(clearance_data)
        return clearance_data

    def _l10n_sa_postprocess_einvoice_submission(self, signed_xml, clearance_data):
        """
        Once an invoice has been successfully submitted, it is returned as a Cleared invoice, on which data
        from ZATCA was applied. To be overridden to account for other cases, such as Reporting.
        """
        if self.resource._l10n_sa_is_simplified():
            # if invoice is B2C, it is a SIMPLIFIED invoice, and thus it is only reported and returns
            # no signed invoice. In this case, we just return the original content
            return signed_xml.decode()
        return b64decode(clearance_data['clearedInvoice']).decode()

    def _l10n_sa_apply_qr_code(self, xml_content):
        """Apply QR code on Invoice UBL content"""
        root = etree.fromstring(xml_content)
        qr_code = self.resource.l10n_sa_qr_code_str
        qr_node = root.xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
        qr_node.text = qr_code
        return etree.tostring(root, with_tail=False)

    def _l10n_sa_get_signed_xml(self, unsigned_xml, certificate):
        """
        Helper method to sign the provided XML, apply the QR code in the case if Simplified invoices (B2C), then
        return the signed XML
        """
        signed_xml = self._l10n_sa_sign_xml(unsigned_xml, certificate, self.resource.l10n_sa_invoice_signature)
        if self.resource._l10n_sa_is_simplified():
            # Applying with_prefetch() to set the _prefetch_ids = _ids,
            # preventing premature QR code computation for other invoices.
            self.resource.with_prefetch()
            return self._l10n_sa_apply_qr_code(signed_xml)
        return signed_xml

    def _l10n_sa_export_zatca_invoice(self, xml_content=None):
        """
        Generate a ZATCA compliant UBL file, make API calls to authenticate, sign and include QR Code and
        Cryptographic Stamp, then create an attachment with the final contents of the UBL file
        """
        # Prepare UBL invoice values and render XML file
        unsigned_xml = xml_content or self.resource._l10n_sa_generate_zatca_template()

        # Load PCISD data and certificate
        try:
            PCSID_data, certificate = self.journal_id._l10n_sa_api_get_pcsid()
        except UserError as e:
            return ({
                'error': e.args[0],
                'blocking_level': 'error',
                'response': unsigned_xml,
            }, unsigned_xml)

        certificate_sudo = self.env['certificate.certificate'].sudo().browse(certificate)

        # Apply Signature/QR code on the generated XML document
        try:
            signed_xml = self._l10n_sa_get_signed_xml(unsigned_xml, certificate_sudo)
        except UserError:
            return ({
                'error': self.env._("Something went wrong. Please retry, and if that does not work, then onboard the journal again."),
                'blocking_level': 'error',
                'response': unsigned_xml,
            }, unsigned_xml)

        # Once the XML content has been generated and signed, we submit it to ZATCA
        return self._l10n_sa_submit_einvoice(signed_xml, PCSID_data), signed_xml

    def _l10n_sa_generate_attachment(self, content, is_rejected=False):
        name = self.env['account.edi.xml.ubl_21.zatca']._export_invoice_filename(self.resource)
        description = False
        if is_rejected:
            name = name[:-4] + '-rejected.xml'
            description = 'Rejected ZATCA Document not to be deleted - ثيقة ZATCA المرفوضة لا يجوز حذفها'
        return self.env['ir.attachment'].create({
            'raw': content,
            'name': name,
            'description': description,
            'res_id': self.res_id,
            'res_model': self.res_model,
            'type': 'binary',
            'mimetype': 'application/xml',
        })

    def _l10n_sa_check_chain_prerequisites(self, notify):
        """Check if chain head was sent successfuly and current document was not already successfuly sent"""
        self.ensure_one()
        chain_head = self._l10n_sa_get_chain_head()
        if chain_head and chain_head != self and not chain_head._l10n_sa_is_in_chain():
            # Chain integrity check: chain head must have been REALLY posted, and did not time out
            # When a submission times out, we reset the chain index of the invoice to False, so it has to be submitted again
            # According to ZATCA, if we end up submitting the same invoice more than once, they will directly reach out
            # to the taxpayer for clarifications
            self.l10n_sa_edi_chain_head_id = chain_head
            self.state = 'error'
            self.message = self.env._("Error: This invoice is blocked due to %s. Please check it.", chain_head.resource.name)
            self._l10n_sa_create_log(notify)
            return False

        return True

    def _l10n_sa_handle_submission_error(self, response_data, xml_content, notify):
        # Check for submission errors
        title = subtitle = content = attachment = False

        # Failed to receive a response from ZATCA
        if response_data.get("excepted"):
            title = self.env._("Warning: Unable to Retrieve a Response from ZATCA")
            subtitle = self.env._("Please check the details below:")
            content = response_data['error']
            self.state = 'unknown'

        # Rejection Response
        elif response_data.get('rejected'):
            attachment = self._l10n_sa_generate_attachment(xml_content.encode(), True)
            title = self.env._("Error: Invoice rejected by ZATCA")
            subtitle = self.env._("Please check the details below and retry after addressing them:")
            content = response_data['error']
            self.state = 'rejected'
            self.journal_id.l10n_sa_latest_submission_hash = self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_generate_invoice_xml_hash(xml_content)
            self.l10n_sa_chain_index = False
            self.env['l10n_sa_edi.document'].search([('l10n_sa_edi_chain_head_id', '=', self.id)]).l10n_sa_edi_chain_head_id = False  # Reset invoices blocked by this since rejections aren't blocking

        else:
            # if there is an error, but no exception or rejection in the response
            # then it is due to an internal error raised.
            title = self.env._("Error: Something went wrong when sending to ZATCA")
            subtitle = self.env._("Please check the details below and retry after addressing them:")
            content = response_data['error']
            self.state = 'unknown'

        self.message = f"{title or ''}\n{subtitle or ''}\n{content or ''}\n"
        self._l10n_sa_create_log(notify, attachment)

    def _l10n_sa_handle_submission_success(self, response_data, submitted_xml, notify):
        # Once submission is done with no errors, check submission status
        cleared_xml = self._l10n_sa_postprocess_einvoice_submission(submitted_xml, response_data)
        status_code = response_data.get('status_code')

        # Set 'l10n_sa_edi_is_production' to True upon the first invoice submission in Production mode
        if not self.resource.company_id.l10n_sa_edi_is_production:
            self.resource.company_id.l10n_sa_edi_is_production = self.resource.company_id.l10n_sa_api_mode == 'prod'

        # Invoice already reported.
        if status_code == 409:
            title = self.env._("Warning: Invoice was already successfully reported to ZATCA")
            subtitle = self.env._("Please check the details below:")
            content = Markup("""<b>%(status_code)s</b>%(errors)s""") % {
                "status_code": f"[{status_code}] " if status_code else "",
                "errors": Markup("<br/>").join([
                    Markup("<b>%(code)s</b> : %(message)s") % {
                        "code": m['code'],
                        "message": m['message'],
                    } for m in response_data['validationResults']['errorMessages']
                ]),
            }
            self.message = f"{title}\n{subtitle}\n{content}\n"
            self.state = 'warning'

        # Save the submitted/returned invoice XML content once the submission has been completed successfully
        elif warning_msgs := response_data.get('validationResults', {}).get('warningMessages'):
            status_code = response_data.get('status_code')
            title = self.env._("Warning: Invoice accepted by ZATCA with warning(s)")
            subtitle = self.env._("Please check the details below:")
            content = Markup("""<b>%(status_code)s</b>%(errors)s""") % {
                "status_code": f"[{status_code}] " if status_code else "",
                "errors": Markup("<br/>").join([
                    Markup("<b>%(code)s</b> : %(message)s") % {
                        "code": m['code'],
                        "message": m['message'],
                    } for m in warning_msgs
                ]),
            }
            self.message = f"{title}\n{subtitle}\n{content}\n"
            self.state = 'warning'

        else:
            self.message = self.env._("Success: Invoice accepted by ZATCA")
            self.state = 'accepted'

        self.env['l10n_sa_edi.document'].search([('l10n_sa_edi_chain_head_id', '=', self.id)]).l10n_sa_edi_chain_head_id = False  # Reset invoices blocked by this invoice
        self.journal_id.l10n_sa_latest_submission_hash = self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_generate_invoice_xml_hash(cleared_xml.encode())
        self.attachment_id = self._l10n_sa_generate_attachment(cleared_xml.encode())
        self._l10n_sa_create_log(notify)

    def _l10n_sa_post_zatca_edi(self, notify=False):  # no batch ensure that there is only one invoice
        """Post invoice to ZATCA"""
        self.ensure_one()

        try:
            self.lock_for_update()
            self.resource.lock_for_update()
        except LockError:
            raise UserError(self.env._('This document is being processed already.'))

        if not self._l10n_sa_check_chain_prerequisites(notify):
            return

        if not self.l10n_sa_chain_index:
            self.l10n_sa_chain_index = self.journal_id._l10n_sa_edi_get_next_chain_index()

        # Generate XML, sign it, then submit it to ZATCA
        xml_content = self.resource._l10n_sa_generate_unsigned_data()
        response_data, submitted_xml = self._l10n_sa_export_zatca_invoice(xml_content)

        # Check for submission errors
        self._l10n_sa_handle_submission_error(response_data, xml_content, notify) if response_data.get('error') else self._l10n_sa_handle_submission_success(response_data, submitted_xml, notify)

    def _l10n_sa_get_chain_head(self):
        self.ensure_one()
        return self.journal_id._l10n_sa_get_last_posted_doc()

    def _l10n_sa_is_in_chain(self):
        """
        If the invoice was successfully posted and confirmed by the government, then this would return True.
        If the invoice timed out then its edi_document will not be in the 'accepted' or 'warning' states.
        """
        return all(record.state in ['accepted', 'warning'] for record in self)

    @api.model
    def _l10n_sa_get_qr_code_encoding(self, tag, field, int_length=1):
        """
        Helper function to encode strings for the QR code generation according to ZATCA specs
        """
        company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
        company_name_length_encoding = len(field).to_bytes(length=int_length, byteorder='big')
        return company_name_tag_encoding + company_name_length_encoding + field

    @api.model
    def _l10n_sa_build_simplified_phase_2_qr(self, company_id, unsigned_xml, certificate, signature):
        """
        Generate QR code string based on XML content of the Invoice UBL file, X509 Production Certificate
        and company info.

        :return b64 encoded QR code string
        """

        def xpath_ns(expr):
            return find_xml_value(expr, root, edi_format._l10n_sa_get_namespaces())

        qr_code_str = b''
        root = etree.fromstring(unsigned_xml)
        edi_format = self.env['account.edi.xml.ubl_21.zatca']

        # Indent XML content to avoid indentation mismatches
        etree.indent(root, space='    ')

        invoice_date = xpath_ns('//cbc:IssueDate')
        invoice_time = xpath_ns('//cbc:IssueTime')
        invoice_datetime = datetime.strptime(invoice_date + ' ' + invoice_time, '%Y-%m-%d %H:%M:%S')

        if invoice_datetime and company_id.vat and certificate and signature:
            prehash_content = etree.tostring(root)
            invoice_hash = edi_format._l10n_sa_generate_invoice_xml_hash(prehash_content, 'digest')

            amount_total = float(xpath_ns('//cbc:PayableAmount'))
            amount_tax = float(xpath_ns('//cac:TaxTotal/cbc:TaxAmount'))
            seller_name_enc = self._l10n_sa_get_qr_code_encoding(1, company_id.display_name.encode())
            seller_vat_enc = self._l10n_sa_get_qr_code_encoding(2, company_id.vat.encode())
            timestamp_enc = self._l10n_sa_get_qr_code_encoding(3, invoice_datetime.strftime("%Y-%m-%dT%H:%M:%S").encode())
            amount_total_enc = self._l10n_sa_get_qr_code_encoding(4, float_repr(abs(amount_total), 2).encode())
            amount_tax_enc = self._l10n_sa_get_qr_code_encoding(5, float_repr(abs(amount_tax), 2).encode())
            invoice_hash_enc = self._l10n_sa_get_qr_code_encoding(6, invoice_hash)
            signature_enc = self._l10n_sa_get_qr_code_encoding(7, signature.encode())
            public_key_enc = self._l10n_sa_get_qr_code_encoding(8, b64decode(certificate._get_public_key_bytes(formatting='base64')))

            qr_code_str = seller_name_enc + seller_vat_enc + timestamp_enc + amount_total_enc + amount_tax_enc + invoice_hash_enc + signature_enc + public_key_enc

            qr_code_str += self._l10n_sa_get_qr_code_encoding(9, b64decode(certificate._get_signature_bytes(formatting='base64')))

        return b64encode(qr_code_str).decode()

    def _l10n_sa_build_standard_phase_2_qr(self):
        if self.state in {'accepted', 'warning'} and self.attachment_id.raw:
            document_xml = self.attachment_id.raw.content
            qr_node = etree.fromstring(document_xml).xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
            return qr_node.text
        return ""

    def _l10n_sa_get_phase_2_qr(self, simplified=False):
        if simplified:
            return self._l10n_sa_build_simplified_phase_2_qr(
                self.company_id,
                self.resource._l10n_sa_generate_zatca_template(),
                self.journal_id.l10n_sa_production_csid_certificate_id,
                self.resource.l10n_sa_invoice_signature,
            )
        return self._l10n_sa_build_standard_phase_2_qr()
