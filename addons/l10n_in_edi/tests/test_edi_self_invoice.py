from odoo.tests import tagged
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiSelfInvoice(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.default_company.l10n_in_edi_feature = True

        AccountChartTemplate = cls.env['account.chart.template']
        cls.igst_purchase_18_service_rc = AccountChartTemplate.ref('igst_purchase_18_service_rc')

        cls.self_invoice_journal = cls.env['account.journal'].create({
            'name': "Self Invoice Test",
            'code': "STES",
            'type': 'purchase',
            'l10n_in_self_invoice': True,
            'company_id': cls.default_company.id,
        })
        cls.unregistered_vendor = cls.env['res.partner'].create({
            'name': "Unregistered Vendor",
            'l10n_in_gst_treatment': 'unregistered',
            'street': "Karansinhji Rd",
            'city': "Rajkot",
            'zip': "360001",
            'state_id': cls.state_in_gj.id,
            'country_id': cls.country_in.id,
        })
        cls.partner_foreign.l10n_in_gst_treatment = 'overseas'
        cls.product_service = cls.env['product.product'].create({
            'name': "Consulting Service",
            'type': 'service',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'l10n_in_hsn_code': "998311",
        })

    def _create_self_invoice(self, partner, product, taxes):
        return self._create_invoice(
            move_type='in_invoice',
            journal_id=self.self_invoice_journal,
            partner_id=partner,
            invoice_date='2026-10-16',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=product, price_unit=1000.0, tax_ids=taxes),
            ],
            post=True,
        )

    def test_self_invoice_rcm_domestic(self):
        bill = self._create_self_invoice(self.unregistered_vendor, self.product_a, self.sgst_purchase_5_rc)
        self.assertEqual(bill.l10n_in_edi_status, 'to_send')

        json_value = bill._l10n_in_edi_generate_invoice_json()
        self.assertDictEqual(
            json_value['TranDtls'],
            {'TaxSch': 'GST', 'SupTyp': 'RCMDOM', 'RegRev': 'Y', 'IgstOnIntra': 'N'},
        )
        self.assertDictEqual(
            json_value['DocDtls'],
            {'Typ': 'INV', 'No': bill.name, 'Dt': '16/10/2026'},
        )
        self.assertDictEqual(
            json_value['SellerDtls'],
            {
                'Addr1': "Karansinhji Rd",
                'Loc': "Rajkot",
                'Pin': 360001,
                'Stcd': "24",
                'LglNm': "Unregistered Vendor",
                'GSTIN': "URP",
            },
        )
        self.assertEqual(json_value['BuyerDtls']['GSTIN'], "24AAGCC7144L6ZE")
        self.assertEqual(json_value['BuyerDtls']['POS'], "24")
        self.assertDictEqual(
            json_value['ItemList'][0],
            {
                'SlNo': "1",
                'PrdDesc': "product_a",
                'IsServc': "N",
                'HsnCd': "111111",
                'Qty': 1.0,
                'Unit': "UNT",
                'UnitPrice': 1000.0,
                'TotAmt': 1000.0,
                'Discount': 0.0,
                'AssAmt': 1000.0,
                'GstRt': 5.0,
                'IgstAmt': 0.0,
                'CgstAmt': 25.0,
                'SgstAmt': 25.0,
                'CesRt': 0.0,
                'CesAmt': 0.0,
                'CesNonAdvlAmt': 0.0,
                'StateCesRt': 0.0,
                'StateCesAmt': 0.0,
                'StateCesNonAdvlAmt': 0.0,
                'OthChrg': 0.0,
                'TotItemVal': 1000.0,
            },
        )
        self.assertDictEqual(
            json_value['ValDtls'],
            {
                'AssVal': 1000.0,
                'CgstVal': 25.0,
                'SgstVal': 25.0,
                'IgstVal': 0.0,
                'CesVal': 0.0,
                'StCesVal': 0.0,
                'Discount': 0.0,
                'RndOffAmt': 0.0,
                'TotInvVal': 1000.0,
            },
        )
        self.assertNotIn('ShipDtls', json_value)
        self.assertNotIn('DispDtls', json_value)

    def test_self_invoice_rcm_import(self):
        bill = self._create_self_invoice(self.partner_foreign, self.product_service, self.igst_purchase_18_service_rc)
        self.assertEqual(bill.l10n_in_edi_status, 'to_send')

        json_value = bill._l10n_in_edi_generate_invoice_json()
        self.assertDictEqual(
            json_value['TranDtls'],
            {'TaxSch': 'GST', 'SupTyp': 'RCMIMP', 'RegRev': 'Y', 'IgstOnIntra': 'N'},
        )
        self.assertDictEqual(
            json_value['SellerDtls'],
            {
                'Addr1': "351 Horner Chapel Rd",
                'Loc': "Peebles",
                'Pin': 999999,
                'Stcd': "96",
                'LglNm': "Foreign Partner",
                'GSTIN': "URP",
            },
        )
        self.assertEqual(json_value['BuyerDtls']['GSTIN'], "24AAGCC7144L6ZE")
        self.assertEqual(json_value['BuyerDtls']['POS'], "24")
        item = json_value['ItemList'][0]
        self.assertEqual(
            {key: item[key] for key in ('IsServc', 'HsnCd', 'GstRt', 'IgstAmt', 'AssAmt', 'TotItemVal', 'OrgCntry')},
            {
                'IsServc': "Y",
                'HsnCd': "998311",
                'GstRt': 18.0,
                'IgstAmt': 180.0,
                'AssAmt': 1000.0,
                'TotItemVal': 1000.0,
                'OrgCntry': "US",
            },
        )
        self.assertEqual(json_value['ValDtls']['IgstVal'], 180.0)
        self.assertEqual(json_value['ValDtls']['TotInvVal'], 1000.0)
        self.assertNotIn('ExpDtls', json_value)

    def test_self_invoice_rcm_import_goods_not_allowed(self):
        bill = self._create_self_invoice(self.partner_foreign, self.product_service, self.igst_purchase_18_service_rc)
        bill.invoice_line_ids.l10n_in_hsn_code = "111111"
        self.assertEqual(len(bill._l10n_in_edi_self_invoice_error_validation()), 1)

    def test_regular_bill_not_eligible(self):
        bill = self._create_invoice(
            move_type='in_invoice',
            partner_id=self.unregistered_vendor,
            invoice_date='2026-10-16',
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=1000.0, tax_ids=self.sgst_purchase_5_rc),
            ],
            post=True,
        )
        self.assertFalse(bill.l10n_in_edi_status)
