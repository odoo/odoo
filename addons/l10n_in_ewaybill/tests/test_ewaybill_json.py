# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import _
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEwaybillJson(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls.init_invoice("out_invoice", post=False, products=cls.product_a + cls.product_with_cess)
        cls.invoice.write({
            "invoice_line_ids": [(1, l_id, {"discount": 10}) for l_id in cls.invoice.invoice_line_ids.ids]
        })
        cls.invoice.action_post()
        cls.invoice_full_discount = cls.init_invoice("out_invoice", post=False, products=cls.product_a)
        cls.invoice_full_discount.write({
            "invoice_line_ids": [(1, l_id, {"discount": 100}) for l_id in cls.invoice_full_discount.invoice_line_ids.ids]})
        cls.invoice_full_discount.action_post()
        cls.invoice_zero_qty = cls.init_invoice("out_invoice", post=False, products=cls.product_a)
        cls.invoice_zero_qty.write({
            "invoice_line_ids": [(1, l_id, {"quantity": 0}) for l_id in cls.invoice_zero_qty.invoice_line_ids.ids]})
        cls.invoice_zero_qty.action_post()

    def test_edi_json(self):
        default_ewaybill_vals = {
            'distance': 20,
            'type_id': self.env.ref("l10n_in_ewaybill.type_tax_invoice_sub_type_supply").id,
            'mode': "1",
            'vehicle_no': "GJ11AA1234",
            'vehicle_type': "R",
        }
        Ewaybill = self.env['l10n.in.ewaybill']
        ewaybill_invoice = Ewaybill.create({
            'account_move_id': self.invoice.id,
            **default_ewaybill_vals
        })
        ewaybill_invoice_full_discount = Ewaybill.create({
            'account_move_id': self.invoice_full_discount.id,
            **default_ewaybill_vals
        })
        ewaybill_invoice_zero_qty = Ewaybill.create({
            'account_move_id': self.invoice_zero_qty.id,
            **default_ewaybill_vals
        })
        json_value = ewaybill_invoice._ewaybill_generate_direct_json()
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
        json_value = ewaybill_invoice._ewaybill_generate_direct_json()
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

        # =================================== Full discount test =====================================
        json_value = ewaybill_invoice_full_discount._ewaybill_generate_direct_json()
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

        # =================================== Zero quantity test =============================================
        json_value = ewaybill_invoice_zero_qty._ewaybill_generate_direct_json()
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

    def test_ewaybill_zero_distance(self):
        """
        Ewaybill Zero distance test
        """
        ewaybill = self.env['l10n.in.ewaybill'].create({
            'type_id': self.env.ref('l10n_in_ewaybill.type_tax_invoice_sub_type_supply').id,
            'account_move_id': self.invoice.id,
            'transporter_id': self.partner_a.id,
            'mode': '2',
            'distance': 0,
            'transportation_doc_no': 123456789,
            'transportation_doc_date': '2024-04-26'
        })

        # Sub-test: Extract `Distance` when multiple alerts in response
        with self.subTest(scenario="Extract distance when multiple alerts in response"):
            expected_distance = 118
            response = {
                'status_cd': '1',
                'status_desc': 'EWAYBILL request succeeds',
                'data': {
                    'ewayBillNo': 123456789012,
                    'ewayBillDate': '26/02/2024 12:09:43 PM',
                    'validUpto': '27/02/2024 12:09:43 PM',
                    "alert": ", Distance between these two pincodes is 118, "
                }
            }
            distance_val = ewaybill._l10n_in_ewaybill_handle_zero_distance_alert_if_present(response.get('data'))
            self.assertEqual(distance_val['distance'], expected_distance)

        # Sub-test: Extract `Distance` when single alert in response
        with self.subTest(scenario="Extract distance when single alert in response"):
            ewaybill.distance = 0
            expected_distance = 222
            response = {
                'status_cd': '1',
                'status_desc': 'EWAYBILL request succeeds',
                'data': {
                    'ewayBillNo': 987654321012,
                    'ewayBillDate': '08/04/2025 11:04:04 AM',
                    'validUpto': '09/04/2025 11:04:04 AM',
                    'alert': 'Distance between these two pincodes is 222'
                }
            }
            distance_val = ewaybill._l10n_in_ewaybill_handle_zero_distance_alert_if_present(response.get('data'))
            self.assertEqual(distance_val['distance'], expected_distance)

    def test_ewaybill_transporter_gst(self):
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
        ewaybill_invoice = self.env['l10n.in.ewaybill'].create({
            "type_id": self.env.ref("l10n_in_ewaybill.type_tax_invoice_sub_type_supply").id,
            "account_move_id": self.invoice.id,
            "distance": 20,
            "mode": "1",
            "vehicle_no": "GJ11AA1234",
            "vehicle_type": "R",
            "transporter_id": self.partner_b.id,
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
        json_value = ewaybill_invoice._ewaybill_generate_direct_json()
        self.assertDictEqual(json_value, expected, "Indian EDI Ewaybill without transporter GST sent json value is not matched")

        # ===================== Unregistered Transporter (No GSTIN) and vehicle number is not present =====================
        ewaybill_invoice_2 = self.env['l10n.in.ewaybill'].create({
            "type_id": self.env.ref("l10n_in_ewaybill.type_tax_invoice_sub_type_supply").id,
            "account_move_id": self.invoice.id,
            "distance": 20,
            "mode": "1",
            "transportation_doc_no": "123456789",
            "vehicle_type": "R",
            "transporter_id": self.partner_b.id,
        })
        expected_msg = _('- Transporter %s does not have a valid GST Number', self.partner_b.name)
        self.assertEqual(ewaybill_invoice_2._check_transporter(), [expected_msg])
