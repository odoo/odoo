from .common import TestMxEdiPosCommon

from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPosOrderDocuments(TestMxEdiPosCommon):

    def test_global_invoice_refund_production_sign_flow_cancel_from_the_sat(self):
        """ Test the case the global invoice refund is signed but the user manually cancel the document from the SAT portal (production environment). """
        self.env.company.l10n_mx_edi_pac_test_env = False
        self.env.company.l10n_mx_edi_pac_username = 'test'
        self.env.company.l10n_mx_edi_pac_password = 'test'

        with freeze_time('2017-01-01'):
            with self.with_pos_session() as _session:
                order = self._create_order({
                    'pos_order_lines_ui_args': [(self.product, 1)],
                    'payments': [(self.bank_pm1, 1160.0)],
                    'customer': self.partner_mx,
                })
                order.l10n_mx_edi_cfdi_to_public = True
            with self.with_mocked_pac_sign_success():
                order._l10n_mx_edi_cfdi_global_invoice_try_send()
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                order.l10n_mx_edi_cfdi_try_sat()
            gi_sent_doc_values = {
                'pos_order_ids': order.ids,
                'state': 'ginvoice_sent',
                'sat_state': 'valid',
            }
            self.assertRecordValues(order.l10n_mx_edi_document_ids, [gi_sent_doc_values])
            self.assertRecordValues(order, [{
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_sat_state': 'valid',
                'l10n_mx_edi_cfdi_state': 'global_sent',
            }])

            # Ask for an invoice.
            with self.with_pos_session() as _session, self.with_mocked_pac_sign_success():
                order.action_pos_order_invoice()
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                order.l10n_mx_edi_cfdi_try_sat()

            refund_sent_doc_values = {
                'pos_order_ids': order.ids,
                'state': 'invoice_sent',
                'sat_state': 'valid',
            }
            self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
                refund_sent_doc_values,
                gi_sent_doc_values,
            ])
            self.assertRecordValues(order, [{
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_sat_state': 'valid',
                'l10n_mx_edi_cfdi_state': 'global_sent',
            }])

        # Manual cancellation from the SAT portal.
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            order.l10n_mx_edi_cfdi_try_sat()

        gi_cancel_doc_values = {
            'pos_order_ids': order.ids,
            'state': 'ginvoice_cancel',
            'sat_state': 'cancelled',
        }
        refund_cancel_doc_values = {
            'pos_order_ids': order.ids,
            'state': 'invoice_cancel',
            'sat_state': 'cancelled',
        }
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            refund_cancel_doc_values,
            gi_cancel_doc_values,
            refund_sent_doc_values,
            gi_sent_doc_values,
        ])
        order._compute_l10n_mx_edi_cfdi_state_and_attachment()
        self.assertRecordValues(order, [{
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'global_cancel',
        }])

    def test_global_invoice_production_sign_flow_cancel_from_the_sat(self):
        """ Test the case the global invoice is signed but the user manually cancel the document from the SAT portal (production environment). """
        self.env.company.l10n_mx_edi_pac_test_env = False
        self.env.company.l10n_mx_edi_pac_username = 'test'
        self.env.company.l10n_mx_edi_pac_password = 'test'

        with freeze_time('2017-01-01'):
            with self.with_pos_session() as _session:
                order = self._create_order({
                    'pos_order_lines_ui_args': [(self.product, 1)],
                    'payments': [(self.bank_pm1, 1160.0)],
                })
            with self.with_mocked_pac_sign_success():
                order._l10n_mx_edi_cfdi_global_invoice_try_send()
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                order.l10n_mx_edi_cfdi_try_sat()
            sent_doc_values = {
                'pos_order_ids': order.ids,
                'state': 'ginvoice_sent',
                'sat_state': 'valid',
            }
            self.assertRecordValues(order.l10n_mx_edi_document_ids, [sent_doc_values])
            self.assertRecordValues(order, [{
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_sat_state': 'valid',
                'l10n_mx_edi_cfdi_state': 'global_sent',
            }])

        # Manual cancellation from the SAT portal.
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            order.l10n_mx_edi_cfdi_try_sat()

        cancel_doc_values = {
            'pos_order_ids': order.ids,
            'state': 'ginvoice_cancel',
            'sat_state': 'cancelled',
        }
        self.assertRecordValues(order.l10n_mx_edi_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(order, [{
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'global_cancel',
        }])
