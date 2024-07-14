from .common import TestMxEdiPosCommon

from odoo.addons.l10n_mx_edi.tests.common import EXTERNAL_MODE
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *(['-standard', 'external'] if EXTERNAL_MODE else []))
class TestCFDIPosOrder(TestMxEdiPosCommon):

    def test_global_invoice_negative_lines_zero_total(self):
        """ Test a pos order completely refunded by the negative lines. """
        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session():
                order = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 12.0),
                        (self.product, -12.0),
                    ],
                    'payments': [(self.bank_pm1, 0.0)],
                })

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(order.l10n_mx_edi_action_create_global_invoice()['context']) \
                    .create({})\
                    .action_create_global_invoice()
            self.assertRecordValues(order, [{'l10n_mx_edi_cfdi_state': 'global_sent'}])
            self.assertRecordValues(order.l10n_mx_edi_document_ids, [{
                'pos_order_ids': order.ids,
                'state': 'ginvoice_sent',
                'attachment_id': False,
                'cancel_button_needed': False,
            }])

    def test_global_invoice_zero_line(self):
        """ Test a pos order with a line of zero. """
        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session():
                order = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 10.0),
                        (self.product, 0.0),
                    ],
                    'payments': [(self.bank_pm1, 11600.0)],
                })

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(order.l10n_mx_edi_action_create_global_invoice()['context']) \
                    .create({})\
                    .action_create_global_invoice()
            self._assert_global_invoice_cfdi_from_orders(order, 'test_global_invoice_zero_line')
            self.assertRecordValues(order.l10n_mx_edi_document_ids, [{
                'pos_order_ids': order.ids,
                'state': 'ginvoice_sent',
            }])

    def test_global_invoice_negative_lines_orphan_negative_line(self):
        """ Test a global invoice containing a pos order having a negative line that failed to be distributed. """
        product1 = self.product
        product2 = self._create_product(taxes_id=[])

        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session():
                order = self._create_order({
                    'pos_order_lines_ui_args': [
                        (product1, 12.0),
                        (product2, -2.0),
                    ],
                    'payments': [(self.bank_pm1, 11920.0)],
                })

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(order.l10n_mx_edi_action_create_global_invoice()['context']) \
                    .create({})\
                    .action_create_global_invoice()
            self.assertRecordValues(order.l10n_mx_edi_document_ids, [{
                'pos_order_ids': order.ids,
                'state': 'ginvoice_sent_failed',
            }])

    def test_global_invoice_including_complex_partial_refund_chain(self):
        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session():
                order1 = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 10.0),  # -2 from order1, -2 from refund1
                        (self.product, -2.0),
                    ],
                    'payments': [(self.bank_pm1, 9280.0)],
                })
                order2 = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 10.0),  # -3 from order2, -4 from refund1, -1 from refund2
                        (self.product, -3.0),
                    ],
                    'payments': [(self.bank_pm1, 8120.0)],
                })
                refund1 = self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product,
                            'quantity': -2.0,
                            'refunded_orderline_id': order1.lines[0].id,
                        },
                        {
                            'product': self.product,
                            'quantity': -4.0,
                            'refunded_orderline_id': order2.lines[0].id,
                        },
                    ],
                    'payments': [(self.bank_pm1, -6960.0)],
                })
                refund2 = self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product,
                            'quantity': -1.0,
                            'refunded_orderline_id': order2.lines[0].id,
                        },
                    ],
                    'payments': [(self.bank_pm1, -1160.0)],
                })

            orders = order1 + order2 + refund1 + refund2
            with self.with_mocked_pac_sign_success():
                # Calling the global invoice on the order will include the refund automatically.
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(order1.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()
            self._assert_global_invoice_cfdi_from_orders(orders, 'test_global_invoice_including_complex_partial_refund_chain_1')

            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [{
                'pos_order_ids': orders.ids,
                'state': 'ginvoice_sent',
            }])

            # New refund after the global invoice.
            with self.with_pos_session(), self.with_mocked_pac_sign_success():
                refund3 = self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product,
                            'quantity': -1.0,
                            'refunded_orderline_id': order2.lines[0].id,
                        },
                    ],
                    'payments': [(self.bank_pm1, -1160.0)],
                })
            self._assert_order_cfdi(refund3, 'test_global_invoice_including_complex_partial_refund_chain_2')

            # Ask for an invoice.
            order2.partner_id = self.customer
            with self.with_pos_session(), self.with_mocked_pac_sign_success():
                order2.action_pos_order_invoice()
            self._assert_order_cfdi(order2, 'test_global_invoice_including_complex_partial_refund_chain_3')

            # You can't make a global invoice since the order is invoiced.
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(order2.l10n_mx_edi_action_create_global_invoice()['context']) \
                    .create({})

            # Sign it.
            invoice = order2.account_move
            self.env['account.move.send'] \
                .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                .create({}) \
                .action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

            # Nothing changed on the order.
            self.assertRecordValues(order2, [{'l10n_mx_edi_cfdi_state': 'global_sent'}])
            self.assertRecordValues(order2.l10n_mx_edi_document_ids.sorted(), [
                {
                    'pos_order_ids': order2.ids,
                    'state': 'invoice_sent',
                },
                {
                    'pos_order_ids': orders.ids,
                    'state': 'ginvoice_sent',
                },
            ])

            # Ask for a credit note.
            refund2.partner_id = self.customer
            with self.with_pos_session(), self.with_mocked_pac_sign_success():
                refund2.action_pos_order_invoice()
            self._assert_order_cfdi(refund2, 'test_global_invoice_including_complex_partial_refund_chain_4')

    def test_global_invoice_including_full_refund(self):
        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session():
                order = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 10.0),
                    ],
                    'payments': [(self.bank_pm1, 11600.0)],
                })
                refund = self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product,
                            'quantity': -10.0,
                            'refunded_orderline_id': order.lines[0].id,
                        },
                    ],
                    'payments': [(self.bank_pm1, -11600.0)],
                })

            orders = order + refund
            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(order.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()

            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [{
                'pos_order_ids': orders.ids,
                'state': 'ginvoice_sent',
                'attachment_id': False,
            }])

    def test_global_invoice_refund_after(self):
        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session():
                order = self._create_order({
                    'pos_order_lines_ui_args': [
                        (self.product, 10.0),
                    ],
                    'payments': [(self.bank_pm1, 11600.0)],
                })

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create']\
                    .with_context(order.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})\
                    .action_create_global_invoice()

            self.assertRecordValues(order.l10n_mx_edi_document_ids, [{
                'pos_order_ids': order.ids,
                'state': 'ginvoice_sent',
            }])

            with self.with_pos_session(), self.with_mocked_pac_sign_success():
                refund = self._create_order({
                    'pos_order_lines_ui_args': [
                        {
                            'product': self.product,
                            'quantity': -3.0,
                            'refunded_orderline_id': order.lines[0].id,
                        },
                    ],
                    'payments': [(self.bank_pm1, -3480.0)],
                })
            self._assert_order_cfdi(refund, 'test_global_invoice_refund_after')

            self.assertRecordValues(refund.l10n_mx_edi_document_ids, [{
                'pos_order_ids': refund.ids,
                'state': 'invoice_sent',
            }])

    def test_global_invoice_documents(self):
        with self.mx_external_setup(self.frozen_today), self.with_pos_session() as _session:
            order1 = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 1)],
                'payments': [(self.bank_pm1, 1160.0)],
            })
            order2 = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 1)],
                'payments': [(self.bank_pm1, 1160.0)],
            })
            orders = order1 + order2

            with self.with_mocked_pac_sign_error():
                orders._l10n_mx_edi_cfdi_global_invoice_try_send()
            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [
                {
                    'pos_order_ids': orders.ids,
                    'state': 'ginvoice_sent_failed',
                    'sat_state': False,
                    'cancel_button_needed': False,
                    'retry_button_needed': True,
                },
            ])

            # Successfully create the global invoice.
            with self.with_mocked_pac_sign_success():
                orders._l10n_mx_edi_cfdi_global_invoice_try_send()
            sent_doc_values = {
                'pos_order_ids': orders.ids,
                'message': False,
                'state': 'ginvoice_sent',
                'sat_state': 'not_defined',
                'cancel_button_needed': True,
                'retry_button_needed': False,
            }
            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [sent_doc_values])
            self.assertTrue(orders.l10n_mx_edi_document_ids.attachment_id)
            self.assertRecordValues(orders, [{
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_state': 'global_sent',
            }] * 2)

            with self.with_mocked_sat_call(lambda _x: 'valid'):
                self.env['l10n_mx_edi.document']._fetch_and_update_sat_status(
                    extra_domain=[('id', '=', orders.l10n_mx_edi_document_ids.id)]
                )
            sent_doc_values['sat_state'] = 'valid'
            self.assertRecordValues(orders.l10n_mx_edi_document_ids, [sent_doc_values])

    def test_invoiced_order_then_refund(self):
        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session() as _session, self.with_mocked_pac_sign_success():
                # Invoice an order, then sign it.
                order = self._create_order({
                    'pos_order_lines_ui_args': [(self.product, 10)],
                    'payments': [(self.bank_pm1, 11600.0)],
                    'customer': self.partner_mx,
                })
                order.l10n_mx_edi_usage = "I01"
                invoice = self.env['account.move'].browse(order.action_pos_order_invoice()['res_id'])

            self._assert_invoice_cfdi(invoice, 'test_invoiced_order_then_refund_1')

            # You are no longer able to create a global invoice for it.
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(order.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(invoice.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})

            with self.with_pos_session() as _session, self.with_mocked_pac_sign_success():
                # Invoice the refund order, then sign it.
                refund_order = self._create_order({
                    'pos_order_lines_ui_args': [{
                        'product': self.product,
                        'quantity': -10,
                        'refunded_orderline_id': order.lines.id,
                    }],
                    'payments': [(self.bank_pm1, -11600.0)],
                    'customer': self.partner_mx,
                })
                refund_order.l10n_mx_edi_usage = "I01"
                refund = self.env['account.move'].browse(refund_order.action_pos_order_invoice()['res_id'])

            # You can't make a global invoice for it.
            with self.assertRaises(UserError):
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(refund.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({})

            # Create the CFDI and sign it.
            with self.with_mocked_pac_sign_success():
                self.env['account.move.send'] \
                    .with_context(active_model=refund._name, active_ids=refund.ids) \
                    .create({})\
                    .action_send_and_print()
            self._assert_invoice_cfdi(refund, 'test_invoiced_order_then_refund_2')
            self.assertRecordValues(refund, [{
                'l10n_mx_edi_cfdi_origin': f'03|{invoice.l10n_mx_edi_cfdi_uuid}',
            }])

    def test_global_invoiced_order_then_invoiced_then_refund_then_cancel_it(self):
        with self.mx_external_setup(self.frozen_today):
            with self.with_pos_session() as _session:
                # Create an order, then make a global invoice and sign it.
                order = self._create_order({
                    'pos_order_lines_ui_args': [(self.product, 10)],
                    'payments': [(self.bank_pm1, 11600.0)],
                    'customer': self.partner_mx,
                    'uid': '0001',
                })
            self.assertFalse(order.l10n_mx_edi_cfdi_to_public)  # a MX partner is set on the order
            order.l10n_mx_edi_cfdi_to_public = True  # needed to create a global invoice for this order

            with self.with_mocked_pac_sign_success():
                self.env['l10n_mx_edi.global_invoice.create'] \
                    .with_context(order.l10n_mx_edi_action_create_global_invoice()['context'])\
                    .create({}) \
                    .action_create_global_invoice()

            ginvoice_doc_values = {
                'pos_order_ids': order.ids,
                'state': 'ginvoice_sent',
                'sat_state': 'not_defined',
                'attachment_uuid': order.l10n_mx_edi_cfdi_uuid,
                'attachment_origin': False,
                'cancellation_reason': False,
                'retry_button_needed': False,
                'cancel_button_needed': True,
            }
            self.assertRecordValues(order.l10n_mx_edi_document_ids, [ginvoice_doc_values])
            self.assertRecordValues(order, [{
                'l10n_mx_edi_cfdi_state': 'global_sent',
                'l10n_mx_edi_cfdi_uuid': ginvoice_doc_values['attachment_uuid'],
            }])

            with self.with_pos_session() as _session:
                # Create an invoice triggering the creating of the global refund (failed to be signed).
                with self.with_mocked_pac_sign_error():
                    order.action_pos_order_invoice()

                # Sign it.
                invoice = order.account_move
                with self.with_mocked_pac_sign_success():
                    self.env['account.move.send'] \
                        .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                        .create({}) \
                        .action_send_and_print()
            self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

            invoice_doc_values = {
                'pos_order_ids': order.ids,
                'state': 'invoice_sent_failed',
                'sat_state': False,
                'attachment_uuid': False,
                'attachment_origin': f'01|{order.l10n_mx_edi_cfdi_uuid}',
                'cancellation_reason': False,
                'retry_button_needed': True,
                'cancel_button_needed': False,
            }
            self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
                invoice_doc_values,
                ginvoice_doc_values,
            ])

            # Retry the global refund.
            with self.with_mocked_pac_sign_success():
                order.l10n_mx_edi_document_ids.sorted()[0].action_retry()
            invoice_doc_values.update({
                'state': 'invoice_sent',
                'sat_state': 'not_defined',
                'attachment_uuid': order.l10n_mx_edi_document_ids.sorted()[0].attachment_uuid,
                'attachment_origin': f"01|{ginvoice_doc_values['attachment_uuid']}",
                'cancellation_reason': False,
                'retry_button_needed': False,
                'cancel_button_needed': True,
            })
            self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
                invoice_doc_values,
                ginvoice_doc_values,
            ])
            self.assertRecordValues(order, [{
                'l10n_mx_edi_cfdi_state': 'global_sent',
                'l10n_mx_edi_cfdi_uuid': ginvoice_doc_values['attachment_uuid'],
            }])
            self._assert_order_cfdi(order, 'test_global_invoiced_order_then_invoiced_then_refund_then_cancel_it')

            # Sat.
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                order.l10n_mx_edi_cfdi_try_sat()
            invoice_doc_values['sat_state'] = 'valid'
            ginvoice_doc_values['sat_state'] = 'valid'
            self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
                invoice_doc_values,
                ginvoice_doc_values,
            ])

            # Try to cancel.
            with self.with_mocked_pac_cancel_error():
                order.l10n_mx_edi_document_ids.sorted()[0].action_cancel()
            invoice_cancel_doc_values = {
                'pos_order_ids': order.ids,
                'state': 'invoice_cancel_failed',
                'sat_state': False,
                'attachment_uuid': invoice_doc_values['attachment_uuid'],
                'attachment_origin': f'01|{order.l10n_mx_edi_cfdi_uuid}',
                'cancellation_reason': '02',
                'retry_button_needed': True,
                'cancel_button_needed': False,
            }
            self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
                invoice_cancel_doc_values,
                invoice_doc_values,
                ginvoice_doc_values,
            ])

            # Retry the cancel.
            with self.with_mocked_pac_cancel_success():
                order.l10n_mx_edi_document_ids.sorted()[0].action_retry()
            invoice_cancel_doc_values.update({
                'state': 'invoice_cancel',
                'sat_state': 'not_defined',
                'attachment_uuid': invoice_doc_values['attachment_uuid'],
                'attachment_origin': f'01|{order.l10n_mx_edi_cfdi_uuid}',
                'cancellation_reason': '02',
                'retry_button_needed': False,
                'cancel_button_needed': False,
            })
            self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
                invoice_cancel_doc_values,
                invoice_doc_values,
                ginvoice_doc_values,
            ])

            # Sat.
            with self.with_mocked_sat_call(lambda _x: 'cancelled'):
                order.l10n_mx_edi_cfdi_try_sat()
            invoice_cancel_doc_values['sat_state'] = 'cancelled'
            invoice_doc_values['sat_state'] = 'cancelled'
            ginvoice_doc_values['sat_state'] = 'cancelled'
            self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
                invoice_cancel_doc_values,
                invoice_doc_values,
                ginvoice_doc_values,
            ])

    def test_invoiced_order_mx_customer(self):
        with self.mx_external_setup(self.frozen_today):
            with self.create_and_invoice_order() as order:
                order.partner_id = self.partner_mx
                self.assertFalse(order.l10n_mx_edi_cfdi_to_public)
            self._assert_invoice_cfdi(order.account_move, 'test_invoiced_order_mx_customer')

    def test_invoiced_order_foreign_customer(self):
        with self.mx_external_setup(self.frozen_today):
            with self.create_and_invoice_order() as order:
                order.partner_id = self.partner_us
                self.assertFalse(order.l10n_mx_edi_cfdi_to_public)
            self._assert_invoice_cfdi(order.account_move, 'test_invoiced_order_foreign_customer')

    def test_invoiced_order_customer_with_no_country(self):
        with self.mx_external_setup(self.frozen_today):
            with self.create_and_invoice_order() as order:
                self.partner_us.country_id = None
                order.partner_id = self.partner_us
                self.assertTrue(order.l10n_mx_edi_cfdi_to_public)
            self._assert_invoice_cfdi(order.account_move, 'test_invoiced_order_customer_with_no_country')

    def test_invoiced_order_then_invoiced_refund(self):
        with self.with_pos_session():
            # Invoice an order.
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product, 10)],
                'payments': [(self.bank_pm1, 11600.0)],
                'customer': self.partner_mx,
                'is_invoiced': True,
            })
            order.account_move.l10n_mx_edi_cfdi_uuid = '424242'

        with self.with_pos_session():
            # Invoice the refund order.
            refund = self._create_order({
                'pos_order_lines_ui_args': [{
                    'product': self.product,
                    'quantity': -10,
                    'refunded_orderline_id': order.lines.id,
                }],
                'payments': [(self.bank_pm1, -11600.0)],
                'customer': self.partner_mx,
                'is_invoiced': True,
            })
        self.assertEqual(refund.account_move.l10n_mx_edi_cfdi_origin, '03|424242')

    def test_refund_order_mx(self):
        """ Test a pos order completely refunded by the negative lines. """
        with self.mx_external_setup(self.frozen_today), self.with_pos_session():
            order = self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product, 1.0),
                ],
                'payments': [(self.bank_pm1, 1160)],
            })
            refund = self.env['pos.order'].browse(order.refund()['res_id'])
            self.assertEqual(refund.refunded_order_ids, order)
