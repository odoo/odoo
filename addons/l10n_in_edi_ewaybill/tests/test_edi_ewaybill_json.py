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
            "docNo": "INV/18-19/0001",
            "docDate": "01/01/2019",
            "fromGstin": "24AAGCC7144L6ZE",
            "fromTrdName": "Default Company",
            "fromAddr1": "Khodiyar Chowk",
            "fromAddr2": "Sala Number 3",
            "fromPlace": "Amreli",
            "fromPincode": 365220,
            "fromStateCode": 24,
            "actFromStateCode": 24,
            "toGstin": "24ABCPM8965E1ZE",
            "toTrdName": "Partner Intra State",
            "toAddr1": "Karansinhji Rd",
            "toAddr2": "Karanpara",
            "toPlace": "Rajkot",
            "toPincode": 360001,
            "actToStateCode": 24,
            "toStateCode": 24,
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
              "hsnCode": "333333",
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
            "cgstValue": 76.5,
            "sgstValue": 76.5,
            "igstValue": 0.0,
            "cessValue": 45.0,
            "cessNonAdvolValue": 1.59,
            "otherValue": 0.0,
            "totInvValue": 1999.59
        }
        self.assertDictEqual(json_value, expected, "Indian EDI send json value is not matched")

        # =================================== Different UOM Test ===========================================
        self.invoice.button_draft()
        self.invoice.invoice_line_ids.product_uom_id = self.env.ref('uom.product_uom_dozen')
        self.invoice.action_post()
        json_value = self.env["account.edi.format"]._l10n_in_edi_ewaybill_generate_json(self.invoice)
        self.assertListEqual(
            json_value['itemList'],
            [
                {
                  "productName": "product_a",
                  "hsnCode": "111111",
                  "productDesc": "product_a",
                  "quantity": 1.0,
                  "qtyUnit": "DOZ",
                  "taxableAmount": 900.0 * 12,
                  "cgstRate": 2.5,
                  "sgstRate": 2.5
                },
                {
                  "productName": "product_with_cess",
                  "hsnCode": "333333",
                  "productDesc": "product_with_cess",
                  "quantity": 1.0,
                  "qtyUnit": "DOZ",
                  "taxableAmount": 900.0 * 12,
                  "cgstRate": 6.0,
                  "sgstRate": 6.0,
                  "cessRate": 5.0
                }
            ],
            "Indian EDI send json UOM value is not matched"
        )

        #=================================== Full discount test =====================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_ewaybill_generate_json(self.invoice_full_discount)
        expected.update({
            "docNo": "INV/18-19/0002",
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
            "docNo": "INV/18-19/0003",
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

    def test_edi_ewaybill_transporter_gst(self):
        self.partner_b.write({
            "vat": False,
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 2",
            "zip": "500001",
            "state_id": self.env.ref("base.state_in_ts").id,
            "country_id": self.env.ref("base.in").id,
            "l10n_in_gst_treatment": "unregistered",
        })
        self.invoice.write({
            "l10n_in_type_id": self.env.ref("l10n_in_edi_ewaybill.type_tax_invoice_sub_type_supply"),
            "l10n_in_distance": 20,
            "l10n_in_mode": "1",
            "l10n_in_vehicle_no": "GJ11AA1234",
            "l10n_in_vehicle_type": "R",
            "l10n_in_transporter_id": self.partner_b.id,
        })
        expected = {
            "supplyType": "O",
            "docType": "INV",
            "subSupplyType": "1",
            "transactionType": 1,
            "transDistance": "20",
            "docNo": "INV/18-19/0001",
            "docDate": "01/01/2019",
            "fromGstin": "24AAGCC7144L6ZE",
            "fromTrdName": "Default Company",
            "fromAddr1": "Khodiyar Chowk",
            "fromAddr2": "Sala Number 3",
            "fromPlace": "Amreli",
            "fromPincode": 365220,
            "fromStateCode": 24,
            "actFromStateCode": 24,
            "toGstin": "24ABCPM8965E1ZE",
            "toTrdName": "Partner Intra State",
            "toAddr1": "Karansinhji Rd",
            "toAddr2": "Karanpara",
            "toPlace": "Rajkot",
            "toPincode": 360001,
            "actToStateCode": 24,
            "toStateCode": 24,
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
              "hsnCode": "333333",
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
            "cgstValue": 76.5,
            "sgstValue": 76.5,
            "igstValue": 0.0,
            "cessValue": 45.0,
            "cessNonAdvolValue": 1.59,
            "otherValue": 0.0,
            "totInvValue": 1999.59,
            "transMode": "1",
            "vehicleNo": "GJ11AA1234",
            "vehicleType": "R",
            "transporterName": self.partner_b.name,
        }
        json_value = self.env["account.edi.format"]._l10n_in_edi_ewaybill_generate_json(self.invoice)
        self.assertDictEqual(json_value, expected, "Indian EDI Ewaybill without transporter GST sent json value is not matched")

        # =================================== Ewaybill Through IRN =============================================
        json_value = self.env["account.edi.format"]._l10n_in_edi_irn_ewaybill_generate_json(self.invoice)
        expected = {
            "Irn": None,
            "Distance": 20,
            "TransMode": "1",
            "TransName": self.partner_b.name,
            "VehType": "R",
            "VehNo": "GJ11AA1234"
        }
        self.assertDictEqual(json_value, expected, "Indian EDI Ewaybill through IRN without transporter GST sent json value is not matched")
