from unittest import SkipTest

from odoo.tests import BenchmarkCase, benchmark


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
            )
        )
        if not cls.pickings:
            msg = "The stock population has no draft pickings with moves in the current company"
            raise SkipTest(msg)

    @benchmark
    def confirm(self):
        self.pickings.action_confirm()

    @benchmark
    def confirm_then_cancel(self):
        with self.measure('confirm'):
            self.pickings.action_confirm()
        with self.measure('cancel'):
            self.pickings.action_cancel()
