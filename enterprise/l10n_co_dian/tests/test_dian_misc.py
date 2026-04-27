import requests
from lxml import etree

import re
from unittest.mock import patch, Mock

from odoo import Command
from odoo.tests import tagged, freeze_time
from odoo.addons.l10n_co_dian import xml_utils
from .common import TestCoDianCommon


@freeze_time('2024-01-30')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDianMisc(TestCoDianCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls._create_move()

    def test_cufe1_generation(self):
        # Invoice -> CUFE
        xml = self._generate_xml(self.invoice)
        self.env['l10n_co_dian.document']._create_document(xml, self.invoice, state='invoice_accepted')
        self.assertEqual(
            self.invoice.l10n_co_edi_cufe_cude_ref,
            "7e08eb9e1c18c85cb77dd46d2000c34b553eb46d270622b74b43401b3bfb2c6875ca88e605ab8dc854cce97002fa77fa",
        )

    def test_cufe2_generation(self):
        # Credit Note -> CUFE
        credit_note = self._create_move(
            move_type='out_refund',
            l10n_co_edi_description_code_credit='1',
        )
        xml = self._generate_xml(credit_note)
        self.env['l10n_co_dian.document']._create_document(xml, credit_note, state='invoice_accepted')
        self.assertEqual(
            credit_note.l10n_co_edi_cufe_cude_ref,
            "863ddd1dfab6cd66de87c8780a5bfcf29baca8424b50986bd26660df6dcd3d453cd4c2e67c3a6415b01ebcbf8c903961",
        )

    def test_cude_generation(self):
        # Debit Note -> CUDE
        debit_note = self._create_move(
            journal_id=self.debit_note_journal.id,
            l10n_co_edi_description_code_debit='1',
        )
        self.assertTrue(debit_note.l10n_co_edi_debit_note)
        xml = self._generate_xml(debit_note)
        self.env['l10n_co_dian.document']._create_document(xml, debit_note, state='invoice_accepted')
        self.assertEqual(
            debit_note.l10n_co_edi_cufe_cude_ref,
            "33d6543a3ab0fbcc6df45c2b3832000718f93e00a45e7b2083065f3a4edb54845d6b988467f66e5f7943cd618c56e83d",
        )

    def test_cuds_generation(self):
        # Support Document -> CUDS
        bill = self._create_move(
            move_type='in_invoice',
            journal_id=self.support_document_journal.id,
            invoice_date=self.frozen_today,
        )
        self.assertTrue(bill.l10n_co_edi_is_support_document)
        xml = self._generate_xml(bill)
        self.env['l10n_co_dian.document']._create_document(xml, bill, state='invoice_accepted')
        self.assertEqual(
            bill.l10n_co_edi_cufe_cude_ref,
            "0e71712630ebff53c24ffcdb15d52546d82919c15a840472ba080063c94c9a14746905c61494e15579b0b1b4f263dd6f",
        )

    def test_dian_soap_headers(self):
        """
        Dian requires the SOAP headers for any request to be hashed and signed using the private key.
        It is very sensitive to any change in the SOAP headers (namespaces, spaces, \n, etc).
        """
        expected_request = '<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wcf="http://wcf.dian.colombia"><soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing"><wsse:Security xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"><wsu:Timestamp><wsu:Created>2024-01-30T00:00:00.000Z</wsu:Created><wsu:Expires>2024-01-30T16:40:00.000Z</wsu:Expires></wsu:Timestamp><wsse:BinarySecurityToken EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary" ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" wsu:Id="X509-bd9c66b3-ad3c-2d6d-1a3d-1fa7bc8960a9">MIIDhzCCAm+gAwIBAgIUJGk07XoDBiRCszEASOoN+L3udZAwDQYJKoZIhvcNAQELBQAwUzENMAsGA1UEAwwET2RvbzERMA8GA1UECAwIV2FsbG9uaWExEjAQBgNVBAcMCVJhbWlsbGllczENMAsGA1UECgwET2RvbzEMMAoGA1UECwwDUiZEMB4XDTIzMTAyNDE0NTMwMVoXDTMzMTAyMTE0NTMwMVowUzENMAsGA1UEAwwET2RvbzERMA8GA1UECAwIV2FsbG9uaWExEjAQBgNVBAcMCVJhbWlsbGllczENMAsGA1UECgwET2RvbzEMMAoGA1UECwwDUiZEMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA1gO1/MhpsIgHhx876mX53HIMQZozcu3/t6QVmMkfZN9mjvO2jpQgL5jVy+5CWeCuF0RnUbSHkeEXkZexVwSb0ylbGYSFC6Y8s5rzdTxMKGQnZ1sSKF1xpBiA1uWM+A//uxnnpxAF1XFhhXJWmhkAvgPusHzYjbk7rbP8Z5YYWcHAJUZTMRueEgnfSES4dRyZiz685XnGYX5q1qRlLN6FbAeqJmngFi30wA4YCtc0N3NOVtpoa64JktJ0XYLCYR9uvKDjk3w0EmuSKDBlC4RuvNZIw3vSXwMw45sZLu1e3W82bdX+/MFslDRiVZ37WFpLv++VEJIiIdXHQR28ibdyDQIDAQABo1MwUTAdBgNVHQ4EFgQUpBLh75v2a/Ar52sjKYj4GWK4WnswHwYDVR0jBBgwFoAUpBLh75v2a/Ar52sjKYj4GWK4WnswDwYDVR0TAQH/BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAT+E6bkiyxzPPcgu3af2/ozwst26vdSjc6KAhxTwVCjq6nU9nRkCF+HZAXViFmMeo7iVKisckmUwJbyMG0//OeGSi3EUX9p1yHe7r2iDpUqUxriLdx2sIUzR7DgwCEbuDgAs5ycndk40qlHUP/vnKOSX1v3n+Crrn9dYCUoKBEOckV/3ZR+pXyqTMFD8KRb9KqQm91iqHTZjTSzhL2dCRw+3dC1bCTeOOO+VG5EvBv3UAymnl/58S47K3juxZtO24wRdXxH2d/MtiCzr9P6riw21JfGvtZfajfDwc26YIk7uJuT4ih56K7vUZWUtyroy9h3tzqqIImWUjtzemINTrHQ==</wsse:BinarySecurityToken><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"><ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"><ec:InclusiveNamespaces xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#" PrefixList="wsa soap wcf"/></ds:CanonicalizationMethod><ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/><ds:Reference URI="#id-972a8469-1641-9f82-8b9d-2434e465e150"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"><ec:InclusiveNamespaces xmlns:ec="http://www.w3.org/2001/10/xml-exc-c14n#" PrefixList="soap wcf"/></ds:Transform></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/><ds:DigestValue>fv6JrbE+eDnMIKLfH6+rsQWwPzYvC4vx9bNEvNC2UT0=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>HS3+vdJMmH07OCnh6dgW6rMoNPR4Lu2Sr7+Nt8uRukBkY0Zm7VOT8lvCHC8WD+1F130dUvPKkIe5\nZBjxgZqKXJEM4djInu4L4dFKsd3fvETMWnOsRX/QdfE+euUNvblib6PGzJBeFvrg42RCWCNWMg8s\nf9/2crjXTXdXA80YcYo6sW+TXclP/BC4f2OEW07RNF55Kq9CQt1f3lFG7npC9+DEUznhTIsE56Lf\n1JGsxK2HH0JGapv026GZ8I4KT/FR3NSiEdumiK2zSh32W5CGdWN1FFBepc+OJai+2cSCCX0IxQRB\n6g6k4zvWttE09GlFFjfsaLxdPom6JFI7jdmajA==\n</ds:SignatureValue><ds:KeyInfo><wsse:SecurityTokenReference><wsse:Reference ValueType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3" URI="#X509-bd9c66b3-ad3c-2d6d-1a3d-1fa7bc8960a9"/></wsse:SecurityTokenReference></ds:KeyInfo></ds:Signature></wsse:Security><wsa:Action>http://wcf.dian.colombia/IWcfDianCustomerServices/SendBillSync</wsa:Action><wsa:To xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" wsu:Id="id-972a8469-1641-9f82-8b9d-2434e465e150">https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc</wsa:To></soap:Header><soap:Body><wcf:SendBillSync><wcf:fileName>invoice.zip</wcf:fileName><wcf:contentFile>test</wcf:contentFile></wcf:SendBillSync></soap:Body></soap:Envelope>'
        expected = etree.tostring(etree.fromstring(expected_request), method='c14n')

        def post(url, data=None, json=None, **kwargs):
            actual_request = etree.fromstring(data.decode())
            actual_request.find('.//{*}contentFile').text = 'test'  # remove the payload to shorten the request
            actual = etree.tostring(actual_request, method='c14n')  # canonize to prevent undeterministic order of the namespaces declarations
            self.assertEqual(expected, actual)
            response = Mock(spec=requests.Response)
            response.status_code = 200
            response.text = '<A><IsValid>true</IsValid></A>'
            return response

        with self._mock_get_status(), patch('requests.post', side_effect=post), self._mock_uuid_generation(), self._disable_get_acquirer_call():
            self.env['account.move.send.wizard'] \
                .with_context(active_model=self.invoice._name, active_ids=self.invoice.ids) \
                .create({}) \
                .action_send_and_print()

    def test_dian_payload(self):
        """
        As for the SOAP headers, Dian requires the invoice xml (the payload) to be hashed and signed using the private
        key. It is very sensitive to any change (namespaces, spaces, \n, etc).
        In case of error, validator will raise: "ZE02, Rechazo: Valor de la firma inválido."
        """
        with self._mock_uuid_generation():
            xml = self._generate_xml(self.invoice)
        # the namespaces 'sts' and 'ext' should be declared on the root node otherwise DIAN raises
        # "Namespace prefix not defined"
        root = etree.fromstring(xml)
        self.assertEqual(f'{{{root.nsmap[None]}}}Invoice', root.tag)
        self.assertIn('sts', root.nsmap)
        self.assertIn('ext', root.nsmap)

        expected_xml = self._read_file('l10n_co_dian/tests/attachments/invoice_signed.xml', 'rb')
        # Remove the namespaces as they are serialized in a non deterministic order
        self.assertEqual(
            re.sub(b'xmlns.*"', b'', expected_xml),
            re.sub(b'xmlns.*"', b'', xml),
        )

    def test_dian_xades_signature(self):
        """ Check the XMLDsig digests and the XAdES digests and signature """
        xml = self._read_file('l10n_co_dian/tests/attachments/invoice_signed.xml', 'rb')
        root = etree.fromstring(xml)

        # Nullify the XMLDsig digests
        expected_digests = []
        for node in root.findall(".//ds:DigestValue", root.nsmap)[:3]:
            expected_digests.append(node.text)
            node.text = ''

        # Recompute the XMLDsig digests
        xml_utils._reference_digests(root.find(".//ds:SignedInfo", root.nsmap))
        actual_digests = [node.text for node in root.findall(".//ds:DigestValue", root.nsmap)[:3]]
        self.assertEqual(expected_digests, actual_digests)

        # Recompute the DigestValue for the X509 certificate
        expected_x509_digest = self.certificate_demo._get_fingerprint_bytes(formatting='base64').decode()
        self.assertEqual(expected_x509_digest, root.find(".//{*}CertDigest/{*}DigestValue").text)

        # Recompute the X509 certificate
        obtained_x509 = self.certificate_demo._get_der_certificate_bytes().decode()
        self.assertEqual(obtained_x509, root.find(".//{*}X509Certificate").text)

        # Recompute the XAdES signature
        expected_sig_value = root.find('.//{*}SignatureValue').text
        root.find('.//{*}SignatureValue').text = ''
        xml_utils._fill_signature(root.find(".//ds:Signature", root.nsmap), self.certificate_demo)
        self.assertEqual(root.find('.//{*}SignatureValue').text, expected_sig_value)

    def test_state_and_city(self):
        """ Check that the colombian codes is correctly padded (length 5 for cities, length 2 for states) """
        self.invoice.partner_id.city_id = self.env.ref('l10n_co_edi.city_co_01')
        self.invoice.partner_id.state_id = self.invoice.partner_id.city_id.state_id
        xml = self._generate_xml(self.invoice)
        root = etree.fromstring(xml)
        self.assertEqual(
            root.find('.//{*}AccountingCustomerParty//{*}RegistrationAddress/{*}CountrySubentityCode').text,
            '05',
        )
        self.assertEqual(
            root.find('.//{*}AccountingCustomerParty//{*}Address/{*}ID').text,
            '05001',
        )

    def test_attached_document_invoice_flow(self):
        self.invoice.partner_id.email = "tmp@odoo.com"  # so the email is sent by default when Send & Printing

        # Send & Print to generate the zip (containing the AttachedDocument + the PDF)
        with self._mock_get_status():
            self._mock_send_and_print(move=self.invoice, response_file='SendBillSync_warnings.xml')

        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self.invoice._name),
            ('res_id', '=', self.invoice.id),
        ])
        self.assertIn("SETP202400001.zip", attachments.mapped('name'))

        # regenerate the attached document
        with self._mock_get_status():
            xml, error = self.invoice.l10n_co_dian_document_ids._get_attached_document()
        self.assertEqual(error, "")
        self._assert_document_dian(xml, "l10n_co_dian/tests/attachments/attached_document.xml")

    def test_account_manager_update_journal(self):
        """
        This test serves both purposes of checking the DIAN configuration reload
        and making sure an account manager has all access needed in this flow
        """
        self.user.groups_id = [Command.unlink(self.env.ref('base.group_system').id)]
        journal = self.support_document_journal
        message = self._mock_button_l10n_co_dian_fetch_numbering_range(journal=journal, response_file='GetNumberingRange_journal.xml')
        self.assertEqual(message['params']['message'], 'The journal values were successfully updated.')
