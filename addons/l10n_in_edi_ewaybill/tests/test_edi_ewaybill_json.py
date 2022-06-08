# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiEwaybillJson(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_in.indian_chart_template_standard"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.maxDiff = None
        cls.company_data["company"].write({
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 1",
            "zip": "247667",
            "state_id": cls.env.ref("base.state_in_uk").id,
            "country_id": cls.env.ref("base.in").id,
            "vat": "05AAACH6188F1ZM",
        })
        cls.partner_a.write({
            "vat": "05AAACH6605F1Z0",
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 2",
            "zip": "248001",
            "state_id": cls.env.ref("base.state_in_uk").id,
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
        })
        cls.product_a.write({"type": "product", "l10n_in_hsn_code": "01111"})
        cls.invoice = cls.init_invoice("out_invoice", post=True, products=cls.product_a)

    def test_edi_ewaybill_json(self):
        json_value = self.env["account.edi.format"]._l10n_in_edi_generate_ewaybill_json(self.invoice)
        expected = {
            'supplyType': 'O',
            'docNo': 'INV/2019/00001',
            'docDate': '01/01/2019',
            'fromGstin': '05AAACH6188F1ZM',
            'fromTrdName': 'company_1_data',
            'fromStateCode': 5,
            'fromAddr1': 'Block no. 401',
            'fromAddr2': 'Street 2',
            'fromPlace': 'City 1',
            'fromPincode': 247667,
            'actFromStateCode': 5,
            'toGstin': '05AAACH6605F1Z0',
            'toTrdName': 'partner_a',
            'toStateCode': 5,
            'toAddr1': 'Block no. 401',
            'toAddr2': 'Street 2',
            'toPlace': 'City 2',
            'toPincode': 248001,
            'actToStateCode': 5,
            'itemList': [{
                'productName': 'product_a',
                'hsnCode': '01111',
                'productDesc': 'product_a',
                'quantity': 1.0,
                'qtyUnit': 'UNT',
                'taxableAmount': 1000.0,
                'cgstRate': 2.5,
                'sgstRate': 2.5
            }],
            'totalValue': 1000.0,
            'cgstValue': 25.0,
            'sgstValue': 25.0,
            'igstValue': 0.0,
            'cessValue': 0.0,
            'cessNonAdvolValue': 0.0,
            'otherValue': 0.0,
            'totInvValue': 1050.0,
            'subSupplyType': '1',
            'docType': 'INV',
            'transactionType': 1,
            'transDistance': '50',
            'transMode': '1',
            'transDocNo': '',
            'vehicleNo': 'KA12KA1234',
            'vehicleType': 'R'
        }
        self.assertDictEqual(json_value, expected, "Indian E-Waybill send json value is not matched")
