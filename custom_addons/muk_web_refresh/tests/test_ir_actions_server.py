from __future__ import annotations

from unittest.mock import patch as mock_patch

from odoo.models import BaseModel
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestReloadViews(TransactionCase):
    """Test the reload-views server action bus broadcast."""

    # ----------------------------------------------------------
    # Setup
    # ----------------------------------------------------------

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.action = cls.env['ir.actions.server'].create(
            {
                'name': 'Test Reload Views',
                'model_id': cls.env.ref('base.model_res_partner').id,
                'state': 'refresh',
            }
        )

    # ----------------------------------------------------------
    # Tests
    # ----------------------------------------------------------

    def _make_eval_context(self, records: BaseModel | None = None) -> dict:
        """Build an evaluation context for the reload-views action."""
        partner = records or self.env['res.partner'].browse()
        return {
            'env': self.env,
            'model': self.env['res.partner'],
            'records': partner,
            'record': partner[:1],
        }

    def test_refresh_sends_bus_notification(self):
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        with mock_patch.object(type(self.env['bus.bus']), '_sendone') as mock_sendone:
            self.action._run_action_refresh_multi(
                eval_context=self._make_eval_context(partner),
            )
            self.assertTrue(mock_sendone.called)
            channel = mock_sendone.call_args[0][0]
            notification_type = mock_sendone.call_args[0][1]
            payload = mock_sendone.call_args[0][2]
            self.assertEqual(channel, 'broadcast')
            self.assertEqual(notification_type, 'muk_web_refresh.reload')
            self.assertEqual(payload['model'], 'res.partner')
            self.assertEqual(payload['rec_ids'], partner.ids)
            self.assertEqual(payload['view_types'], [])

    def test_refresh_notifies_all_internal_users(self):
        with mock_patch.object(type(self.env['bus.bus']), '_sendone') as mock_sendone:
            self.action._run_action_refresh_multi(
                eval_context=self._make_eval_context(),
            )
            self.assertEqual(mock_sendone.call_count, 1)

    def test_refresh_with_view_types(self):
        self.action.refresh_view_types = 'list, kanban'
        with mock_patch.object(type(self.env['bus.bus']), '_sendone') as mock_sendone:
            self.action._run_action_refresh_multi(
                eval_context=self._make_eval_context(),
            )
            payload = mock_sendone.call_args[0][2]
            self.assertEqual(payload['view_types'], ['list', 'kanban'])
