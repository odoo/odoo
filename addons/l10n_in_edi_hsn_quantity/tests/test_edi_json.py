# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiJson(AccountTestInvoicingCommon):


    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_in.indian_chart_template_standard"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data["company"].write({
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 1",
            "zip": "500001",
            "state_id": cls.env.ref("base.state_in_ts").id,
            "country_id": cls.env.ref("base.in").id,
            "vat": "36AABCT1332L011",
        })
        cls.partner_a.write({
            "vat": "36BBBFF5679L8ZR",
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 2",
            "zip": "500001",
            "state_id": cls.env.ref("base.state_in_ts").id,
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
        })
        cls.product_a.write({
            "l10n_in_hsn_code": "01111"})
        cls.invoice_zero_hsn_quantity = cls.init_invoice("out_refund", post=False, products=cls.product_a)
        cls.invoice_zero_hsn_quantity.write({
            "invoice_line_ids": [(1, l_id, {"quantity": 1, "hsn_quantity": 0}) for l_id in cls.invoice_zero_hsn_quantity.invoice_line_ids.ids],
            "invoice_date": '2023-01-01',
            "name": 'RINV/2023/00001',
            })
        cls.invoice_zero_hsn_quantity.action_post()


    def test_edi_json(self):
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_invoice_json(self.invoice_zero_hsn_quantity)
        expected = {
                'Version': '1.1',
                'TranDtls': {
                    'TaxSch': 'GST',
                    'SupTyp': 'B2B',
                    'RegRev': 'N',
                    'IgstOnIntra': 'N'
                },
                'DocDtls': {
                    'Typ': 'CRN',
                    'No': 'RINV/2023/00001',
                    'Dt': '01/01/2023'
                },
                'SellerDtls': {
                    'Addr1': 'Block no. 401',
                    'Loc': 'City 1',
                    'Pin': 500001,
                    'Stcd': '36',
                    'Addr2': 'Street 2',
                    'LglNm': 'company_1_data',
                    'GSTIN': '36AABCT1332L011'
                },
                'BuyerDtls': {
                    'Addr1': 'Block no. 401',
                    'Loc': 'City 2',
                    'Pin': 500001,
                    'Stcd': '36',
                    'Addr2': 'Street 2',
                    'POS': '36',
                    'LglNm': 'partner_a',
                    'GSTIN': '36BBBFF5679L8ZR'
                },
                'ItemList': [
                    {
                    'SlNo': '1',
                    'PrdDesc': 'product_a',
                    'IsServc': 'N',
                    'HsnCd': '01111',
                    'Qty': 0.0,
                    'Unit': 'UNT',
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
                    'TotItemVal': 1050.0
                    }
                ],
                'ValDtls': {
                    'AssVal': 1000.0,
                    'CgstVal': 25.0,
                    'SgstVal': 25.0,
                    'IgstVal': 0.0,
                    'CesVal': 0.0,
                    'StCesVal': 0.0,
                    'RndOffAmt': 0.0,
                    'TotInvVal': 1050.0
                }
        }
        self.assertDictEqual(json_value, expected, "Indian EDI with 0(zero) hsn_quantity sent json value is not matched")
