from unittest.mock import patch

from freezegun import freeze_time

import odoo

from odoo.addons.point_of_sale.models.pos_order import TRACKING_NUMBER_SEQUENCE_CODE
from odoo.addons.point_of_sale.models.pos_payment_method import PosPaymentMethod
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestBackend(TestPoSCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tracking_product = cls.create_product('Tracking Product', cls.categ_basic, 10, 15)

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

    def _open_tracking_session(self, config):
        config.open_ui()
        self.config = config
        self.pricelist = config.pricelist_id
        self.currency = config.currency_id
        self.pos_session = config.current_session_id
        self.pos_session.set_opening_control(0, "")
        self.assertEqual(self.pos_session.state, 'opened')

    def _create_tracking_orders(self, count, pos_order_ui_args=None, env=None):
        order_data = [
            self.create_ui_order_data([(self.tracking_product, 1)], pos_order_ui_args or {})
            for _ in range(count)
        ]
        return (env or self.env)['pos.order'].create(order_data)

    def _get_tracking_sequence(self, company):
        return self.env['ir.sequence'].sudo().search([
            ('code', '=', TRACKING_NUMBER_SEQUENCE_CODE),
            ('company_id', '=', company.id),
        ])

    @freeze_time('2030-01-01 10:00:00')
    def test_backend_tracking_number(self):
        """ Tracking numbers are shared by all the configs of a company. """
        self._open_tracking_session(self.basic_config)
        orders = self._create_tracking_orders(3)
        self.assertEqual(orders.mapped('tracking_number'), ['1', '2', '3'])

        self._open_tracking_session(self.other_currency_config)
        orders = self._create_tracking_orders(3)
        self.assertEqual(orders.mapped('tracking_number'), ['4', '5', '6'])

    @freeze_time('2030-01-01 10:00:00')
    def test_backend_tracking_number_kept_when_provided(self):
        """ A tracking number sent by the client (cashier screen) is kept and does not consume the sequence. """
        self._open_tracking_session(self.basic_config)
        order = self._create_tracking_orders(1, {'tracking_number': '0042'})
        self.assertEqual(order.tracking_number, '0042')
        order = self._create_tracking_orders(1)
        self.assertEqual(order.tracking_number, '1')

    def test_backend_tracking_number_daily_reset(self):
        """ Tracking numbers restart every day, based on the company timezone. """
        self.env.company.tz = 'Europe/Brussels'  # UTC+1 in January
        with freeze_time('2030-01-01 10:00:00'):
            self._open_tracking_session(self.basic_config)
            orders = self._create_tracking_orders(2)
            self.assertEqual(orders.mapped('tracking_number'), ['1', '2'])
        with freeze_time('2030-01-01 22:30:00'):  # 23:30 in Brussels: same day
            order = self._create_tracking_orders(1)
            self.assertEqual(order.tracking_number, '3')
        with freeze_time('2030-01-01 23:30:00'):  # 00:30 in Brussels: next day
            orders = self._create_tracking_orders(2)
            self.assertEqual(orders.mapped('tracking_number'), ['1', '2'])

    @freeze_time('2030-01-01 10:00:00')
    def test_backend_tracking_number_uses_order_company(self):
        """ The sequence of the order's company is used, not the one of the current company. """
        other_company = self.setup_other_company()['company']
        self._open_tracking_session(self.basic_config)
        orders = self._create_tracking_orders(2, env=self.env['pos.order'].with_company(other_company).env)
        self.assertEqual(orders.mapped('tracking_number'), ['1', '2'])
        self.assertEqual(len(self._get_tracking_sequence(self.env.company)), 1)
        self.assertFalse(self._get_tracking_sequence(other_company))

    @freeze_time('2030-01-10 10:00:00')
    def test_backend_tracking_number_date_range_gc(self):
        """ The autovacuum removes the old daily ranges of the tracking number sequence only. """
        self._open_tracking_session(self.basic_config)
        self._create_tracking_orders(1)
        sequence = self._get_tracking_sequence(self.env.company)
        DateRange = self.env['ir.sequence.date_range'].sudo()
        for day in ('2030-01-01', '2030-01-07', '2030-01-08'):
            DateRange.create({'sequence_id': sequence.id, 'date_from': day, 'date_to': day})
        other_sequence = self.env['ir.sequence'].sudo().create({
            'name': 'Unrelated sequence',
            'use_date_range': True,
        })
        other_range = DateRange.create({'sequence_id': other_sequence.id, 'date_from': '2030-01-01', 'date_to': '2030-01-01'})

        self.env['pos.order']._gc_tracking_number_date_ranges()

        self.assertEqual(
            sorted(str(d) for d in sequence.date_range_ids.mapped('date_from')),
            ['2030-01-08', '2030-01-10'],
        )
        self.assertTrue(other_range.exists())
