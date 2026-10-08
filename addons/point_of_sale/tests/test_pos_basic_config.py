# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from unittest.mock import patch

import odoo
from odoo import fields, Command
from odoo.exceptions import UserError, ValidationError

from odoo.addons.point_of_sale.models.pos_payment_method import PosPaymentMethod
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSBasicConfig(CommonPosTest):
    """ Test PoS with basic configuration

    The tests contain base scenarios in using pos.
    More specialized cases are tested in other tests.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.pos_config_usd
        cls.product0 = cls.create_product('Product 0', cls.categ_basic, 0.0, 0.0)
        cls.product1 = cls.create_product('Product 1', cls.categ_basic, 10.0, 5)
        cls.product2 = cls.create_product('Product 2', cls.categ_basic, 20.0, 10)
        cls.product4 = cls.create_product('Product_4', cls.categ_basic, 9.96, 4.98)

    def test_pos_session_name_sequencing(self):
        """ This test check if the session name is correctly set according to the sequence """

        sequence = self.env['ir.sequence'].search([('code', '=', 'pos.session')])
        sequence.prefix = '/'
        sequence.write({'number_next_actual': 1000})
        name = self.config.name

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, name + '/01000')

        self.close_pos_session()

        sequence.prefix = 'TEST/'

        self.open_new_session(0)
        self.assertEqual(self.pos_session.name, 'TEST/01001')

    def test_load_data_should_not_fail(self):
        """load_data shouldn't fail

        (Include test conditions here if possible)

        - When there are partners that belong to different company
        """
        company_data_2 = self.setup_other_company()
        # create a partner that belongs to different company
        company2 = company_data_2['company']
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
        pm_1 = self.cash_pm
        pm_2 = self.bank_pm
        pm_3, pm_4 = (pm_1 + pm_2).copy()

        self.assertTrue(pm_3)
        self.assertFalse(pm_3.journal_id)
        self.assertTrue(pm_4)
        self.assertEqual(pm_4.journal_id.type, "bank")

    def test_single_config_global_invoice(self):
        """For a single POS config, create multiple orders and consolidate them into a single invoice"""
        self.open_new_session()
        orders = self.create_orders([
            {'lines': [[self.product1, 2], [self.product4, 3]], 'payments': [[self.bank_pm, 49.88]]},
            {'lines': [[self.product4, 1], [self.product2, 5]], 'payments': [[self.bank_pm, 109.96]]},
        ])
        self.close_pos_session()
        pos_orders = sum(orders.values(), self.env['pos.order'])
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
        self.assertEqual(pos_orders.account_move.payment_state, pos_orders.account_move._get_invoice_in_payment_state())
        self.assertEqual(pos_orders.account_move.state, 'posted')
        self.assertEqual(pos_orders.account_move.amount_residual, 0)

    def test_multi_config_global_invoice(self):
        self.open_new_session()
        orders = self.create_orders([
            {'lines': [[self.product1, 3], [self.product2, 10]], 'payments': [[self.bank_pm, 230]]},
            {'lines': [[self.product1, 5], [self.product0, 10]], 'payments': [[self.bank_pm, 50]]},
        ])
        self.close_pos_session()

        # Open a second session and create orders.
        self.open_new_session()
        orders2 = self.create_orders([
            {'lines': [[self.product1, 2], [self.product4, 3]], 'payments': [[self.bank_pm, 49.88]]},
            {'lines': [[self.product4, 1], [self.product2, 5]], 'payments': [[self.bank_pm, 109.96]]},
        ])
        self.close_pos_session()
        pos_orders = sum((*orders.values(), *orders2.values()), self.env['pos.order'])
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
        self.assertEqual(pos_orders.account_move.payment_state, pos_orders.account_move._get_invoice_in_payment_state())
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

    def test_refunded_order_id(self):
        """
        An order containing refunded lines from two different orders is no longer allowed,
        but some legacy records of this kind may still exist.
        This test ensures that the refunded_order_id is correctly computed in such cases.
        """
        self.open_new_session()
        orders = list(self.create_orders([
            {'lines': [[self.product1]], 'payments': [[self.bank_pm, 10]]},
            {'lines': [[self.product2]], 'payments': [[self.bank_pm, 20]]},
        ]).values())

        # Create the legacy record through the ORM: sync_from_ui rejects refunds
        # containing lines from multiple original orders.
        refund_data = self._create_ui_order_data(
            [
                [self.product1, 1, 0, {'price_unit': -10, 'refunded_orderline_id': orders[0].lines.id}],
                [self.product2, 1, 0, {'price_unit': -10, 'refunded_orderline_id': orders[1].lines.id}],
            ],
            payments=[],
            state='draft',
        )
        refund_order = self.env['pos.order'].create(refund_data)

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
            'receivable_account_id': self.cash_pm.receivable_account_id.id,
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

        order = self.create_pos_order(
            [[self.product1]],
            payments=[[self.bank_pm, 10]],
            customer=self.customer,
        )

        order.with_user(pos_only_user)._generate_pos_order_invoice()

        self.assertEqual(order.account_move.review_state, 'no_review')

    def test_delete_archive_product_pos_category_with_active_pos_session(self):
        self.env['pos.session'].search([('state', '!=', 'closed')]).state = "closed"
        category1 = self.env['pos.category'].create({'name': 'Category 1'})
        category2 = self.env['pos.category'].create({'name': 'Category 2'})

        product1 = self.create_product('Product 1', self.categ_basic, 0.0, 0.0)
        product2 = self.create_product('Product 2', self.categ_basic, 0.0, 0.0)

        product1.pos_categ_ids = [(6, 0, [category1.id])]
        product2.pos_categ_ids = [(6, 0, [category2.id])]

        # Open unrestricted session -> everything protected.
        self.pos_config_usd.open_ui()
        self.pos_config_usd.iface_available_categ_ids = []

        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            product2.action_archive()

        with self.assertRaisesRegex(UserError, "active Point of Sale session"):
            category2.unlink()

        # Open restricted session for category1 only.
        self.pos_config_usd.iface_available_categ_ids = [(6, 0, [category1.id])]

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
        self.pos_config_usd.current_session_id.state = 'closed'

        with self.assertRaisesRegex(UserError, "currently in use in a point of sale"):
            category1.unlink()

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
        commands = [Command.link(id) for id in linked_ids if id != second_id]

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

    def test_no_default_pricelist(self):
        """ Verify that the default pricelist isn't automatically set in the config """
        new_config = self.env['pos.config'].create({
            'name': 'usd config',
            'available_pricelist_ids': [Command.set(self.pricelist_eur.ids)]
        })
        self.assertEqual(
            new_config.pricelist_id,
            self.env['product.pricelist'],
            'POS config incorrectly has pricelist %s' % new_config.pricelist_id.display_name
        )

    def test_pos_bill_digits(self):
        coin = self.env.ref('point_of_sale.0_05')
        coin.value = 0.005
        self.assertEqual(coin.value, 0.005)

    def test_basic_config_values(self):
        config = self.pos_config_usd
        self.assertEqual(config.currency_id, self.company_currency)
        self.assertFalse(config.use_pricelist)
        self.assertFalse(config.pricelist_id)

    def test_other_currency_config_values(self):
        config = self.pos_config_eur
        self.assertEqual(config.currency_id, self.other_currency)
        self.assertEqual(config.pricelist_id.currency_id, self.other_currency)

    def test_product_price(self):
        def get_price(pricelist, product):
            return pricelist._get_product_price(product, 1)

        products = [
            self.create_product('Product 1', self.categ_basic, lst_price=10.0, standard_price=5),
            self.create_product('Product 2', self.categ_basic, lst_price=20.0, standard_price=10),
            self.create_product('Product 3', self.categ_basic, lst_price=30.0, standard_price=15),
        ]
        # check usd pricelist
        pricelist = self.pos_config_usd.pricelist_id
        for product in products:
            self.assertAlmostEqual(get_price(pricelist, product), product.lst_price)

        # check eur pricelist
        # exchange rate to the other currency is set to 0.5, thus, lst_price
        # is expected to have half its original value.
        pricelist = self.pos_config_eur.pricelist_id
        for product in products:
            self.assertAlmostEqual(get_price(pricelist, product), product.lst_price * 0.5)

    def test_taxes(self):
        tax7 = self.taxes['tax7']
        self.assertAlmostEqual(tax7.amount, 7)
        self.assertFalse(tax7.price_include)
        tax10 = self.taxes['tax10']
        self.assertAlmostEqual(tax10.amount, 10)
        self.assertFalse(tax10.price_include)
        self.assertTrue(self.taxes['tax10_incl'].price_include)
        self.assertEqual(self.taxes['tax10_incl'].amount, 10)
        tax_group_7_10 = self.taxes['tax_group_7_10']
        self.assertEqual(tax_group_7_10.amount_type, 'group')
        self.assertEqual(sorted(tax_group_7_10.children_tax_ids.ids), sorted((tax7 | tax10).ids))

    def test_archive_used_journal(self):
        self.create_pos_order([[self.ten_dollars_no_tax.product_variant_id]], payments=[[self.bank_pm, 10]])
        with self.assertRaises(ValidationError):
            self.bank_pm.journal_id.action_archive()

    def test_card_payment_method_initialization(self):
        """Test that the 'Card' payment method created by default has an outstanding account."""
        (self.bank_pm | self.bank_pm2).active = False
        _, payment_method_ids = self.pos_config_usd._create_journal_and_payment_methods()
        card_pm = self.env['pos.payment.method'].browse(payment_method_ids).filtered(lambda pm: pm.name == 'Card')
        self.assertTrue(card_pm)
        self.assertTrue(card_pm.outstanding_account_id)
