from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged
from .common import TestMXEdiStockCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIPickingWorkflow(TestMXEdiStockCommon):

    def test_picking_workflow(self):
        warehouse = self._create_warehouse()
        picking = self._create_picking(warehouse)

        # No pac found.
        self.env.company.l10n_mx_edi_pac = None
        with freeze_time('2017-01-05'):
            picking.l10n_mx_edi_cfdi_try_send()
        self.assertRecordValues(picking.l10n_mx_edi_document_ids, [
            {
                'datetime': fields.Datetime.from_string('2017-01-05 00:00:00'),
                'message': "No PAC specified.",
                'state': 'picking_sent_failed',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
        ])
        self.assertRecordValues(picking, [{'l10n_mx_edi_cfdi_state': None}])

        # Set back the PAC but make it raising an error.
        self.env.company.l10n_mx_edi_pac = 'solfact'
        with freeze_time('2017-01-06'), self.with_mocked_pac_sign_error():
            picking.l10n_mx_edi_cfdi_try_send()
        self.assertRecordValues(picking.l10n_mx_edi_document_ids, [
            {
                'datetime': fields.Datetime.from_string('2017-01-06 00:00:00'),
                'message': "turlututu",
                'state': 'picking_sent_failed',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
        ])
        self.assertRecordValues(picking, [{'l10n_mx_edi_cfdi_state': None}])

        # The failing attachment remains accessible for the user.
        self.assertTrue(picking.l10n_mx_edi_document_ids.attachment_id)

        # Sign.
        with freeze_time('2017-01-07'), self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_document_ids.action_retry()
        sent_doc_values = {
            'datetime': fields.Datetime.from_string('2017-01-07 00:00:00'),
            'message': False,
            'state': 'picking_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(picking.l10n_mx_edi_document_ids, [sent_doc_values])
        self.assertTrue(picking.l10n_mx_edi_cfdi_attachment_id)
        self.assertTrue(picking.l10n_mx_edi_document_ids.attachment_id)
        self.assertRecordValues(picking, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Cancel failed.
        self.env.company.l10n_mx_edi_pac = None
        with freeze_time('2017-02-01'):
            picking._l10n_mx_edi_cfdi_try_cancel(picking.l10n_mx_edi_document_ids)
        self.assertRecordValues(picking.l10n_mx_edi_document_ids.sorted(), [
            {
                'datetime': fields.Datetime.from_string('2017-02-01 00:00:00'),
                'message': "No PAC specified.",
                'state': 'picking_cancel_failed',
                'sat_state': False,
                'cancellation_reason': '02',
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
            sent_doc_values,
        ])

        # Set back the PAC but make it raising an error.
        self.env.company.l10n_mx_edi_pac = 'solfact'
        with freeze_time('2017-02-06'), self.with_mocked_pac_cancel_error():
            picking.l10n_mx_edi_document_ids.sorted()[0].action_retry()
        self.assertRecordValues(picking.l10n_mx_edi_document_ids.sorted(), [
            {
                'datetime': fields.Datetime.from_string('2017-02-06 00:00:00'),
                'message': "turlututu",
                'state': 'picking_cancel_failed',
                'sat_state': False,
                'cancellation_reason': '02',
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
            sent_doc_values,
        ])

        # Cancel
        with freeze_time('2017-02-07'), self.with_mocked_pac_cancel_success():
            picking.l10n_mx_edi_document_ids.sorted()[0].action_retry()

        picking.l10n_mx_edi_document_ids.invalidate_recordset(fnames=['cancel_button_needed'])
        sent_doc_values['cancel_button_needed'] = False
        sent_doc_values['sat_state'] = 'skip'

        cancel_doc_values = {
            'datetime': fields.Datetime.from_string('2017-02-07 00:00:00'),
            'message': False,
            'state': 'picking_cancel',
            'sat_state': 'not_defined',
            'cancellation_reason': '02',
            'cancel_button_needed': False,
            'retry_button_needed': False,
        }
        self.assertRecordValues(picking.l10n_mx_edi_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(picking, [{'l10n_mx_edi_cfdi_state': 'cancel'}])

        # Sign again.
        with freeze_time('2017-03-10'), self.with_mocked_pac_sign_success():
            picking.l10n_mx_edi_cfdi_try_send()
        sent_doc_values2 = {
            'datetime': fields.Datetime.from_string('2017-03-10 00:00:00'),
            'message': False,
            'state': 'picking_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(picking.l10n_mx_edi_document_ids.sorted(), [
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(picking, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Sat.
        with freeze_time('2017-04-01'), self.with_mocked_sat_call(lambda x: 'valid' if x['state'] == 'picking_sent' else 'cancelled'):
            picking.l10n_mx_edi_cfdi_try_sat()
        sent_doc_values2['sat_state'] = 'valid'
        cancel_doc_values['sat_state'] = 'cancelled'
        self.assertRecordValues(picking.l10n_mx_edi_document_ids.sorted(), [
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(picking, [{'l10n_mx_edi_cfdi_state': 'sent'}])

    def test_picking_production_sign_flow_cancel_from_the_sat(self):
        """ Test the case the invoice/payment is signed but the user manually cancel the document from the SAT portal (production environment). """
        self.env.company.l10n_mx_edi_pac_test_env = False
        self.env.company.l10n_mx_edi_pac_username = 'test'
        self.env.company.l10n_mx_edi_pac_password = 'test'

        with freeze_time('2017-01-01'):
            warehouse = self._create_warehouse()
            picking = self._create_picking(warehouse)
            with self.with_mocked_pac_sign_success():
                picking.l10n_mx_edi_cfdi_try_send()
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                picking.l10n_mx_edi_cfdi_try_sat()
            sent_doc_values = {
                'picking_id': picking.id,
                'state': 'picking_sent',
                'sat_state': 'valid',
            }
            self.assertRecordValues(picking.l10n_mx_edi_document_ids, [sent_doc_values])
            self.assertRecordValues(picking, [{
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_sat_state': 'valid',
                'l10n_mx_edi_cfdi_state': 'sent',
            }])

        # Manual cancellation from the SAT portal.
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            picking.l10n_mx_edi_cfdi_try_sat()

        cancel_doc_values = {
            'picking_id': picking.id,
            'state': 'picking_cancel',
            'sat_state': 'cancelled',
        }
        self.assertRecordValues(picking.l10n_mx_edi_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(picking, [{
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'cancel',
        }])
