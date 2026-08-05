# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import Command, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestEBupot(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'street': "test",
            'phone': "12345",
            'vat': "1234567890123456",
            'withholding_tax_base_account_id': cls.env['account.account'].create({
                'code': 'WITHB', 'name': "Withholding Tax Base", 'account_type': 'asset_current',
            }).id,
        })
        cls.company_data_2 = cls.setup_other_company()
        cls.partner_a.write({"vat": "1234567890123457", "country_id": cls.env.ref('base.id').id})

        company_id = cls.company_data['company'].id
        ChartTemplate = cls.env['account.chart.template'].with_company(company_id)
        cls.tax_pph_22 = ChartTemplate.ref(f'account.{company_id}_tax_22-102-01_purchase')   # 0.5%, code 22-102-01
        cls.tax_pph_23 = ChartTemplate.ref(f'account.{company_id}_tax_24-104-01_purchase')   # 2%, code 24-104-01
        cls.tax_pph_23_sale = ChartTemplate.ref(f'account.{company_id}_tax_24-104-01')
        cls.tax_facility = ChartTemplate.ref(f'account.{company_id}_tax_TaxExAr23_purchase')  # SKB, 0%, facility TaxExAr23
        cls.tax_ppn = ChartTemplate.ref(f'account.{company_id}_tax_PT4')

        path = "l10n_id_efaktur_coretax/tests/results/sample_ebupot.xml"
        with tools.file_open(path, mode='rb') as test_file:
            cls.sample_xml = test_file.read()

    # -----------------
    # Helpers
    # -----------------

    def _create_bill(self, price_unit=1000, taxes=None, invoice_date='2026-04-24', ref='ABC123', partner=None,
                     move_type='in_invoice'):
        bill = self.env['account.move'].create({
            'move_type': move_type,
            'ref': ref,
            'invoice_date': invoice_date,
            'partner_id': (partner or self.partner_a).id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': price_unit,
                'tax_ids': [Command.set((self.tax_pph_22 if taxes is None else taxes).ids)],
            })],
        })
        bill.action_post()
        return bill

    def _get_wizard(self, bills, payment_date='2026-04-24', withhold='withhold_pay'):
        """ The Pay wizard as the accountant opens it. Pass withhold=None to keep the wizard's own default. """
        return self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=bills.ids,
        ).create({
            'payment_date': payment_date,
            'group_payment': True,
            **({'withhold': withhold} if withhold else {}),
        })

    def _pay_bill(self, payment_date='2026-04-24', withhold='withhold_pay', **bill_vals):
        """ Withhold the PPh of a new bill and pay it, as the accountant does through the Pay wizard. """
        return self._get_wizard(self._create_bill(**bill_vals), payment_date, withhold)._create_payments()

    # -----------------
    # Validation
    # -----------------

    def test_download_ebupot_multi_company_user_error(self):
        """ Ensure that payments belonging to different companies cannot be gathered into one E-Bupot document. """
        payment_1 = self._pay_bill()
        payment_2 = self.env['account.payment'].create({
            'partner_id': self.partner_a.id,
            'amount': 1000,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'company_id': self.company_data_2['company'].id,
        })
        with self.assertRaisesRegex(UserError, "different companies"):
            (payment_1 | payment_2).download_ebupot()

    def test_download_ebupot_missing_npwp(self):
        """ Ensure that the download is blocked when either side is not properly identified,
        and that every problem is reported at once. """
        payment = self._pay_bill()
        payment.company_id.write({'vat': False, 'account_fiscal_country_id': self.env.ref('base.us').id})
        payment.partner_id.vat = False

        with self.assertRaises(ValidationError) as error:
            payment.download_ebupot()

        message = error.exception.args[0]
        self.assertIn("NPWP hasn't been configured", message, "The company must have an NPWP")
        self.assertIn("not located in Indonesia", message, "The company must be an Indonesian one")
        self.assertIn("NPWP/NIK for partner", message, "The vendor must have an NPWP/NIK")

    def test_download_ebupot_partner_without_country_is_allowed(self):
        """ Ensure that a partner without a country does not block the certificate (PO request). """
        payment = self._pay_bill()
        payment.partner_id.country_id = False
        payment.download_ebupot()  # does not raise
        self.assertTrue(payment.l10n_id_coretax_document)

    def test_download_ebupot_no_withholding(self):
        """ Ensure that a payment which withholds nothing has nothing to certify. """
        payment = self._pay_bill(withhold='payment')
        with self.assertRaisesRegex(ValidationError, "does not withhold any PPh"):
            payment.download_ebupot()

    def test_download_ebupot_no_object_code(self):
        """ Ensure that a withholding line whose origin resolves no object code cannot be reported. """
        payment = self._pay_bill()
        # Drop the origin so neither the line's tax nor its origin resolve an object code.
        payment.withholding_line_ids.write({'source_tax_id': False, 'tax_id': self.tax_facility.id})
        with self.assertRaisesRegex(ValidationError, "has no E-Bupot object code"):
            payment.download_ebupot()

    def test_ebupot_regenerate_is_validated(self):
        """ Ensure that regenerating from the document runs the same checks as generating from the payment. """
        payment = self._pay_bill()
        payment.download_ebupot()
        payment.partner_id.vat = False
        with self.assertRaisesRegex(ValidationError, "NPWP/NIK for partner"):
            payment.l10n_id_coretax_document.action_regenerate()

    # -----------------
    # Reported amounts
    # -----------------

    def test_ebupot_vals_from_withholding_line(self):
        """ Ensure that everything the certificate reports about a line comes from the bill and its withholding tax. """
        payment = self._pay_bill(price_unit=1000)
        vals = payment._l10n_id_ebupot_prepare_vals()[0]['data']

        self.assertEqual(len(vals), 1)
        self.assertEqual(float(vals[0]['TaxBase']), 1000.0, "The base is the vendor's income, before the PPh is withheld")
        self.assertEqual(
            {key: vals[0][key] for key in ('TaxObjectCode', 'TaxCertificate', 'Rate', 'Document', 'DocumentNumber', 'DocumentDate')},
            {
                'TaxObjectCode': '22-102-01',
                'TaxCertificate': 'N/A',
                'Rate': 0.5,
                'Document': 'TaxInvoice',
                'DocumentNumber': 'ABC123',
                'DocumentDate': '2026-04-24',
            },
        )

    def test_ebupot_facility_tax(self):
        """ Ensure that a facility (SKB) tax reports the object code of its Origin Tax, its own facility code
        and its 0% rate, whether the bill already carries it or the accountant sets it on the withholding line. """
        # The bill carries the 0% facility tax: the wizard must keep the line that owes nothing, so that the
        # accountant only sets the Origin Tax instead of re-entering everything by hand.
        wizard = self._get_wizard(self._create_bill(price_unit=1000, taxes=self.tax_facility), withhold=None)
        self.assertEqual(wizard.withhold, 'withhold_pay', "A pure 0% facility bill defaults to Withhold and Pay")
        self.assertRecordValues(wizard.withholding_line_ids, [{'tax_id': self.tax_facility.id, 'amount': 0.0}])
        wizard.withholding_line_ids.source_tax_id = self.tax_pph_23
        payment_from_bill = wizard._create_payments()

        # The bill carries the regular PPh, and the vendor holds an SKB: the accountant switches the Tax of the
        # withholding line to the facility one, which keeps the origin.
        wizard = self._get_wizard(self._create_bill(price_unit=1000, taxes=self.tax_pph_23))
        wizard.withholding_line_ids.tax_id = self.tax_facility
        payment_from_wizard = wizard._create_payments()
        self.assertEqual(payment_from_wizard.withholding_line_ids.source_tax_id, self.tax_pph_23)

        for source, payment in (('bill', payment_from_bill), ('wizard', payment_from_wizard)):
            with self.subTest(facility_set_on=source):
                vals = payment._l10n_id_ebupot_prepare_vals()[0]['data']
                self.assertEqual(len(vals), 1)
                self.assertEqual(vals[0]['TaxObjectCode'], '24-104-01', "Object code from the Origin Tax")
                self.assertEqual(vals[0]['TaxCertificate'], 'TaxExAr23', "Facility code from the line's tax")
                self.assertEqual(vals[0]['Rate'], 0.0, "The rate is the facility's, not the origin's")
                self.assertEqual(float(vals[0]['TaxBase']), 1000.0)

    def test_ebupot_tax_base(self):
        """ Ensure that the reported base is the untaxed amount of what is actually paid: the PPh is not
        deducted from it, nor the VAT added to it. """
        payment = self._pay_bill(price_unit=1000, taxes=self.tax_ppn | self.tax_pph_22)
        vals = payment._l10n_id_ebupot_prepare_vals()[0]['data']
        self.assertEqual(len(vals), 1, "Only the PPh is reported, not the VAT")
        self.assertEqual(vals[0]['TaxObjectCode'], '22-102-01')
        self.assertEqual(float(vals[0]['TaxBase']), 1000.0)

        # A payment settling half of what was billed withholds and reports half of the base.
        wizard = self._get_wizard(self._create_bill(price_unit=1000))
        wizard.amount = wizard.amount / 2
        partial_vals = wizard._create_payments()._l10n_id_ebupot_prepare_vals()[0]['data']
        self.assertEqual(len(partial_vals), 1)
        self.assertEqual(float(partial_vals[0]['TaxBase']), 500.0)

    def test_ebupot_default_withhold(self):
        """ Ensure that in Indonesia the Pay wizard defaults to settling the PPh together with the payment
        whenever there is one, and keeps the framework's 'Payment Only' default when there is nothing to withhold. """
        for move, expected, message in (
            (self._create_bill(taxes=self.tax_pph_23), 'withhold_pay', "A purchase PPh defaults to 'Withhold and Pay'"),
            (self._create_bill(taxes=self.tax_pph_23_sale, move_type='out_invoice'), 'withhold_pay', "A sales PPh defaults to 'Withhold and Pay'"),
            (self._create_bill(taxes=self.tax_ppn), 'payment', "A move without any PPh keeps the framework's 'Payment Only' default"),
        ):
            with self.subTest(move=move.move_type, taxes=move.invoice_line_ids.tax_ids.mapped('name')):
                defaults = self.env['account.payment.register'].with_context(
                    active_model='account.move', active_ids=move.ids,
                ).default_get(['withhold'])
                self.assertEqual(defaults['withhold'], expected, message)

    # -----------------
    # Grouping
    # -----------------

    def test_prepare_ebupot_grouping_by_payment_month(self):
        """ Ensure that payments are reported per month: those of the same month end up in the same certificate. """
        april_1 = self._pay_bill(ref='BILL1')
        april_2 = self._pay_bill(ref='BILL2', payment_date='2026-04-30')
        may = self._pay_bill(ref='BILL3', invoice_date='2026-05-01', payment_date='2026-05-01')

        result = (april_1 | april_2 | may)._l10n_id_ebupot_prepare_vals()
        self.assertEqual(
            {group['payment_month']: len(group['data']) for group in result},
            {'2026-04': 2, '2026-05': 1},
        )

    # -----------------
    # Document
    # -----------------

    def test_ebupot_document_type(self):
        """ Ensure that the document created for a payment is an E-Bupot one, since E-Bupot and E-Faktur
        share the same model and are only told apart by their type. """
        payment = self._pay_bill()
        payment.download_ebupot()
        document = payment.l10n_id_coretax_document

        self.assertRecordValues(document, [{'document_type': 'ebupot'}])
        self.assertEqual(document.payment_ids, payment)
        self.assertFalse(document.invoice_ids)
        self.assertTrue(document.attachment_ids)

    def test_ebupot_generated_xml(self):
        """ Ensure that the generated XML matches the expected one: the tax period, document
        and withholding date all come from the payment. """
        payment = self._pay_bill()

        payment.download_ebupot()
        result_xml = payment.l10n_id_coretax_document._get_xml_files()[0]['xml']

        self.assertXmlTreeEqual(etree.fromstring(result_xml), etree.fromstring(self.sample_xml))

    def test_ebupot_generated_xml_with_sp2d_number(self):
        """ Ensure that an SP2D number set on the payment is exported instead of the nil placeholder. """
        payment = self._pay_bill()
        payment.l10n_id_ebupot_sp2d_number = 'SP2D-001'

        payment.download_ebupot()
        result_xml = etree.fromstring(payment.l10n_id_coretax_document._get_xml_files()[0]['xml'])

        sp2d_node = result_xml.xpath('./ListOfBpu/Bpu/SP2DNumber')[0]
        self.assertEqual(sp2d_node.text, 'SP2D-001')
        self.assertNotIn('{http://www.w3.org/2001/XMLSchema-instance}nil', sp2d_node.attrib)
