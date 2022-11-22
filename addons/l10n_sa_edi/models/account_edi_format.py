import re
import json
import uuid
import requests
from hashlib import sha256
from base64 import b64decode, b64encode
from lxml import etree
from datetime import date, datetime
from odoo import models, fields, _, api
from odoo.exceptions import UserError
from odoo.tools import float_repr
from odoo.modules.module import get_module_resource
from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_der_x509_certificate


ZATCA_API_URLS = {
    "sandbox": "https://gw-apic-gov.gazt.gov.sa/e-invoicing/developer-portal",
    "production": "https://gw-apic-gov.gazt.gov.sa/e-invoicing/core",
    "apis": {
        "ccsid": "/compliance",
        "pcsid": "/production/csids",
        "compliance": "/compliance/invoices",
        "reporting": "/invoices/reporting/single",
        "clearance": "/invoices/clearance/single",
    }
}


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    """
        In order to clear/report an eInvoice through the ZATCA API, the following logic needs to be applied:
        
            STEP 1: 
                Make a call to the Compliance CSID API '/compliance'.
                This will return three things: 
                    -   X509 Compliance Cryptographic Stamp Identifier (CCSID/Certificate) 
                    -   Password (Secret)
                    -   Compliance Request ID
            STEP 2:
                Make a call to the Compliance Checks API '/compliance/invoices'.
                This will check if the provided Standard/Simplified Invoices complies with UBL 2.1 standards in line 
                with ZATCA specifications
            STEP 3:
                Make a call to the Production CSID API '/production/csids' including the Compliance Certificate, 
                Password and Request ID from STEP 1.
                This will return three things:
                    -   X509 Production Certificate 
                    -   Password (Secret)
                    -   Production Request ID
            STEP 4:
                A) STANDARD Invoice:
                    Make a call to the Clearance API '/invoices/clearance/single'.
                    This will validate the invoice, sign it and apply a QR code then return the result.
                B) SIMPLIFIED Invoice:
                    Make a call to the Reporting API '/invoices/reporting/single'.
                    This will validate the invoice then return the result.
                The X509 Certificate and password from STEP 3 need to be provided in the request headers.
    """

    # ====== Helper Functions =======

    def _l10n_sa_get_zatca_datetime(self, timestamp):
        return fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), timestamp)

    def _l10n_sa_get_namespaces(self):
        return {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
            'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
            'sbc': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#'
        }

    def _l10n_sa_xml_node_content(self, root, xpath, namespaces=None):
        namespaces = namespaces or self._l10n_sa_get_namespaces()
        return etree.tostring(root.xpath(xpath, namespaces=namespaces)[0], with_tail=False,
                              encoding='utf-8', method='xml')

    def _l10n_sa_generate_invoice_hash(self, invoice, mode='hexdigest'):
        """
            Function that generates the Base 64 encoded SHA256 hash of a given invoice
        :param recordset invoice: Invoice to hash
        :param str mode: Function used to return the SHA256 hashing result. Either 'digest' or 'hexdigest'
        :return: Given Invoice's hash
        :rtype: bytes
        """
        e_invoice = next((d for d in invoice.edi_document_ids if d.edi_format_id.code == 'sa_zatca'), None)
        if not invoice.company_id.l10n_sa_production_env or not e_invoice:
            # If no invoice, or if using Sandbox, return the b64 encoded SHA256 value of the '0' character
            return "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ==".encode()
        return self._l10n_sa_generate_invoice_xml_hash(b64decode(e_invoice.attachment_id.datas), mode)

    # ====== Xades Signing =======

    def _l10n_sa_generate_invoice_xml_sha(self, xml_content):
        """
            Transform, canonicalize then hash the invoice xml content using the SHA256 algorithm,
            then return the hashed content
        :param xml_content:
        :return: sha256 hashing results
        """

        def _canonicalize_xml(content):
            """
                Canonicalize XML content using the c14n method. The specs mention using the c14n11 canonicalization,
                which is simply calling etree.tostring and setting the method argument to 'c14n'. There are minor
                differences between c14n11 and c14n canonicalization algorithms, but for the purpose of ZATCA signing,
                c14n is enough
            :param content: XML content to canonicalize
            :return: Canonicalized XML content
            """
            return etree.tostring(content, method="c14n", exclusive=False, with_comments=False,
                                  inclusive_ns_prefixes=self._l10n_sa_get_namespaces())

        def _transform_and_canonicalize_xml(content):
            """
                Transform XML content to remove certain elements and signatures using an XSL template
            :param content: XML content to transform
            :return: Transformed & Canonicalized XML content
            """
            invoice_xsl = etree.parse(get_module_resource('l10n_sa_edi', 'data', 'pre-hash_invoice.xsl'))
            transform = etree.XSLT(invoice_xsl)
            return _canonicalize_xml(transform(content))

        root = etree.fromstring(xml_content)
        # Transform & canonicalize the XML content
        transformed_xml = _transform_and_canonicalize_xml(root)
        # Get the SHA256 hashed value of the XML content
        return sha256(transformed_xml)

    def _l10n_sa_generate_invoice_xml_hash(self, xml_content, mode='hexdigest'):
        """
            Generate the b64 encoded sha256 hash of a given xml string:
                - First: Transform the xml content using a pre-hash_invoice.xsl file
                - Second: Canonicalize the transformed xml content using the c14n method
                - Third: hash the canonicalized content using the sha256 algorithm then encode it into b64 format
        :param str xml_content: The XML content string to be transformed, canonicalized & hashed
        :param str mode: Name of the function used to return the SHA256 hashing result. Either 'digest' or 'hexdigest'
        :return: XML content hash
        :rtype: bytes
        """
        xml_sha = self._l10n_sa_generate_invoice_xml_sha(xml_content)
        if mode == 'hexdigest':
            xml_hash = xml_sha.hexdigest().encode()
        elif mode == 'digest':
            xml_hash = xml_sha.digest()
        else:
            raise UserError(_("Only 'hexdigest' and 'digest' methods are supported when generating invoice hash"))
        return b64encode(xml_hash)

    def _l10n_sa_get_qr_code(self, company_id, xml_content, from_pos):
        """
            Generate ZATCA compliant QR Code for a given invoice.
            Requirements for Phase 2 are different than the ones for Phase 1.

        :param invoice: The invoice for which the QR code will be generated
        :param xml_content: Rendered UBL content for the invoice
        :return: b64 encoded QR code string
        """

        qr_code_str = ''
        root = etree.fromstring(xml_content)

        def get_qr_encoding(tag, field, int_length=1):
            company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
            company_name_length_encoding = len(field).to_bytes(length=int_length, byteorder='big')
            return company_name_tag_encoding + company_name_length_encoding + field

        def xpath_ns(expr):
            return root.xpath(expr, namespaces=self._l10n_sa_get_namespaces())[0].text.strip()

        invoice_date = xpath_ns('//cbc:IssueDate')
        invoice_time = xpath_ns('//cbc:IssueTime')
        invoice_datetime = datetime.strptime(invoice_date + ' ' + invoice_time, '%Y-%m-%d %H:%M:%S')

        amount_total = float(xpath_ns('//cbc:TaxInclusiveAmount'))
        amount_tax = float(xpath_ns('//cac:TaxTotal/cbc:TaxAmount'))

        if invoice_datetime and company_id.vat:
            x509_certificate = load_der_x509_certificate(b64decode(xpath_ns('//ds:X509Certificate')), default_backend())
            seller_name_enc = get_qr_encoding(1, company_id.display_name.encode())
            seller_vat_enc = get_qr_encoding(2, company_id.vat.encode())
            timestamp_enc = get_qr_encoding(3, invoice_datetime.strftime("%Y-%m-%dT%H:%M:%SZ").encode())
            amount_total_enc = get_qr_encoding(4, float_repr(abs(amount_total), 2).encode())
            amount_tax_enc = get_qr_encoding(5, float_repr(abs(amount_tax), 2).encode())
            invoice_hash_enc = get_qr_encoding(6, xpath_ns('//ds:SignedInfo/ds:Reference/ds:DigestValue').encode())
            signature_enc = get_qr_encoding(7, xpath_ns('//ds:SignatureValue').encode())
            public_key_enc = get_qr_encoding(8, x509_certificate.public_key().public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo))

            str_to_encode = (seller_name_enc + seller_vat_enc + timestamp_enc + amount_total_enc +
                             amount_tax_enc + invoice_hash_enc + signature_enc + public_key_enc)

            if from_pos:
                str_to_encode += get_qr_encoding(9, x509_certificate.signature)

            qr_code_str = b64encode(str_to_encode).decode()
        return qr_code_str

    @api.model
    def _l10n_sa_get_digital_signature(self, company_id, invoice_hash):
        """
            Generate an ECDSA SHA256 digital signature for the XML eInvoice
        :param invoice: Invoice record
        :param invoice_hash: base64 sha256 hash of the invoice
        :return: digital signature
        """
        decoded_hash = b64decode(invoice_hash).decode()
        private_key = load_pem_private_key(company_id.l10n_sa_private_key, password=None, backend=default_backend())
        signature = private_key.sign(decoded_hash.encode(), ECDSA(hashes.SHA256()))
        return b64encode(signature)

    def _l10n_sa_calculate_signed_properties_hash(self, issuer_name, serial_number, signing_time, public_key):
        """
            Calculate the SHA256 value of the SignedProperties XML node. The algorithm used by ZATCA expects the indentation
            of the nodes to start with 40 spaces, except for the root SignedProperties node.

        :param issuer_name: Name of the issuer extracted from the X509 Certificate
        :param serial_number: Serial number of the issuer extracted from the X509 Certificate
        :param signing_time: Time at which the signature is applied
        :param public_key: Public key extracted from the X509 Certificate
        :return: B64 encoded SHA256 hash of the signedProperties node
        """
        signed_properties = etree.fromstring(self.env.ref('l10n_sa_edi.export_sa_zatca_ubl_signed_properties')._render({
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

    def _l10n_sa_sign_xml(self, company_id, xml_content, certificate_str, from_pos=False):
        """
            Function that signs XML content of a UBL document with a provided B64 encoded X509 certificate
        :param company_id: Company id to be used for signing
        :param xml_content: XML content of the UBL document to be signed
        :param certificate_str: Base64 encoded stringself.env.ref('l10n_sa_edi.export_sa_zatca_ubl_signed_properties')._render(cert_data) of the X509 certificate
        :return: signed xml content
        """
        root = etree.fromstring(xml_content)
        etree.indent(root, space='    ')

        def _set_content(attr_id, content):
            node = root.xpath('//*[@id="%s"]' % attr_id)[0]
            node.text = content
            node.attrib.pop('id')

        b64_decoded_cert = b64decode(certificate_str)
        x509_certificate = load_der_x509_certificate(b64decode(b64_decoded_cert.decode()), default_backend())

        issuer_name = ', '.join([s.rfc4514_string() for s in x509_certificate.issuer.rdns[::-1]])
        serial_number = str(x509_certificate.serial_number)
        signing_time = self._l10n_sa_get_zatca_datetime(datetime.now()).strftime('%Y-%m-%dT%H:%M:%SZ')
        public_key_hashing = b64encode(sha256(b64_decoded_cert).hexdigest().encode()).decode()

        signed_properties_hash = self._l10n_sa_calculate_signed_properties_hash(issuer_name, serial_number,
                                                                                signing_time, public_key_hashing)

        _set_content('issuer_name', issuer_name)
        _set_content('serial_number', serial_number)
        _set_content('signing_time', signing_time)
        _set_content('public_key_hashing', public_key_hashing)

        prehash_content = etree.tostring(root)
        invoice_hash_hex = self._l10n_sa_generate_invoice_xml_hash(prehash_content).decode()
        invoice_hash = self._l10n_sa_generate_invoice_xml_hash(prehash_content, 'digest')
        digital_signature = self._l10n_sa_get_digital_signature(company_id, invoice_hash_hex)

        _set_content('invoice_hash', invoice_hash)
        _set_content('x509_certificate', b64_decoded_cert.decode())
        _set_content('digital_signature', digital_signature)
        _set_content('signed_properties_hashing', signed_properties_hash)

        final_xml = etree.tostring(root, with_tail=False)

        if from_pos:
            final_xml = self._l10n_sa_apply_qr_code(company_id, final_xml, from_pos)

        return final_xml

    def _l10n_sa_apply_qr_code(self, company_id, xml_content, from_pos=False):
        """
            Apply QR code on Invoice UBL content
        :return: XML content with QR code applied
        """
        root = etree.fromstring(xml_content)
        qr_code = self._l10n_sa_get_qr_code(company_id, xml_content, from_pos)
        qr_node = root.xpath('//*[local-name()="ID"][text()="QR"]/following-sibling::*/*')[0]
        qr_node.text = qr_code
        return etree.tostring(root, with_tail=False)

    # ====== API Helper Methods =======

    def _l10n_sa_call_api(self, request_data, request_url, method):
        """
            Helper function to make api calls to the ZATCA API Endpoint
        :param dict request_data: data to be sent along with the request
        :param str request_url: URI used for the request
        :param str method: HTTP method used for the request (ex: POST, GET)
        :return: Results of the API call
        :rtype: dict
        """
        api_url = ZATCA_API_URLS['production' if self.env.company.l10n_sa_production_env else 'sandbox']
        request_url = api_url + request_url
        try:
            request_response = requests.request(method, request_url, data=request_data.get('body'),
                                                headers={
                                                    **self._l10n_sa_api_headers(),
                                                    **request_data.get('header')
                                                }, timeout=(30, 30))
        except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema,
                requests.exceptions.Timeout, requests.exceptions.HTTPError) as ex:
            return {
                'error': str(ex),
                'blocking_level': 'warning'
            }
        # Authentication errors do not return json
        if request_response.status_code == 401:
            return {
                'error': _("API %s could not be authenticated") % request_url,
                'blocking_level': 'error'
            }

        if request_response.status_code in (303, 400, 500, 409, 502, 503):
            return {'error': request_response.text, 'blocking_level': 'error'}

        try:
            response_data = request_response.json()
        except json.decoder.JSONDecodeError as e:
            return {
                'error': _("JSON response from ZATCA could not be decoded"),
                'blocking_level': 'error'
            }

        if not request_response.ok and (response_data.get('errors') or response_data.get('warnings')):
            if isinstance(response_data, dict) and response_data.get('errors'):
                return {
                    'error': response_data['errors'][0],
                    'blocking_level': 'error'
                }
            return {
                'error': request_response.reason,
                'blocking_level': 'error'
            }
        return response_data

    def _l10n_sa_api_headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept-Language': 'en',
            'Accept-Version': 'V2'
        }

    def _l10n_sa_authorization_header(self, CSID_data):
        auth_str = "%s:%s" % (CSID_data['binarySecurityToken'], CSID_data['secret'])
        return 'Basic ' + b64encode(auth_str.encode()).decode()

    def _l10n_sa_assert_clearance_results(self, invoice, clearance_data):
        """
            Check clearance/reporting api results for success/errors
        """
        if clearance_data.get('error'):
            errors = json.loads(clearance_data['error'])
            validation_results = errors.get('validationResults', {})
            error_msg = ''
            for err in validation_results.get('warningMessages', []):
                error_msg += '\n - %s | %s' % (err['code'], err['message'])
            for err in validation_results.get('errorMessages', []):
                error_msg += '\n - %s | %s' % (err['code'], err['message'])
            raise UserError(_("Invoice submissions failed: %s ") % error_msg)
        mode = 'reporting' if invoice.l10n_sa_pos_origin else 'clearance'
        if mode == 'clearance' and clearance_data.get('clearanceStatus', '') != 'CLEARED':
            raise UserError(_("Invoice could not be cleared: \r\n %s ") % clearance_data)
        elif mode == 'reporting' and clearance_data.get('reportingStatus', '') != 'REPORTED':
            raise UserError(_("Invoice could not be reported: \r\n %s ") % clearance_data)

    # ====== API Calls to ZATCA =======

    def _l10n_sa_api_get_compliance_CSID(self, journal_id, otp):
        """
            API call to the Compliance CSID API to generate a CCSID certificate, password and compliance request_id
            Requires a CSR token and a One Time Password (OTP)
        :return: API call results
        :rtype: dict
        """
        if not otp:
            raise UserError(_("Please, set a valid OTP to be used for Onboarding"))
        if not journal_id.l10n_sa_csr:
            raise UserError(_("Please, generate a CSR before requesting a CCSID"))
        request_data = {
            'body': json.dumps({'csr': journal_id.l10n_sa_csr.decode()}),
            'header': {'OTP': otp}
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['ccsid'], 'POST')

    def _l10n_sa_api_get_production_CSID(self, CCSID_data):
        """
            API call to the Production CSID API to generate a PCSID certificate, password and production request_id
            Requires a requestID from the Compliance CSID API
        :return: API call results
        :rtype: dict
        """
        request_data = {
            'body': json.dumps({'compliance_request_id': str(CCSID_data['requestID'])}),
            'header': {'Authorization': self._l10n_sa_authorization_header(CCSID_data)}
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['pcsid'], 'POST')

    def _l10n_sa_api_renew_production_CSID(self, journal_id, PCSID_data, OTP):
        """
            API call to the Production CSID API to renew a PCSID certificate, password and production request_id
            Requires an expired Production CSID
        :return: API call results
        :rtype: dict
        """
        request_data = {
            'body': json.dumps({'csr': journal_id.l10n_sa_csr.decode()}),
            'header': {
                'OTP': OTP,
                'Authorization': self._l10n_sa_authorization_header(PCSID_data)
            }
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['pcsid'], 'PATCH')

    def _l10n_sa_api_compliance_checks(self, xml_content, CCSID_data):
        """
            API call to the COMPLIANCE endpoint to generate a security token used for subsequent API calls
            Requires a CSR token and a One Time Password (OTP)
        :return: API call results
        :rtype: dict
        """
        invoice_tree = etree.fromstring(xml_content)

        # Get the Invoice Hash from the XML document
        invoice_hash_node = invoice_tree.xpath('//*[@Id="invoiceSignedData"]/*[local-name()="DigestValue"]')[0]
        invoice_hash = invoice_hash_node.text

        # Get the Invoice UUID from the XML document
        invoice_uuid_node = invoice_tree.xpath('//*[local-name()="UUID"]')[0]
        invoice_uuid = invoice_uuid_node.text

        request_data = {
            'body': json.dumps({
                "invoiceHash": invoice_hash,
                "uuid": invoice_uuid,
                "invoice": b64encode(xml_content.encode()).decode()
            }),
            'header': {
                'Authorization': self._l10n_sa_authorization_header(CCSID_data),
                'Clearance-Status': '1'
            }
        }
        return self._l10n_sa_call_api(request_data, ZATCA_API_URLS['apis']['compliance'], 'POST')

    def _l10n_sa_api_clearance(self, invoice, xml_content, PCSID_data):
        """
            API call to the CLEARANCE/REPORTING endpoint to sign an invoice
                - If SIMPLIFIED invoice: Reporting
                - If STANDARD invoice: Clearance
        :param recordset invoice: Invoice to sign
        :param str xml_content: XML content of the invoice
        :param dict compliance_data: Result of the Compliance API call containing the Security Token
        :return: API call results
        :rtype: dict
        """
        invoice_tree = etree.fromstring(xml_content)
        invoice_hash_node = invoice_tree.xpath('//*[@Id="invoiceSignedData"]/*[local-name()="DigestValue"]')[0]
        invoice_hash = invoice_hash_node.text
        request_data = {
            'body': json.dumps({
                "invoiceHash": invoice_hash,
                "uuid": invoice.l10n_sa_uuid,
                "invoice": b64encode(xml_content.encode()).decode()
            }),
            'header': {
                'Authorization': self._l10n_sa_authorization_header(PCSID_data),
                'Clearance-Status': '1'
            }
        }
        url_string = ZATCA_API_URLS['apis']['reporting' if invoice.l10n_sa_pos_origin else 'clearance']
        return self._l10n_sa_call_api(request_data, url_string, 'POST')

    # ====== Certificate Methods =======

    def _l10n_sa_generate_compliance_csid(self, journal_id, otp):
        """
            Generate company Compliance CSID data
        :param journal_id: account.journal record
        """
        CCSID_data = self._l10n_sa_api_get_compliance_CSID(journal_id, otp)
        if not CCSID_data.get('error'):
            json.dumps(CCSID_data)
        return CCSID_data

    def _l10n_sa_get_pcsid_validity(self, PCSID_data):
        b64_decoded_pcsid = b64decode(PCSID_data['binarySecurityToken'])
        x509_certificate = load_der_x509_certificate(b64decode(b64_decoded_pcsid.decode()), default_backend())
        return x509_certificate.not_valid_after

    def _l10n_sa_generate_production_csid(self, journal_id, csid_data, renew=False, OTP=None):
        """
            Generate company Production CSID data
        :param journal_id: account.journal record
        :param csid_data: Compliance CSID data (onboarding), Production CSID data (renewal)
        """
        if renew:
            PCSID_data = self._l10n_sa_api_renew_production_CSID(journal_id, csid_data, OTP)
        else:
            PCSID_data = self._l10n_sa_api_get_production_CSID(csid_data)
        return PCSID_data

    def _l10n_sa_api_get_pcsid(self, journal_id):
        """
            Get CSIDs required to perform ZATCA api calls, and regenerate them if they need to be regenerated.
        :param journal_id:
        :return:
        """
        if not journal_id.l10n_sa_production_csid_json:
            raise UserError("Please, make a request to obtain the Compliance CSID and Production CSID before sending "
                            "documents to ZATCA")
        pcsid_validity = self._l10n_sa_get_zatca_datetime(journal_id.l10n_sa_production_csid_validity)
        time_now = self._l10n_sa_get_zatca_datetime(datetime.now())
        if pcsid_validity < time_now:
            raise UserError(_("Production certificate has expired, please renew the PCSID before proceeding"))
        return json.loads(journal_id.l10n_sa_production_csid_json)

    # ====== UBL Document Rendering & Submission =======

    def _l10n_sa_prepare_values(self, invoice):
        """
            Prepare the values that will be used to generate the invoice's UBL file
        :param recordset invoice: Invoice from which to extract the data
        :return: Values used to render the ZATCA UBL file
        :rtype: dict
        """
        values = self._get_ubl_values(invoice)
        # Get the payment means from the pos's payment method, else use 'unknown' until a payment is registered
        # for the invoice.
        payment_means = 'unknown'
        if invoice.l10n_sa_pos_origin:
            payment_means = invoice.pos_order_ids.payment_ids.payment_method_id.type
        is_export_invoice = invoice.partner_id.country_id != invoice.company_id.country_id and not invoice.l10n_sa_pos_origin
        values.update({
            'type_code': 383 if invoice.debit_origin_id else 381 if invoice.move_type == 'out_refund' else 388,
            'payment_means_code': {
                'bank': 42,
                'card': 48,
                'cash': 10,
                'transfer': 30,
                'unknown': 1
            }[payment_means],
            'invoice_transaction_code': '0%s00%s00' % (
                '2' if invoice.l10n_sa_pos_origin else '1',
                '1' if is_export_invoice else '0'
            ),
            'is_export_invoice': is_export_invoice,
            'invoice_datetime': self._l10n_sa_get_zatca_datetime(invoice.l10n_sa_confirmation_datetime),
            'previous_invoice_hash': self._l10n_sa_generate_invoice_hash(invoice._l10n_sa_get_previous_invoice()),
            # Add Process control (ProfileID) in compliance with rule BR-KSA-EN16931-01
            'profile_id': 'reporting:1.0'
        })
        return values

    def _l10n_sa_postprocess_zatca_template(self, invoice, xml_content, invoice_values):
        """
            Post-process xml content generated according to the ZATCA UBL specifications. Specifically, this entails:
                -   Add Invoice Transaction Code
                -   Force the xmlns:ext namespace on the root element (Invoice). This is required, since, by default
                    the generated UBL file does not have any ext namespaced element, so the namespace is removed
                    since it is unused.
        :param str xml_content: string representation of the generated xml file
        :param dict invoice_values: dictionary of the invoice values used to generate the xml content
        :return: Post-processed xml content
        :rtype: str
        """
        root = etree.fromstring(xml_content)

        # Add Invoice Transaction Code in compliance with rule BR-KSA-06
        invoice_type_el = root.xpath('//*[local-name()="InvoiceTypeCode"]')[0]
        invoice_type_el.attrib['name'] = invoice_values['invoice_transaction_code']

        # Force xmlns:ext namespace on UBl file
        ns_map = {'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'}
        etree.cleanup_namespaces(root, top_nsmap=ns_map, keep_ns_prefixes=['ext'])

        # Generate QR code and insert into UBL file
        qr_code_el = root.xpath('//*[@id="invoiceQR"]')[0]
        qr_code_el.text = invoice.l10n_sa_qr_code_str
        qr_code_el.attrib.pop('id')

        return etree.tostring(root, with_tail=False).decode()

    def _l10n_sa_generate_zatca_template(self, invoice, invoice_values):
        """
            Render the ZATCA UBL file
        :param dict invoice_values: values used to render the UBL file
        :return: XML content of the rendered UBL file
        :rtype: str
        """
        xml_content = self.env.ref('l10n_sa_edi.export_sa_zatca_invoice')._render(invoice_values)
        return self._l10n_sa_postprocess_zatca_template(invoice, xml_content, invoice_values)

    def _l10n_sa_submit_einvoice(self, invoice, xml_content):
        """
            Submit a generated Invoice UBL file by making calls to the following APIs:
                -   A. Clearance API: Submit a standard Invoice to ZATCA for validation, returns signed UBL
                -   B. Reporting API: Submit a simplified Invoice to ZATCA for validation
        :return: Signed Invoice's XML content string
        """
        company_id = invoice.company_id
        pos_origin = bool(invoice.pos_order_ids)
        PCSID_data = self._l10n_sa_api_get_pcsid(invoice.journal_id)
        x509_cert = PCSID_data['binarySecurityToken']
        signed_xml = self._l10n_sa_sign_xml(company_id, xml_content, x509_cert, pos_origin)
        clearance_data = self._l10n_sa_api_clearance(invoice, signed_xml.decode(), PCSID_data)
        self._l10n_sa_assert_clearance_results(invoice, clearance_data)
        if invoice.l10n_sa_pos_origin:
            # if invoice originates from POS, it is a SIMPLIFIED invoice, and thus it is only reported and returns
            # no signed invoice. In this case, we just return the original content
            return signed_xml.decode()
        return b64decode(clearance_data['clearedInvoice']).decode()

    def _l10n_sa_export_zatca_invoice(self, invoice):
        """
            Generate a ZATCA compliant UBL file, make API calls to authenticate, sign and include QR Code and
            Cryptographic Stamp, then create an attachment with the final contents of the UBL file
        :param recordset invoice: Invoice to be processed
        :return: Attachment record with the content of the processed Invoice UBL file
        :rtype: ir.attachment recordset
        """
        self.ensure_one()
        # Create file content.
        invoice_values = self._l10n_sa_prepare_values(invoice)
        unsigned_xml = self._l10n_sa_generate_zatca_template(invoice, invoice_values)
        cleared_xml = self._l10n_sa_submit_einvoice(invoice, unsigned_xml)
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        invoice_number = re.sub("[^a-zA-Z0-9 -]", "-", invoice.name)
        invoice_date = self._l10n_sa_get_zatca_datetime(invoice.l10n_sa_confirmation_datetime)
        # The ZATCA naming convention follows the following business rules:
        # Seller Vat Number (BT-31), Date (BT-2), Time (KSA-25), Invoice Number (BT-1)
        xml_name = '%s_%s_%s.xml' % (vat, invoice_date.strftime('%Y%m%dT%H%M%S'), invoice_number)
        return self.env['ir.attachment'].create({
            'name': xml_name,
            'raw': cleared_xml.encode(),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'mimetype': 'application/xml'
        })

    def _l10n_sa_check_partner_missing_info(self, partner_id, is_commercial=True):
        """
            Helper function to check if ZATCA mandated partner fields are missing for a specified partner record
        :param recordset partner_id: Partner record to check
        :return: Missing partner fields
        :rtype: list
        """
        missing = []
        fields_to_check = [
            ('l10n_sa_edi_building_number', _('Building Number')),
            ('l10n_sa_edi_plot_identification', _('Plot Identification (4 digits)'), lambda v: len(str(v)) == 4),
            ('l10n_sa_edi_neighborhood', _('Neighborhood')),
            ('l10n_sa_additional_identification_scheme', _('Additional Identification Scheme is required for commercial partners')),
            ('l10n_sa_additional_identification_number', _('Additional Identification Number is required for commercial partners')),
            ('state_id', _('State / Country subdivision'))
        ]
        for field in fields_to_check:
            field_value = partner_id[field[0]]
            if not field_value or (len(field) == 3 and not field[2](field_value)):
                missing.append(field[1])
        return missing

    def _l10n_sa_edi_is_required_for_invoice(self, invoice):
        """
            Determine whether a ZATCA EDI document needs to be generated for a given invoice
        """
        return invoice.is_sale_document() and invoice.country_code == 'SA'

    def _l10n_sa_post_zatca_edi(self, invoice):  # no batch ensure that there is only one invoice
        """
            Post invoice to ZATCA and return a dict of invoices and their success/attachment
        :param invoice: invoice to post
        :return: dict of invoices and their success/attachment
        """
        if not invoice.l10n_sa_confirmation_datetime:
            invoice.l10n_sa_confirmation_datetime = fields.Datetime.now()
        if not invoice.l10n_sa_uuid:
            invoice.l10n_sa_uuid = uuid.uuid1()
        try:
            attachment = self._l10n_sa_export_zatca_invoice(invoice)
        except UserError as e:
            return {'error': e.args[0]}
        return {invoice: {'success': True, 'attachment': attachment}}

    # ====== EDI Format Overrides =======

    def _is_required_for_invoice(self, invoice):
        """
            Override to add ZATCA edi checks on required invoices
        """
        self.ensure_one()
        if self.code != 'sa_zatca':
            return super()._is_required_for_invoice(invoice)

        return self._l10n_sa_edi_is_required_for_invoice(invoice)

    def _check_move_configuration(self, invoice):
        """
            Override to add ZATCA compliance checks on the Invoice
        """

        def _set_missing_partner_fields(missing_fields, name):
            return _("- Please, set the following fields on the %s: %s") % (name, ', '.join(missing_fields))

        journal = invoice.journal_id
        company = invoice.company_id

        errors = super()._check_move_configuration(invoice)
        if self.code != 'sa_zatca' or company.country_id.code != 'SA':
            return errors

        if not journal._l10n_sa_can_submit_einvoices():
            errors.append(
                _("- Finish the Onboarding procees for journal %s by requesting the CSIDs and completing the checks.") % journal.name)

        if not company._l10n_sa_check_vat_tin():
            errors.append(
                _("- The company VAT identification must contain 15 digits, with the first and last digits being '3' as per the BR-KSA-39 ZATCA KSA business rule."))
        if not company._l10n_sa_check_organization_unit():
            errors.append(
                _("- The eleventh digit of your company VAT identification is equal to 1, in this case, the company's Organisation Unit must be a 10-digit TIN."))
        if not company.l10n_sa_private_key:
            errors.append(
                _("- No Private Key was generated for company %s. A Private Key is mandatory in order to generate Certificate Signing Requests (CSR).") % company.name)
        if not company.l10n_sa_serial_number:
            errors.append(
                _("- No Serial Number was assigned for company %s. A Serial Number (provided by ZATCA) is mandatory in order to generate Certificate Signing Requests (CSR).") % company.name)

        supplier_missing_info = self._l10n_sa_check_partner_missing_info(
            invoice.company_id.partner_id.commercial_partner_id)
        customer_missing_info = self._l10n_sa_check_partner_missing_info(invoice.commercial_partner_id)

        if supplier_missing_info:
            errors.append(_set_missing_partner_fields(supplier_missing_info, _("Supplier")))
        if customer_missing_info:
            errors.append(_set_missing_partner_fields(customer_missing_info, _("Customer")))
        if invoice.invoice_date > date.today():
            errors.append(_("- Please, make sure the invoice date is set to either the same as or before Today."))
        if invoice.move_type in ('in_refund', 'out_refund') and not (
                (invoice.reversed_entry_id or invoice.ref) and invoice.l10n_sa_reversal_reason
        ):
            errors.append(
                _("- Please, make sure both the Reversed Entry and the Reversal Reason are specified when confirming a Credit/Debit note"))
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

    def _post_invoice_edi(self, invoices):
        """
            Override to post ZATCA edi formats
        """
        self.ensure_one()
        invoice = invoices
        if self.code != 'sa_zatca' or invoice.company_id.country_code != 'SA':
            return super()._post_invoice_edi(invoices)
        if not invoice.journal_id.l10n_sa_compliance_checks_passed:
            return {'error': _("ZATCA Compliance Checks need to be completed for the current company "
                              "before invoices can be submitted to the Authority")}
        return self._l10n_sa_post_zatca_edi(invoices)

    def _cancel_invoice_edi(self, invoices):
        """
            Override to cancel sa_zatca invoice EDIs
        """
        if self.code != "sa_zatca" or invoices.edi_state != 'sent':
            return super()._cancel_invoice_edi(invoices)
        raise UserError(_("Cannot cancel an invoice that has been reported/cleared by ZATCA"))
