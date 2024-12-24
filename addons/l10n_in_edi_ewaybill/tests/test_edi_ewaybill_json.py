# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.l10n_in_edi.tests.test_edi_json import TestEdiJson
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiEwaybillJson(TestEdiJson):

    def test_edi_json(self):
        self.env['account.move'].browse((
            self.invoice.id,
            self.invoice_full_discount.id,
            self.invoice_zero_qty.id,
            self.invoice_reverse.id,
        )).write({
            "l10n_in_type_id": self.env.ref("l10n_in_edi_ewaybill.type_tax_invoice_sub_type_supply"),
            "l10n_in_distance": 20,
            "l10n_in_mode": "1",
            "l10n_in_vehicle_no": "GJ11AA1234",
            "l10n_in_vehicle_type": "R",
        })
        json_value = self.env["account.edi.format"]._l10n_in_edi_ewaybill_generate_json(self.invoice)
        expected = {
            "supplyType": "O",
            "docType": "INV",
            "subSupplyType": "1",
            "transactionType": 1,
            "transDistance": "20",
            "transMode": "1",
            "vehicleNo": "GJ11AA1234",
            "vehicleType": "R",
            "docNo": "INV/2019/00001",
            "docDate": "01/01/2019",
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
              "hsnCode": "111111",
              "productDesc": "product_a",
              "quantity": 1.0,
              "qtyUnit": "UNT",
              "taxableAmount": 900.0,
              "cgstRate": 2.5,
              "sgstRate": 2.5
            },
            {
              "productName": "product_with_cess",
              "hsnCode": "222222",
              "productDesc": "product_with_cess",
              "quantity": 1.0,
              "qtyUnit": "UNT",
              "taxableAmount": 900.0,
              "cgstRate": 6.0,
              "sgstRate": 6.0,
              "cessRate": 5.0
            }
            ],
            "totalValue": 1800.0,
            "cgstValue": 79.3,
            "sgstValue": 79.3,
            "igstValue": 0.0,
            "cessValue": 45.0,
            "cessNonAdvolValue": 1.59,
            "otherValue": 0.0,
            "totInvValue": 2005.19
        }
        self.assertDictEqual(json_value, expected, "Indian EDI send json value is not matched")

        # =================================== Credit Note Test =============================================
        credit_note_expected = expected.copy()
        credit_note_expected.update({
            'docDate': '25/12/2023',
            'docNo': 'RINV/2023/00001',
            'supplyType': 'I',
            "fromGstin": expected['toGstin'],
            "fromTrdName": expected['toTrdName'],
            "fromAddr1": expected['toAddr1'],
            "fromAddr2": expected['toAddr2'],
            "fromPlace": expected['toPlace'],
            "fromPincode": expected['toPincode'],
            "fromStateCode": expected['toStateCode'],
            "actFromStateCode": expected['actToStateCode'],
            "toGstin": expected['fromGstin'],
            "toTrdName": expected['fromTrdName'],
            "toAddr1": expected['fromAddr1'],
            "toAddr2": expected['fromAddr2'],
            "toPlace": expected['fromPlace'],
            "toPincode": expected['fromPincode'],
            "toStateCode": expected['fromStateCode'],
            "actToStateCode": expected['actFromStateCode'],
        })
        self.assertDictEqual(
            self.env.ref(
                'l10n_in_edi_ewaybill.edi_in_ewaybill_json_1_03'
            )._l10n_in_edi_ewaybill_generate_json(self.invoice_reverse),
            credit_note_expected,
        )

        #=================================== Full discount test =====================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_ewaybill_generate_json(self.invoice_full_discount)
        expected.update({
            "docNo": "INV/2019/00002",
            "itemList": [{
                "productName": "product_a", "hsnCode": "111111", "productDesc": "product_a", "quantity": 1.0,
                "qtyUnit": "UNT", "taxableAmount": 0.0, "cgstRate": 0.0, "sgstRate": 0.0, 'igstRate': 0.0,
            }],
            "totalValue": 0.0,
            "cgstValue": 0.0,
            "sgstValue": 0.0,
            "igstValue": 0.0,
            "cessValue": 0.0,
            "cessNonAdvolValue": 0.00,
            "otherValue": 0.0,
            "totInvValue": 0.0
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with 100% discount sent json value is not matched")

        #=================================== Zero quantity test =============================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_ewaybill_generate_json(self.invoice_zero_qty)
        expected.update({
            "docNo": "INV/2019/00003",
            "itemList": [{
                "productName": "product_a", "hsnCode": "111111", "productDesc": "product_a", "quantity": 0.0,
                "qtyUnit": "UNT", "taxableAmount": 0.0, "cgstRate": 0.0, "sgstRate": 0.0, 'igstRate': 0.0,
            }],
            "totalValue": 0.0,
            "cgstValue": 0.0,
            "sgstValue": 0.0,
            "igstValue": 0.0,
            "cessValue": 0.0,
            "cessNonAdvolValue": 0.00,
            "otherValue": 0.0,
            "totInvValue": 0.0
        })
        self.assertDictEqual(json_value, expected, "Indian EDI with 0(zero) quantity sent json value is not matched")
