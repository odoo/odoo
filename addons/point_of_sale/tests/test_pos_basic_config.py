# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSBasicConfig(TestPoSCommon):
    """ Test PoS with basic configuration

    The tests contain base scenarios in using pos.
    More specialized cases are tested in other tests.
    """

    def setUp(self):
        super(TestPoSBasicConfig, self).setUp()
        self.config = self.basic_config
        self.product0 = self.create_product('Product 0', self.categ_basic, 0.0, 0.0)
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5)
        self.product2 = self.create_product('Product 2', self.categ_basic, 20.0, 10)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15)
        self.product4 = self.create_product('Product_4', self.categ_basic, 9.96, 4.98)
        self.product99 = self.create_product('Product_99', self.categ_basic, 99, 50)
        self.product_multi_tax = self.create_product('Multi-tax product', self.categ_basic, 100, 100, (self.taxes['tax8'] | self.taxes['tax9']).ids)
        self.company_data_2 = self.setup_other_company()

    def test_pos_session_name_sequencing(self):
        """ This test check if the session name is correctly set according to the sequence """

        sequence = self.env['ir.sequence'].search([('code', '=', 'pos.session')])
        sequence.prefix = '/'
        sequence.write({'number_next_actual': 1000})
        name = self.config.name

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, name + '/01000')

        self.pos_session.close_session_from_ui()

        sequence.prefix = 'TEST/'

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, 'TEST/01001')

    def test_load_data_should_not_fail(self):
        """load_data shouldn't fail

        (Include test conditions here if possible)

        - When there are partners that belong to different company
        """

        # create a partner that belongs to different company
        company2 = self.company_data_2['company']
        self.env['res.partner'].create({
            'name': 'Test',
            'company_id': company2.id,
        })

        self.open_new_session()

        # calling load_data should not raise an error
        self.pos_session.load_data([])

    def test_load_data_picks_the_company_website_domain(self):
        if self.env['ir.module.module']._get('website').state != 'installed':
            self.skipTest("website module is required for this test")

        company_website = self.config.company_id.website_id

        if company_website:
            company_website.write({'domain': 'https://custom.test.domain.com'})
            self.open_new_session()
            response = self.pos_session.load_data([])

            self.assertEqual(response['pos.config'][0]['_base_url'], company_website.domain)

    def test_limited_products_loading(self):
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 3)

        # Make the service products that are available in the pos inactive.
        # We don't need them to test the loading of 'consu' products.
        self.env['product.template'].search([('available_in_pos', '=', True), ('type', '=', 'service')]).write({'available_in_pos': False})

        session = self.open_new_session(0)
        self.product1.write({'company_id': False})
        self.product2.write({'company_id': False})
        self.product3.write({'company_id': False})

        def get_top_product_ids(count):
            data = session.load_data([])
            special_product = session.config_id._get_special_products().ids
            available_top_product = [product for product in data['product.template'] if product['product_variant_ids'][0] not in special_product]
            return [p['product_variant_ids'][0] for p in available_top_product[:count]]

        self.patch(self.env.cr, 'now', lambda: datetime.now() + timedelta(days=1))
        self.env['pos.order'].sync_from_ui([self.create_ui_order_data([(self.product1, 1)])])
        self.assertEqual(get_top_product_ids(1), [self.product1.id])

        self.patch(self.env.cr, 'now', lambda: datetime.now() + timedelta(days=2))
        self.env['pos.order'].sync_from_ui([self.create_ui_order_data([(self.product2, 1)])])
        self.assertEqual(get_top_product_ids(2), [self.product1.id, self.product2.id])

        self.patch(self.env.cr, 'now', lambda: datetime.now() + timedelta(days=3))
        self.env['pos.order'].sync_from_ui([self.create_ui_order_data([(self.product3, 1)])])
        self.assertEqual(get_top_product_ids(3), [self.product1.id, self.product2.id, self.product3.id])

    def test_pos_payment_method_copy(self):
        """
        Test POS payment method copy:
            - Create two payment methods in which one of the payment method's journal type be cash
            - Copy multiple payment methods
            - Check the duplicated cash payment method journal should be empty
        """
        pm_1 = self.cash_pm1
        pm_2 = self.bank_pm1
        pm_3, pm_4 = (pm_1 + pm_2).copy()

        self.assertTrue(pm_3)
        self.assertFalse(pm_3.journal_id)
        self.assertTrue(pm_4)
        self.assertEqual(pm_4.journal_id.type, "bank")

    def test_single_config_global_invoice(self):
        """For a single POS config, create multiple orders and consolidate them into a single invoice"""
        self.open_new_session()
        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 2), (self.product4, 3)],
            payments=[(self.bank_pm1, 49.88)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product4, 1), (self.product2, 5)],
            payments=[(self.bank_pm1, 109.96)]
        ))

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)
        # close the session
        self.pos_session.close_session_from_ui()

        pos_orders = self.env['pos.order'].search([])
        # set customer for the orders
        pos_orders.write({'partner_id': self.customer.id})

        # create consolidated invoice
        self.env['pos.make.invoice'].create({
            "consolidated_billing": True,
        }).with_context({
            "active_ids": pos_orders.ids,
        }).action_create_invoices()
        # check if have single invoice
        self.assertEqual(len(pos_orders), 2)
        self.assertEqual(len(pos_orders.account_move), 1)
        self.assertEqual(pos_orders.account_move.partner_id, self.customer)
        self.assertEqual(pos_orders.account_move.amount_total, sum(pos_orders.mapped('amount_total')))
        self.assertEqual(pos_orders.account_move.payment_state, 'in_payment')
        self.assertEqual(pos_orders.account_move.state, 'posted')
        self.assertEqual(pos_orders.account_move.amount_residual, 0)

    def test_multi_config_global_invoice(self):
        self.open_new_session()
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 3), (self.product2, 10)],
            payments=[(self.bank_pm1, 230)]
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product0, 10)],
            payments=[(self.bank_pm1, 50)]
        ))
        self.env['pos.order'].sync_from_ui(orders)
        self.pos_session.close_session_from_ui()

        # open new session & create orders
        self.open_new_session()
        orders2 = []
        orders2.append(self.create_ui_order_data(
            [(self.product1, 2), (self.product4, 3)],
            payments=[(self.bank_pm1, 49.88)]
        ))
        orders2.append(self.create_ui_order_data(
            [(self.product4, 1), (self.product2, 5)],
            payments=[(self.bank_pm1, 109.96)]
        ))
        self.env['pos.order'].sync_from_ui(orders2)
        self.pos_session.close_session_from_ui()

        pos_orders = self.env['pos.order'].search([])
        # set customer for the orders
        pos_orders.write({'partner_id': self.customer.id})

        # create consolidated invoice
        self.env['pos.make.invoice'].create({
            "consolidated_billing": True,
        }).with_context({
            "active_ids": pos_orders.ids,
        }).action_create_invoices()
        # check if have single invoice
        self.assertEqual(len(pos_orders), 4)
        self.assertTrue(all(order.state == 'done' for order in pos_orders))
        self.assertEqual(len(pos_orders.account_move), 1)
        self.assertNotEqual(self.pos_session.move_ids, pos_orders.account_move)
        self.assertEqual(pos_orders.account_move.partner_id, self.customer)
        self.assertEqual(pos_orders.account_move.amount_total, round(sum(pos_orders.mapped('amount_total')), 2))
        self.assertEqual(pos_orders.account_move.payment_state, 'in_payment')
        self.assertEqual(pos_orders.account_move.state, 'posted')
        self.assertEqual(pos_orders.account_move.amount_residual, 0)

    def test_pos_archived_combination(self):
        product = self.env['product.template'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        attribute_1, attribute_2, attribute_3 = self.env['product.attribute'].create([{
            'name': 'Attribute 1',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }, {
            'name': 'Attribute 2',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }, {
            'name': 'Attribute 3',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }])

        _, _, ptal = self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product.id,
            'attribute_id': attribute_1.id,
            'value_ids': [(6, 0, attribute_1.value_ids.ids)],
            'sequence': 3,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_2.id,
            'value_ids': [(6, 0, attribute_2.value_ids.ids)],
            'sequence': 2,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_3.id,
            'value_ids': [(6, 0, attribute_3.value_ids.ids)],
            'sequence': 1,
        }])

        product.write({
            'attribute_line_ids': [(2, ptal.id)],
        })

        self.open_new_session()
        response = self.pos_session.load_data([])
        product_data = next((item for item in response['product.template'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 0, "There should be no archived combinations for the product")

        first_variant = product.product_variant_ids[0]
        first_variant.write({'active': False})

        response = self.pos_session.load_data([])
        product_data = next((item for item in response['product.template'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 1, "There should be one archived combination for the product")
        self.assertEqual(len(product_data['_archived_combinations'][0]), 2, "Archived combination should have two values")
        self.assertTrue(all(value in product_data['_archived_combinations'][0] for value in first_variant.product_template_attribute_value_ids.ids), "Archived combination should match the first variant's attribute values")

    def test_refunded_order_id(self):
        """
        An order containing refunded lines from two different orders is no longer allowed,
        but some legacy records of this kind may still exist.
        This test ensures that the refunded_order_id is correctly computed in such cases.
        """
        current_session = self.open_new_session()
        orders = list(self._create_orders([
            {'pos_order_lines_ui_args': [(self.product1, 1)]},
            {'pos_order_lines_ui_args': [(self.product2, 1)]}
        ]).values())

        refund_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'lines': [
                (0, 0, {
                    'product_id': self.product1.id,
                    'price_unit': -10,
                    'qty': 1,
                    'tax_ids': [[6, False, []]],
                    'price_subtotal': -10,
                    'price_subtotal_incl': -10,
                    'refunded_orderline_id': orders[0].lines[0].id
                }),
                (0, 0, {
                    'product_id': self.product2.id,
                    'price_unit': -10,
                    'qty': 1,
                    'tax_ids': [[6, False, []]],
                    'price_subtotal': -10,
                    'price_subtotal_incl': -10,
                    'refunded_orderline_id': orders[1].lines[0].id
                })
            ],
            'amount_paid': -10,
            'amount_total': -10,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })

        self.assertEqual(refund_order.refunded_order_id, orders[0])

    def test_cannot_archive_journal_linked_to_pos_payment_method(self):
        """Test that archiving a journal linked to a POS payment method is blocked, and allowed when not linked."""

        test_journal = self.env['account.journal'].create({
            'name': 'Test POS Journal',
            'type': 'cash',
            'code': 'TPJ',
            'company_id': self.env.company.id,
        })
        test_payment_method = self.env['pos.payment.method'].create({
            'name': 'Test PM',
            'type': 'cash',
            'journal_id': test_journal.id,
            'receivable_account_id': self.cash_pm1.receivable_account_id.id,
        })

        with self.assertRaises(ValidationError):
            test_journal.action_archive()

        # Unlink the payment method and try again (should succeed)
        test_payment_method.journal_id = False
        test_journal.action_archive()
        self.assertFalse(test_journal.active, "Journal should be archived when not linked to a POS payment method.")

    def test_archive_delete_special_product(self):
        special_product = self.env.ref('point_of_sale.product_product_tip')
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.action_archive()
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.product_variant_ids[0].action_archive()
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.unlink()
        with self.assertRaisesRegex(UserError, "You cannot archive a product that is set as a special product in a Point of Sale configuration. Please change the configuration first."):
            special_product.product_variant_ids[0].unlink()

    def test_pos_invoice_not_to_review_pos_only_user(self):
        """POS invoices must not be 'marked as 'to review' even when
        the invoicing user has no accounting review permissions."""
        self.open_new_session()

        pos_only_user = self.env['res.users'].create({
            'name': 'POS Only User',
            'login': 'pos_only_user',
            'password': 'pos_only_user',
            'group_ids': [self.env.ref('point_of_sale.group_pos_manager').id],
        })

        orders = self._create_orders([{
            'pos_order_lines_ui_args': [(self.product1, 1)],
            'customer': self.customer,
            'is_invoiced': False,
        }])
        orders = sum(orders.values(), self.env['pos.order'])

        orders.with_user(pos_only_user)._generate_pos_order_invoice()

        self.assertEqual(orders.account_move.review_state, 'no_review')
