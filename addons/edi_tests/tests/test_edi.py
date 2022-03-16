# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.edi.tests.common import EdiTestCommon

from unittest.mock import patch
import base64


@tagged('post_install', '-at_install')
class TestEdi(EdiTestCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        super().EDISetUpClass(edi_format_ref='edi_tests.test_edi')
        cls.document = cls.env['res.partner'].create({
            'name': "Edi Test Partner",
        })

    def test_prepare_jobs(self):
        edi_flows = self.env['edi.flow']
        # The EDI does not support batching, two similar flows won't be processed together.
        with patch('odoo.addons.edi_tests.models.edi_format.EdiFormat._get_edi_format_settings',
                   return_value=self._mock_get_edi_format_settings_return(batching_key=False)):
            edi_flows |= self.create_edi_flow()
            edi_flows |= self.create_edi_flow()

            to_process = edi_flows._prepare_jobs()
            self.assertEqual(len(to_process), 2)

        # The EDI supports batching, two similar flows will be processed together.
        to_process = edi_flows._prepare_jobs()
        self.assertEqual(len(to_process), 1)

        # The EDI supports batching, it will group the two similar send flows and the two similar cancel flows in two batches.
        edi_flows |= self.create_edi_flow(flow_type='cancel')
        edi_flows |= self.create_edi_flow(flow_type='cancel')
        to_process = edi_flows._prepare_jobs()
        self.assertEqual(len(to_process), 2)

    @patch('odoo.addons.edi.tests.common.EdiTestCommon._mocked_send', return_value={})
    def test_warning_is_retried(self, patched):
        """ Create a new edi flows, which call the "action" of the stage (_mocked_send).
        Then make it so that the flow is in error, and call _process_documents_web_services, which would call the action if not in error.
        Ensure that the action is not called a second time.
        """
        with patch('odoo.addons.edi_tests.models.edi_format.EdiFormat._get_edi_format_settings',
                   return_value=self._mock_get_edi_format_settings_return()):
            edi_flows = self.create_edi_flow()
            edi_flows.error = 'Test Error'
            edi_flows.blocking_level = 'warning'

            edi_flows._process_documents_web_services()
            patched.assert_called_once()

    def test_edi_flow(self):
        with patch('odoo.addons.edi_tests.models.edi_format.EdiFormat._get_edi_format_settings',
                   return_value=self._mock_get_edi_format_settings_return(needs_web_services=True)):
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            self.assertFalse(flow)
            self.document._do_something_creating_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            flow._process_documents_web_services()
            self.assertEqual(len(flow), 1)
            self.assertEqual(flow.state, 'sent')
            self.document._do_something_canceling_edi_flows()
            # The sent flow has been aborted, and a new cancellation flow has been created. We get the new one.
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            flow._process_documents_web_services()
            self.assertEqual(len(flow), 1)
            self.assertEqual(flow.state, 'cancelled')

    def test_edi_flow_two_steps(self):
        def _mocked_send_step_one(flows):
            return {document.id: {'success': True} for document in flows._get_documents()}

        def _mocked_send_step_two(flows):
            res = {}
            documents = flows._get_documents()
            for flow in flows:
                for document in documents.filtered(lambda d: d.id == flow.res_id):
                    attachment = flow.env['ir.attachment'].create({
                        'name': 'mock_simple.xml',
                        'datas': base64.encodebytes(b"<?xml version='1.0' encoding='UTF-8'?><Invoice/>"),
                        'mimetype': 'application/xml'
                    })
                    res[document.id] = {'success': True, 'attachment': attachment}
            return res

        with patch('odoo.addons.edi_tests.models.edi_format.EdiFormat._get_edi_format_settings',
                   return_value={
                       'needs_web_services': True,
                       'stages': {
                           'send': {
                               'step_one': {
                                   'new_state': 'to_send',
                                   'action': _mocked_send_step_one,
                               },
                               'step_two': {
                                   'action': _mocked_send_step_two,
                               },
                               'done': {
                                   'new_state': 'sent',
                               },
                           }}
                   }):
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            self.assertFalse(flow)
            self.document._do_something_creating_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            self.assertEqual(len(flow), 1)
            self.assertEqual(flow.state, 'to_send')
            flow._process_documents_web_services(with_commit=False)
            self.assertEqual(flow.state, 'to_send')
            flow._process_documents_web_services(with_commit=False)
            self.assertEqual(flow.state, 'sent')

    def test_edi_flow_request_cancel_success(self):
        self.document._do_something_creating_edi_flows()
        flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
        self.assertEqual(flow.state, 'to_send')
        flow._process_documents_web_services(with_commit=False)
        self.assertEqual(flow.state, 'sent')
        self.document._do_something_canceling_edi_flows()
        flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
        self.assertEqual(flow.state, 'to_cancel')
        flow._process_documents_web_services(with_commit=False)
        self.assertEqual(flow.state, 'cancelled')

    def test_edi_flow_request_cancel_failed(self):
        def _mocked_cancel_failed(flows):
            return {document.id: {'error': 'Faked error (mocked)'} for document in flows._get_documents()}

        with patch('odoo.addons.edi_tests.models.edi_format.EdiFormat._get_edi_format_settings',
                   return_value=self._mock_get_edi_format_settings_return(mocked_cancel_method=_mocked_cancel_failed)):
            self.document._do_something_creating_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            self.assertEqual(flow.state, 'to_send')
            flow._process_documents_web_services(with_commit=False)
            self.assertEqual(flow.state, 'sent')
            self.document._do_something_canceling_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            self.assertEqual(flow.state, 'to_cancel')
            # Call off edi Cancellation
            self.env['edi.flow']._abandon_cancel_flow(documents=self.document)
            # After cancelling the cancel, the document has no more active flows. We create a new one.
            self.document._do_something_creating_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            flow._process_documents_web_services(with_commit=False)
            self.assertEqual(flow.state, 'sent')
            self.assertFalse(flow.error)

            # Failed cancel
            self.document._do_something_canceling_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            self.assertEqual(flow.state, 'to_cancel')
            flow._process_documents_web_services(with_commit=False)
            self.assertEqual(flow.state, 'to_cancel')

            # Call off edi Cancellation
            self.env['edi.flow']._abandon_cancel_flow(documents=self.document)
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            # We once again have no active flows left, since we cancelled the cancellation.
            self.assertFalse(flow)

    def test_edi_flow_two_step_cancel_with_call_off_request(self):
        def _mock_cancel_step_one(flows):
            documents_no_ref = flows._get_documents().filtered(lambda d: not d.ref)
            documents_no_ref.ref = 'test_ref_cancel'
            return {document.id: {'success': True} for document in flows._get_documents()}

        def _mock_cancel_step_two(flows):
            documents_ref = flows._get_documents().filtered(lambda d: d.ref)
            documents_ref.ref = None
            return {document.id: {'success': True} for document in flows._get_documents()}

        with patch('odoo.addons.edi_tests.models.edi_format.EdiFormat._get_edi_format_settings',
                   return_value={
                       'needs_web_services': True,
                       'stages': {
                           'send': {
                               'step_one': {
                                   'new_state': 'to_send',
                                   'action': self._mocked_send
                               },
                               'done': {
                                   'new_state': 'sent',
                               },
                           },
                           'cancel': {
                               'step_one': {
                                   'new_state': 'to_cancel',
                                   'action': _mock_cancel_step_one
                               },
                               'step_two': {
                                   'action': _mock_cancel_step_two
                               },
                               'done': {
                                   'new_state': 'cancelled',
                               },
                           }
                       }
                   }):
            self.document._do_something_creating_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            flow._process_documents_web_services(with_commit=False)
            self.assertEqual(flow.state, 'sent')

            # Request Cancellation
            self.document._do_something_canceling_edi_flows()  # first step of cancel
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            flow._process_documents_web_services(with_commit=False)  # second step of cancel
            self.assertEqual(flow.state, 'to_cancel')

            # Call off edi Cancellation, which will fail because of _is_format_required
            self.document.abandon_edi_cancellation()
            self.assertEqual(flow.state, 'to_cancel')

            # If we cannot call off edi cancellation, only solution is to post again
            flow._process_documents_web_services(with_commit=False)  # third step of cancel
            self.assertEqual(flow.state, 'cancelled')
            self.document._do_something_creating_edi_flows()
            flow = self.document.edi_flow_ids._get_relevants(edi_format=self.edi_format)
            flow._process_documents_web_services(with_commit=False)
            self.assertEqual(flow.state, 'sent')

    def test_batches(self):
        edi_flows = self.env['edi.flow']
        document_2, document_3 = self.env['res.partner'].create([{
            'name': "Edi Test Partner 2",
        }, {
            'name': "Edi Test Partner 3",
        }])
        flow1 = self.create_edi_flow()
        edi_flows |= flow1
        flow2 = self.create_edi_flow(document=document_2)
        edi_flows |= flow2
        flow3 = self.create_edi_flow(document=document_3)
        edi_flows |= flow3

        to_process = edi_flows._prepare_jobs()
        self.assertEqual(len(to_process), 1)

        flow1._get_documents().ref = 'batch1'
        flow2._get_documents().ref = 'batch2'
        flow3._get_documents().ref = 'batch3'

        to_process = edi_flows._prepare_jobs()
        self.assertEqual(len(to_process), 3)

        flow2._get_documents().ref = 'batch1'
        to_process = edi_flows._prepare_jobs()
        self.assertEqual(len(to_process), 2)

    def test_cron_self_trigger(self):
        # Process single job by CRON call (and thus, disable the auto-commit).
        edi_cron = self.env.ref('edi.ir_cron_edi_network')
        edi_cron.code = 'model._cron_process_documents_web_services(job_count=1)'

        # Create invoices.
        documents = self.env['res.partner'].create([{
            'name': f"Edi Test Partner {i}",
        } for i in range(4)])

        with self.capture_triggers('edi.ir_cron_edi_network') as capt, \
                patch('odoo.addons.edi_tests.models.edi_format.EdiFormat._get_edi_format_settings',
                      return_value=self._mock_get_edi_format_settings_return(batching_key=False)):
            documents._do_something_creating_edi_flows()
            self.env.ref('edi.ir_cron_edi_network')._trigger()
            self.env.ref('edi.ir_cron_edi_network').method_direct_trigger()
            self.assertEqual(len(capt.records), 2, "Not all records have been processed in this run, the cron should "
                                                   "re-trigger itself to process some more later")
