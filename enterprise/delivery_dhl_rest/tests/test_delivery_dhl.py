# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from datetime import timedelta
import requests
from contextlib import contextmanager
from unittest.mock import patch

from odoo import fields, Command
from odoo.tests import Form, TransactionCase, tagged
from ..models.dhl_request import DHLProvider


class TestDeliveryDHLCommon(TransactionCase):

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
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        self.incoterm = self.env['account.incoterms'].create({
            'name': 'Delivered At Place',
            'code': 'DAP',
        })
        self.env.company.write({
            'incoterm_id': self.incoterm.id,
        })

        self.your_company = self.env.ref('base.main_partner')
        self.your_company.write({
            'street': "Rue du Laid Burniat 5",
            'street2': "",
            'city': "Saint-Hubert",
            'zip': 6870,
            'state_id': False,
            'country_id': self.env.ref('base.be').id,
            'phone': '+1 555-555-5555',
        })
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
        self.delta_pc = self.env['res.partner'].create({
            'name': 'Delta PC',
            'phone': '(803)-873-6126',
            'street': "1515 Main Street",
            'street2': "",
            'city': "Columbia",
            'zip': 29201,
            'state_id': self.env.ref('base.state_us_41').id,
            'country_id': self.env.ref('base.us').id,
        })
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')

        self.delivery_carrier_dhl_be_dom = self.env.ref('delivery_dhl_rest.delivery_carrier_dhl_be_dom', raise_if_not_found=False)
        if not self.delivery_carrier_dhl_be_dom:
            product_dhl = self.env['product.product'].create({
                "name": 'DHL BE',
                "default_code": 'Delivery_014',
                "type": 'service',
                "categ_id": self.env.ref('delivery.product_category_deliveries').id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 0.0,
                "invoice_policy": 'order',
            })
            self.delivery_carrier_dhl_be_dom = self.env['delivery.carrier'].create({
                "name": 'DHL BE',
                "product_id": product_dhl.id,
                "delivery_type": 'dhl_rest',
                "dhl_product_code": 'N',
                "dhl_api_key": 'apI8zX6vT2hQ9f',
                "dhl_api_secret": 'S^2eZ$1aL#2nF^0d',
                "dhl_account_number": '272699353',
                "dhl_default_package_type_id": self.env.ref('delivery_dhl_rest.dhl_packaging_BOX').id,
            })
        # Ask for delivery in 5 days, at noon.
        # This is to avoid errors where DHL return an error because it's not possible for them to deliver on time.
        self.delivery_date = fields.Datetime.today() + timedelta(hours=12) + timedelta(days=5)
        self.delivery_carrier_dhl_eu_intl = self.env.ref('delivery_dhl_rest.delivery_carrier_dhl_eu_intl', raise_if_not_found=False)
        if not self.delivery_carrier_dhl_eu_intl:
            product_dhl = self.env['product.product'].create({
                "name": 'DHL EU International',
                "default_code": 'Delivery_015',
                "type": 'service',
                "categ_id": self.env.ref('delivery.product_category_deliveries').id,
                "sale_ok": False,
                "purchase_ok": False,
                "list_price": 0.0,
                "invoice_policy": 'order',
            })
            self.delivery_carrier_dhl_eu_intl = self.env['delivery.carrier'].create({
                "name": 'DHL EU International',
                "product_id": product_dhl.id,
                "delivery_type": 'dhl_rest',
                "dhl_product_code": 'D',
                "dhl_api_key": 'apI8zX6vT2hQ9f',
                "dhl_api_secret": 'S^2eZ$1aL#2nF^0d',
                "dhl_account_number": '272699353',
                "dhl_default_package_type_id": self.env.ref('delivery_dhl_rest.dhl_packaging_BOX').id,
            })

    def wiz_put_in_pack(self, picking):
        """ Helper to use the 'choose.delivery.package' wizard
        in order to call the 'action_put_in_pack' method.
        """
        wiz_action = picking.action_put_in_pack()
        self.assertEqual(wiz_action['res_model'], 'choose.delivery.package', 'Wrong wizard returned')
        wiz = Form(self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'delivery_package_type_id': picking.carrier_id.dhl_default_package_type_id.id
        }))
        choose_delivery_carrier = wiz.save()
        choose_delivery_carrier.action_put_in_pack()

    def dhl_basic_be_domestic_flow_with_insurance(self):

        def update_shipping_rate(sale_order, carrier):
            # I add free delivery cost in Sales order
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': sale_order.id,
                'default_carrier_id': carrier.id,
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()

        def validate_shipment(sale_order):
            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id, sale_order.carrier_id, "Carrier is not the same on Picking and on SO.")

            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
                move.picked = True
            self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

            picking.scheduled_date = self.delivery_date
            picking._action_done()
            self.assertTrue(picking.carrier_tracking_ref, "DHL did not return any tracking number")
            self.assertGreater(picking.carrier_price, 0.0, "DHL carrying price is probably incorrect")

        def cancel_shipment(sale_order):
            picking = sale_order.picking_ids[0]
            picking.cancel_shipment()
            self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
            self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

        SaleOrder = self.env['sale.order']

        delivery_carrier_dhl_be_dom_insured = self.delivery_carrier_dhl_be_dom.copy()
        delivery_carrier_dhl_be_dom_insured.shipping_insurance = 80

        sol_vals = {
            'product_id': self.iPadMini.id,
            'name': "[A1232] Large Cabinet",
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        }

        so_vals = {
            'partner_id': self.agrolait.id,
            'order_line': [(0, None, sol_vals)],
            'date_order': self.delivery_date,
        }

        sale_order = SaleOrder.create(so_vals)
        insured_sale_order = SaleOrder.create(so_vals)

        update_shipping_rate(sale_order, self.delivery_carrier_dhl_be_dom)
        update_shipping_rate(insured_sale_order, delivery_carrier_dhl_be_dom_insured)

        delivery_cost = sum(line.price_total for line in sale_order.order_line if line.is_delivery)
        insured_delivery_cost = sum(line.price_total for line in insured_sale_order.order_line if line.is_delivery)
        self.assertGreater(delivery_cost, 0.0, "DHL delivery cost for this SO has not been correctly estimated.")
        self.assertGreater(insured_delivery_cost, 0.0, "DHL delivery cost for this SO has not been correctly estimated.")
        self.assertGreater(insured_delivery_cost, delivery_cost, "Insured delivery cost should be greater than uninsured delivery cost.")

        (sale_order | insured_sale_order).action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")
        self.assertEqual(len(insured_sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        validate_shipment(sale_order)
        validate_shipment(insured_sale_order)
        self.assertGreater(insured_sale_order.picking_ids[0].carrier_price, sale_order.picking_ids[0].carrier_price, "Insured delivery cost should be greater than uninsured delivery cost.")

        cancel_shipment(sale_order)
        cancel_shipment(insured_sale_order)

    def dhl_basic_international_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {
            'product_id': self.iPadMini.id,
            'name': "[A1232] Large Cabinet",
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': self.iPadMini.lst_price
        }

        so_vals = {
            'partner_id': self.delta_pc.id,
            'carrier_id': self.delivery_carrier_dhl_eu_intl.id,
            'order_line': [(0, None, sol_vals)],
            'date_order': self.delivery_date,
        }

        sale_order = SaleOrder.create(so_vals)
        # I add free delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.delivery_carrier_dhl_eu_intl.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        # doesn't work with the mocked request, because the productCode isn't the same...
        # self.assertGreater(sum(line.price_total for line in sale_order.order_line if line.is_delivery), 0.0, "DHL delivery cost for this SO has not been correctly estimated.")
        choose_delivery_carrier.button_confirm()

        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

        picking = sale_order.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

        picking.move_ids[0].quantity = 1.0
        picking.move_ids[0].picked = True
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking.scheduled_date = self.delivery_date
        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "DHL did not return any tracking number")
        self.assertGreater(picking.carrier_price, 0.0, "DHL carrying price is probably incorrect")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def dhl_multipackage_international_flow(self):
        SaleOrder = self.env['sale.order']

        sol_1_vals = {
            'product_id': self.iPadMini.id,
            'name': "[A1232] Large Cabinet",
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': self.iPadMini.lst_price
        }
        sol_2_vals = {
            'product_id': self.large_desk.id,
            'name': "[A1090] Large Desk",
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': self.large_desk.lst_price
        }

        so_vals = {
            'partner_id': self.delta_pc.id,
            'carrier_id': self.delivery_carrier_dhl_eu_intl.id,
            'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)],
            'date_order': self.delivery_date,
        }

        sale_order = SaleOrder.create(so_vals)
        # I add free delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.delivery_carrier_dhl_eu_intl.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
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

        self.assertEqual(len(picking.move_line_ids.mapped('result_package_id')), 2, "2 Packages should have been created at this point")
        self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

        picking.scheduled_date = self.delivery_date
        picking._action_done()
        self.assertIsNot(picking.carrier_tracking_ref, False, "DHL did not return any tracking number")

        picking.cancel_shipment()
        self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
        self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def dhl_flow_from_delivery_order(self):
        StockPicking = self.env['stock.picking']

        order1_vals = {
            'product_id': self.iPadMini.id,
            'name': "[A1232] iPad Mini",
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id
        }

        do_vals = {
            'partner_id': self.delta_pc.id,
            'carrier_id': self.delivery_carrier_dhl_eu_intl.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'state': 'draft',
            'move_ids_without_package': [(0, None, order1_vals)],
            'scheduled_date': self.delivery_date,
        }

        delivery_order = StockPicking.create(do_vals)
        self.assertEqual(delivery_order.state, 'draft', 'Shipment state should be draft.')

        delivery_order.action_confirm()
        self.assertEqual(delivery_order.state, 'assigned', 'Shipment state should be ready(assigned).')
        delivery_order.move_ids_without_package.quantity = 1.0
        delivery_order.move_ids_without_package.picked = True

        delivery_order.button_validate()
        self.assertEqual(delivery_order.state, 'done', 'Shipment state should be done.')


@tagged('-standard', 'external')
class TestDeliveryDHL(TestDeliveryDHLCommon):

    def test_01_dhl_basic_be_domestic_flow_with_insurance(self):
        super().dhl_basic_be_domestic_flow_with_insurance()

    def test_02_dhl_basic_international_flow(self):
        super().dhl_basic_international_flow()

    def test_03_dhl_multipackage_international_flow(self):
        super().dhl_multipackage_international_flow()

    def test_04_dhl_flow_from_delivery_order(self):
        super().dhl_flow_from_delivery_order()


@contextmanager
def _mock_request_call():
    RATE_MOCK_RESPONSE = {
        "products": [
            {
                "productName": "MEDICAL EXPRESS",
                "productCode": "C",
                "localProductCode": "O",
                "localProductCountryCode": "BE",
                "networkTypeCode": "TD",
                "isCustomerAgreement": True,
                "weight": {
                    "volumetric": 19.01,
                    "provided": 19.5,
                    "unitOfMeasurement": "metric"
                },
                "totalPrice": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "price": 76.24
                    },
                    {
                        "currencyType": "PULCL",
                        "price": 0
                    },
                    {
                        "currencyType": "BASEC",
                        "price": 0
                    }
                ],
                "totalPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "priceBreakdown": [
                            {
                                "typeCode": "STTXA",
                                "price": 13.23
                            },
                            {
                                "typeCode": "SPRQT",
                                "price": 58.88
                            }
                        ]
                    }
                ],
                "detailedPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "breakdown": [
                            {
                                "name": "MEDICAL EXPRESS",
                                "price": 58.88,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "EU_VAT",
                                        "price": 10.22,
                                        "rate": 21,
                                        "basePrice": 48.66
                                    }
                                ]
                            },
                            {
                                "name": "FUEL SURCHARGE",
                                "serviceCode": "FF",
                                "localServiceCode": "FF",
                                "serviceTypeCode": "SCH",
                                "price": 17.36,
                                "isCustomerAgreement": False,
                                "isMarketedService": False,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "EU_VAT",
                                        "price": 3.01,
                                        "rate": 21,
                                        "basePrice": 14.35
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "pickupCapabilities": {
                    "nextBusinessDay": False,
                    "localCutoffDateAndTime": "2024-05-02T17:30:00",
                    "GMTCutoffTime": "19:00:00",
                    "pickupEarliest": "09:30:00",
                    "pickupLatest": "19:00:00",
                    "originServiceAreaCode": "BRU",
                    "originFacilityAreaCode": "ANN",
                    "pickupAdditionalDays": 0,
                    "pickupDayOfWeek": 4
                },
                "deliveryCapabilities": {
                    "deliveryTypeCode": "QDDF",
                    "estimatedDeliveryDateAndTime": "2024-05-03T23:59:00",
                    "destinationServiceAreaCode": "BRU",
                    "destinationFacilityAreaCode": "LG1",
                    "deliveryAdditionalDays": 0,
                    "deliveryDayOfWeek": 5,
                    "totalTransitDays": 1
                },
                "pricingDate": "2024-05-02"
            },
            {
                "productName": "EXPRESS DOMESTIC",
                "productCode": "N",
                "localProductCode": "L",
                "localProductCountryCode": "BE",
                "networkTypeCode": "TD",
                "isCustomerAgreement": False,
                "weight": {
                    "volumetric": 19.01,
                    "provided": 19.5,
                    "unitOfMeasurement": "metric"
                },
                "totalPrice": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "price": 56.25
                    },
                    {
                        "currencyType": "PULCL",
                        "price": 0
                    },
                    {
                        "currencyType": "BASEC",
                        "price": 0
                    }
                ],
                "totalPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "priceBreakdown": [
                            {
                                "typeCode": "STTXA",
                                "price": 9.76
                            },
                            {
                                "typeCode": "SPRQT",
                                "price": 43.44
                            }
                        ]
                    }
                ],
                "detailedPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "breakdown": [
                            {
                                "name": "EXPRESS DOMESTIC",
                                "price": 43.44,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "EU_VAT",
                                        "price": 7.54,
                                        "rate": 21,
                                        "basePrice": 35.9
                                    }
                                ]
                            },
                            {
                                "name": "FUEL SURCHARGE",
                                "serviceCode": "FF",
                                "localServiceCode": "FF",
                                "serviceTypeCode": "SCH",
                                "price": 12.81,
                                "isCustomerAgreement": False,
                                "isMarketedService": False,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "EU_VAT",
                                        "price": 2.22,
                                        "rate": 21,
                                        "basePrice": 10.59
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "pickupCapabilities": {
                    "nextBusinessDay": False,
                    "localCutoffDateAndTime": "2024-05-02T17:30:00",
                    "GMTCutoffTime": "19:00:00",
                    "pickupEarliest": "09:30:00",
                    "pickupLatest": "19:00:00",
                    "originServiceAreaCode": "BRU",
                    "originFacilityAreaCode": "ANN",
                    "pickupAdditionalDays": 0,
                    "pickupDayOfWeek": 4
                },
                "deliveryCapabilities": {
                    "deliveryTypeCode": "QDDF",
                    "estimatedDeliveryDateAndTime": "2024-05-03T23:59:00",
                    "destinationServiceAreaCode": "BRU",
                    "destinationFacilityAreaCode": "LG1",
                    "deliveryAdditionalDays": 0,
                    "deliveryDayOfWeek": 5,
                    "totalTransitDays": 1
                },
                "pricingDate": "2024-05-02"
            },
            {
                "productName": "EXPRESS WORLDWIDE",
                "productCode": "D",
                "localProductCode": "I",
                "localProductCountryCode": "BE",
                "networkTypeCode": "TD",
                "isCustomerAgreement": True,
                "weight": {
                    "volumetric": 19.01,
                    "provided": 19.5,
                    "unitOfMeasurement": "metric"
                },
                "totalPrice": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "price": 45
                    },
                    {
                        "currencyType": "PULCL",
                        "price": 0
                    },
                    {
                        "currencyType": "BASEC",
                        "price": 0
                    }
                ],
                "totalPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "priceBreakdown": [
                            {
                                "typeCode": "STTXA",
                                "price": 7.81
                            },
                            {
                                "typeCode": "SPRQT",
                                "price": 45
                            }
                        ]
                    }
                ],
                "detailedPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "breakdown": [
                            {
                                "name": "EXPRESS EASY",
                                "price": 45,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "EU_VAT",
                                        "price": 7.81,
                                        "rate": 21,
                                        "basePrice": 37.19
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "pickupCapabilities": {
                    "nextBusinessDay": False,
                    "localCutoffDateAndTime": "2024-05-02T17:30:00",
                    "GMTCutoffTime": "19:00:00",
                    "pickupEarliest": "09:30:00",
                    "pickupLatest": "19:00:00",
                    "originServiceAreaCode": "BRU",
                    "originFacilityAreaCode": "ANN",
                    "pickupAdditionalDays": 0,
                    "pickupDayOfWeek": 4
                },
                "deliveryCapabilities": {
                    "deliveryTypeCode": "QDDF",
                    "estimatedDeliveryDateAndTime": "2024-05-03T23:59:00",
                    "destinationServiceAreaCode": "BRU",
                    "destinationFacilityAreaCode": "LG1",
                    "deliveryAdditionalDays": 0,
                    "deliveryDayOfWeek": 5,
                    "totalTransitDays": 1
                },
                "pricingDate": "2024-05-02"
            }
        ]
    }
    SHIP_MOCK_RESPONSE = {
        "shipmentTrackingNumber": "3436501003",
        "cancelPickupUrl": "https://express.api.dhl.com/mydhlapi/test/pickups/PRG240502001481",
        "trackingUrl": "https://express.api.dhl.com/mydhlapi/test/shipments/3436501003/tracking",
        "dispatchConfirmationNumber": "PRG240502001481",
        "packages": [
            {
                "referenceNumber": 1,
                "trackingNumber": "JD014600004860442740",
                "trackingUrl": "https://express.api.dhl.com/mydhlapi/test/shipments/3436501003/tracking?pieceTrackingNumber=JD014600004860442740"
            }
        ],
        "documents": [
            {
                "imageFormat": "PDF",
                "content": "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",
                "typeCode": "label"
            },
        ],
    }
    INSURED_RATE_MOCK_RESPONSE = {
        "products": [
            {
                "productName": "EXPRESS DOMESTIC",
                "productCode": "N",
                "localProductCode": "L",
                "localProductCountryCode": "BE",
                "networkTypeCode": "TD",
                "isCustomerAgreement": False,
                "weight": {
                    "volumetric": 19.01,
                    "provided": 19.5,
                    "unitOfMeasurement": "metric",
                },
                "totalPrice": [
                    {"currencyType": "BILLC", "priceCurrency": "EUR", "price": 96.85},
                    {"currencyType": "PULCL", "price": 0},
                    {"currencyType": "BASEC", "price": 0},
                ],
                "totalPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "priceBreakdown": [
                            {"typeCode": "STTXA", "price": 14.9},
                            {"typeCode": "SPRQT", "price": 72.3},
                        ],
                    },
                ],
                "detailedPriceBreakdown": [
                    {
                        "currencyType": "BILLC",
                        "priceCurrency": "EUR",
                        "breakdown": [
                            {
                                "name": "EXPRESS DOMESTIC",
                                "price": 72.3,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "EU_VAT",
                                        "price": 12.55,
                                        "rate": 21,
                                        "basePrice": 59.75,
                                    },
                                ],
                            },
                            {
                                "name": "FUEL SURCHARGE",
                                "serviceCode": "FF",
                                "localServiceCode": "FF",
                                "serviceTypeCode": "SCH",
                                "price": 13.55,
                                "isCustomerAgreement": False,
                                "isMarketedService": False,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "EU_VAT",
                                        "price": 2.35,
                                        "rate": 21,
                                        "basePrice": 11.2,
                                    },
                                ],
                            },
                            {
                                "name": "SHIPMENT INSURANCE",
                                "serviceCode": "II",
                                "localServiceCode": "II",
                                "serviceTypeCode": "XCH",
                                "price": 11,
                                "isCustomerAgreement": False,
                                "isMarketedService": True,
                                "priceBreakdown": [
                                    {
                                        "priceType": "TAX",
                                        "typeCode": "Insura",
                                        "price": 0,
                                        "rate": 0,
                                        "basePrice": 11,
                                    },
                                ],
                            },
                        ],
                    },
                ],
                "pickupCapabilities": {
                    "nextBusinessDay": False,
                    "localCutoffDateAndTime": "2025-09-03T14:00:00",
                    "GMTCutoffTime": "16:00:00",
                    "pickupEarliest": "10:00:00",
                    "pickupLatest": "16:00:00",
                    "originServiceAreaCode": "BRU",
                    "originFacilityAreaCode": "LG1",
                    "pickupAdditionalDays": 0,
                    "pickupDayOfWeek": 3,
                },
                "deliveryCapabilities": {
                    "deliveryTypeCode": "QDDF",
                    "estimatedDeliveryDateAndTime": "2025-09-04T23:59:00",
                    "destinationServiceAreaCode": "BRU",
                    "destinationFacilityAreaCode": "LGG",
                    "deliveryAdditionalDays": 0,
                    "deliveryDayOfWeek": 4,
                    "totalTransitDays": 1,
                },
                "pricingDate": "2025-09-02",
            },
        ],
    }

    def is_insured_request(url, json):
        if 'rates' in url:
            return 'II' in [service['serviceCode'] for service in json['productsAndServices'][0]['valueAddedServices']]
        elif 'shipment' in url:
            return 'II' in [service['serviceCode'] for service in json.get('valueAddedServices', [])]

    def _mock_request(*args, **kwargs):
        url = kwargs.get('url')
        json_ = kwargs.get('json')  # not to override the json module
        responses = {
            'rates': INSURED_RATE_MOCK_RESPONSE,
            'shipments': SHIP_MOCK_RESPONSE,
        } if is_insured_request(url, json_) else {
            'rates': RATE_MOCK_RESPONSE,
            'shipments': SHIP_MOCK_RESPONSE,
        }

        for endpoint, content in responses.items():
            if endpoint in url:
                response = requests.Response()
                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

    with patch.object(requests.Session, 'request', _mock_request):
        yield


class TestMockedDeliveryDHL(TestDeliveryDHLCommon):
    def test_01_dhl_basic_be_domestic_flow_with_insurance(self):
        with _mock_request_call():
            super().dhl_basic_be_domestic_flow_with_insurance()

    def test_02_dhl_basic_international_flow(self):
        with _mock_request_call():
            super().dhl_basic_international_flow()

    def test_03_dhl_multipackage_international_flow(self):
        with _mock_request_call():
            super().dhl_multipackage_international_flow()

    def test_04_dhl_flow_from_delivery_order(self):
        with _mock_request_call():
            super().dhl_flow_from_delivery_order()

    def test_05_dhl_test_export_declaration_rounding(self):
        """Test that the rounding respects the DHL requirements"""

        picking = self.env['stock.picking'].create({
            'partner_id': self.delta_pc.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'carrier_id': self.delivery_carrier_dhl_eu_intl.id,
            'move_ids_without_package': [
            Command.create({
                'product_id': self.iPadMini.id,
                'product_uom_qty': 7,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'name': self.iPadMini.name,
            }),
            Command.create({
                'product_id': self.large_desk.id,
                'product_uom_qty': 7,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'name': self.large_desk.name,
            })
            ]
        })
        picking.action_confirm()
        picking.move_line_ids[0].sale_price = 11.43
        picking.move_line_ids[1].sale_price = 6.666666600000001
        dhl_provider = DHLProvider(self.delivery_carrier_dhl_eu_intl)
        export_declaration = dhl_provider._get_export_declaration_vals(self.delivery_carrier_dhl_eu_intl, picking)
        item_1, item_2 = export_declaration['lineItems']

        self.assertEqual(item_1['price'], 1.633)
        self.assertEqual(item_2['price'], 0.952)

    def test_06_dhl_weight_conversion_rounding(self):
        """Test that the weight conversion method correctly rounds according to DHL requirements"""

        weight_with_precision_issue = 0.7000000000000001
        rounded_weight_metric = self.delivery_carrier_dhl_eu_intl._dhl_convert_weight(weight_with_precision_issue)
        self.assertEqual(rounded_weight_metric, 0.7)

        weight_needs_rounding = 1.23456789
        rounded_weight_precise = self.delivery_carrier_dhl_eu_intl._dhl_convert_weight(weight_needs_rounding)
        self.assertEqual(rounded_weight_precise, 1.235)
