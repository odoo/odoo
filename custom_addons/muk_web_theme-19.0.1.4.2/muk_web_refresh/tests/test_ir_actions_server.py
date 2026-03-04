from unittest.mock import patch as mock_patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestReloadViews(TransactionCase):

    # ----------------------------------------------------------
    # Setup
    # ----------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.action = cls.env['ir.actions.server'].create({
            'name': 'Test Reload Views',
            'model_id': cls.env.ref('base.model_res_partner').id,
            'state': 'refresh',
        })

    # ----------------------------------------------------------
    # Tests
    # ----------------------------------------------------------

    def _make_eval_context(self, records=None):
        partner = records or self.env['res.partner'].browse()
        return {
            'env': self.env,
            'model': self.env['res.partner'],
            'records': partner,
            'record': partner[:1],
        }

    def test_refresh_sends_bus_notification(self):
        partner = self.env.ref('base.res_partner_1')
        with mock_patch.object(
            type(self.env['res.users']), '_bus_send'
        ) as mock_bus_send:
            self.action._run_action_refresh_multi(
                eval_context=self._make_eval_context(partner),
            )
            self.assertTrue(mock_bus_send.called)
            payload = mock_bus_send.call_args[0][1]
            self.assertEqual(payload['model'], 'res.partner')
            self.assertEqual(payload['rec_ids'], partner.ids)
            self.assertEqual(payload['view_types'], [])

    def test_refresh_notifies_all_internal_users(self):
        internal_users = self.env['res.users'].search(
            [('share', '=', False)]
        )
        with mock_patch.object(
            type(self.env['res.users']), '_bus_send'
        ) as mock_bus_send:
            self.action._run_action_refresh_multi(
                eval_context=self._make_eval_context(),
            )
            self.assertEqual(
                mock_bus_send.call_count, len(internal_users),
            )

    def test_refresh_with_view_types(self):
        self.action.refresh_view_types = 'list, kanban'
        with mock_patch.object(
            type(self.env['res.users']), '_bus_send'
        ) as mock_bus_send:
            self.action._run_action_refresh_multi(
                eval_context=self._make_eval_context(),
            )
            payload = mock_bus_send.call_args[0][1]
            self.assertEqual(payload['view_types'], ['list', 'kanban'])


