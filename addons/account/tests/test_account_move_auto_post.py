from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.base.tests.test_ir_cron import CronMixinCase


@tagged('post_install', '-at_install')
class TestAccountMoveAutoPost(AccountTestInvoicingCommon, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_auto_post_infinite_loop(self):
        """ The scheduled action 'account.ir_cron_auto_post_draft_entry' can fall into an infinite
        loop in certain conditions """

        auto_post_journal = self.env['account.journal'].create({
            "type": "sale",
            "name": "Test journal",
            "code": "TEST",
            "company_id": self.company_data["company"].id,
        })

        # creating 100 invalid invoices (missing partner)
        self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 10,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
            'journal_id': auto_post_journal.id,
            'auto_post': 'at_date',
            'checked': True
        } for _ in range(100)])

        cron = self.env.ref('account.ir_cron_auto_post_draft_entry')

        with self.capture_triggers('account.ir_cron_auto_post_draft_entry') as captured_triggers:
            # Calling method_direct_trigger the first time to fetch all 100 invoices.
            # A trigger would be captured here since it tries to trigger itself again.
            cron.method_direct_trigger()
            # Calling method_direct_trigger a second time.
            # No triggers should be captured here, since no invoices should be fetched.
            cron.method_direct_trigger()

        self.assertEqual(len(captured_triggers.records), 1)
