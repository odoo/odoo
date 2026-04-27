# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch, Mock

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.sale_amazon.tests import common
from odoo.addons.stock.tests.common import TestStockCommon


@tagged('post_install', '-at_install')
class TestStock(common.TestAmazonCommon, TestStockCommon):

    # As this test class is exclusively intended to test Amazon-related check on pickings, the
    # normal flows of stock are put aside in favor of manual updates on quantities.

    def setUp(self):
        super().setUp()

        # Create sales order
        self.partner = self.env['res.partner'].create({'name': "Gederic Frilson"})
        amazon_offer = self.account._find_or_create_offer(
            'test SKU', self.account.base_marketplace_id
        )
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': 'test',
                'product_id': self.productA.id,
                'product_uom_qty': 2,
                'amazon_item_ref': '123456789',
                'amazon_offer_id': amazon_offer.id,
            })],
            'amazon_order_ref': '123456789',
        })

        # Create picking
        self.picking = self.PickingObj.create({
            'picking_type_id': self.picking_type_in,
            'location_id': self.supplier_location,
            'location_dest_id': self.customer_location,
        })
        move_vals = {
            'name': self.productA.name,
            'product_id': self.productA.id,
            'product_uom_qty': 1,
            'product_uom': self.productA.uom_id.id,
            'picking_id': self.picking.id,
            'location_id': self.supplier_location,
            'location_dest_id': self.customer_location,
            'sale_line_id': self.sale_order.order_line[0].id,
        }
        self.move_1 = self.MoveObj.create(move_vals)
        self.move_2 = self.MoveObj.create(move_vals)
        self.picking.sale_id = self.sale_order.id  # After creating the moves as it clears the field

    def test_confirm_picking_trigger_SOL_check(self):
        """ Test that confirming a picking triggers a check on sales order lines completion. """

        with patch(
            'odoo.addons.sale_amazon.models.stock_picking.StockPicking'
            '._check_sales_order_line_completion',
            new=Mock(),
        ) as mock:
            self.picking.date_done = fields.Datetime.now()  # Trigger the check for SOL completion
            self.assertEqual(
                mock.call_count, 1, "confirming a picking should trigger a check on the sales "
                                    "order lines completion"
            )

    def test_check_SOL_completion_no_move(self):
        """ Test that the check on SOL completion passes if no move is confirmed. """

        self.assertIsNone(
            self.picking._check_sales_order_line_completion(),
            "the check of SOL completion should not raise for pickings with completions of 0% (no"
            "confirmed move for a given sales order line)"
        )

    def test_check_SOL_completion_all_moves(self):
        """ Test that the check on SOL completion passes if all moves are confirmed. """

        self.move_1.quantity = 1
        self.move_2.quantity = 1
        self.assertIsNone(
            self.picking._check_sales_order_line_completion(),
            "the check of SOL completion should not raise for pickings with completions of 100% "
            "(all moves related to a given sales order line are confirmed)"
        )

    def test_check_SOL_completion_some_moves(self):
        """ Test that the check on SOL completion fails if only some moves are confirmed. """

        self.move_1.quantity = 1
        with self.assertRaises(UserError):
            # The check of SOL completion should raise for pickings with completions of ]0%, 100%[
            # (some moves related to a given sales order line are confirmed, but not all)
            self.picking._check_sales_order_line_completion()

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_check_carrier_details_compliance_delivered_for_amazon(self):
        """ Test the validation of a picking when Amazon already flagged it as being delivered. """

        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.write({
                'amazon_sync_status': 'done', 'carrier_id': None, 'carrier_tracking_ref': None
            })
            picking.location_dest_id.usage = 'customer'
            picking._check_carrier_details_compliance()  # Don't raise when Amazon has the info

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_check_carrier_details_compliance_no_carrier(self):
        """ Test the validation of a picking when the delivery carrier is not set. """
        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id = None
            picking.carrier_tracking_ref = self.tracking_ref
            picking.location_dest_id.usage = 'customer'
            with self.assertRaises(UserError):
                picking._check_carrier_details_compliance()

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_check_carrier_details_compliance_intermediate_delivery_step(self):
        """ Test the validation of a picking when the delivery is in an intermediate step."""
        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id = None
            picking.carrier_tracking_ref = self.tracking_ref
            intermediate_destination_id = self.env.ref('stock.location_pack_zone').id
            picking.location_dest_id = intermediate_destination_id
            picking._check_carrier_details_compliance()  # Don't raise if intermediate delivery step

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_check_carrier_details_compliance_no_tracking_number(self):
        """ Test the validation of a picking when the tracking reference is not set. """
        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id = self.carrier
            picking.carrier_tracking_ref = None
            with self.assertRaises(UserError):
                picking._check_carrier_details_compliance()

    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_check_carrier_details_compliance_requirements_met_in_last_step_delivery(self):
        """ Test the validation of a picking when the delivery carrier and tracking ref are set. """
        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.carrier_id, picking.carrier_tracking_ref = self.carrier, self.tracking_ref
            picking._check_carrier_details_compliance()  # Everything is fine, don't raise

    def test_get_carrier_details_returns_carrier_name_when_unsupported(self):
        """Test that we fall back on the custom carrier's name if it's not supported by Amazon."""
        self.picking.carrier_id = self.carrier
        carrier_name = self.picking._get_formatted_carrier_name()
        self.assertEqual(carrier_name, self.carrier.name)

    def test_get_carrier_details_returns_formatted_carrier_name_when_supported(self):
        """Test that we use the formatted carrier name when it is supported by Amazon."""
        self.carrier.name = 'd_H l)'
        self.picking.carrier_id = self.carrier
        carrier_name = self.picking._get_formatted_carrier_name()
        self.assertEqual(carrier_name, 'DHL')

    def test_sync_orders_confirms_pickings_with_a_pending_status(self):
        """ Test pickings with a status of pending in odoo are updated when receiving the
        information that the order is delivered from Amazon. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mock response without making an actual call to the Selling Partner API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            if operation_ == 'getOrder':
                response_ = {'payload': dict(common.ORDER_MOCK, OrderStatus='Shipped')}
            else:
                response_ = base_response_
            return response_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ):
            # Set up the test pickings
            self.picking.update({'amazon_sync_status': 'error', 'state': 'cancel'})
            # Create a new picking
            pending_picking = self.PickingObj.create({
                'picking_type_id': self.picking_type_in,
                'location_id': self.supplier_location,
                'location_dest_id': self.customer_location,
            })
            move_vals = {
                'name': self.productA.name,
                'product_id': self.productA.id,
                'product_uom_qty': 1,
                'product_uom': self.productA.uom_id.id,
                'picking_id': pending_picking.id,
                'location_id': self.supplier_location,
                'location_dest_id': self.customer_location,
                'sale_line_id': self.sale_order.order_line[0].id,
            }
            self.MoveObj.create(move_vals)
            pending_picking.sale_id = self.sale_order.id

            self.account._sync_order_by_reference(self.sale_order.amazon_order_ref)
            self.assertEqual(
                self.picking.amazon_sync_status,
                'error',
                msg="Picking with an errored Amazon sync status should not be updated when there is"
                    "another pending picking and the picking is confirmed by Amazon."
            )
            self.assertEqual(
                pending_picking.amazon_sync_status,
                'done',
                msg="Picking with a pending Amazon sync status should be updated when the picking "
                    "is confirmed by Amazon."
            )

    def test_sync_orders_confirms_pickings_with_an_errored_status(self):
        """ Test pickings with a status of errored in odoo are updated when receiving the
        information that the order is delivered from Amazon. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mock response without making an actual call to the Selling Partner API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            if operation_ == 'getOrder':
                response_ = {'payload': dict(common.ORDER_MOCK, OrderStatus='Shipped')}
            else:
                response_ = base_response_
            return response_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ):
            # Set up the test pickings
            self.picking.update({'amazon_sync_status': 'error'})

            self.account._sync_order_by_reference(self.sale_order.amazon_order_ref)
            self.assertEqual(
                self.picking.amazon_sync_status,
                'done',
                msg="Picking with an errored Amazon sync status should be updated when the picking "
                    "is confirmed by Amazon and there is no pending picking."
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_action_retry_amazon_sync_dont_resync_when_picking_is_confirmed_from_amazon(self):

        self.picking.amazon_sync_status = 'error'

        with patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._sync_order_by_reference',
            new=lambda self_, *args_: self.picking.update({'amazon_sync_status': 'done'})
        ):
            self.picking.action_retry_amazon_sync()
        msg = "Picking with Amazon sync status updated during the sync order should stay as done."
        self.assertEqual(self.picking.amazon_sync_status, 'done', msg=msg)

    def test_action_retry_amazon_sync_set_waiting_state_after_resync(self):
        # Make sure we have those fields set on the company.
        self.env.company.partner_id.write({
            'street': 'Company Street Office 2',
            'country_id': self.env.ref('base.be').id,
        })
        self.picking.amazon_sync_status = 'error'
        with patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._sync_order_by_reference',
        ), patch('odoo.addons.sale_amazon.utils.submit_feed', return_value='Mock feed ID'):
            self.picking.action_retry_amazon_sync()
        msg = "Picking with Amazon sync status not updated in the sync order should be re-submitted"
        self.assertEqual(self.picking.amazon_sync_status, 'processing', msg=msg)
        msg = "Picking re-submitted have the new feed ID set."
        self.assertEqual(self.picking.amazon_feed_ref, 'Mock feed ID', msg=msg)

    def test_generate_stock_moves_for_not_tracked_product_sets_move_done(self):
        self.product.tracking = 'none'
        self.env['stock.quant'].create(
            {'product_id': self.product.id, 'location_id': self.stock_location, 'quantity': 30}
        )
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({
                'product_id': self.product.id,
                'amazon_item_ref': 'item_ref',
                'product_uom_qty': 2,
            })],
            'amazon_order_ref': 'test_ref',
            'state': 'sale',
            'locked': True,
        })
        StockMove = self.env['stock.move']
        initial_moves = StockMove.search([('product_id', '=', self.product.id)])
        self.assertFalse(initial_moves, msg="No stock move should be created yet.")

        self.account._generate_stock_moves(sale_order)

        new_moves = StockMove.search(
            [('product_id', '=', self.product.id), ('id', 'not in', initial_moves.ids)]
        )

        msg = "All moves should be set as done."
        self.assertEqual(new_moves.state, 'done', msg=msg)
