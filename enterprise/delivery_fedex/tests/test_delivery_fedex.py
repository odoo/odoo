# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
import unittest
from unittest.mock import Mock, patch
from odoo.tests import Form, TransactionCase, tagged
from odoo.exceptions import UserError


# These errors are due to failures of Fedex test server and are not implementation errors
ERROR_200 = u"200: Rating is temporarily unavailable, please try again later."
ERROR_200_BIS = u"200: An unexpected exception occurred"
ERROR_200_TER = u"200: An unexpected exception occurred, not found"
ERROR_1000 = u"1000: General Failure"
SKIPPABLE_ERRORS = [ERROR_200, ERROR_200_BIS, ERROR_200_TER, ERROR_1000]
SKIP_MSG = u"Test skipped due to FedEx server unavailability"


@tagged('-standard', 'external')
class TestDeliveryFedex(TransactionCase):

    def setUp(self):
        super(TestDeliveryFedex, self).setUp()

        self.iPadMini = self.env['product.product'].create({
            'name': 'Ipad Mini',
            'weight': 0.01,
        })
        self.large_desk = self.env['product.product'].create({
            'name': 'Large Desk',
            'weight': 0.01,
        })
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        self.your_company = self.env.ref('base.main_partner')
        self.your_company.write({'country_id': self.env.ref('base.us').id,
                                 'state_id': self.env.ref('base.state_us_5').id,
                                 'city': 'San Francisco',
                                 'street': '51 Federal Street',
                                 'zip': '94107',
                                 'phone': 9874582356})

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

    def wiz_put_in_pack(self, picking):
        """ Helper to use the 'choose.delivery.package' wizard
        in order to call the 'action_put_in_pack' method.
        """
        wiz_action = picking.action_put_in_pack()
        self.assertEqual(wiz_action['res_model'], 'choose.delivery.package', 'Wrong wizard returned')
        wiz = Form.from_action(self.env, wiz_action)
        wiz.delivery_package_type_id: picking.carrier_id.fedex_default_package_type_id
        wiz.save().action_put_in_pack()

    def test_01_fedex_basic_us_domestic_flow(self):
        try:

            SaleOrder = self.env['sale.order']

            sol_vals = {'product_id': self.iPadMini.id,
                        'name': "[A1232] iPad Mini",
                        'product_uom': self.uom_unit.id,
                        'product_uom_qty': 1.0,
                        'price_unit': self.iPadMini.lst_price}

            so_vals = {'partner_id': self.delta_pc.id,
                       'order_line': [(0, None, sol_vals)]}

            sale_order = SaleOrder.create(so_vals)
            # I add delivery cost in Sales order
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': sale_order.id,
                'default_carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_us').id
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.update_price()
            self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")
            choose_delivery_carrier.button_confirm()

            sale_order.action_confirm()
            self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

            picking.move_ids[0].quantity = 1.0
            picking.move_ids[0].picked = True
            self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
            self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

            picking.cancel_shipment()
            self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
            self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

        except UserError as e:
            if e.args[0].strip() in SKIPPABLE_ERRORS:
                raise unittest.SkipTest(SKIP_MSG)
            else:
                raise e

    def test_02_fedex_basic_international_flow(self):
        try:

            SaleOrder = self.env['sale.order']

            sol_vals = {'product_id': self.iPadMini.id,
                        'name': "[A1232] Large Cabinet",
                        'product_uom': self.uom_unit.id,
                        'product_uom_qty': 1.0,
                        'price_unit': self.iPadMini.lst_price}

            so_vals = {'partner_id': self.agrolait.id,
                       'order_line': [(0, None, sol_vals)]}

            sale_order = SaleOrder.create(so_vals)
            # I add delivery cost in Sales order
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': sale_order.id,
                'default_carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_inter').id,
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.update_price()
            self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")
            choose_delivery_carrier.button_confirm()

            sale_order.action_confirm()
            self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

            picking.move_ids[0].quantity = 1.0
            picking.move_ids[0].picked = True
            self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
            self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

            picking.cancel_shipment()
            self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
            self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

        except UserError as e:
            if e.args[0].strip() in SKIPPABLE_ERRORS:
                raise unittest.SkipTest(SKIP_MSG)
            else:
                raise e

    def test_03_fedex_multipackage_international_flow(self):
        try:

            SaleOrder = self.env['sale.order']

            sol_1_vals = {'product_id': self.iPadMini.id,
                          'name': "[A1232] iPad Mini",
                          'product_uom': self.uom_unit.id,
                          'product_uom_qty': 1.0,
                          'price_unit': self.iPadMini.lst_price}
            sol_2_vals = {'product_id': self.large_desk.id,
                          'name': "[A1090] Large Desk",
                          'product_uom': self.uom_unit.id,
                          'product_uom_qty': 1.0,
                          'price_unit': self.large_desk.lst_price}

            so_vals = {'partner_id': self.agrolait.id,
                       'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

            sale_order = SaleOrder.create(so_vals)
            # I add delivery cost in Sales order
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': sale_order.id,
                'default_carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_inter').id
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.update_price()
            self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")
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

            picking._action_done()
            self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
            self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

            picking.cancel_shipment()
            self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
            self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

        except UserError as e:
            if e.args[0].strip() in SKIPPABLE_ERRORS:
                raise unittest.SkipTest(SKIP_MSG)
            else:
                raise e

    def test_04_fedex_international_delivery_from_delivery_order(self):
        StockPicking = self.env['stock.picking']

        order1_vals = {
                    'product_id': self.iPadMini.id,
                    'name': "[A1232] iPad Mini",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id}

        do_vals = { 'partner_id': self.agrolait.id,
                    'carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_inter').id,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'state': 'draft',
                    'move_ids_without_package': [(0, None, order1_vals)]}

        delivery_order = StockPicking.create(do_vals)
        self.assertEqual(delivery_order.state, 'draft', 'Shipment state should be draft.')

        delivery_order.action_confirm()
        self.assertEqual(delivery_order.state, 'assigned', 'Shipment state should be ready(assigned).')
        delivery_order.move_ids_without_package.quantity = 1.0

        delivery_order.button_validate()
        self.assertEqual(delivery_order.state, 'done', 'Shipment state should be done.')


@tagged('standard', '-external')
class TestMockDeliveryFedex(TestDeliveryFedex):

    @contextmanager
    def patch_fedex_requests(self):
        """ Mock context for requests to the fedex API. """

        class MockedSession:
            def __init__(self, *args, **kwargs):
                self.headers = dict()

            def mount(self, *args, **kwargs):
                return None

            def close(self, *args, **kwargs):
                return None

            def post(self, *args, **kwargs):
                response = Mock()
                response.headers = {}
                response.status_code = 200
                if b'<ns0:ProcessShipmentRequest' in kwargs.get('data'):
                    response.content = b'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body><ProcessShipmentReply xmlns="http://fedex.com/ws/ship/v28"><HighestSeverity>SUCCESS</HighestSeverity><Notifications><Severity>SUCCESS</Severity><Source>ship</Source><Code>0000</Code><Message>Success</Message><LocalizedMessage>Success</LocalizedMessage></Notifications><TransactionDetail><CustomerTransactionId>234</CustomerTransactionId></TransactionDetail><Version><ServiceId>ship</ServiceId><Major>28</Major><Intermediate>0</Intermediate><Minor>0</Minor></Version><JobId>d7c541d1044e0079c63225709</JobId><CompletedShipmentDetail><UsDomestic>true</UsDomestic><CarrierCode>FDXE</CarrierCode><MasterTrackingId><TrackingIdType>FEDEX</TrackingIdType><FormId>0201</FormId><TrackingNumber>794668707764</TrackingNumber></MasterTrackingId><ServiceDescription><ServiceType>PRIORITY_OVERNIGHT</ServiceType><Code>01</Code><Names><Type>long</Type><Encoding>utf-8</Encoding><Value>FedEx Priority Overnight\xc3\x82\xc2\xae</Value></Names><Names><Type>long</Type><Encoding>ascii</Encoding><Value>FedEx Priority Overnight</Value></Names><Names><Type>medium</Type><Encoding>utf-8</Encoding><Value>FedEx Priority Overnight\xc3\x82\xc2\xae</Value></Names><Names><Type>medium</Type><Encoding>ascii</Encoding><Value>FedEx Priority Overnight</Value></Names><Names><Type>short</Type><Encoding>utf-8</Encoding><Value>P-1</Value></Names><Names><Type>short</Type><Encoding>ascii</Encoding><Value>P-1</Value></Names><Names><Type>abbrv</Type><Encoding>ascii</Encoding><Value>PO</Value></Names><Description>Priority Overnight</Description><AstraDescription>P1</AstraDescription></ServiceDescription><PackagingDescription><PackagingType>FEDEX_BOX</PackagingType><Code>03</Code><Names><Type>long</Type><Encoding>utf-8</Encoding><Value>FedEx\xc3\x82\xc2\xae Box</Value></Names><Names><Type>long</Type><Encoding>ascii</Encoding><Value>FedEx Box</Value></Names><Names><Type>medium</Type><Encoding>utf-8</Encoding><Value>FedEx\xc3\x82\xc2\xae Box</Value></Names><Names><Type>medium</Type><Encoding>ascii</Encoding><Value>FedEx Box</Value></Names><Names><Type>small</Type><Encoding>utf-8</Encoding><Value>Box</Value></Names><Names><Type>small</Type><Encoding>ascii</Encoding><Value>Box</Value></Names><Names><Type>short</Type><Encoding>utf-8</Encoding><Value>Box</Value></Names><Names><Type>short</Type><Encoding>ascii</Encoding><Value>Box</Value></Names><Names><Type>abbrv</Type><Encoding>ascii</Encoding><Value>B</Value></Names><Description>FedEx Box</Description><AstraDescription>FDX BOX</AstraDescription></PackagingDescription><SpecialServiceDescriptions><Identifier><Id>EP1000000060</Id><Type>DELIVER_WEEKDAY</Type><Code>02</Code></Identifier><Names><Type>long</Type><Encoding>utf-8</Encoding><Value>Deliver Weekday</Value></Names><Names><Type>long</Type><Encoding>ascii</Encoding><Value>Deliver Weekday</Value></Names><Names><Type>medium</Type><Encoding>utf-8</Encoding><Value>Deliver Weekday</Value></Names><Names><Type>medium</Type><Encoding>ascii</Encoding><Value>Deliver Weekday</Value></Names><Names><Type>short</Type><Encoding>utf-8</Encoding><Value>WDY</Value></Names><Names><Type>short</Type><Encoding>ascii</Encoding><Value>WDY</Value></Names></SpecialServiceDescriptions><OperationalDetail><UrsaPrefixCode>XG</UrsaPrefixCode><UrsaSuffixCode>USCA </UrsaSuffixCode><OriginLocationId>JCCA </OriginLocationId><OriginLocationNumber>0</OriginLocationNumber><OriginServiceArea>A1</OriginServiceArea><DestinationLocationId>USCA </DestinationLocationId><DestinationLocationNumber>0</DestinationLocationNumber><DestinationServiceArea>A1</DestinationServiceArea><DestinationLocationStateOrProvinceCode>SC</DestinationLocationStateOrProvinceCode><DeliveryDate>2022-09-26</DeliveryDate><DeliveryDay>MON</DeliveryDay><CommitDate>2022-09-26</CommitDate><CommitDay>MON</CommitDay><IneligibleForMoneyBackGuarantee>false</IneligibleForMoneyBackGuarantee><AstraPlannedServiceLevel>MON - 26 SEP 10:30A</AstraPlannedServiceLevel><AstraDescription>PRIORITY OVERNIGHT</AstraDescription><PostalCode>29201</PostalCode><StateOrProvinceCode>SC</StateOrProvinceCode><CountryCode>US</CountryCode><AirportId>CAE</AirportId><ServiceCode>01</ServiceCode><PackagingCode>03</PackagingCode></OperationalDetail><ShipmentRating><ActualRateType>PAYOR_ACCOUNT_PACKAGE</ActualRateType><ShipmentRateDetails><RateType>PAYOR_ACCOUNT_PACKAGE</RateType><RateScale>1618</RateScale><RateZone>08</RateZone><PricingCode>PACKAGE</PricingCode><RatedWeightMethod>PACKAGING_MINIMUM</RatedWeightMethod><DimDivisor>0</DimDivisor><FuelSurchargePercent>19.5</FuelSurchargePercent><TotalBillingWeight><Units>LB</Units><Value>2.0</Value></TotalBillingWeight><TotalBaseCharge><Currency>USD</Currency><Amount>101.28</Amount></TotalBaseCharge><TotalFreightDiscounts><Currency>USD</Currency><Amount>0.0</Amount></TotalFreightDiscounts><TotalNetFreight><Currency>USD</Currency><Amount>101.28</Amount></TotalNetFreight><TotalSurcharges><Currency>USD</Currency><Amount>19.75</Amount></TotalSurcharges><TotalNetFedExCharge><Currency>USD</Currency><Amount>121.03</Amount></TotalNetFedExCharge><TotalTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalTaxes><TotalNetCharge><Currency>USD</Currency><Amount>121.03</Amount></TotalNetCharge><TotalRebates><Currency>USD</Currency><Amount>0.0</Amount></TotalRebates><TotalDutiesAndTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalDutiesAndTaxes><TotalAncillaryFeesAndTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalAncillaryFeesAndTaxes><TotalDutiesTaxesAndFees><Currency>USD</Currency><Amount>0.0</Amount></TotalDutiesTaxesAndFees><TotalNetChargeWithDutiesAndTaxes><Currency>USD</Currency><Amount>121.03</Amount></TotalNetChargeWithDutiesAndTaxes><Surcharges><SurchargeType>FUEL</SurchargeType><Description>Fuel</Description><Amount><Currency>USD</Currency><Amount>19.75</Amount></Amount></Surcharges></ShipmentRateDetails></ShipmentRating><CompletedPackageDetails><SequenceNumber>1</SequenceNumber><TrackingIds><TrackingIdType>FEDEX</TrackingIdType><FormId>0201</FormId><TrackingNumber>794668707764</TrackingNumber></TrackingIds><GroupNumber>0</GroupNumber><PackageRating><ActualRateType>PAYOR_ACCOUNT_PACKAGE</ActualRateType><PackageRateDetails><RateType>PAYOR_ACCOUNT_PACKAGE</RateType><RatedWeightMethod>PACKAGING_MINIMUM</RatedWeightMethod><BillingWeight><Units>LB</Units><Value>2.0</Value></BillingWeight><BaseCharge><Currency>USD</Currency><Amount>101.28</Amount></BaseCharge><TotalFreightDiscounts><Currency>USD</Currency><Amount>0.0</Amount></TotalFreightDiscounts><NetFreight><Currency>USD</Currency><Amount>101.28</Amount></NetFreight><TotalSurcharges><Currency>USD</Currency><Amount>19.75</Amount></TotalSurcharges><NetFedExCharge><Currency>USD</Currency><Amount>121.03</Amount></NetFedExCharge><TotalTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalTaxes><NetCharge><Currency>USD</Currency><Amount>121.03</Amount></NetCharge><TotalRebates><Currency>USD</Currency><Amount>0.0</Amount></TotalRebates><Surcharges><SurchargeType>FUEL</SurchargeType><Description>Fuel</Description><Amount><Currency>USD</Currency><Amount>19.75</Amount></Amount></Surcharges></PackageRateDetails></PackageRating><OperationalDetail><OperationalInstructions><Number>2</Number><Content>TRK#</Content></OperationalInstructions><OperationalInstructions><Number>3</Number><Content>0201</Content></OperationalInstructions><OperationalInstructions><Number>5</Number><Content>XG USCA </Content></OperationalInstructions><OperationalInstructions><Number>7</Number><Content>1001897543480002920100794668707764</Content></OperationalInstructions><OperationalInstructions><Number>8</Number><Content>581J1/EC8C/FE2D</Content></OperationalInstructions><OperationalInstructions><Number>10</Number><Content>7946 6870 7764</Content></OperationalInstructions><OperationalInstructions><Number>12</Number><Content>MON - 26 SEP 10:30A</Content></OperationalInstructions><OperationalInstructions><Number>13</Number><Content>PRIORITY OVERNIGHT</Content></OperationalInstructions><OperationalInstructions><Number>15</Number><Content>29201</Content></OperationalInstructions><OperationalInstructions><Number>16</Number><Content>SC-US</Content></OperationalInstructions><OperationalInstructions><Number>17</Number><Content>CAE</Content></OperationalInstructions><Barcodes><BinaryBarcodes><Type>COMMON_2D</Type><Value>Wyk+HjAxHTAyMjkyMDEdODQwHTAxHTc5NDY2ODcwNzc2NDAyMDEdRkRFHTYwMTM1NjgwNR0yNjYdHTEvMR0wLjcyTEIdTh0xNTE1IE1haW4gU3RyZWV0HUNvbHVtYmlhHVNDHVJlYWR5IE1hdB4wNh0xMFpFRDAwOB0xMlo4MDM4NzM2MTI2HTE1WjExODY3OTY4NR0yMFocHTMxWjEwMDE4OTc1NDM0ODAwMDI5MjAxMDA3OTQ2Njg3MDc3NjQdMzJaMDIdMzRaMDMdMzlaSkNDQR1LUzAwNDAyHR4wOR1GRFgdeh04HQ4sOBw2MH9AHgQ=</Value></BinaryBarcodes><StringBarcodes><Type>FEDEX_1D</Type><Value>1001897543480002920100794668707764</Value></StringBarcodes></Barcodes></OperationalDetail><Label><Type>OUTBOUND_LABEL</Type><ShippingDocumentDisposition>RETURNED</ShippingDocumentDisposition><ImageType>PDF</ImageType><Resolution>200</Resolution><CopiesToPrint>1</CopiesToPrint><Parts><DocumentPartSequenceNumber>1</DocumentPartSequenceNumber><Image>JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMyAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL091dGxpbmVzCi9Db3VudCAwCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9QYWdlcwovQ291bnQgMQovS2lkcyBbMTggMCBSXQo+PgplbmRvYmoKNCAwIG9iagpbL1BERiAvVGV4dCAvSW1hZ2VCIC9JbWFnZUMgL0ltYWdlSV0KZW5kb2JqCjUgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhCi9FbmNvZGluZyAvTWFjUm9tYW5FbmNvZGluZwo+PgplbmRvYmoKNiAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9IZWx2ZXRpY2EtQm9sZAovRW5jb2RpbmcgL01hY1JvbWFuRW5jb2RpbmcKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvSGVsdmV0aWNhLU9ibGlxdWUKL0VuY29kaW5nIC9NYWNSb21hbkVuY29kaW5nCj4+CmVuZG9iago4IDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0hlbHZldGljYS1Cb2xkT2JsaXF1ZQovRW5jb2RpbmcgL01hY1JvbWFuRW5jb2RpbmcKPj4KZW5kb2JqCjkgMCBvYmoKPDwKL1R5cGUgL0ZvbnQKL1N1YnR5cGUgL1R5cGUxCi9CYXNlRm9udCAvQ291cmllcgovRW5jb2RpbmcgL01hY1JvbWFuRW5jb2RpbmcKPj4KZW5kb2JqCjEwIDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0NvdXJpZXItQm9sZAovRW5jb2RpbmcgL01hY1JvbWFuRW5jb2RpbmcKPj4KZW5kb2JqCjExIDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0NvdXJpZXItT2JsaXF1ZQovRW5jb2RpbmcgL01hY1JvbWFuRW5jb2RpbmcKPj4KZW5kb2JqCjEyIDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0NvdXJpZXItQm9sZE9ibGlxdWUKL0VuY29kaW5nIC9NYWNSb21hbkVuY29kaW5nCj4+CmVuZG9iagoxMyAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9UaW1lcy1Sb21hbgovRW5jb2RpbmcgL01hY1JvbWFuRW5jb2RpbmcKPj4KZW5kb2JqCjE0IDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL1RpbWVzLUJvbGQKL0VuY29kaW5nIC9NYWNSb21hbkVuY29kaW5nCj4+CmVuZG9iagoxNSAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9UaW1lcy1JdGFsaWMKL0VuY29kaW5nIC9NYWNSb21hbkVuY29kaW5nCj4+CmVuZG9iagoxNiAwIG9iago8PAovVHlwZSAvRm9udAovU3VidHlwZSAvVHlwZTEKL0Jhc2VGb250IC9UaW1lcy1Cb2xkSXRhbGljCi9FbmNvZGluZyAvTWFjUm9tYW5FbmNvZGluZwo+PgplbmRvYmoKMTcgMCBvYmogCjw8Ci9DcmVhdGlvbkRhdGUgKEQ6MjAwMykKL1Byb2R1Y2VyIChGZWRFeCBTZXJ2aWNlcykKL1RpdGxlIChGZWRFeCBTaGlwcGluZyBMYWJlbCkNL0NyZWF0b3IgKEZlZEV4IEN1c3RvbWVyIEF1dG9tYXRpb24pDS9BdXRob3IgKENMUyBWZXJzaW9uIDUxMjAxMzUpCj4+CmVuZG9iagoxOCAwIG9iago8PAovVHlwZSAvUGFnZQ0vUGFyZW50IDMgMCBSCi9SZXNvdXJjZXMgPDwgL1Byb2NTZXQgNCAwIFIgCiAvRm9udCA8PCAvRjEgNSAwIFIgCi9GMiA2IDAgUiAKL0YzIDcgMCBSIAovRjQgOCAwIFIgCi9GNSA5IDAgUiAKL0Y2IDEwIDAgUiAKL0Y3IDExIDAgUiAKL0Y4IDEyIDAgUiAKL0Y5IDEzIDAgUiAKL0YxMCAxNCAwIFIgCi9GMTEgMTUgMCBSIAovRjEyIDE2IDAgUiAKID4+Ci9YT2JqZWN0IDw8IC9GZWRFeEV4cHJlc3MgMjAgMCBSCi9FeHByZXNzRSAyMSAwIFIKL2JhcmNvZGUwIDIyIDAgUgo+Pgo+PgovTWVkaWFCb3ggWzAgMCA3OTIgNjEyXQovVHJpbUJveFswIDAgNzkyIDYxMl0KL0NvbnRlbnRzIDE5IDAgUgovUm90YXRlIDkwPj4KZW5kb2JqCjE5IDAgb2JqCjw8IC9MZW5ndGggMzY0NgovRmlsdGVyIFsvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGVdIAo+PgpzdHJlYW0KR2F0ViFoZXNMRCZdYGM0akY6OikwOS9vNTNAJ0FFb1FFRWgqUCZKT2xIVnMwcG5eXj9MU0A4bCJEcmVqcCYxJVltRUhbOU9CIXJpK21lc3MKRjYlOlAzNV0kM0I7NjIqak4wRDtAOkpWOTIvLGptJEZtMU0tZFE8TktyYFxLVC5YR1VSLUdgLi4sUFxOJXRYNFlqWGlLNCcxRyw5TWpwNG0KVCJXTWVeRCVmZ1k/ODhfbigkQ1ZqX0kjNWwwdCNJY2RVaTsoREJPPChCMV1rJW5TJlU+R0dvXCFSVSojcS1uWW5Ha2YyRl4tO0pmQFghJmIKTztfVWdwVysyXWhoTzUnMiJiUDg3V3N1VWMuZjNYIjBIXEBHbylETWVjcV4qKTduVjxzNXMwLF0lUy1JUV1qPyloN19COCw8R0VlZ2hbTVkKXWZCPzdgbmpCSlk+MClPSktsKkBjRlRzWm9aZzRfWHFRMzhddFUjTnFyWyJycW5sKCcxclZaKlJiOzghX3E1czJFT1pXJ0guVE9fPzs9OisKa1hXWWtoO3UiPmJHYl9ZKFtQVF5kW0VOSyQrZWpIKzNtQypvS2tdVlJscjE4UD4tX2JZPjIlJ1U0blxAUjZRRz5kbHIiOVglYm1TaylecigKaSZUMUZBZjRiRTlxSVtnVSNYYGEoJ1tXLEpdKkFAazRjVENxb3BrbmYkbkVyKjtHaVkpVEknZV1sdCI9RG0iI1ZsYDg0PGdbL1VnT0cmYi0KQTRcJFtDT2hZVk8zXzspKzI9QnVMRFNbSylkJkdRRTV0NGdkZD1cLnJqcl1pcD9wYzhrNFpeYm5fJkE0NDIkKnFnaHM9aWdVaU1SNTcpMlkKKGdyZT1uI2dnRVMiIixBR2hEQm46WkxePkNTbGo8KiRjcCtxWyFXSi9iWF1COz10aERtcixCP10uNlBkYV9hOFVoYGldcipTNGY1XE8nMUUKVDluSSZeVjtbNVdCTSRGYmBSaDVLaSduNy1gNW8uRWQqaUs5blU1PF0xYEpNJSoiVGY3SjcsZGEhYTNQQHROTkFJQC9sLiVTbj1jOHJrNiwKQFhvI09bOSo7OzVlZGZycS9cK0NAQ2suKWc+LEZVVlE3Pm5wP2pXMi9hTjYoLWMxLWRoIkwwdXJPWi5fUnFdWFZMM2NPZl5SXillJkVcJHQKLk1OaDJWdSQwPi4iaC9DcjpnPzhJTlgnRyo6PVhaWUhEZFRUPVw7MWw9NTpITUJHOWg8czFaaTg6UCVKMkFcbzhpTF9qIVtVQFZxQ1VxIVAKSFhBJVNKS29LLUliPjoxSGpZZUEyKHJwQVwrRl5NJUdSNVFHUF5UQGFnYSZKa0tBKkgnNm5GRFJRUygiU0lWOStyRl9oZ1JFY1dFaGQ5W1kKO0duVnBrYTRob2grRlM1czEsKytjQWQ+Tmw9MGVEImVEXFQhP0s9TkhsMy4+JERHZDk/cGcsQ1pnP00kYjBgOTo0P2BqbVZRcyE0JEJBKnQKXUxuP3NwNFFeJjI1M0VQTHF0OFZOanFeSDpZMiloazxXVVFgZUdSZ3EuYVVEI0YiPG8iUVApblc8LUNHUS4yRkJUSzInVkApI2EkaSckKDcKQmBSPj1BSFlmdUE7MDd0QUgzTS9QTFl1KzknWUgyYWNWUjVpKDA9N09dRW41MFhpa09RcV9QVk1jSGwqTSombUI1J250NFJXVTRoNFwobS4KYDJZYCZycFdIdWFmZ01JVThWbW1eZTNxKSpSYG9qMlhlPzNHZFJ1KWE7V2I8ZCRATVszY2FqYkg8cnJYIVErOE0nSUhYSSlpRVJFOSo1cyoKPU5YamwtYFJgUVFiNXJWQi47N2tGLlNXSjlLTWk0N3BySFkhME44aEFLQE46SllgbDhaaU06LTdAZnIpPWkiOHBTWm43XS84Mm5KUCdjOXQKZkBnMzk3OzxtUTBjJDwhMkhnLV9bMVQoJkQpKzNARUZlYSE7cUtfLzBbLzMtTk8qUzNYNXQ4T2cmUjVaOVxKaWJVMzVoYClWPFtLRSUpL2cKNm1nPTBXUiRoMVIlbW9sLiRSPGU6Wl4vLjkqNWRtQC5KXSs3UilEKT9gbj1MTjwlZiRQKGZ1R05pOyk4IyQ+VTwxbFpnbVMvbmhTXE8lIkMKPXJUL2dHR1VTNldUUVQlOERebTZKQVtbWVJeZCQ1NCJKIkpQIidFIUdRX1ZoJ2UoTWM9KTAlcjpuMy1kUj1JTjxTTEZaRlcoUkorIkkpPlkKKFpkcU0pWmRPVWtgIS08TzQlL1xXSzRzS2I5ayYzVGE0SiQsYVg2RCFdN2tARTcqQHNBM09qRCxKWy0nIWE3ajgzb1FXJiIkImBqJSlKJ2UKNXQpUjJWNGlrS1xOIzohJj1CJExTUCcmRV1jOCoyNWNJXz5FXj1HVyJEREZOXjw3UDFUb0ImI0U9NlU5TGFcW29DMiFaXFcpVEskRmVfRDwKKzteaik3WSVZK1U3U2BLVnVsI1tDTWExa01kKWtAZDE1OTo+YHI4MCEqVzxpKDJyXmo+OEEqZlRvQiU+XFc1XChUcW1gPSFcOCpmYUFhLnMKSF51WEUuJVI2ZDdZImFUKFFWSj9DPUdIXD1EN2smMXVcNy0laWQxIkAmO0lTZEtuLDRhJD5wTEUqX25zJTtjNzNrOl5xbVtGP2lCZFxBUl0KYSstRUQxXihBK1tGUW9CMWNGYyxNNSY4Nlh0KVQ7PXJKNWFKQj85REtSZShIVUNhcS0pREdKT1YkYDIxcnBjLDdYZV5FaEpHLF1XQDcxNk4KYG0tL1VrTC4uVlojQFspNGkzU2MpXFRZUSlPUEAlbyZxT1Y/citFIj4qP0NDWSpSOyJjSUdJYmRnJHM3a0wyZEBVWGpMdEdCXk9GTVs/ZmkKSVduIz1caG4uSGNnJk48QksuJyRlLEAyV2g4QXBFX2ZZWT9tYyFtOWJyOkQkLTsoWF1AbjJLPDI1XD1NUnVeTjZFJU0tXVRUJSNUMkchPDsKbjlYIlZWLCk2ZmxeJCNJKCtNQldXbkRvNVNzSXMvI0tZQUNxcjc3USFdW3A5bl1SYCZhLks/LjE5NnRTUykqPj5XLFtmPGQ6Yy1kVyM8OVgKYlhbOSo4JyhTUF1ESig9TUIuJFRELSJnUkRsMzoraiRVMic+WU0rc2JCTGYzbCtFNTk9ZkBiSEFmTDgrN1VfUy00Yio2Yz9pVGNZbWFwOXUKSixmPm4wPkMxXjVAKzFBWW1gOmVyNVk4cytxITAoQkhAOUxGJGA7XkQySUMlVUREIWlgRnRQNzRvT1EsImNdLTdGJWkkZFtmZCxCUmt1Q0sKM25lJiNNPV1tcHJWWFEvNUNRTGFaXj9SJyNNTm9GTyNiVGtgWGokK29gNGg/LUVVKmU3Sm9zXXI3PkMsLlFwNSNNZklRXmtfTl0sL0ZSJDMKMFowJClaIyJtXGksX2hrWVhZbFknYlUhU1whLlZAPXFoaGFKbFg9K1ImL290Mj9oUzElTjBcazInZGBnLWBscUMsXytBbV4uMkVbJCFicXUKPU1NMVRIOk0takZVKl1dLGsoXEZKbCM0OGA4YClHVjAuY1FUSTxtNDI7VGBSRF8lcClMPVJIPz5DdDpFXm4uWEdnLD5hdXEyZ2NfcDVcTVQKVGdVL11mP2VoKzgqKiFNOWpLOU88azs0UFteWkY1NDpcQCYzNVIvQV0rRThZXW9YQE1bRkU3OWlYQUJLTDZzaCk+VjEpck1BZSYuZHMyVSkKVGhRYTEpY0NTaDQ+NSMoUXM8NnVfSyQqYjlDcCs1RTFcSzA+RCxDM2w7JzonJVlbI2NSMGxeS0M4bmZWNXFnUEEhXWIwdGUlT2BaO0smXmgKYjc3OjBkV2dhamkuZmFYcTluUWw8Nk4pbkBOP0BiTnR0YVssO15QXDNPUzwrWFdfZnJMS1pMU1VKPDxVWzIzUGorYScsL2c8c2JIaURCPlgKSFBYK3BsSFtxSENdVEc1YnUpWnBlbCRecGZeLWInYyxqPkdMaUAzRiIyTWtfa29EQFhlJ1dhSWVsbSIrbCQ2OyEjPltPMCQ1LUUzSUc0Nm0KZVQmZTc9KTdkIWRTZWI1ZTJaOmdsJEciISE2RT9vNSt0JjkwaFBhdSVIKEtqbGpQbltFJi9rZVtGWSJfQ14mcFVZVEorTD9dbDFAQlxhQ3AKPnQwK2ZVOSNTaGlkX0s/Y2Erb3RVPi9gIWIyb1JkNTBHVipXQ2tfJmpDMHNRNSZZYEBjYV1wJDNvQ1VbOSdYaWAvdVA/aFRRLCdHRFZRaEcKXlUuWidFakBNVjRuM2E5ODc4Um1TXjNmaDwiY11eVilxb1I+aEtvRVxsaHVXLVtzW29xUW1TJk9fSnF1NzYoRCI+KDx1KEMkVmo/N2RhclQKZCU+KSU/KEZdbjxYK2pvRz4lNjROTC4rNy83W2UjLzovOjVoZlFNMVIyMWJrM1NCVFJVay1vRkRoaEdVZCNAZkhMR2xOQnEwNzBMalJGTycKNXMmMEVLNi00OmNBbzg4KVNkcUMwZi81YVVHJjFAUUZca3A5OjxvX0s0UG0saWJFPTxHZDInPlhDNXU3QU1VRWJtZFJsXDluJzZYZCdAQzIKSGAzN11HSiYlc1A+LV1vJC1MQmBoOWMjaW9xQmwvbG5samQtMEpLKnJVR1UsYWtpMDNkLyljMVtaaD5aRlFJIllPJiNha1hoLGRuUG5qZWkKK2AmZCNwa0k6clNOZUo5WnFCVWYwLnRpczNDWFJNYCosT28+OyVVQW9NLjFbX15HSDhkKDhoLlkoVjxdKUYmbGo+T2xOJ25HV2ZxbylHJH4KPgplbmRzdHJlYW0KZW5kb2JqCjIwIDAgb2JqCjw8IC9UeXBlIC9YT2JqZWN0Ci9TdWJ0eXBlIC9JbWFnZQovV2lkdGggMTE4Ci9IZWlnaHQgNDkKL0NvbG9yU3BhY2UgL0RldmljZUdyYXkKL0JpdHNQZXJDb21wb25lbnQgOAovTGVuZ3RoIDQ2MQovRmlsdGVyIFsvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGVdCj4+c3RyZWFtCkdiIi9lSkldUj8jWG5Ya1Q2QT5YS25EYldCIk1aRWFqUHBkNF0nKF5AUmx0ImtCIlMwJGYlPz1tPTRDOzsuJE4oalJjWVIlc2QmbDkkT3ReCikmNz1MKDctZXFxZUAuKC9TQzk4NC1mTFhlTFo1cWNaNWxBRUI1NT4zQDA9ayI7UmgyaEJjUUwzJko/NW9bY0gwYlNGTl48OztANDFTWTltCmMiWkk9WWwjYzQpYF8iWWxtTjMlLkEubE5TYFZlL1k8JT8uNygoKS8uZEJbO2shSlslJyVESlxJPythNzo1b05rWVxxRVM+MzxJNWJabShJCiVkPEBCKThEYnQzcEtHY2xiUWsxJ2laVnM3Tk0wXG8mUipxVT5nSHUtRnJDa2g8a0hGRypcJE09X3NWLy0kXEpGOmUvPz5mWEErQ0NtcERlCmRTUDZHY3UsXFgnQUw9YTVKQ1s0NkcuaHAyPVU0ZV4kZW9cUSNiKm03QzgkLUpBKGNaP1lgJ0M7NkpwSGVQbFwkSEVDIXVeKlFhKzZnRU1rCltmRVYqYi4jPnByPi1XU2YjPmgmVz91a2tUc2hZYD0vWC42NkEqO2Jpcy9kZ0BRWFhzcjhtO34+CmVuZHN0cmVhbQplbmRvYmoKMjEgMCBvYmoKPDwgL1R5cGUgL1hPYmplY3QKL1N1YnR5cGUgL0ltYWdlCi9XaWR0aCA1NAovSGVpZ2h0IDU0Ci9Db2xvclNwYWNlIC9EZXZpY2VHcmF5Ci9CaXRzUGVyQ29tcG9uZW50IDgKL0xlbmd0aCA3NwovRmlsdGVyIFsvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGVdCj4+c3RyZWFtCkdiIjBKZDBUZHEkajRvRl5VLCJIVHM5RUlFOzBBVCxfRSpMWiVvQDdKbDVWO0gnQ3M9VHJxRGFILjRCZiNjNE9WVDsoZCNmPEdFOX4+CmVuZHN0cmVhbQplbmRvYmoKMjIgMCBvYmoKPDwgL1R5cGUgL1hPYmplY3QKL1N1YnR5cGUgL0ltYWdlCi9XaWR0aCAyMDkKL0hlaWdodCA2OAovQ29sb3JTcGFjZSAvRGV2aWNlR3JheQovQml0c1BlckNvbXBvbmVudCA4Ci9MZW5ndGggMTMwOAovRmlsdGVyIFsvQVNDSUk4NURlY29kZSAvRmxhdGVEZWNvZGVdCj4+c3RyZWFtCkdiIi9jZDtnM20jUXNvJlQtYjxBVyRVVE9NPVpsOGolSmBCY09NKDslR2E3QFQ/aSNkZUc4Yi5uK1hZRHBpbm5bXGotMmNmXVchIV5qM3QvCl44aVVmcExgP0lyVjs6KzxJPSFvN0YwNUInayZKczhbLShZUDpEX1dZWSNCVUNFSz0tNkEjZj03IUgxQj0/bGJJTzZcZ0xlckx0XCU2TiotCjtocXFSJlwoND1aZU9SX2tnayRYYkBaTFciKi85O1VwbjhzVkE6JT9rZEl0O1MkZDYzXEZdImktZTtjMmQvdUc9ZkZaczs4OypSK2lSZWNICidTX1NCTj4yTiU7IWIkPzZtbUYkUWItcT0rZlVWUGtxJW5qM0BvaGAtblY0Z1xpLTk5VEE1ZmlrSzhtUFhiTDAlW0dzb0AzNjojKilMdWxaCkRPLyxqZXFXODRfNkdqS0lAaFtWMWhOckswODYoZmRgLTosTV8tKl5CLXEmYTAnLS00OnEjKmkhS2xBaGRuLztuTFE/Sy8taSRWUUpgaS8hCiQnJnE2IyEhTSI9Mm9ySyxoaiJdKikkYzIzMkkvYUIjPVNeIiFCPmQ+V1ZwXklENDxwbi1KTmJzKCpXZVxMb1RqMlRWXlhacV01KTo6M0E+CkVsZGlpNl5pQ2hpR2dpMSshQ2MtKDFSUHFBQ0B1UykoaSFzPFBnNDxlZidEUCgvVV8uOTRpY01APkNhIiVQdHFTXkZmW2IzYjFTQCdRdFArCilLSWAvbGFBK1dkLnR0QUtlOU4+LFJ0ZGInPWUta0NLaGNrMGJdSFM7KDRlXiVETT0uckg9ayRyN0gtZjdcXXMnM1hPMnMkZ2hNNi5oKlkwCiVQYUk0QU11YlUpcUFyXWknXHUvLSNdOVVKVFJpMVZxKWI5JGIlX2Q5I0FzOU9bIkhBa1s+LG1cPDIjXWpIWGB1TWFLcipHIWZiP2o3c108Ci0qblU5Z19JSiZnMm9EVXJkJ2cqXjVtOUBmWyxhY0BoSldZSU51LilUQnFjPiprdG5oZS1wTDAtK20/UzpPPE9iMy1GdTgmOFgzJjElSzw/CjBWcTA/RzJqSkA/YElZQyY/aTc+MjpPQFRJLnJIXmFNbDY4U19tTk1tNUM/SmQ+KU8yWmI4LjgwIV8wRCVIWTZgXStOSm9vUUs6Iz1QLmwwCkFdU3VCKnFBXTpLT09WVzJdR1hXSHBlW0hFMW9UTjpRQTFab2xrXFM5ZkgnPy5NIjEoRiJjbDsiQGhQbV1HW1lgQkkwamxHRSc2cydCSyxgCjYkP2JJK1RrYmdXKnR1OEwtPCMhNls7PCxhSVg9bkZpOjlrTVFwLDFQZHVobyVATz5jXWBYWkMrdWBAXFEhRnU2LmNNWyU1QGgjO2ApOnFZCnMpbUQ6VC04N2tfNzpsP0BVR0o+W3Q+Kl1QUXRlNSU4XlVQViYvZGhbXzE6VE9yRmNcIyZeW1tQUlJIJTdTSm8xPUFmSGFdUiE8U2QnZDoqCjx1TS4yPlJEZCI5WF9mNitDVF42YmMxalFfK2AybUQqb1hUOjE1VCJUOnJFbGRQZDhWRiJvKTQ6RzM9MVNJTC0obVpJXEBJYWcrKScibGtZCkBGQE1AYCNDIXU1WzYlaylocEs2UkFORC5qTW1nVGJKR3JsLmgsTTprLSgrJmVDNXAsRyJHYHEuLWh0cjdYPT5YJVNlM25XZkkrJThjUzQ1Cl49aFpjOnNccmh+PgplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCAyMwowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMDkgMDAwMDAgbiAKMDAwMDAwMDA1OCAwMDAwMCBuIAowMDAwMDAwMTA0IDAwMDAwIG4gCjAwMDAwMDAxNjIgMDAwMDAgbiAKMDAwMDAwMDIxNCAwMDAwMCBuIAowMDAwMDAwMzEyIDAwMDAwIG4gCjAwMDAwMDA0MTUgMDAwMDAgbiAKMDAwMDAwMDUyMSAwMDAwMCBuIAowMDAwMDAwNjMxIDAwMDAwIG4gCjAwMDAwMDA3MjcgMDAwMDAgbiAKMDAwMDAwMDgyOSAwMDAwMCBuIAowMDAwMDAwOTM0IDAwMDAwIG4gCjAwMDAwMDEwNDMgMDAwMDAgbiAKMDAwMDAwMTE0NCAwMDAwMCBuIAowMDAwMDAxMjQ0IDAwMDAwIG4gCjAwMDAwMDEzNDYgMDAwMDAgbiAKMDAwMDAwMTQ1MiAwMDAwMCBuIAowMDAwMDAxNjIyIDAwMDAwIG4gCjAwMDAwMDIwMDIgMDAwMDAgbiAKMDAwMDAwNTc0MCAwMDAwMCBuIAowMDAwMDA2Mzg3IDAwMDAwIG4gCjAwMDAwMDY2NDggMDAwMDAgbiAKdHJhaWxlcgo8PAovSW5mbyAxNyAwIFIKL1NpemUgMjMKL1Jvb3QgMSAwIFIKPj4Kc3RhcnR4cmVmCjgxNDMKJSVFT0YK</Image></Parts></Label><SignatureOption>SERVICE_DEFAULT</SignatureOption></CompletedPackageDetails></CompletedShipmentDetail></ProcessShipmentReply></SOAP-ENV:Body></SOAP-ENV:Envelope>'
                elif b'<ns0:DeleteShipmentRequest' in kwargs.get('data'):
                    response.content = b'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body><ShipmentReply xmlns="http://fedex.com/ws/ship/v28"><HighestSeverity>SUCCESS</HighestSeverity><Notifications><Severity>SUCCESS</Severity><Source>ship</Source><Code>0000</Code><Message>Success</Message><LocalizedMessage>Success</LocalizedMessage></Notifications><TransactionDetail><CustomerTransactionId>234</CustomerTransactionId></TransactionDetail><Version><ServiceId>ship</ServiceId><Major>28</Major><Intermediate>0</Intermediate><Minor>0</Minor></Version></ShipmentReply></SOAP-ENV:Body></SOAP-ENV:Envelope>'
                elif b'<ns0:RateRequest' in kwargs.get('data'):
                    response.content = b'<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"><SOAP-ENV:Header/><SOAP-ENV:Body><RateReply xmlns="http://fedex.com/ws/rate/v31"><HighestSeverity>WARNING</HighestSeverity><Notifications><Severity>WARNING</Severity><Source>crs</Source><Code>396</Code><Message>The returned rate types are in the requested preferred currency; preferred rates not returned.</Message><LocalizedMessage>The returned rate types are in the requested preferred currency; preferred rates not returned.</LocalizedMessage></Notifications><TransactionDetail><CustomerTransactionId>S00402</CustomerTransactionId></TransactionDetail><Version><ServiceId>crs</ServiceId><Major>31</Major><Intermediate>0</Intermediate><Minor>0</Minor></Version><RateReplyDetails><ServiceType>PRIORITY_OVERNIGHT</ServiceType><ServiceDescription><ServiceType>PRIORITY_OVERNIGHT</ServiceType><Code>01</Code><Names><Type>long</Type><Encoding>utf-8</Encoding><Value>FedEx Priority Overnight\xc3\x82\xc2\xae</Value></Names><Names><Type>long</Type><Encoding>ascii</Encoding><Value>FedEx Priority Overnight</Value></Names><Names><Type>medium</Type><Encoding>utf-8</Encoding><Value>FedEx Priority Overnight\xc3\x82\xc2\xae</Value></Names><Names><Type>medium</Type><Encoding>ascii</Encoding><Value>FedEx Priority Overnight</Value></Names><Names><Type>short</Type><Encoding>utf-8</Encoding><Value>P-1</Value></Names><Names><Type>short</Type><Encoding>ascii</Encoding><Value>P-1</Value></Names><Names><Type>abbrv</Type><Encoding>ascii</Encoding><Value>PO</Value></Names><Description>Priority Overnight</Description><AstraDescription>P1</AstraDescription></ServiceDescription><PackagingType>FEDEX_BOX</PackagingType><DestinationAirportId>CAE</DestinationAirportId><IneligibleForMoneyBackGuarantee>false</IneligibleForMoneyBackGuarantee><OriginServiceArea>A1</OriginServiceArea><DestinationServiceArea>A1</DestinationServiceArea><SignatureOption>SERVICE_DEFAULT</SignatureOption><ActualRateType>PAYOR_ACCOUNT_PACKAGE</ActualRateType><RatedShipmentDetails><ShipmentRateDetail><RateType>PAYOR_ACCOUNT_PACKAGE</RateType><RateScale>1618</RateScale><RateZone>08</RateZone><PricingCode>PACKAGE</PricingCode><RatedWeightMethod>PACKAGING_MINIMUM</RatedWeightMethod><DimDivisor>0</DimDivisor><FuelSurchargePercent>19.5</FuelSurchargePercent><TotalBillingWeight><Units>LB</Units><Value>2.0</Value></TotalBillingWeight><TotalBaseCharge><Currency>USD</Currency><Amount>101.28</Amount></TotalBaseCharge><TotalFreightDiscounts><Currency>USD</Currency><Amount>0.0</Amount></TotalFreightDiscounts><TotalNetFreight><Currency>USD</Currency><Amount>101.28</Amount></TotalNetFreight><TotalSurcharges><Currency>USD</Currency><Amount>19.75</Amount></TotalSurcharges><TotalNetFedExCharge><Currency>USD</Currency><Amount>121.03</Amount></TotalNetFedExCharge><TotalTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalTaxes><TotalNetCharge><Currency>USD</Currency><Amount>121.03</Amount></TotalNetCharge><TotalRebates><Currency>USD</Currency><Amount>0.0</Amount></TotalRebates><TotalDutiesAndTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalDutiesAndTaxes><TotalAncillaryFeesAndTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalAncillaryFeesAndTaxes><TotalDutiesTaxesAndFees><Currency>USD</Currency><Amount>0.0</Amount></TotalDutiesTaxesAndFees><TotalNetChargeWithDutiesAndTaxes><Currency>USD</Currency><Amount>121.03</Amount></TotalNetChargeWithDutiesAndTaxes><Surcharges><SurchargeType>FUEL</SurchargeType><Description>Fuel</Description><Amount><Currency>USD</Currency><Amount>19.75</Amount></Amount></Surcharges></ShipmentRateDetail><RatedPackages><GroupNumber>0</GroupNumber><PackageRateDetail><RateType>PAYOR_ACCOUNT_PACKAGE</RateType><RatedWeightMethod>PACKAGING_MINIMUM</RatedWeightMethod><BillingWeight><Units>LB</Units><Value>2.0</Value></BillingWeight><BaseCharge><Currency>USD</Currency><Amount>101.28</Amount></BaseCharge><TotalFreightDiscounts><Currency>USD</Currency><Amount>0.0</Amount></TotalFreightDiscounts><NetFreight><Currency>USD</Currency><Amount>101.28</Amount></NetFreight><TotalSurcharges><Currency>USD</Currency><Amount>19.75</Amount></TotalSurcharges><NetFedExCharge><Currency>USD</Currency><Amount>121.03</Amount></NetFedExCharge><TotalTaxes><Currency>USD</Currency><Amount>0.0</Amount></TotalTaxes><NetCharge><Currency>USD</Currency><Amount>121.03</Amount></NetCharge><TotalRebates><Currency>USD</Currency><Amount>0.0</Amount></TotalRebates><Surcharges><SurchargeType>FUEL</SurchargeType><Description>Fuel</Description><Amount><Currency>USD</Currency><Amount>19.75</Amount></Amount></Surcharges></PackageRateDetail></RatedPackages></RatedShipmentDetails></RateReplyDetails></RateReply></SOAP-ENV:Body></SOAP-ENV:Envelope>'
                return response

        # zeep.Client.transport is using post from requests.Session
        with patch('zeep.transports.requests.Session') as mocked_session:
            mocked_session.side_effect = MockedSession
            yield mocked_session


    def test_01_fedex_basic_us_domestic_flow(self):
        with self.patch_fedex_requests():
            super().test_01_fedex_basic_us_domestic_flow()

    def test_02_fedex_basic_international_flow(self):
        with self.patch_fedex_requests():
            super().test_02_fedex_basic_international_flow()

    def test_03_fedex_multipackage_international_flow(self):
        with self.patch_fedex_requests():
            super().test_03_fedex_multipackage_international_flow()

    def test_04_fedex_international_delivery_from_delivery_order(self):
        with self.patch_fedex_requests():
            super().test_04_fedex_international_delivery_from_delivery_order()

    def test_05_fedex_multistep_delivery_tracking(self):
        with self.patch_fedex_requests():
            # Set Warehouse as multi steps delivery
            self.env.ref("stock.warehouse0").delivery_steps = "pick_pack_ship"

            sale_order = self.env['sale.order'].create({
                'partner_id': self.agrolait.id,
                'order_line': [(0, None, {
                    'product_id': self.iPadMini.id,
                    'name': "[A1232] iPad Mini",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price,
                })],
            })
            # I add delivery cost in Sales order
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': sale_order.id,
                'default_carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_inter').id
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.update_price()
            choose_delivery_carrier.button_confirm()

            # Confirm the picking and send to shipper
            sale_order.action_confirm()
            picking = sale_order.picking_ids[0]
            picking.move_ids.quantity = 1.0
            picking.move_ids.picked = True
            picking._action_done()
            picking.send_to_shipper()

            for p in sale_order.picking_ids:
                self.assertTrue(any("Tracking Numbers:" in m for m in p.message_ids.mapped('preview')))
