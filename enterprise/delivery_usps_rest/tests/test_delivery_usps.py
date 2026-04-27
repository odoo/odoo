# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from contextlib import contextmanager
import requests
from unittest.mock import patch

from odoo import Command
from odoo.tests import Form, tagged, TransactionCase


@tagged('-standard', 'external')
class TestDeliveryUSPS(TransactionCase):

    def setUp(self):
        super().setUp()

        self.iPadMini = self.env['product.product'].create({
            'name': 'iPad Mini',
            'weight': 0.01,
        })
        self.large_desk = self.env['product.product'].create({
            'name': 'Large Desk',
            'weight': 0.01,
        })

        self.your_company = self.env.ref('base.main_partner')
        self.agrolait = self.env['res.partner'].create({
            'name': 'Agrolait',
            'phone': '(603)-996-3829',
            'street': "rue des Bourlottes, 9",
            'street2': "",
            'city': "Ramillies",
            'zip': 1367,
            'state_id': False,
            'country_id': self.env.ref('base.be').id,
        })
        self.think_big_system = self.env['res.partner'].create({
            'name': 'Think Big Systems',
            'phone': 3132223456,
            'street': '1 Infinite Loop',
            'street2': 'Tower 2',
            'city': 'Cupertino',
            'state_id': self.env.ref('base.state_us_13').id,
            'country_id': self.env.ref('base.us').id,
            'zip': '95014-2083'
        })

        self.delivery_usps_domestic = self.env.ref('delivery_usps_rest.delivery_carrier_usps_domestic')
        self.delivery_usps_international = self.env.ref('delivery_usps_rest.delivery_carrier_usps_international')

        self.uom_unit = self.env.ref('uom.product_uom_unit')

    def wiz_put_in_pack(self, picking):
        """ Helper to use the 'choose.delivery.package' wizard
        in order to call the 'action_put_in_pack' method. """
        wiz_action = picking.action_put_in_pack()
        self.assertEqual(wiz_action['res_model'], 'choose.delivery.package', 'Wrong wizard returned')
        wiz = Form(self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'delivery_package_type_id': picking.carrier_id.usps_default_package_type_id.id,
        }))
        choose_deivery_carrier = wiz.save()
        choose_deivery_carrier.action_put_in_pack()

    def test_01_usps_basic_us_domestic_flow(self):
        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        so_vals = {'partner_id': self.think_big_system.id,
                   'order_line': [Command.create(sol_vals)]}

        sale_order = self.env['sale.order'].create(so_vals)
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.delivery_usps_domestic.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "USPS delivery cost for this SO has not been correctly estimated.")

        choose_delivery_carrier.button_confirm()
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity = 1.0
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "USPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "USPS carrying price is probably incorrect")

        picking.cancel_shipment()

        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_02_usps_basic_us_international_flow(self):
        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [Command.create(sol_vals)]}

        sale_order = self.env['sale.order'].create(so_vals)
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.delivery_usps_international.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "USPS delivery cost for this SO has not been correctly estimated.")

        choose_delivery_carrier.button_confirm()
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity = 1.0
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "USPS did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "USPS carrying price is probably incorrect")

        picking.cancel_shipment()

        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_03_usps_multipackage_domestic_flow(self):
        sol_1_vals = {
            'product_id': self.iPadMini.id,
            'name': "[A1232] Large Cabinet",
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': self.iPadMini.lst_price
        }
        sol_2_vals = {
            'product_id': self.large_desk.id,
            'name': "[A1233] Large Desk",
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': self.large_desk.lst_price
        }

        so_vals = {
            'partner_id': self.think_big_system.id,
            'carrier_id': self.delivery_usps_domestic.id,
            'order_line': [Command.create(sol_1_vals), Command.create(sol_2_vals)]
        }
        sale_order = self.env['sale.order'].create(so_vals)

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.delivery_usps_domestic.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "USPS delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        move0 = picking.move_ids[0]
        move0.quantity = 1.0
        move0.picked = True
        self.wiz_put_in_pack(picking)

        move1 = picking.move_ids[1]
        move1.quantity = 1.0
        move1.picked = True
        self.wiz_put_in_pack(picking)

        self.assertEqual(len(picking.move_line_ids.mapped('result_package_id')), 2, "Two packages should have been created at this point.")
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "USPS did not return any tracking number")
        tracking_numbers = picking.carrier_tracking_ref.split(',')
        self.assertEqual(len(tracking_numbers), 2, "Two tracking numbers should have been returned.")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")


@contextmanager
def _mock_request_call():
    RATE_MOCK_RESPONSE = {
        "rateOptions": [
            {
                "totalBasePrice": 9.25,
                "rates": [
                    {
                        "SKU": "DPXX0XXXXR01010",
                        "description": "Priority Mail Nonmachinable Single-piece",
                        "priceType": "RETAIL",
                        "price": 9.25,
                        "weight": 0.03,
                        "dimWeight": 0,
                        "fees": [],
                        "startDate": "2024-01-21",
                        "endDate": "",
                        "mailClass": "PRIORITY_MAIL",
                        "zone": "01"
                    }
                ]
            },
            {
                "totalBasePrice": 30.45,
                "rates": [
                    {
                        "SKU": "DEXX0XXXXR01005",
                        "description": "Priority Mail Express Nonmachinable Single-piece",
                        "priceType": "RETAIL",
                        "price": 30.45,
                        "weight": 0.03,
                        "dimWeight": 0,
                        "fees": [],
                        "startDate": "2024-01-21",
                        "endDate": "",
                        "mailClass": "PRIORITY_MAIL_EXPRESS",
                        "zone": "01"
                    }
                ]
            },
            {
                "totalBasePrice": 5,
                "rates": [
                    {
                        "SKU": "DUXP0XXXUR01010",
                        "description": "USPS Ground Advantage Nonmachinable Single-piece",
                        "priceType": "RETAIL",
                        "price": 5,
                        "weight": 0.03,
                        "dimWeight": 0,
                        "fees": [],
                        "startDate": "2024-01-21",
                        "endDate": "",
                        "mailClass": "USPS_GROUND_ADVANTAGE",
                        "zone": "01"
                    }
                ]
            },
            {
                "totalBasePrice": 2.95,
                "rates": [
                    {
                        "SKU": "DFOFXXXUXR00010",
                        "description": "Connect Local Mail",
                        "priceType": "RETAIL",
                        "price": 2.95,
                        "weight": 0.03,
                        "dimWeight": 0,
                        "fees": [],
                        "startDate": "2024-01-21",
                        "endDate": "",
                        "mailClass": "USPS_GROUND_ADVANTAGE",
                        "zone": "00"
                    }
                ]
            }
        ]
    }
    INTERNATIONAL_RATE_MOCK_RESPONSE = {
    "rateOptions": [
            {
                "rates": [
                    {
                        "mailClass": "GLOBAL_EXPRESS_GUARANTEED",
                        "priceType": "COMMERCIAL_BASE",
                        "dimWeight": 0,
                        "zone": "03",
                        "fees": [],
                        "startDate": "2024-01-21",
                        "endDate": "",
                        "SKU": "IGXX0XXXXB03005",
                        "price": 91.44,
                        "weight": 0.03,
                        "description": "Global Express Guaranteed Nonmachinable ISC Single-piece"
                    }
                ],
                "totalBasePrice": 91.44
            },
            {
                "rates": [
                    {
                        "mailClass": "GLOBAL_EXPRESS_GUARANTEED",
                        "priceType": "COMMERCIAL_BASE",
                        "dimWeight": 0,
                        "zone": "03",
                        "fees": [],
                        "startDate": "2024-01-21",
                        "endDate": "",
                        "SKU": "IGXX0XXXXB03005",
                        "price": 91.44,
                        "weight": 0.03,
                        "description": "Global Express Guaranteed Nonmachinable ISC Single-piece"
                    }
                ],
                "totalBasePrice": 91.44
            },
            {
                "rates": [
                    {
                        "mailClass": "PRIORITY_MAIL_INTERNATIONAL",
                        "priceType": "COMMERCIAL_BASE",
                        "dimWeight": 0,
                        "zone": "04",
                        "fees": [],
                        "startDate": "2024-01-21",
                        "endDate": "",
                        "SKU": "IPXX0XXXXB04010",
                        "price": 61.8,
                        "weight": 0.03,
                        "description": "Priority Mail International Nonmachinable ISC Single-piece"
                    }
                ],
                "totalBasePrice": 61.8
            }
        ]
    }
    SHIP_MOCK_RESPONSE = """--6p7jEqRvNj5nnsuzalbLR5zG
Content-Type: application/json
Content-Disposition: form-data; name="labelMetadata"\r
\r
{"labelAddress":{"streetAddress":"STE 150","secondaryAddress":"1100 WYOMING ST","city":"SAINT LOUIS","state":"MO","ZIPCode":"63118","ZIPPlus4":"2628","firstName":"JOE","lastName":"DOE","ignoreBadAddress":false},"routingInformation":"420631182628","trackingNumber":"9205590109770100242076","postage":7.9,"extraServices":[{"name":"USPS Tracking","price":0.0,"SKU":"DXTP0EXXXCX0000"}],"zone":"01","commitment":{"name":"6 Days","scheduleDeliveryDate":"2024-06-01"},"weightUOM":"LB","weight":0.5,"fees":[],"SKU":"DPXX0XXXXC01005"}
--6p7jEqRvNj5nnsuzalbLR5zG
Content-Type: application/pdf
Content-Disposition: form-data; filename="labelImage.pdf"; name="labelImage"\r
\r
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CjE1IDAgb2JqCjw8CiAgL0ZvbnQgPDwKICAvRjEgMTcgMCBSCiAgL0YyIDE4IDAgUgogIC9GMyAxOSAwIFIKPj4KICAvUHJvY1NldCBbL1BERiAvSW1hZ2VCIC9JbWFnZUMgL1RleHRdCiAgL1hPYmplY3QgPDwgL0ltMSA1IDAgUiAvSW0yIDEwIDAgUiA+PgogIC9Db2xvclNwYWNlIDw8IC9JQ0MyIDQgMCBSIC9JQ0M3IDkgMCBSID4+Cj4+CmVuZG9iagp4cmVmCjAgMjEKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDE1IDAwMDAwIG4gCjAwMDAwMDAxMzEgMDAwMDAgbiAKMDAwMDAwMjY4OCAwMDAwMCBuIAowMDAwMDAyNzA4IDAwMDAwIG4gCjAwMDAwMDI3NDEgMDAwMDAgbiAKMDAwMDAwMzAxNyAwMDAwMCBuIAowMDAwMDAzMDM1IDAwMDAwIG4gCjAwMDAwMDU1OTIgMDAwMDAgbiAKMDAwMDAwNTYxMiAwMDAwMCBuIAowMDAwMDA1NjQ1IDAwMDAwIG4gCjAwMDAwMDU5NjkgMDAwMDAgbiAKMDAwMDAwNTk4OSAwMDAwMCBuIAowMDAwMDEyODIwIDAwMDAwIG4gCjAwMDAwMTI4NDEgMDAwMDAgbiAKMDAwMDAxMzUwMSAwMDAwMCBuIAowMDAwMDEzMzY2IDAwMDAwIG4gCjAwMDAwMTMwMzUgMDAwMDAgbiAKMDAwMDAxMzE0MSAwMDAwMCBuIAowMDAwMDEzMjU1IDAwMDAwIG4gCjAwMDAwMTM0MjYgMDAwMDAgbiAKdHJhaWxlcgo8PAogIC9Sb290IDIwIDAgUgogIC9JbmZvIDEgMCBSCiAgL0lEIFs8NkNBQ0JCMzBEQzY1NEJDQkU5QjYwRUQwOTRFMkY4QTQ+IDw2Q0FDQkIzMERDNjU0QkNCRTlCNjBFRDA5NEUyRjhBND5dCiAgL1NpemUgMjEKPj4Kc3RhcnR4cmVmCjEzNzAwCiUlRU9GCg==
--6p7jEqRvNj5nnsuzalbLR5zG--"""
    ACCESS_TOKEN_MOCK_RESPONSE = {
        "access_token": "eyJraWQiOiJ5MmRGRGY3eDdFQkFsQXlob0RLYld2ejlNaWxHTzlnaEJZS2c3OV9zRko4IiwidHlwIjoiSldUIiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiIzNDk3MTcyNCIsImNyaWQiOiI5NDg3OTk1OSIsInN1Yl9pZCI6IjM0OTcxNzI0IiwicGF5bWVudF9hY2NvdW50cyI6IntcImFjY291bnRzXCI6XCIxMDAwMDEzNjYxLCAxMDAwMDE1ODUxLCAxMDAwMDA1NTQ5LCAxMDAwMDEzNjE1XCJ9IiwiaXNzIjoiaHR0cHM6XC9cL2NhdC1rZXljLnVzcHMuY29tXC9yZWFsbXNcL1VTUFMiLCJjb250cmFjdHMiOiJ7XCJwYXltZW50QWNjb3VudHNcIjp7XCJhY2NvdW50c1wiOlwiMTAwMDAxMzY2MSwgMTAwMDAxNTg1MSwgMTAwMDAwNTU0OSwgMTAwMDAxMzYxNVwifSxcInBlcm1pdHNcIjp7XCJwZXJtaXRzXCI6XCIzMDA4LCAzMDA5LCAxMTcyLCAxMTc5LCAxMTgwLCAzMDA2LCAzMDA3LCAzMDA4LCAzMDA5LCAxMTcyLCAxMTc5LCAxMTgwLCAzMDA2LCAzMDA3XCJ9fSIsImZhc3QiOiIiLCJhenAiOiJyNmhFTzl1WU1aVWxTVEFGelpqVVhhYnNHTW53NmVBNSIsIm1haWxfb3duZXJzIjoiW3tcImNyaWRcIjpcIjk0ODc5OTU5XCIsXCJtaWRzXCI6XCI5MDEwOTc3MDEsIDkwMTEwMTYwOCwgOTAxMTAxNjA3LCA5MDExMDE2MDYsIDkwMTA5NzY5OVwifV0iLCJzY29wZSI6ImludGVybmF0aW9uYWwtcHJpY2VzIGFkZHJlc3NlcyBhcHBvaW50bWVudHMgcGF5bWVudHMgcGlja3VwIHRyYWNraW5nIHNoaXBtZW50cyBsYWJlbHMgc2Nhbi1mb3JtcyBzZXJ2aWNlLXN0YW5kYXJkcyBzY2FuLWZvcm0gbG9jYXRpb25zIGNvbnRhaW5lcnMgaW50ZXJuYXRpb25hbC1sYWJlbHMgcHJpY2VzIiwib3JnYW5pemF0aW9uX2lkIjoiMjE3MCIsImV4cCI6MTcxNTcyNzYzMywiaWF0IjoxNzE1Njk4ODMzLCJqdGkiOiI5ZmUyNmRiNy03NjcwLTQ1Y2MtODk4ZS1kZGFiNzczOGQwN2QifQ.e8TfCFsFOrIoiiXYKueMlfedIc71LG7Eihg5KlLdtolVyNLP3km8KrzxuhjND-lf0jtEMrH_6jp5jraDDZlfn36YZHRqsghgeS96aPwcRR8AiHPsyMzLdvakJ-fEuqVbBTlb5RjAU6cAQuDZp1yMu7rc61I0GKz1dtSG5t0LIiUC9NqyJtQPhD7IWrTtPEzX5gNljQXzSzuetwmu5zt-t9MkoLPvo25v89FSo6TKKrMB0DZGZaa1r2ka71cMsIcwMTvtrDW8msWqwb2u1yeHU0ZI4_YHZEvI0Qj43oJym1fwWTe-03pgKDss376j48a84Prdy1-b_HY0wl0wHEnjoQ",
        "token_type": "Bearer",
        "issued_at": 1715698833561,
        "expires_in": 28799,
        "status": "approved",
        "scope": "international-prices addresses appointments payments pickup tracking shipments labels scan-forms service-standards scan-form locations containers international-labels prices",
        "issuer": "https://cat-keyc.usps.com/realms/USPS",
        "client_id": "r6hEO9uYMZUlSTAFzZjUXabsGMnw6eA5",
        "application_name": "odoo",
        "api_products": "[Shipping Version 3]",
        "public_key": "LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQklqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FROEFNSUlCQ2dLQ0FRRUFxVzI0ZVJQdUVudjgwN3JPZldicApJSkZ5R25ES1dnc3NBUEg5UzRTWWtuUU1jVGRQRVlXYU1oQks1M3c4VW43L0E2TkV4V25YVklFNTR1dEVpMUk4CkhVeUdjbFVMVFlvZ1lFRHBRb1lGYXBKRnhVTUxQQlM3WExvYmZlci9vM01WOGpRRFpWRFE0VEhtM29MKzdMZFgKemxaSjk0RFRIQ3VTc3B4dWtIZ3Fwa01SYlBzcWdwYTBaSWZZa2pMc1hZVTFnbFk5UzJwQUZNOFBDWm9sYjE3MgpzVndIUVJadnVOdXhWc2t1ME5jdmZJWjlZNzJYeDZUK3JHWFJCOExDNjhhV0pQTmNEQmpteUEvZmFWYWVZNVVNCkYyT3F2N2R2ditKNWw0ZlpCYkU5eUZPZUlMWmtscGhmOXJzMHF1WWc2ejh4cHFVaURpSFA4U3d0WWI4QWZ3Yk8KOXdJREFRQUIKLS0tLS1FTkQgUFVCTElDIEtFWS0tLS0t"
    }
    PAYMENT_TOKEN_MOCK_RESPONSE = {
        "paymentAuthorizationToken": "eyJraWQiOiJ5MmRGRGY3eDdFQkFsQXlob0RLYld2ejlNaWxHTzlnaEJZS2c3OV9zRko4IiwidHlwIjoiSldUIiwiYWxnIjoiUlMyNTYifQ.eyJzdWIiOiIzNDk3MTcyNCIsImF1ZCI6WyJsYWJlbHMiLCJpbnRlcm5hdGlvbmFsLWxhYmVscyJdLCJtYW5pZmVzdF90eXBlIjoiIiwiYXpwIjoicjZoRU85dVlNWlVsU1RBRnpaalVYYWJzR01udzZlQTUiLCJyb2xlcyI6W3siQ1JJRCI6Ijk0ODc5OTU5IiwiYWNjb3VudFR5cGUiOiJFUFMiLCJyb2xlTmFtZSI6IlBBWUVSIiwiTUlEIjoiOTAxMDk3NzAxIiwiYWNjb3VudFpJUCI6IjYzMTQxLTU4MjAiLCJhY2NvdW50TnVtYmVyIjoiMTAwMDAwNTU0OSJ9LHsiQ1JJRCI6Ijk0ODc5OTU5IiwiYWNjb3VudFR5cGUiOiJFUFMiLCJyb2xlTmFtZSI6IkxBQkVMX09XTkVSIiwiTUlEIjoiOTAxMDk3NzAxIiwiYWNjb3VudE51bWJlciI6IjEwMDAwMDU1NDkiLCJtYW5pZmVzdE1JRCI6IjkwMTA5NzY5OSJ9XSwiaXNzIjoiaHR0cHM6XC9cL2NhdC1rZXljLnVzcHMuY29tXC9yZWFsbXNcL1VTUFMiLCJzb3VyY2UiOiIiLCJleHAiOjE3MTU3MDYzNDUsImlhdCI6MTcxNTY3NzU0NSwianRpIjoiOWQ3ODA3MTUtODU3ZS00NGY5LTg3MzItYzAzMWQ1MzU4OTNmIn0.dP8bK-nQvQbjryXHWOO4mtxmKBuIqDCt-qoSQrSuSSX2hMbpuoSwFQ4zlneMhOTkuQivmdu_fSMMEsqUsanPNFQf0nQ1RFTsi-8b983IfaR6lMOyE1IKZsMksyaKi_3HpTok7X-jXMEATkzuVv-3bZyBGo3IG6vRfxuBRbU6Xf4q5OFgcpTgVPnn2ZIfy5NCBFQ12E0RWImnkdlm3I8D0KoagUAxOn3HoZ3hkpIn2ztg_XmB40OiJdvVbMkIAaVOweNN9X--WGf-J3K_y5jMARdj5MB9LIsmBeP8IPaf0LnwIBZeVVpqN2-YkNqPRmh8A3p78DuawtKP82_rfEmTNg",
        "roles": [
            {
                "roleName": "PAYER",
                "CRID": "94879959",
                "MID": "901097701",
                "accountType": "EPS",
                "accountNumber": "1000005549"
            },
            {
                "roleName": "LABEL_OWNER",
                "CRID": "94879959",
                "MID": "901097701",
                "manifestMID": "901097699",
                "accountType": "EPS",
                "accountNumber": "1000005549"
            }
        ]
    }

    def _mock_request(*args, **kwargs):
        url = kwargs.get('url')
        responses = {
            'international-prices': INTERNATIONAL_RATE_MOCK_RESPONSE,
            'prices': RATE_MOCK_RESPONSE,
            'labels': SHIP_MOCK_RESPONSE,  # This is used for both creating and canceling labels but it doesn't matter since the cancellation request only cares about the status code
            'oauth': ACCESS_TOKEN_MOCK_RESPONSE,
            'payments': PAYMENT_TOKEN_MOCK_RESPONSE,
        }

        for endpoint, content in responses.items():
            if endpoint in url:
                respone = requests.Response()
                if endpoint != 'labels':
                    respone._content = json.dumps(content).encode()
                else:
                    respone._content = content.encode()
                respone.status_code = 200
                if endpoint == 'labels':
                    respone.headers['Content-Type'] = 'multipart/form-data; boundary=6p7jEqRvNj5nnsuzalbLR5zG'
                return respone

    with patch.object(requests.Session, 'request', _mock_request):
        yield


@tagged('-standard', 'external')
class TestMockedDeliveryUSPS(TestDeliveryUSPS):

    def test_01_usps_basic_us_domestic_flow(self):
        with _mock_request_call():
            super().test_01_usps_basic_us_domestic_flow()

    def test_02_usps_basic_us_international_flow(self):
        with _mock_request_call():
            super().test_02_usps_basic_us_international_flow()

    def test_03_usps_multipackage_domestic_flow(self):
        with _mock_request_call():
            super().test_03_usps_multipackage_domestic_flow()
