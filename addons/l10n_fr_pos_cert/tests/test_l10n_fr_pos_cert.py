from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.models import Model
from odoo.tests import tagged
from odoo.exceptions import UserError
from odoo.tools import format_date
from odoo import fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPosCertInalterableHash(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product1 = self.create_product('Product 1', self.categ_basic, 150, standard_price=50)
        self.company_fr = self.env['res.company'].create({
            'name': 'Company FR',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
        })
        self.open_new_session()

    def _create_pos_order(self, name, amount_total):
        order = self.env['pos.order'].create({
            'company_id': self.company_fr.id,
            'session_id': self.pos_session.id,
            'lines': [(0, 0, {
                'name': name,
                'product_id': self.product1.id,
                'price_unit': amount_total,
                'discount': 5.0,
                'notice': 'test',
                'qty': 1.0,
                'price_subtotal': amount_total,
                'price_subtotal_incl': amount_total,
                'total_cost': 50,
            })],
            'amount_total': amount_total,
            'amount_tax': 0.0,
            'amount_paid': amount_total,
            'amount_return': 0.0,
        })
        order.action_pos_order_paid()
        return order

    def test_l10n_fr_pos_order_get_blockchain_record_dict_to_hash(self):
        """
        Knowing that:
        pos.order()._get_blockchain_inalterable_hash_fields() = [
            'date_order', 'user_id', 'lines', 'payment_ids', 'pricelist_id', 'partner_id',
            session_id', 'pos_reference', 'sale_journal', 'fiscal_position_id'
        ]
        pos.order.line()._get_sub_blockchain_inalterable_hash_fields() = [
            'notice', 'product_id', 'qty', 'price_unit', 'discount',
            'tax_ids', 'tax_ids_after_fiscal_position'
        ]
        //!\\ This test should probably not be modified as it makes sure that the
        computation of the hash is not altered between versions which would break
        the inalterability hash report.
        """
        order = self._create_pos_order("OL/0001", 150)
        dict_to_hash = order._get_blockchain_record_dict_to_hash()
        line = order.lines[0]
        self.assertEqual(dict_to_hash, {
            'date_order': str(order.date_order),
            'user_id': str(order.user_id.id),
            'lines': f"[{line.id}]",
            'payment_ids': '[]',
            'pricelist_id': str(order.pricelist_id.id),
            'partner_id': 'False',
            'session_id': str(order.session_id.id),
            'pos_reference': 'False',
            'sale_journal': str(order.sale_journal.id),
            'fiscal_position_id': 'False',
            f'line_{line.id}_notice': 'test',
            f'line_{line.id}_product_id': str(self.product1.id),
            f'line_{line.id}_qty': '1.0',
            f'line_{line.id}_price_unit': '150.0',
            f'line_{line.id}_discount': '5.0',
            f'line_{line.id}_tax_ids': '[]',
            f'line_{line.id}_tax_ids_after_fiscal_position': '[]',
        })

    def test_l10n_fr_pos_order_inalterable_hash(self):
        """Test that we cannot alter a field used for the computation of the inalterable hash"""
        order = self._create_pos_order("OL/0001", 150)

        expected_error_msg = "You cannot edit the following fields due to restrict mode being activated.*"

        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Responsible"):
            order.user_id = 666
        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Sales Journal"):
            order.sale_journal = 666
        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Quantity"):
            order.lines[0].qty = 666
        with self.assertRaisesRegex(UserError, f"{expected_error_msg} Notice"):
            order.lines[0].notice = 'fake notice'

        # The following fields are not part of the hash so they can be modified
        order.note = 'new note'
        order.lines[0].customer_note = "some customer note"

    def test_l10n_fr_pos_cert_hash_integrity_report(self):
        """Test the hash integrity report"""
        orders = self.env['pos.order']

        # No record yet
        pos_orders_check = self.env['report.l10n_fr_pos_cert.report_l10n_fr_pos_blockchain_integrity'].with_company(self.company_fr)._check_blockchain_integrity()['results'][0]
        self.assertEqual(pos_orders_check['status'], 'no_record')
        self.assertEqual(pos_orders_check['msg'], "There isn't any record flagged for data inalterability.")

        # Everything should be correctly hashed and verified
        orders |= (
            self._create_pos_order("order1", 100)
            | self._create_pos_order("order2", 200)
            | self._create_pos_order("order3", 300)
            | self._create_pos_order("order4", 400)
            | self._create_pos_order("order5", 500)
        )
        for order in orders:
            order.action_pos_order_paid()
        pos_orders_check = self.env['report.l10n_fr_pos_cert.report_l10n_fr_pos_blockchain_integrity'].with_company(self.company_fr)._check_blockchain_integrity()['results'][0]
        self.assertEqual(pos_orders_check['status'], 'verified')
        self.assertRegex(pos_orders_check['msg'], 'Entries are hashed from.*')
        self.assertEqual(pos_orders_check['first_date'], format_date(self.env, fields.Date.to_string(orders[0].date_order)))
        self.assertEqual(pos_orders_check['last_date'], format_date(self.env, fields.Date.to_string(orders[-1].date_order)))

        # Let's change one of the fields used by the hash. It should be detected by the integrity report.
        # We need to bypass the write method of pos.order to do so.
        date_order = orders[2].date_order
        Model.write(orders[2], {'date_order': fields.Date.from_string("2020-01-01")})
        pos_orders_check = self.env['report.l10n_fr_pos_cert.report_l10n_fr_pos_blockchain_integrity'].with_company(self.company_fr)._check_blockchain_integrity()['results'][0]
        self.assertEqual(pos_orders_check['status'], 'corrupted')
        self.assertEqual(pos_orders_check['msg'], f'Corrupted data on record {orders[2].name} with id {orders[2].id}.')

        # Let's try with the blockchain_inalterable_hash field itself
        Model.write(orders[2], {'date_order': date_order})
        Model.write(orders[-1], {'blockchain_inalterable_hash': 'fake_hash'})
        pos_orders_check = self.env['report.l10n_fr_pos_cert.report_l10n_fr_pos_blockchain_integrity'].with_company(self.company_fr)._check_blockchain_integrity()['results'][0]
        self.assertEqual(pos_orders_check['status'], 'corrupted')
        self.assertEqual(pos_orders_check['msg'], f'Corrupted data on record {orders[-1].name} with id {orders[-1].id}.')
