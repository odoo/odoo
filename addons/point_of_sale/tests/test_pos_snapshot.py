# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.fields import Domain
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestPosSnapshot(TestPoSCommon):

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        product = self.create_product('Snapshot Product', self.categ_basic, 10)
        self.open_new_session()
        self.paid_order, = self._create_orders([
            {'pos_order_lines_ui_args': [(product, 2)], 'payments': [(self.bank_pm1, 20)]},
        ]).values()
        self.cancelled_order, = self._create_orders([
            {'pos_order_lines_ui_args': [(product, 1)], 'payments': [], 'pos_order_ui_args': {'state': 'draft'}},
        ]).values()
        self.cancelled_order.with_context(active_ids=self.cancelled_order.ids).action_pos_order_cancel()
        self.snapshot = self.env['pos.snapshot']
        self.keys = self.snapshot._keys()

    def _snapshot_state(self):
        """Version of each snapshot of the session and whether it is built."""
        self.env.cr.execute(
            "SELECT key, version, data IS NOT NULL FROM pos_snapshot WHERE session_id = %s", [self.pos_session.id],
        )
        return {key: (version, built) for key, version, built in self.env.cr.fetchall()}

    def _session_domain(self, key):
        return Domain(self.env[key.rsplit('.', 1)[0]]._snapshot_session_path(), '=', self.pos_session.id)

    def _live(self, key):
        """Snapshot data computed live for the session."""
        records = self.env[key.rsplit('.', 1)[0]].search(self._session_domain(key))
        return self.snapshot._snapshot_method(key)(records)

    def _close_and_build(self):
        self.pos_session.close_session_from_ui()
        self.snapshot._build(self.pos_session.id)

    def test_snapshot_queued_on_close_and_reused(self):
        self.snapshot._enqueue(self.pos_session)
        self.assertEqual(self._snapshot_state(), {}, "Open sessions are never queued")

        self.pos_session.close_session_from_ui()
        self.assertEqual(self._snapshot_state(), {key: (0, False) for key in self.keys})

        self.snapshot._build(self.pos_session.id)
        self.assertEqual(self._snapshot_state(), {key: (version, True) for key, version in self.keys.items()})
        for key in self.keys:
            # nothing matches the domain, so the data must come from the stored snapshot
            self.assertEqual(self.snapshot._get(key, Domain.FALSE, self.pos_session.ids), {self.pos_session: self._live(key)})

    def test_snapshot_invalidation(self):
        self._close_and_build()

        # the customer is not used in the computation, so it keeps the snapshots
        self.paid_order.partner_id = self.customer
        self.assertTrue(all(built for _version, built in self._snapshot_state().values()))

        self.cancelled_order.unlink()
        self.assertFalse(any(built for _version, built in self._snapshot_state().values()))

    def test_snapshot_version_change_rebuilds(self):
        self._close_and_build()
        self.env.cr.execute("UPDATE pos_snapshot SET version = version - 1 WHERE session_id = %s", [self.pos_session.id])

        # the cron commits after each session, which is not allowed in tests
        with patch.object(self.env.registry['ir.cron'], '_commit_progress', return_value=1.0):
            self.snapshot._cron_build()
        self.assertEqual(self._snapshot_state(), {key: (version, True) for key, version in self.keys.items()})
