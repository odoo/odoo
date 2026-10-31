import logging
from unittest import SkipTest

from odoo.tests import BenchmarkCase

_logger = logging.getLogger(__name__)


class BenchmarkPicking(BenchmarkCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        blueprint = cls.env.ref('stock.benchmark_updates', raise_if_not_found=False)
        if not blueprint:
            msg = "Required blueprint stock.benchmark_updates is missing"
            raise SkipTest(msg)

        cls.pickings = blueprint._get_populated('upd_pickings').filtered(
            lambda picking: (
                picking.state == 'draft'
                and picking.company_id == cls.env.company
                and picking.move_ids
            ),
        )
        if not cls.pickings:
            msg = "The stock population has no draft pickings with moves in the current company"
            raise SkipTest(msg)

        _logger.info(
            'Benchmark dataset stock.benchmark_updates: pickings=%s moves=%s',
            len(cls.pickings), len(cls.pickings.mapped('move_ids')),
        )

    def test_confirm(self):
        """Confirm all selected draft pickings, including their final flush."""
        self.pickings.action_confirm()

    def test_confirm_then_cancel(self):
        """Confirm then cancel the same pickings in one round, reporting each phase."""
        with self.measure('confirm'):
            self.pickings.action_confirm()
        with self.measure('cancel'):
            self.pickings.action_cancel()
