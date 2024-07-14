# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.addons.delivery_easypost.tests.common import EasypostTestCommon
from odoo.exceptions import UserError
from odoo.tests import tagged, Form

_logger = logging.getLogger(__name__)


@tagged('-standard', 'external')
class TestDeliveryEasypost(EasypostTestCommon):
    def wiz_put_in_pack(self, picking):
        """ Helper to use the 'choose.delivery.package' wizard
        in order to call the 'action_put_in_pack' method.
        """
        wiz_action = picking.action_put_in_pack()
        self.assertEqual(wiz_action['res_model'], 'choose.delivery.package', 'Wrong wizard returned')
        wiz = Form(self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'delivery_package_type_id': picking.carrier_id.easypost_default_package_type_id.id
        }))
        choose_delivery_carrier = wiz.save()
        choose_delivery_carrier.action_put_in_pack()

    def test_easypost_one_package_shipping(self):
        """ Try to rate and ship an order from
        New York to Miami. It will not use a specific
        package and everything will be consider to be
        inside the same package.
        """
        SaleOrder = self.env['sale.order']
        sol_1_vals = {'product_id': self.server.id}
        sol_2_vals = {'product_id': self.miniServer.id}
        so_vals_fedex = {'partner_id': self.jackson.id,
                   'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

        sale_order_fedex = SaleOrder.create(so_vals_fedex)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order_fedex.id,
            'default_carrier_id': self.easypost_fedex_carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()

        self.assertGreater(choose_delivery_carrier.delivery_price, 0.00, "Could't get rate for this order from easypost fedex")
        choose_delivery_carrier.button_confirm()
        sale_order_fedex.action_confirm()

        self.assertEqual(len(sale_order_fedex.picking_ids), 1, "The Sales Order did not generate a picking for ep-fedex.")
        picking_fedex = sale_order_fedex.picking_ids[0]

        picking_fedex.action_assign()
        picking_fedex.move_line_ids.write({'quantity': 1})
        self.assertGreater(picking_fedex.weight, 0.0, "Picking weight should be positive.(ep-fedex)")

        # Set a service in order to test rate request for a specific service.
        self.easypost_fedex_carrier.easypost_default_service_id = self.env['easypost.service'].search([('name', '=', 'STANDARD_OVERNIGHT')]).id

        if not self.easypost_fedex_carrier.easypost_default_service_id:
            _logger.warning('"STANDARD_OVERNIGHT" is not anymore a fedex service, easypost default service is not tested.')

        picking_fedex.move_ids.picked = True
        picking_fedex._action_done()
        self.assertGreater(picking_fedex.carrier_price, 0.0, "Easypost carrying price is probably incorrect(fedex)")
        self.assertIsNot(picking_fedex.carrier_tracking_ref, False,
                         "Easypost did not return any tracking number (fedex)")

    # broken -> FedEx returned error: Ground Shipping is not authorized for this User
    def test_easypost_multiple_packages_shipping(self):
        """ Same than test with one package. This
        time it will use the put in pack functionality.
        It will send twice the default package type with
        2 servers and 3 mini servers.
        """
        SaleOrder = self.env['sale.order']
        sol_1_vals = {'product_id': self.server.id}
        sol_2_vals = {'product_id': self.miniServer.id}
        so_vals_fedex = {'partner_id': self.jackson.id,
                   'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

        sale_order_fedex = SaleOrder.create(so_vals_fedex)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order_fedex.id,
            'default_carrier_id': self.easypost_fedex_carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()
        self.assertGreater(choose_delivery_carrier.delivery_price, 0.00, "Could't get rate for this order from easypost fedex")
        choose_delivery_carrier.button_confirm()
        sale_order_fedex.action_confirm()

        self.assertEqual(len(sale_order_fedex.picking_ids), 1, "The Sales Order did not generate a picking for ep-fedex.")
        picking_fedex = sale_order_fedex.picking_ids[0]
        self.assertEqual(picking_fedex.carrier_id.id, sale_order_fedex.carrier_id.id,
                          "Carrier is not the same on Picking and on SO(easypost-fedex).")

        picking_fedex.action_assign()
        picking_fedex.move_ids[0].write({'quantity': 2, 'picked': True})
        self.wiz_put_in_pack(picking_fedex)
        picking_fedex.move_ids[0].move_line_ids.result_package_id.package_type_id = self.fedex_default_package_type.id
        picking_fedex.move_ids[0].move_line_ids.result_package_id.shipping_weight = 10.0
        picking_fedex.move_ids[1].write({'quantity': 3, 'picked': True})
        self.wiz_put_in_pack(picking_fedex)
        picking_fedex.move_ids[1].move_line_ids.result_package_id.package_type_id = self.fedex_default_package_type.id
        picking_fedex.move_ids[1].move_line_ids.result_package_id.shipping_weight = 10.0
        self.assertGreater(picking_fedex.weight, 0.0, "Picking weight should be positive.(ep-fedex)")
        picking_fedex._action_done()
        self.assertGreater(picking_fedex.carrier_price, 0.0, "Easypost carrying price is probably incorrect(fedex)")
        self.assertIsNot(picking_fedex.carrier_tracking_ref, False,
                         "Easypost did not return any tracking number (fedex)")

    def test_easypost_one_package_international_shipping(self):
        """ Same than test_easypost_one_package_shipping with
        an international shipping. (it matters due to customs info).
        """
        SaleOrder = self.env['sale.order']
        sol_1_vals = {'product_id': self.server.id}
        sol_2_vals = {'product_id': self.miniServer.id}
        so_vals_fedex = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

        # Modify price due to US customs info. If you a value greater than
        # 2500$, it requires an specific AES code.
        self.server['list_price'] = 10.0
        self.miniServer['list_price'] = 10.0

        sale_order_fedex = SaleOrder.create(so_vals_fedex)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order_fedex.id,
            'default_carrier_id': self.easypost_fedex_carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()

        self.assertGreater(choose_delivery_carrier.delivery_price, 0.00, "Could't get rate for this order from easypost fedex")
        choose_delivery_carrier.button_confirm()
        sale_order_fedex.action_confirm()

        self.assertEqual(len(sale_order_fedex.picking_ids), 1, "The Sales Order did not generate a picking for ep-fedex.")
        picking_fedex = sale_order_fedex.picking_ids[0]
        self.assertEqual(picking_fedex.carrier_id.id, sale_order_fedex.carrier_id.id,
                          "Carrier is not the same on Picking and on SO(easypost-fedex).")

        picking_fedex.action_assign()
        picking_fedex.move_line_ids.write({'quantity': 1})
        picking_fedex.move_ids.picked = True
        self.assertGreater(picking_fedex.weight, 0.0, "Picking weight should be positive.(ep-fedex)")
        try:
            picking_fedex._action_done()
        except UserError as exc:
            if "carrier is not responding to our request" in exc.args[0]:
                _logger.warning('easypost test aborted, carrier is unresponsive.')
                return
            raise
        self.assertGreater(picking_fedex.carrier_price, 0.0, "Easypost carrying price is probably incorrect(fedex)")
        self.assertIsNot(picking_fedex.carrier_tracking_ref, False,
                         "Easypost did not return any tracking number (fedex)")

    def test_easypost_extralight_package_shipping(self):
        """ Try to rate and ship an order from
        New York to Miami. Use a very light product.
        """
        SaleOrder = self.env['sale.order']
        sol_1_vals = {'product_id': self.microServer.id}
        so_vals_fedex = {'partner_id': self.jackson.id,
                         'order_line': [(0, None, sol_1_vals)]}

        sale_order_fedex = SaleOrder.create(so_vals_fedex)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order_fedex.id,
            'default_carrier_id': self.easypost_fedex_carrier.id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.update_price()

        self.assertGreater(choose_delivery_carrier.delivery_price, 0.00, "Could't get rate for this order from easypost fedex")
        choose_delivery_carrier.button_confirm()
        sale_order_fedex.action_confirm()

    def test_easypost_sends_correct_delivery_type_for_amazon(self):
        amazon_expected_delivery_type = self.easypost_fedex_carrier._get_delivery_type()
        self.assertEqual(amazon_expected_delivery_type, 'FedEx')


@tagged('standard', '-external')
class TestMockedDeliveryEasypost(TestDeliveryEasypost):
    def setUp(self):
        # this is needed because we use call the API for the carrier setup.
        with self.patch_easypost_requests():
            super().setUp()

    def test_easypost_one_package_shipping(self):
        with self.patch_easypost_requests():
            super().test_easypost_one_package_shipping()

    def test_easypost_multiple_packages_shipping(self):
        with self.patch_easypost_requests():
            super().test_easypost_multiple_packages_shipping()

    def test_easypost_one_package_international_shipping(self):
        with self.patch_easypost_requests():
            super().test_easypost_one_package_international_shipping()

    def test_easypost_extralight_package_shipping(self):
        with self.patch_easypost_requests():
            super().test_easypost_extralight_package_shipping()

    def test_easypost_sends_correct_delivery_type_for_amazon(self):
        with self.patch_easypost_requests():
            super().test_easypost_sends_correct_delivery_type_for_amazon()
