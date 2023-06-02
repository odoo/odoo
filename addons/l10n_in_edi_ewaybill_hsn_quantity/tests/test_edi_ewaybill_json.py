# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_in_edi_hsn_quantity.tests.test_edi_json import TestEdiJson
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiEwaybillJson(TestEdiJson):


    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_in.indian_chart_template_standard"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.invoice_zero_hsn_quantity.write({
            "l10n_in_type_id": cls.env.ref("l10n_in_edi_ewaybill.type_tax_invoice_sub_type_supply"),
            "l10n_in_distance": 20,
            "l10n_in_mode": "1",
            "l10n_in_vehicle_no": "GJ11AA1234",
            "l10n_in_vehicle_type": "R",})

    def test_edi_ewaybill_json(self):
        json_value = self.env["account.edi.format"]._l10n_in_edi_ewaybill_generate_json(self.invoice_zero_hsn_quantity)
        expected = {
            "supplyType": "O",
            "docType": "INV",
            "subSupplyType": "1",
            "transactionType": 1,
            "transDistance": "20",
            "transMode": "1",
            "vehicleNo": "GJ11AA1234",
            "vehicleType": "R",
            "docNo": "RINV/2023/00001",
            "docDate": "01/01/2023",
            "fromGstin": "36AABCT1332L011",
            "fromTrdName": "company_1_data",
            "fromAddr1": "Block no. 401",
            "fromAddr2": "Street 2",
            "fromPlace": "City 1",
            "fromPincode": 500001,
            "fromStateCode": 36,
            "actFromStateCode": 36,
            "toGstin": "36BBBFF5679L8ZR",
            "toTrdName": "partner_a",
            "toAddr1": "Block no. 401",
            "toAddr2": "Street 2",
            "toPlace": "City 2",
            "toPincode": 500001,
            "actToStateCode": 36,
            "toStateCode": 36,
            "itemList": [
            {
              "productName": "product_a",
              "hsnCode": "01111",
              "productDesc": "product_a",
              "quantity": 0.0,
              "qtyUnit": "UNT",
              "taxableAmount": 1000.0,
              "cgstRate": 2.5,
              "sgstRate": 2.5
            },
            ],
            'totalValue': 1000.0,
            'cgstValue': 25.0,
            'sgstValue': 25.0,
            'igstValue': 0.0,
            'cessValue': 0.0,
            'cessNonAdvolValue': 0.0,
            'otherValue': 0.0,
            'totInvValue': 1050.0,

        }
        self.maxDiff = None
        self.assertDictEqual(json_value, expected, "Indian EDI with 0(zero) HSN quantity sent json value is not matched")
