from datetime import date

from openerp.tests.common import TransactionCase
from openerp.osv.orm import except_orm

class TestPeriodState(TransactionCase):
    """
    Forbid creation of Journal Entries for a closed period.
    """

    def setUp(self):
        super(TestPeriodState, self).setUp()
        cr, uid = self.cr, self.uid
        self.wizard_period_close = self.registry('account.period.close')
        self.wizard_period_close_id = self.wizard_period_close.create(cr, uid, {'sure': 1})
        _, self.sale_journal_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "sales_journal")
        _, self.period_9_id = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "period_9")

    def test_period_state(self):
        cr, uid = self.cr, self.uid
        self.wizard_period_close.data_save(cr, uid, [self.wizard_period_close_id], {
            'lang': 'en_US',
            'active_model': 'account.period',
            'active_ids': [self.period_9_id],
            'tz': False,
            'active_id': self.period_9_id
        })
        with self.assertRaises(except_orm):
            self.registry('account.move').create(cr, uid, {
                'name': '/',
                'period_id': self.period_9_id,
                'journal_id': self.sale_journal_id,
                'date': date.today(),
                'line_id': [(0, 0, {
                        'name': 'foo',
                        'debit': 10,
                    }), (0, 0, {
                        'name': 'bar',
                        'credit': 10,
                    })]
            })
