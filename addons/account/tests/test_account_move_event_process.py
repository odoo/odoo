from odoo import Command
from odoo.exceptions import LockError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestAccountMoveEventProcess(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [Command.create({'price_unit': 100})],
        })

    def test_get_batch_to_process(self):
        event_code = 'concurrent_event'
        self.env['account.move.event.process'].create({
            'move_id': self.invoice.id,
            'event_code': event_code,
        })
        events = self.env['account.move.event.process'].get_batch_to_process(event_code)
        self.assertEqual(len(events), 1)

        with self.assertRaises(LockError), self.env.registry.cursor() as cr:
            self.env(cr=cr)['account.move.event.process'].browse(events.ids).lock_for_update()
