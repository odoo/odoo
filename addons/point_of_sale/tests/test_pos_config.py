# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

import odoo
from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSBasicConfig(TestPoSCommon):
    """ Test PoS with basic configuration

    The tests contain base scenarios in using pos.
    More specialized cases are tested in other tests.
    """
    _test_user_groups = None  # FIXME list needed groups

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
        self.pos_session.load_data()

    def test_load_data_picks_the_company_website_domain(self):
        if self.env['ir.module.module']._get('website').state != 'installed':
            self.skipTest("website module is required for this test")

        company_website = self.config.company_id.website_id

        if company_website:
            company_website.write({'domain': 'https://custom.test.domain.com'})
            self.open_new_session()
            response = self.pos_session.load_data({'only_records': True})

            self.assertEqual(response['pos.config'][0]['_base_url'], company_website.domain)

    def _get_loaded_product_ids(self, session):
        data = session.load_data()
        special_product = session.config_id._get_special_products().ids
        return [p['product_variant_ids'][0] for p in data['product.template']['records']
                if p['active'] and p['product_variant_ids'][0] not in special_product]

    def test_limited_products_loading(self):
        """
        This test makes sure that the limited products loading feature loads
        at most `point_of_sale.limited_product_count` product templates,
        regardless of which specific criteria decides which ones make the
        cut. That ordering is a separate concern which can be overridden by
        other modules.
        """
        # Restrict the loaded-product domain to our own POS category so any
        # other available_in_pos product (demo data, combos, setUp fixtures)
        # never competes for the limited slots.
        test_categ = self.env['pos.category'].create({'name': 'Limited Loading Test Category'})
        self.config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, test_categ.ids)],
        })
        products = self.env['product.product']
        for i in range(5):
            products |= self.create_product(f'Count Product {i}', self.categ_basic, 10)
        products.product_tmpl_id.write({'pos_categ_ids': [(6, 0, test_categ.ids)]})
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 3)
        self.env.flush_all()
        session = self.open_new_session(0)

        self.assertEqual(len(self._get_loaded_product_ids(session)), 3)

    def test_limited_products_loading_priority(self):
        """
        This test makes sure that our limited products loading feature
        prioritizes product templates in this order, with ties being broken
        by the next trait:
        1st. "Favorited" products (is_favorite)
        2nd. "Service" type products (type)
        3rd. Recently written to products (write_date)
        """
        if 'pos_stock' in self.env['ir.module.module']._installed():
            self.skipTest(
                "The module pos_stock is installed and defines a conflicting ordering.")
        # Restrict the loaded-product domain to our own POS category so any
        # other available_in_pos product (demo data, combos, setUp fixtures)
        # never competes for the limited spots.
        test_categ = self.env['pos.category'].create({'name': 'Priority Test Category'})
        self.config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, test_categ.ids)],
        })
        product0 = self.create_product('Priority Product 0', self.categ_basic, 10)
        product1 = self.create_product('Priority Product 1', self.categ_basic, 10)
        product2 = self.create_product('Priority Product 2', self.categ_basic, 10)
        product3 = self.create_product('Priority Product 3', self.categ_basic, 10)
        product4 = self.create_product('Priority Product 4', self.categ_basic, 10)
        (product0 | product1 | product2 | product3 | product4).product_tmpl_id.write({
            'pos_categ_ids': [(6, 0, test_categ.ids)],
        })
        product2.product_tmpl_id.write({"is_favorite": True, "type": "consu"})
        product3.product_tmpl_id.write({"is_favorite": False, "type": "service"})
        product4.product_tmpl_id.write({"is_favorite": False, "type": "consu"})

        # product0 and product1 are tied on (is_favorite, type); only
        # write_date should decide between them.
        now = fields.Datetime.now()
        self.patch(self.env.cr, 'now', lambda: now - relativedelta(minutes=1))
        product1.product_tmpl_id.write({"is_favorite": True, "type": "service"})
        self.env.flush_all()
        self.patch(self.env.cr, 'now', lambda: now)
        product0.product_tmpl_id.write({"is_favorite": True, "type": "service"})
        self.env.flush_all()

        session = self.open_new_session(0)

        def loaded_ids(limit):
            self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', limit)
            return self._get_loaded_product_ids(session)

        # write_date breaks the tie between product0 and product1.
        self.assertCountEqual(loaded_ids(1), [product0.id])
        # is_favorite outranks type: both favorited products beat any non-favorite.
        self.assertCountEqual(loaded_ids(3), [product0.id, product1.id, product2.id])
        # type breaks ties among non-favorited products too.
        self.assertCountEqual(loaded_ids(4), [product0.id, product1.id, product2.id, product3.id])

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
        self.assertEqual(pos_orders.account_move.payment_state, 'paid')
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
        self.assertEqual(pos_orders.account_move.payment_state, 'paid')
        self.assertEqual(pos_orders.account_move.state, 'posted')
        self.assertEqual(pos_orders.account_move.amount_residual, 0)

    def test_invoice_paid_with_cash_change_same_receivable_account(self):
        """ Test that when the PoS receivable account and the partner
        account_receivable are the same, an invoiced order paid in cash
        with change is correctly marked as paid.
        """
        self.config.default_partner_id.property_account_receivable_id = self.customer.property_account_receivable_id
        self.open_new_session()

        order_data = self.create_ui_order_data(
            [(self.product1, 1)],
            pos_order_ui_args={'amount_return': -5},
            payments=[(self.cash_pm1, 15)],
            customer=self.customer,
            is_invoiced=True,
        )
        res = self.env['pos.order'].sync_from_ui([order_data])
        order = self.env['pos.order'].browse(res['pos.order'][0]['id'])
        self.assertEqual(order.account_move.payment_state, 'paid')

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
        response = self.pos_session.load_data()
        product_data = next((item for item in response['product.template']['records'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 0, "There should be no archived combinations for the product")

        first_variant = product.product_variant_ids[0]
        first_variant.write({'active': False})

        response = self.pos_session.load_data()
        product_data = next((item for item in response['product.template']['records'] if item['id'] == product.id), None)

        self.assertEqual(len(product_data['_archived_combinations']), 1, "There should be one archived combination for the product")
        self.assertEqual(len(product_data['_archived_combinations'][0]), 2, "Archived combination should have two values")
        self.assertTrue(all(value in product_data['_archived_combinations'][0] for value in first_variant.product_template_attribute_value_ids.ids), "Archived combination should match the first variant's attribute values")

    def test_load_product_from_pos_archived_attribute_line(self):
        """ Loading the archived variant of a past order must not link the archived
        attribute line and variants to the template used for new sales. """
        size_attribute, color_attribute = self.env['product.attribute'].create([{
            'name': 'Size',
            'create_variant': 'dynamic',
            'value_ids': [(0, 0, {'name': 'S'}), (0, 0, {'name': 'M'})],
        }, {
            'name': 'Color',
            'create_variant': 'always',
            'value_ids': [(0, 0, {'name': 'Red'}), (0, 0, {'name': 'Blue'})],
        }])
        product = self.env['product.template'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': size_attribute.id,
                'value_ids': [(6, 0, size_attribute.value_ids.ids)],
            }), (0, 0, {
                'attribute_id': color_attribute.id,
                'value_ids': [(6, 0, color_attribute.value_ids.ids)],
            })],
        })
        size_line = product.attribute_line_ids.filtered(lambda l: l.attribute_id == size_attribute)
        color_line = product.attribute_line_ids - size_line
        sold_variant = product._create_product_variant(
            product.attribute_line_ids.product_template_value_ids.filtered(lambda v: v.name in ('S', 'Red'))
        )

        self.open_new_session()
        self._create_orders([{'pos_order_lines_ui_args': [(sold_variant, 1)]}])

        # The sold variant can't be deleted, so removing the line archives both
        product.write({'attribute_line_ids': [(2, size_line.id)]})
        self.assertFalse(size_line.active)
        self.assertFalse(sold_variant.active)

        # Same call as when the POS loads a past order containing the archived variant
        result = self.pos_session.load_data({
            'models': ['product.template', 'product.product', 'product.template.attribute.line', 'product.template.attribute.value'],
            'search_params': {
                'product.product': {'domain': [('id', 'in', sold_variant.ids)], 'context': {'active_test': False}},
                'product.template': {'domain': [('product_variant_ids', 'in', sold_variant.ids)], 'context': {'active_test': False}},
            },
            'only_records': True,
        })
        product_data = next(item for item in result['product.template'] if item['id'] == product.id)
        self.assertEqual(product_data['attribute_line_ids'], color_line.ids, "The archived attribute line should not be linked to the template")
        self.assertNotIn(sold_variant.id, product_data['product_variant_ids'], "The archived variant should not be linked to the template")
        # The archived variant is still loaded so that the past order can be displayed
        self.assertIn(sold_variant.id, [p['id'] for p in result['product.product']])


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
        self.config.iface_tipproduct = True
        special_product = self.env.ref('point_of_sale.product_product_tip')
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
            special_product.action_archive()
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
            special_product.product_variant_ids[0].action_archive()
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
            special_product.unlink()
        with self.assertRaisesRegex(UserError, "a special product in a Point of Sale configuration"):
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

    def test_delete_archive_product_pos_category_with_active_pos_session(self):
        self.env['pos.session'].search([('state', '!=', 'closed')]).state = "closed"
        category1 = self.env['pos.category'].create({'name': 'Category 1'})
        category2 = self.env['pos.category'].create({'name': 'Category 2'})

        product1 = self.create_product('Product 1', self.categ_basic, 0.0, 0.0)
        product2 = self.create_product('Product 2', self.categ_basic, 0.0, 0.0)

        product1.pos_categ_ids = [(6, 0, [category1.id])]
        product2.pos_categ_ids = [(6, 0, [category2.id])]

        # Open unrestricted session -> everything protected.
        self.basic_config.open_ui()
        self.basic_config.iface_available_categ_ids = []

        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            product2.action_archive()

        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            category2.unlink()

        # Open restricted session for category1 only.
        self.basic_config.iface_available_categ_ids = [(6, 0, [category1.id])]

        # category1/product1 still protected.
        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            product1.product_variant_id.action_archive()

        with self.assertRaisesRegex(UserError, "currently in use in a point of sale"):
            category1.action_archive()

        # category2/product2 no longer protected.
        product2.action_archive()
        product2.unlink()

        category2.action_archive()
        category2.unlink()

        # After session close, only config protection remains.
        self.basic_config.current_session_id.state = 'closed'

        with self.assertRaisesRegex(UserError, "currently in use in a point of sale"):
            category1.unlink()


    def test_set_journal_on_bank_payment_method_with_open_session(self):
        bank_pm = self.env['pos.payment.method'].create({
            'name': 'Bank without journal',
            'type': 'bank',
            'receivable_account_id': self.pos_receivable_bank.id,
            'config_ids': [Command.link(self.config.id)],
        })
        self.open_new_session()
        self.assertTrue(bank_pm.open_session_ids)

        # Other protected fields remain locked
        with self.assertRaisesRegex(UserError, "close and validate"):
            bank_pm.receivable_account_id = self.cash_pm1.receivable_account_id

        bank_pm.write({
            'journal_id': self.company_data['default_journal_bank'].id,
            'outstanding_account_id': self.outstanding_bank.id,
        })
        self.assertEqual(bank_pm.journal_id, self.company_data['default_journal_bank'])
        self.assertEqual(bank_pm.outstanding_account_id, self.outstanding_bank)

        with self.assertRaisesRegex(UserError, "close and validate"):
            bank_pm.journal_id = False



from unittest.mock import patch

import odoo

from odoo.addons.point_of_sale.models.pos_payment_method import PosPaymentMethod
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestBackend(TestPoSCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_onchange_payment_provider(self):
        pm = self.env['pos.payment.method'].create({'name': 'Test PM', 'type': 'bank'})
        with patch.object(PosPaymentMethod, '_get_terminal_provider_selection', return_value=[('terminal_1', 'Terminal 1'), ('terminal_2', 'Terminal 2')]), \
             patch.object(PosPaymentMethod, '_get_external_qr_provider_selection', return_value=[('qr_1', 'QR Code 1'), ('qr_2', 'QR Code 2')]), \
             patch.object(PosPaymentMethod, '_get_cash_machine_selection', return_value=[('cash_1', 'Cash Machine 1'), ('cash_2', 'Cash Machine 2')]):
            # False --> terminal_1 = terminal
            pm.payment_provider = 'terminal_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_1 --> terminal_2 = terminal
            pm.payment_provider = 'terminal_2'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_2 --> qr_1 = external_qr
            pm.payment_provider = 'qr_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_1 --> qr_2 = external_qr
            pm.payment_provider = 'qr_2'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_2 --> False = external_qr
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # False --> qr_1 = external_qr
            pm.payment_provider = 'qr_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_1 --> cash_1 = cash_machine
            pm.payment_provider = 'cash_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'cash_machine')

            # cash_1 --> terminal_1 = terminal
            pm.payment_provider = 'terminal_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_1 --> False = terminal
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # False --> cash_1 = cash_machine
            pm.payment_provider = 'cash_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'cash_machine')

    def test_onchange_payment_method_type(self):
        pm = self.env['pos.payment.method'].create({'name': 'Test PM', 'type': 'bank'})
        with patch.object(PosPaymentMethod, '_get_terminal_provider_selection', return_value=[('terminal_1', 'Terminal 1'), ('terminal_2', 'Terminal 2')]), \
             patch.object(PosPaymentMethod, '_get_external_qr_provider_selection', return_value=[('qr_1', 'QR Code 1'), ('qr_2', 'QR Code 2')]), \
             patch.object(PosPaymentMethod, '_get_cash_machine_selection', return_value=[('cash_1', 'Cash Machine 1'), ('cash_2', 'Cash Machine 2')]):
            # (False) none --> terminal = False
            pm.payment_method_type = 'terminal'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> external_qr = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'external_qr'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (qr_1) external_qr --> terminal = False
            pm.payment_provider = 'qr_1'
            pm.payment_method_type = 'terminal'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> cash_machine = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'cash_machine'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> none = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'none'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import ValidationError

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSetup(TestPoSCommon):
    """ This group of tests is for sanity check in setting up global records which will be used
    in each testing.

    If a test fails here, then it means there are inconsistencies in what we expect in the setup.
    """
    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super(TestPoSSetup, self).setUp()

        self.config = self.basic_config
        self.products = [
            self.create_product('Product 1', self.categ_basic, lst_price=10.0, standard_price=5),
            self.create_product('Product 2', self.categ_basic, lst_price=20.0, standard_price=10),
            self.create_product('Product 3', self.categ_basic, lst_price=30.0, standard_price=15),
        ]

    def test_basic_config_values(self):

        config = self.basic_config
        self.assertEqual(config.currency_id, self.company_currency)
        self.assertEqual(config.pricelist_id.currency_id, self.company_currency)

    def test_other_currency_config_values(self):
        config = self.other_currency_config
        self.assertEqual(config.currency_id, self.other_currency)
        self.assertEqual(config.pricelist_id.currency_id, self.other_currency)

    def test_product_price(self):
        def get_price(pricelist, product):
            return pricelist._get_product_price(product, 1)


        # check usd pricelist
        pricelist = self.basic_config.pricelist_id
        for product in self.products:
            self.assertAlmostEqual(get_price(pricelist, product), product.lst_price)

        # check eur pricelist
        # exchange rate to the other currency is set to 0.5, thus, lst_price
        # is expected to have half its original value.
        pricelist = self.other_currency_config.pricelist_id
        for product in self.products:
            self.assertAlmostEqual(get_price(pricelist, product), product.lst_price * 0.5)

    def test_taxes(self):
        tax7 = self.taxes['tax7']
        self.assertEqual(tax7.name, 'Tax 7%')
        self.assertAlmostEqual(tax7.amount, 7)
        self.assertEqual(tax7.invoice_repartition_line_ids.mapped('account_id').id, self.tax_received_account.id)
        tax10 = self.taxes['tax10']
        self.assertEqual(tax10.name, 'Tax 10%')
        self.assertAlmostEqual(tax10.amount, 10)
        self.assertEqual(tax10.price_include, True)
        self.assertEqual(tax10.invoice_repartition_line_ids.mapped('account_id').id, self.tax_received_account.id)
        tax_group_7_10 = self.taxes['tax_group_7_10']
        self.assertEqual(tax_group_7_10.name, 'Tax 7+10%')
        self.assertEqual(tax_group_7_10.amount_type, 'group')
        self.assertEqual(sorted(tax_group_7_10.children_tax_ids.ids), sorted((tax7 | tax10).ids))

    def test_archive_used_journal(self):
        journal = self.env['account.journal'].create({
            'name': 'BANKOS',
            'company_id': self.company.id,
            'code': 'BANKOS',
            'type': 'bank',
            'invoice_reference_type': 'invoice',
            'invoice_reference_model': 'odoo'
        })
        payment_method = self.env['pos.payment.method'].create({
            'name': 'Lets Pay for Tests', 'journal_id': journal.id, 'type': 'bank'})
        self.basic_config.write({'payment_method_ids': [payment_method.id]})
        journal.write({'pos_payment_method_ids': [payment_method.id]})
        session = self.env['pos.session'].create(
            {
                'name': 'lets sell some tests',
                'config_id': self.basic_config.id,
                'user_id': self.env.user.id,
                'state': 'opened'
            }
        )
        order = self.env['pos.order'].create(
            {
                'name': 'MIX',
                'amount_tax': 0,
                'amount_total': 0,
                'amount_paid': 0,
                'amount_return': 0,
                'company_id': self.company.id,
                'pricelist_id': self.currency_pricelist.id,
                'session_id': session.id
            }
        )
        self.env['pos.payment'].create(
            {
                'amount': 100,
                'payment_date': '2025-01-01',
                'payment_method_id': payment_method.id,
                'pos_order_id': order.id
            }
        )
        with self.assertRaises(ValidationError):
            journal.action_archive()

    def test_card_payment_method_initialization(self):
        """Test that the 'Card' payment method created by default has an outstanding account."""
        card_pm = self.env['pos.payment.method'].search([
            ('name', '=', 'Card'), ('company_id', '=', self.env.company.id),
        ], limit=1)
        self.assertTrue(card_pm)
        self.assertTrue(card_pm.outstanding_account_id)


import odoo

from odoo import fields, tools
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSOtherCurrencyConfig(TestPoSCommon):
    """ Test PoS with basic configuration
    """
    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super(TestPoSOtherCurrencyConfig, self).setUp()

        self.config = self.other_currency_config
        self.product1 = self.create_product('Product 1', self.categ_basic, 10.0, 5)
        self.product2 = self.create_product('Product 2', self.categ_basic, 20.0, 10)
        self.product3 = self.create_product('Product 3', self.categ_basic, 30.0, 15)
        self.product7 = self.create_product('Product 7', self.categ_basic, 7, 7, tax_ids=self.taxes['tax7'].ids)
        # change the price of product2 to 12.99 fixed. No need to convert.
        pricelist_item = self.env['product.pricelist.item'].create({
            'product_tmpl_id': self.product2.product_tmpl_id.id,
            'fixed_price': 12.99,
        })
        self.config.pricelist_id.write({'item_ids': [(6, 0, (self.config.pricelist_id.item_ids | pricelist_item).ids)]})

    def test_01_check_product_cost(self):
        # Product price should be half of the original price because currency rate is 0.5.
        # (see `self._create_other_currency_config` method)
        # Except for product2 where the price is specified in the pricelist.

        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product1, 1), 5.00)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product2, 1), 12.99)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product3, 1), 15.00)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product7, 1), 3.50)

    def test_bank_journal_balance(self):
        """Verify that debit and credit are balanced when adding a difference to the bank."""

        # Make a sale paid by bank
        self.other_currency_config.open_ui()
        session_id = self.other_currency_config.current_session_id
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': session_id.id,
            'partner_id': False,
            'lines': [(0, 0, {
                'name': 'OL/0001',
                'product_id': self.product1.id,
                'price_unit': 10.00,
                'discount': 0,
                'qty': 1,
                'tax_ids': False,
                'price_subtotal': 10.00,
                'price_subtotal_incl': 10.00,
            })],
            'pricelist_id': self.other_currency_config.pricelist_id.id,
            'amount_paid': 10.00,
            'amount_total': 10.00,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })

        # Make payment
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.bank_pm2.id
        })
        order_payment.with_context(**payment_context).check()

        # Close session with counted +10 for bank compared with expected
        session_id.close_session_from_ui()  # Real 20, expected 10, diff 10

        # Check debit/credit session's balance
        for move in session_id._get_related_account_moves():
            debit = credit = 0.0
            for line in move.line_ids:
                debit += line.debit
                credit += line.credit
            self.assertEqual(tools.float_compare(debit, credit, precision_rounding=self.other_currency_config.currency_id.rounding), 0)  # debit and credit should be equal

    def test_with_session_check_product_cost(self):
        def find_by(list_of_dicts, key, value):
            return next((d for d in list_of_dicts if d.get(key) == value), None)

        self.other_currency_config.open_ui()
        product = self.other_currency_config.current_session_id.load_data({'only_records': True})['product.product']

        self.assertAlmostEqual(find_by(product, 'id', self.product1.id)['lst_price'], 5.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product2.id)['lst_price'], 10.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product3.id)['lst_price'], 15.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product7.id)['lst_price'], 3.50)

    def test_pos_data_standard_price_converted(self):
        self.other_currency_config.open_ui()
        res = self.other_currency_config.current_session_id.load_data({'only_records': True})
        product1_data = next(filter(lambda product: product['display_name'] == "Product 1", res['product.product']))
        self.assertEqual(product1_data['standard_price'], 2.5)  # standard price should be converted

    def test_pos_data_shared_product_cost_currency(self):
        """ A product shared across companies (company_id = False) takes its sale-price
        currency from the main company but its cost currency from the active company.
        When the POS runs in a company whose currency differs from the main company, the
        cost (standard_price) must be converted from cost_currency_id, not currency_id,
        otherwise it gets wrongly multiplied by the exchange rate even though it is
        already expressed in the POS currency.
        """
        main_company = self.env['res.company']._get_main_company()
        self.assertNotEqual(main_company.currency_id, self.other_currency)

        other_company = self.env['res.company'].create({
            'name': 'Other Currency Company',
            'currency_id': self.other_currency.id,
        })
        self.env.user.company_ids |= other_company

        self.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'currency_id': main_company.currency_id.id,
            'rate': 2.0,
            'company_id': other_company.id,
        })

        shared_product = self.env['product.product'].create({
            'name': 'Shared Product',
            'available_in_pos': True,
            'is_storable': True,
            'taxes_id': [(5, 0, 0)],
            'lst_price': 100.0,
            'company_id': False,
        }).with_company(other_company)
        # standard_price is company-dependent: set it for the active company, where it
        # is therefore expressed in that company's currency (the "other" currency).
        shared_product.standard_price = 100.0

        self.assertEqual(shared_product.currency_id, main_company.currency_id)
        self.assertEqual(shared_product.cost_currency_id, self.other_currency)

        self.assertEqual(self.other_currency_config.currency_id, self.other_currency)
        [data] = shared_product._load_pos_data_read(shared_product, self.other_currency_config)

        self.assertAlmostEqual(data['standard_price'], 100.0)
        self.assertAlmostEqual(data['lst_price'], 50.0)

    def test_combo_prices_converted_to_pos_currency(self):
        # A combo's `base_price` and its items' `extra_price` are stored in the
        # company currency. When loaded in a PoS running another currency they
        # must be converted, just like standalone product prices (rate 0.5).
        combo = self.env['product.combo'].create({
            'name': 'Combo choice',
            'company_id': self.company.id,
            'combo_item_ids': [
                (0, 0, {'product_id': self.product1.product_variant_id.id, 'extra_price': 20.0}),
                (0, 0, {'product_id': self.product3.product_variant_id.id, 'extra_price': 0.0}),
            ],
        })
        # base_price is the min lst_price among the items, in company currency (product1 = 10.0).
        self.assertAlmostEqual(combo.base_price, 10.0)

        combo_read = self.env['product.combo']._load_pos_data_read(combo, self.config)[0]
        self.assertAlmostEqual(combo_read['base_price'], 5.0)

        combo_item_read = self.env['product.combo.item']._load_pos_data_read(combo.combo_item_ids, self.config)
        extra_prices = {rec['product_id']: rec['extra_price'] for rec in combo_item_read}
        self.assertAlmostEqual(extra_prices[self.product1.product_variant_id.id], 10.0)
        self.assertAlmostEqual(extra_prices[self.product3.product_variant_id.id], 0.0)


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo import Command
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestConfigureShops(TestPoSCommon):
    """ Shops are now configured from the general settings.
        This test suite ensures that changes made in the general settings
        should reflect to the pos.config record pointed by the
        pos_config_id field.
    """
    _test_user_groups = None  # FIXME list needed groups

    def _remove_on_payment_taxes(self):
        """ Call this when testing the res.config.settings with Form.
            The `on_payment` taxes need to be removed, otherwise, a warning will show in the log.
        """
        self.env['account.tax'].search([
            ('company_id', '=', self.env.company.id), ('tax_exigibility', '=', 'on_payment')
        ]).unlink()

    def test_properly_set_pos_config_x2many_fields(self):
        """Simulate what is done from the res.config.settings view when editing x2 many fields."""

        self._remove_on_payment_taxes()
        pos_config = self.env['pos.config'].create({
            'name': 'Shop 1',
            'module_pos_restaurant': False,
            'payment_method_ids': [
                Command.create({
                    'name': 'Bank 1',
                    'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
                    'type': 'bank',
                    'company_id': self.env.company.id,
                }),
                Command.create({
                    'name': 'Bank 2',
                    'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
                    'type': 'bank',
                    'company_id': self.env.company.id,
                }),
                Command.create({
                    'name': 'Cash',
                    'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
                    'type': 'cash',
                    'company_id': self.env.company.id,
                })
            ]
        })

        # Manually simulate the unlinking of the second record and then save the settings.
        # It will be a set of link commands except the one we want to delete.
        linked_ids = pos_config.payment_method_ids.ids
        second_id = linked_ids[1]
        commands = [Command.link(_id) for _id in linked_ids if _id != second_id]

        pos_config.with_context(from_settings_view=True).write({
            'payment_method_ids': commands
        })

        self.assertTrue(second_id not in pos_config.payment_method_ids.ids)
        self.assertTrue(len(pos_config.payment_method_ids) == 2)

    def test_write_default_and_available_presets_on_multiple_pos_configs(self):
        preset = self.env['pos.preset'].create({'name': 'Preset 1'})

        pos_config1 = self.env['pos.config'].create({'name': 'Shop 1', 'module_pos_restaurant': False})
        pos_config2 = self.env['pos.config'].create({'name': 'Shop 2', 'module_pos_restaurant': False})
        pos_config3 = self.env['pos.config'].create({'name': 'Shop 3', 'module_pos_restaurant': False})

        pos_configs = pos_config1 | pos_config2 | pos_config3

        pos_configs.write({
            'use_presets': True,
            'available_preset_ids': [(6, 0, [preset.id])],
            'default_preset_id': preset.id,
        })


# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import tagged, TransactionCase
from odoo.exceptions import UserError


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPointOfSale(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ignore pre-existing pricelists for the purpose of this test
        cls.env["product.pricelist"].search([]).write({"active": False})

        cls.currency = cls.env.ref("base.USD")
        cls.company1, cls.company2 = cls.env["res.company"].create([{
            "name": "company 1",
            "currency_id": cls.currency.id
        }, {
            "name": "company 2",
            "currency_id": cls.currency.id
        }])
        cls.company2_pricelist = cls.env["product.pricelist"].create({
            "name": "company 2 pricelist",
            "currency_id": cls.currency.id,
            "company_id": cls.company2.id,
            "sequence": 1,  # force this pricelist to be first
        })
        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Bank',
            'type': 'bank',
            'company_id': cls.company1.id,
            'code': 'BNK',
            'sequence': 11,
        })

        cls.env.user.company_id = cls.company1

    def test_no_default_pricelist(self):
        """ Verify that the default pricelist isn't automatically set in the config """
        company1_pricelist = self.env["product.pricelist"].create({
            "name": "company 1 pricelist",
            "currency_id": self.currency.id,
            "company_id": self.company1.id,
            "sequence": 2,
        })

        # make sure this doesn't pick a pricelist as default
        new_config = self.env["pos.config"].create({
            "name": "usd config", "available_pricelist_ids": [(6, 0, [company1_pricelist.id])]
        })

        self.assertEqual(new_config.pricelist_id, self.env['product.pricelist'],
                         "POS config incorrectly has pricelist %s" % new_config.pricelist_id.display_name)

    def test_product_combo_variants(self):
        # Create product and combo
        product = self.env['product.product'].create({
            'name': 'Test Product 1',
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
        })

        product_combo = self.env["product.combo"].create(
            {
                "name": "Product combo",
                "combo_item_ids": [
                    Command.create({
                        "product_id": product.id,
                        "extra_price": 0,
                    }),
                ],
            }
        )
        # Add attribute and values, simulating variant creation
        size_attribute = self.env['product.attribute'].create({'name': 'Size'})
        attribute_value_1 = self.env['product.attribute.value'].create({'name': 'Large', 'attribute_id': size_attribute.id})
        attribute_value_2 = self.env['product.attribute.value'].create({'name': 'Small', 'attribute_id': size_attribute.id})
        original_product_id = product.id
        product_template = product.product_tmpl_id
        product.product_tmpl_id.with_context(create_product_product=True).write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': size_attribute.id,
                'value_ids': [(6, 0, [attribute_value_1.id, attribute_value_2.id])],
            })],
        })
        # Check that original product should not be in combo anymore (replace by variants)
        self.assertTrue(original_product_id not in product_combo.combo_item_ids.mapped('product_id').ids, "Original product should not be in combo")

    def test_pos_bill_digits(self):
        coin = self.env["pos.bill"].create({
            "name": "0.005 not rounded",
            "value": 0.005
        })
        self.assertEqual(coin.value, 0.005)

    def test_session_filter_local_data(self):
        product1 = self.env['product.template'].create({
            'name': 'product1'
        })
        product2 = self.env['product.template'].create({
            'name': 'product2'
        })
        product3 = self.env['product.template'].create({
            'name': 'product3'
        })
        config = self.env["pos.config"].create({
            "name": "shop"
        })
        session = self.env['pos.session'].create({'name': 'Test Session', 'config_id': config.id})

        # Delete one product and archive another one
        products_to_display = [product1.id, product2.id, product3.id]
        product1.write({'active': False})
        product2.unlink()
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(products_to_display, [product3.id])

        # No change
        product4 = self.env['product.template'].create({
            'name': 'product4'
        })
        products_to_display = [product3.id, product4.id]
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(sorted(products_to_display), sorted([product3.id, product4.id]))

        # Delete all products
        products_to_display = [product3.id, product4.id]
        product3.unlink()
        product4.unlink()
        models_to_filter = {'product.template': products_to_display}
        products_to_display = list(set(products_to_display) - set(session.filter_local_data(models_to_filter)['product.template']))
        self.assertEqual(products_to_display, [])

        # Cannot archive config while session is active
        with self.assertRaises(UserError):
            config.write({'active': False})
