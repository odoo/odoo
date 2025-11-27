from odoo import fields
from odoo.tests.common import tagged

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpDeadlines(PdpTestCommon):
    def test_deadline_override_stored(self):
        """Overrides should recompute stored deadline fields."""
        today = fields.Date.today()
        self.company.write({
            'l10n_fr_pdp_deadline_override_start': today.day,
            'l10n_fr_pdp_deadline_override_end': today.day,
        })
        self._create_invoice(sent=True)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')
        self.assertEqual(flow.next_deadline_start, today, 'Override start should be stored on flow')
        self.assertEqual(flow.next_deadline_end, today, 'Override end should be stored on flow')
