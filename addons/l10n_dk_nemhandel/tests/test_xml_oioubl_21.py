from freezegun import freeze_time
from requests import PreparedRequest, Response, Session
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLDKOIOUBL21(TestUBLCommon, TestAccountMoveSendCommon):

    @classmethod
    @TestUBLCommon.setup_country('dk')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'city': 'Aalborg',
            'zip': '9430',
            'vat': 'DK12345674',
            'phone': '+45 32 12 34 56',
            'street': 'Paradisæblevej, 10',
        })
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'DK5000400440116243',
        })

        cls.company_data['company'].partner_id.update({
            'peppol_endpoint': False,
        })

        cls.partner_a.write({
            'name': 'SUPER DANISH PARTNER',
            'city': 'Aalborg',
            'zip': '9430',
            'vat': 'DK12345674',
            'phone': '+45 32 12 35 56',
            'street': 'Paradisæblevej, 11',
            'country_id': cls.env.ref('base.dk').id,
            'invoice_edi_format': 'oioubl_21',
        })
        cls.partner_b.write({
            'name': 'SUPER BELGIAN PARTNER',
            'street': 'Rue du Paradis, 10',
            'zip': '6870',
            'city': 'Eghezee',
            'country_id': cls.env.ref('base.be').id,
            'phone': '061928374',
            'vat': 'BE0897223670',
            'invoice_edi_format': 'oioubl_21',
            'nemhandel_identifier_type': '0088',
            'nemhandel_identifier_value': '5798009811512',

        })
        cls.partner_c = cls.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': cls.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'company_registry': '123 568 941 00056',
            'invoice_edi_format': 'oioubl_21',
            'nemhandel_identifier_type': '0088',
            'nemhandel_identifier_value': '5798009811639',
        })
        cls.dk_local_sale_tax_1 = cls.env["account.chart.template"].ref('tax_s1y')
        cls.dk_local_sale_tax_2 = cls.env["account.chart.template"].ref('tax_s1')
        cls.dk_foreign_sale_tax_1 = cls.env["account.chart.template"].ref('tax_s0')
        cls.dk_foreign_sale_tax_2 = cls.env["account.chart.template"].ref('tax_s7')
        cls.dk_local_purchase_tax_goods = cls.env["account.chart.template"].ref('tax_k1')

    def create_post_and_send_invoice(self, partner=None, move_type='out_invoice'):
        if not partner:
            partner = self.partner_a

        if partner == self.partner_a:
            # local dk taxes
            tax_1, tax_2 = self.dk_local_sale_tax_1, self.dk_local_sale_tax_2
        else:
            # dk taxes for foreigners
            tax_1, tax_2 = self.dk_foreign_sale_tax_1, self.dk_foreign_sale_tax_2

        invoice = self.env["account.move"].create({
            'move_type': move_type,
            'partner_id': partner.id,
            'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'narration': 'test narration',
            'ref': 'ref_move',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(tax_1.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_2.ids)],
                }),
            ],
        })
        invoice.action_post()
        with patch('odoo.addons.l10n_dk_nemhandel.models.res_partner.ResPartner._get_nemhandel_verification_state', return_value='not_valid'):
            wizard = self.env['account.move.send.wizard'] \
                .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                .create({})
            wizard.action_send_and_print()
        return invoice

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200
        if r.url.endswith('iso6523-actorid-upis%3A%3A0184%3A12345674'):
            response._content = b"""<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0208:0477472701</id:ParticipantIdentifier>'
            '<smp:ServiceMetadataReferenceCollection><smp:ServiceMetadataReference href="http://smp.nemhandel.dk/iso6523-actorid-upis%3A%3A0184%3A12345674/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1"/>'
            '</smp:ServiceMetadataReferenceCollection></smp:ServiceGroup>"""
            return response
        if r.url.endswith('iso6523-actorid-upis%3A%3A0208%3A5798009811639'):
            response._content = b"""<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0088:5798009811639</id:ParticipantIdentifier>
            '<smp:ServiceMetadataReferenceCollection><smp:ServiceMetadataReference href="http://smp.nemhandel.dk/iso6523-actorid-upis%3A%3A0208%3A5798009811639/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1"/>'
            '</smp:ServiceMetadataReferenceCollection></smp:ServiceGroup>"""
            return response
        if r.url.endswith('iso6523-actorid-upis%3A%3A0208%3A5798009811512'):
            response._content = b"""<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0088:5798009811512</id:ParticipantIdentifier>
            '<smp:ServiceMetadataReferenceCollection><smp:ServiceMetadataReference href="http://smp.nemhandel.dk/iso6523-actorid-upis%3A%3A0088%3A5798009811512/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1"/>'
            '</smp:ServiceMetadataReferenceCollection></smp:ServiceGroup>"""
            return response

        return super()._request_handler(s, r, **kw)

    #########
    # EXPORT
    #########

    @freeze_time('2017-01-01')
    def test_export_invoice_partner_dk(self):
        invoice = self.create_post_and_send_invoice()
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_partner_dk.xml")

    @freeze_time('2017-01-01')
    def test_export_invoice_foreign_partner_be(self):
        # Set peppol endpoint to have schemeID of 'GLN'
        self.company_data['company'].partner_id.peppol_endpoint = '0239843188'
        invoice = self.create_post_and_send_invoice(partner=self.partner_b)
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_foreign_partner_be.xml")

    @freeze_time('2017-01-01')
    def test_export_invoice_foreign_partner_fr(self):
        invoice = self.create_post_and_send_invoice(partner=self.partner_c)
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_foreign_partner_fr.xml")

    @freeze_time('2017-01-01')
    def test_export_credit_note_partner_dk(self):
        refund = self.create_post_and_send_invoice(move_type='out_refund')
        self.assertTrue(refund.ubl_cii_xml_id)
        self._assert_invoice_attachment(refund.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_refund_partner_dk.xml")

    @freeze_time('2017-01-01')
    def test_export_credit_note_partner_fr(self):
        refund = self.create_post_and_send_invoice(partner=self.partner_c, move_type='out_refund')
        self.assertTrue(refund.ubl_cii_xml_id)
        self._assert_invoice_attachment(refund.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_refund_foreign_partner_fr.xml")

    @freeze_time('2017-01-01')
    def test_oioubl_export_should_still_be_valid_when_currency_has_more_precision_digit(self):
        self.company_data['company'].currency_id.rounding = 0.001
        invoice = self.create_post_and_send_invoice()
        self.assertTrue(invoice.ubl_cii_xml_id)
        self._assert_invoice_attachment(invoice.ubl_cii_xml_id, xpaths=None, expected_file_path="from_odoo/oioubl_out_invoice_partner_dk.xml")

    @freeze_time('2017-01-01')
    def test_oioubl_export_should_raise_an_error_when_partner_building_number_is_missing(self):
        self.partner_a.street = 'Paradisæblevej'  # remove the street number from the address
        with self.assertRaisesRegex(UserError, "The following partner's street number is missing"):
            self.create_post_and_send_invoice()

    @freeze_time('2017-01-01')
    def test_oioubl_export_should_raise_an_error_when_company_building_number_is_missing(self):
        self.env.company.partner_id.street = 'Paradisæblevej'
        with self.assertRaisesRegex(UserError, "The following partner's street number is missing"):
            self.create_post_and_send_invoice()

    @freeze_time('2017-01-01')
    def test_export_partner_fr_without_siret_should_raise_an_error(self):
        self.partner_c.company_registry = False
        self.partner_c.invoice_edi_format = 'oioubl_21'
        with self.assertRaisesRegex(UserError, "The company registry is required for french partner:"):
            self.create_post_and_send_invoice(partner=self.partner_c)

    @freeze_time('2017-01-01')
    def test_oioubl_export_partner_without_vat_number(self):
        """ This test verifies that we can't export an OIOUBL file for a partner
            who doesn't have a tax ID. It verifies that we receive a UserError
            telling to the user that this field is missing.
        """
        self.partner_b.vat = None
        self.partner_b.invoice_edi_format = 'oioubl_21'  # default format recomputes when vat is changed
        with self.assertRaises(UserError) as exception:
            self.create_post_and_send_invoice(partner=self.partner_b)
        self.assertIn(f"The field '{self.partner_b._fields['vat'].string}' is required", exception.exception.args[0])
