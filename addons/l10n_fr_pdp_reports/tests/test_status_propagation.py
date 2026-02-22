import base64
import json
from unittest.mock import patch

from odoo import Command, fields
from odoo.tests.common import tagged

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpStatusPropagation(PdpTestCommon):
    def test_invalid_sale_invoice_is_pending_in_open_and_error_in_grace(self):
        """Before grace, invalid sale invoices stay pending; during grace they become error."""
        invoice_date = fields.Date.from_string('2025-02-05')
        open_day = fields.Date.from_string('2025-02-06')
        grace_day = fields.Date.from_string('2025-02-15')
        inv = self._create_invoice(sent=False, date_val=invoice_date)

        with patch('odoo.fields.Date.context_today', return_value=open_day):
            self._aggregate_company()
            inv.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(inv.l10n_fr_pdp_status, 'pending')

        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            self._aggregate_company()
            inv.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(inv.l10n_fr_pdp_status, 'error')

    def test_invoice_status_moves_from_pending_to_done(self):
        """Invoice PDP status becomes 'sent' after a successful send."""
        inv = self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]

        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy', return_value={
            'id': 'X-PENDING',
            'status': 'RECEIVED',
            'message': '',
            'acknowledgement': [],
        }):
            flow.action_send()
        inv.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(inv.l10n_fr_pdp_status, 'sent')

    def test_send_persists_transport_traceability_fields(self):
        """Flow send should keep transport ids/status/messages and acknowledgement details."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        proxy_response = {
            'id': 'UUID-TRACE-001',
            'flow_id': 'FLOW-TRACE-001',
            'status': 'ACCEPTED',
            'message': 'Accepted by proxy',
            'acknowledgement': [{'code': 'ACK_OK', 'message': 'ok'}],
        }
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy', return_value=proxy_response):
            flow.action_send()
        flow.invalidate_recordset([
            'state',
            'transport_identifier',
            'transport_status',
            'transport_message',
            'acknowledgement_status',
            'acknowledgement_details',
            'send_datetime',
            'last_send_datetime',
        ])
        self.assertEqual(flow.state, 'completed')
        self.assertEqual(flow.transport_identifier, 'UUID-TRACE-001')
        self.assertEqual(flow.transport_status, 'ACCEPTED')
        self.assertEqual(flow.transport_message, 'Accepted by proxy')
        self.assertEqual(flow.acknowledgement_status, 'ok')
        self.assertTrue(flow.acknowledgement_details)
        self.assertTrue(flow.send_datetime)
        self.assertTrue(flow.last_send_datetime)
        transport_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'l10n.fr.pdp.flow'),
            ('res_id', '=', flow.id),
            ('mimetype', '=', 'application/json'),
            ('name', 'like', '%_transport_response.json'),
        ])
        self.assertEqual(len(transport_attachments), 1)
        decoded_payload = base64.b64decode(transport_attachments.datas or b'').decode('utf-8')
        response_payload = json.loads(decoded_payload)
        self.assertEqual(response_payload['transport']['id'], 'UUID-TRACE-001')
        self.assertEqual(response_payload['acknowledgement_status'], 'ok')

    def test_proxy_status_mapping_is_stable_for_sent_completed_and_error(self):
        """Proxy return contract must map deterministically to internal flow states."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]

        # Processing without ack stays in "sent/pending".
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy', return_value={
            'id': 'UUID-MAP-1',
            'flow_id': 'FLOW-MAP-1',
            'status': 'PROCESSING',
            'message': '',
            'acknowledgement': [],
        }):
            flow.action_send()
        flow.invalidate_recordset(['state', 'acknowledgement_status'])
        self.assertEqual(flow.state, 'sent')
        self.assertEqual(flow.acknowledgement_status, 'pending')

        # Positive ack upgrades sent->completed and acknowledgement to ok.
        flow.write({'state': 'ready'})
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy', return_value={
            'id': 'UUID-MAP-2',
            'flow_id': 'FLOW-MAP-2',
            'status': 'DRAFT',
            'message': '',
            'acknowledgement': [{'code': 'ACK_OK', 'message': 'accepted'}],
        }):
            flow.action_send()
        flow.invalidate_recordset(['state', 'acknowledgement_status'])
        self.assertEqual(flow.state, 'completed')
        self.assertEqual(flow.acknowledgement_status, 'ok')

        # Rejection code forces error state.
        flow.write({'state': 'ready'})
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy', return_value={
            'id': 'UUID-MAP-3',
            'flow_id': 'FLOW-MAP-3',
            'status': 'DRAFT',
            'message': '',
            'acknowledgement': [{'code': 'REJ_COH', 'message': 'rejected'}],
        }):
            flow.action_send()
        flow.invalidate_recordset(['state', 'acknowledgement_status'])
        self.assertEqual(flow.state, 'error')
        self.assertEqual(flow.acknowledgement_status, 'error')

    def test_duplicate_acknowledgement_marks_flow_as_duplicate(self):
        """REJ_UNI should mark transport as duplicate without forcing business error."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]

        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy', return_value={
            'id': 'UUID-DUP-1',
            'flow_id': 'FLOW-DUP-1',
            'status': 'DRAFT',
            'message': 'already received',
            'acknowledgement': [{'code': 'REJ_UNI', 'message': 'duplicate transmission'}],
        }):
            flow.action_send()
        flow.invalidate_recordset(['state', 'acknowledgement_status', 'transport_status'])
        self.assertEqual(flow.state, 'completed')
        self.assertEqual(flow.acknowledgement_status, 'ok')
        self.assertEqual(flow.transport_status, 'DUPLICATE')

    def test_partial_rejection_marks_only_rejected_document_as_error(self):
        """Partial acknowledgement rejection should not force all documents to error."""
        rejected_invoice = self._create_invoice(sent=True)
        accepted_invoice = self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertEqual(len(flow.move_ids), 2)

        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._send_to_proxy', return_value={
            'id': 'UUID-PARTIAL-1',
            'flow_id': 'FLOW-PARTIAL-1',
            'status': 'DRAFT',
            'message': 'partially rejected',
            'acknowledgement': [{
                'code': 'REJ_COH',
                'message': 'invalid invoice',
                'invoice_id': rejected_invoice.name,
            }],
        }):
            flow.action_send()

        flow.invalidate_recordset(['state', 'transport_status', 'acknowledgement_status', 'error_move_ids'])
        rejected_invoice.invalidate_recordset(['l10n_fr_pdp_status'])
        accepted_invoice.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(flow.state, 'completed')
        self.assertEqual(flow.transport_status, 'PARTIAL_REJECTED')
        self.assertEqual(flow.acknowledgement_status, 'error')
        self.assertIn(rejected_invoice, flow.error_move_ids)
        self.assertNotIn(accepted_invoice, flow.error_move_ids)
        self.assertEqual(rejected_invoice.l10n_fr_pdp_status, 'error')
        self.assertEqual(accepted_invoice.l10n_fr_pdp_status, 'sent')

    def test_cron_sync_transport_status_updates_completed_and_acks_message(self):
        """Polling cron should upgrade sent flow to completed and acknowledge message UUID."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        flow.write({
            'state': 'sent',
            'transport_identifier': 'UUID-CRON-OK',
            'transport_status': 'DRAFT',
            'acknowledgement_status': 'pending',
        })

        class DummyProxy:
            def __init__(self):
                self.calls = []

            def _l10n_fr_pdp_call_proxy(self, endpoint, params=None):
                self.calls.append((endpoint, params or {}))
                if endpoint == '/api/pdp/1/get_all_documents':
                    return {
                        'messages': [{
                            'uuid': 'UUID-CRON-OK',
                            'state': 'done',
                            'direction': 'outgoing',
                            'document_type': 'Report',
                        }],
                    }
                if endpoint == '/api/pdp/1/ack':
                    return {}
                raise AssertionError(f'Unexpected endpoint: {endpoint}')

        dummy_proxy = DummyProxy()
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._get_pdp_proxy_user', return_value=dummy_proxy):
            self.env['l10n.fr.pdp.flow']._cron_sync_transport_statuses()

        flow.invalidate_recordset(['state', 'transport_status', 'acknowledgement_status'])
        self.assertEqual(flow.state, 'completed')
        self.assertEqual(flow.transport_status, 'DONE')
        self.assertEqual(flow.acknowledgement_status, 'ok')
        self.assertIn(('/api/pdp/1/ack', {'message_uuids': ['UUID-CRON-OK']}), dummy_proxy.calls)

    def test_cron_sync_transport_status_maps_error_payload(self):
        """Polling cron should map proxy error state and keep readable transport message."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        flow.write({
            'state': 'sent',
            'transport_identifier': 'UUID-CRON-ERR',
            'transport_status': 'PROCESSING',
            'acknowledgement_status': 'pending',
        })

        class DummyProxy:
            def __init__(self):
                self.calls = []

            def _l10n_fr_pdp_call_proxy(self, endpoint, params=None):
                self.calls.append((endpoint, params or {}))
                if endpoint == '/api/pdp/1/get_all_documents':
                    return {
                        'messages': [{
                            'uuid': 'UUID-CRON-ERR',
                            'state': 'error',
                            'direction': 'outgoing',
                            'document_type': 'Report',
                            'error': '{"message":"PPF rejected this flow"}',
                        }],
                    }
                if endpoint == '/api/pdp/1/ack':
                    return {}
                raise AssertionError(f'Unexpected endpoint: {endpoint}')

        dummy_proxy = DummyProxy()
        with patch('odoo.addons.l10n_fr_pdp_reports.models.pdp_flow.PdpFlow._get_pdp_proxy_user', return_value=dummy_proxy):
            self.env['l10n.fr.pdp.flow']._cron_sync_transport_statuses()

        flow.invalidate_recordset(['state', 'transport_status', 'transport_message', 'acknowledgement_status'])
        self.assertEqual(flow.state, 'error')
        self.assertEqual(flow.transport_status, 'ERROR')
        self.assertEqual(flow.acknowledgement_status, 'error')
        self.assertEqual(flow.transport_message, 'PPF rejected this flow')

    def test_statusbar_fold_configuration(self):
        """Form view statusbar reflects the v1.2 lifecycle."""
        view = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_flow_form')
        self.assertIn('statusbar_visible="pending,ready,error,cancelled,sent,completed"', view.arch_db)
        self.assertNotIn('statusbar_fold="done,error"', view.arch_db)

    def test_document_status_field_is_computed_readonly(self):
        """UI must display PDP status only; business logic computes it."""
        field = self.env['account.move']._fields['l10n_fr_pdp_status']
        self.assertTrue(field.readonly)
        self.assertEqual(field.compute, '_compute_l10n_fr_pdp_status')

    def test_pdp_status_field_is_visible_in_tree_form_and_kanban_views(self):
        """Document status should be exposed in list/form/kanban views."""
        sale_tree = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_out_invoice_tree')
        purchase_tree = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_in_invoice_tree')
        move_form = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_move_form')
        move_kanban = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_move_kanban')
        self.assertIn('name="l10n_fr_pdp_status"', sale_tree.arch_db)
        self.assertIn('name="l10n_fr_pdp_status"', purchase_tree.arch_db)
        self.assertIn('name="l10n_fr_pdp_status"', move_form.arch_db)
        self.assertIn('name="l10n_fr_pdp_status"', move_kanban.arch_db)

    def test_flow_marked_outdated_on_partner_change(self):
        """Changing partner VAT should reset open flows to pending and clear payload."""
        self._create_invoice(partner=self.partner_international, sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertIn(flow.state, {'pending', 'ready'})
        self.assertTrue(flow.has_payload)

        self.partner_international.with_context(no_vat_validation=True).write({'vat': 'BE000'})
        flow.invalidate_recordset(['state', 'has_payload', 'revision'])
        self.assertEqual(flow.state, 'pending', 'Flow should be reset to pending after partner change')
        self.assertFalse(flow.payload, 'Flow payload field should be cleared when marked outdated')

    def test_error_moves_cleared_after_fix_and_rebuild(self):
        """Fixing invalid invoice and rebuilding should clear error_move_ids."""
        bad = self._create_invoice(sent=False)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertIn(bad, flow.error_move_ids)

        bad.is_move_sent = True
        flow._build_payload()
        flow.invalidate_recordset(['error_move_ids', 'state'])
        self.assertFalse(flow.error_move_ids, 'error_move_ids should be cleared after fixing issues')
        self.assertEqual(flow.state, 'ready')

    def test_document_status_follows_flow_state_transitions(self):
        """Move status should stay coherent with the latest flow state for the same period."""
        invoice_date = fields.Date.from_string('2025-02-05')
        grace_day = fields.Date.from_string('2025-02-15')
        inv = self._create_invoice(sent=True, date_val=invoice_date)

        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
            flow.invalidate_recordset(['state'])
            inv.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(flow.state, 'ready')
            self.assertEqual(inv.l10n_fr_pdp_status, 'ready')

            flow.write({
                'state': 'error',
                'error_move_ids': [Command.set([inv.id])],
            })
            inv.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(inv.l10n_fr_pdp_status, 'error')

            flow.write({'state': 'sent'})
            inv.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(inv.l10n_fr_pdp_status, 'sent')

    def test_document_status_cancelled_when_flow_cancelled(self):
        """Move status should become cancelled when the only relevant flow is cancelled."""
        invoice_date = fields.Date.from_string('2025-02-05')
        grace_day = fields.Date.from_string('2025-02-15')
        inv = self._create_invoice(sent=True, date_val=invoice_date)

        with patch('odoo.fields.Date.context_today', return_value=grace_day):
            flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
            flow.write({'state': 'cancelled'})
            inv.invalidate_recordset(['l10n_fr_pdp_status'])
            self.assertEqual(inv.l10n_fr_pdp_status, 'cancelled')

    def test_document_status_moves_from_out_of_scope_to_pending_when_context_changes(self):
        """Changing partner context from domestic B2B to in-scope must flip status to pending."""
        fr_business_partner = self.env['res.partner'].create({
            'name': 'FR B2B Local',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR40303265045',
            'property_account_receivable_id': self.partner_b2c.property_account_receivable_id.id,
            'property_account_payable_id': self.partner_b2c.property_account_payable_id.id,
        })
        invoice = self._create_invoice(partner=fr_business_partner, sent=True)
        invoice.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(invoice.l10n_fr_pdp_status, 'out_of_scope')

        invoice.button_draft()
        invoice.write({'partner_id': self.partner_b2c.id})
        invoice.action_post()
        invoice.invalidate_recordset(['l10n_fr_pdp_status'])
        self.assertEqual(invoice.l10n_fr_pdp_status, 'pending')
