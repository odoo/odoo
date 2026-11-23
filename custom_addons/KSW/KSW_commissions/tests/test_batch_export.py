"""Tests for ksw.commission.batch."""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
class TestCommissionBatch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        dept = env['hr.department'].create({'name': 'Batch Dept'})
        cls.emp = env['hr.employee'].sudo().create({
            'name': 'Batch Emp', 'department_id': dept.id,
            'x_is_attendance_sheet': True,
        })
        cats = env['ksw.commission.category'].search([('code', '=', 'other')])
        cls.cat = cats[:1]
        cls.period = '2026-05-01'
    def _done_sheet(self):
        sheet = self.env['ksw.commission.sheet'].sudo().create({
            'employee_id': self.emp.id,
            'period': self.period,
        })
        self.env['ksw.commission.sheet.line'].sudo().create({
            'sheet_id': sheet.id,
            'category_id': self.cat.id,
            'amount': 500.0,
        })
        sheet.action_confirm()
        sheet.sudo().action_done()
        return sheet
    def _batch(self, sheets=None):
        b = self.env['ksw.commission.batch'].sudo().create({
            'name': 'Test Batch',
            'period': self.period,
        })
        if sheets:
            b.write({'sheet_ids': [(4, s.id) for s in sheets]})
        return b
    def test_01_batch_created_in_draft(self):
        b = self._batch()
        self.assertEqual(b.state, 'draft')
    def test_02_sheet_count(self):
        s = self._done_sheet()
        b = self._batch([s])
        self.assertEqual(b.sheet_count, 1)
    def test_03_total_payable_computed(self):
        s = self._done_sheet()
        b = self._batch([s])
        self.assertAlmostEqual(b.total_payable, 500.0)
    def test_04_close_requires_done_sheets(self):
        """Batch with a non-done sheet cannot be closed."""
        sheet = self.env['ksw.commission.sheet'].sudo().create({
            'employee_id': self.emp.id,
            'period': '2026-07-01',
        })
        # sheet is still draft
        b = self._batch()
        b.write({'sheet_ids': [(4, sheet.id)]})
        with self.assertRaises(UserError):
            b.action_close()
    def test_05_close_succeeds_all_done(self):
        s = self._done_sheet()
        b = self._batch([s])
        b.action_close()
        self.assertEqual(b.state, 'closed')
    def test_06_reset_to_draft(self):
        s = self._done_sheet()
        b = self._batch([s])
        b.action_close()
        b.action_reset_to_draft()
        self.assertEqual(b.state, 'draft')
    def test_07_sequence_assigned_on_create(self):
        b = self._batch()
        self.assertFalse(b.name == 'New')
    def test_08_group_by_bank_no_bank_bucket(self):
        """Employee without bank → sheet goes into empty-bank bucket."""
        s = self._done_sheet()
        b = self._batch([s])
        groups = b._group_sheets_by_bank_account()
        no_bank = self.env['res.partner.bank']
        self.assertIn(no_bank, groups)
    def test_09_period_normalised_to_first(self):
        b = self.env['ksw.commission.batch'].sudo().create({
            'period': '2026-05-20',
        })
        self.assertEqual(b.period.day, 1)
