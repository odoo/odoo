import unittest

from openerp.tests import common
from datetime import date


class test_ir_sequence_date_range_standard(common.SingleTransactionCase):
    """ A few tests for a 'Standard' (i.e. PostgreSQL) sequence. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object with date ranges enabled. """
        d = dict(code='test_sequence_date_range', name='Test sequence', use_date_range=True)
        c = self.registry('ir.sequence').create(self.cr, self.uid, d, {})
        assert c

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Draw numbers to create a first subsequence then change its date range. Then, try to draw a new number adn check a new subsequence was correctly created. """
        year = str(int(date.today().strftime("%Y")) - 1)
        dt = "{}-01-16".format(year)
        n = self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range', {'ir_sequence_date': dt})
        self.assertEqual(n, '1')
        n = self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range', {'ir_sequence_date': dt})
        self.assertEqual(n, '2')
        # modify the range of date created
        domain = [('sequence_id.code', '=', 'test_sequence_date_range'), ('date_from', '=', '{}-01-01'.format(year))]
        seq_date_range_id = self.registry('ir.sequence.date_range').search(self.cr, self.uid, domain, {})
        self.registry('ir.sequence.date_range').write(self.cr, self.uid, seq_date_range_id, {'date_from': '{}-01-18'.format(year)}, {})
        n = self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range', {'ir_sequence_date': dt})
        self.assertEqual(n, '1')
        # check the newly created sequence stops at the 17th of January
        domain = [('sequence_id.code', '=', 'test_sequence_date_range'), ('date_from', '=', '{}-01-01'.format(year))]
        seq_date_range_id = self.registry('ir.sequence.date_range').search(self.cr, self.uid, domain, {})
        seq_date_range = self.registry('ir.sequence.date_range').browse(self.cr, self.uid, seq_date_range_id[0])
        self.assertEqual(seq_date_range.date_to, '{}-01-17'.format(year))

    def test_ir_sequence_date_range_3_unlink(self):
        ids = self.registry('ir.sequence').search(self.cr, self.uid, [('code', '=', 'test_sequence_date_range')])
        self.registry('ir.sequence').unlink(self.cr, self.uid, ids)


class test_ir_sequence_date_range_no_gap(common.SingleTransactionCase):
    """ Copy of the previous tests for a 'No gap' sequence. """

    def test_ir_sequence_date_range_1_create_no_gap(self):
        """ Try to create a sequence object. """
        d = dict(code='test_sequence_date_range_2', name='Test sequence',
                 implementation='no_gap', use_date_range=True)
        c = self.registry('ir.sequence').create(self.cr, self.uid, d, {})
        assert c

    def test_ir_sequence_date_range_2_change_dates(self):
        """ Draw numbers to create a first subsequence then change its date range. Then, try to draw a new number adn check a new subsequence was correctly created. """
        year = str(int(date.today().strftime("%Y")) - 1)
        dt = "{}-01-16".format(year)
        n = self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range_2', {'ir_sequence_date': dt})
        self.assertEqual(n, '1')
        n = self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range_2', {'ir_sequence_date': dt})
        self.assertEqual(n, '2')
        # modify the range of date created
        domain = [('sequence_id.code', '=', 'test_sequence_date_range_2'), ('date_from', '=', '{}-01-01'.format(year))]
        seq_date_range_id = self.registry('ir.sequence.date_range').search(self.cr, self.uid, domain, {})
        self.registry('ir.sequence.date_range').write(self.cr, self.uid, seq_date_range_id, {'date_from': '{}-01-18'.format(year)}, {})
        n = self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range_2', {'ir_sequence_date': dt})
        self.assertEqual(n, '1')
        # check the newly created sequence stops at the 17th of January
        domain = [('sequence_id.code', '=', 'test_sequence_date_range_2'), ('date_from', '=', '{}-01-01'.format(year))]
        seq_date_range_id = self.registry('ir.sequence.date_range').search(self.cr, self.uid, domain, {})
        seq_date_range = self.registry('ir.sequence.date_range').browse(self.cr, self.uid, seq_date_range_id[0])
        self.assertEqual(seq_date_range.date_to, '{}-01-17'.format(year))

    def test_ir_sequence_date_range_3_unlink(self):
        ids = self.registry('ir.sequence').search(self.cr, self.uid, [('code', '=', 'test_sequence_date_range_2')])
        self.registry('ir.sequence').unlink(self.cr, self.uid, ids)


class test_ir_sequence_date_range_change_implementation(common.SingleTransactionCase):
    """ Create sequence objects and change their ``implementation`` field. """

    def test_ir_sequence_date_range_1_create(self):
        """ Try to create a sequence object. """
        d = dict(code='test_sequence_date_range_3', name='Test sequence', use_date_range=True)
        c = self.registry('ir.sequence').create(self.cr, self.uid, d, {})
        assert c
        d = {
            'code': 'test_sequence_date_range_4',
            'name': 'Test sequence',
            'implementation': 'no_gap',
            'use_date_range': True
        }
        c = self.registry('ir.sequence').create(self.cr, self.uid, d, {})
        assert c

    def test_ir_sequence_date_range_2_use(self):
        """ Make some use of the sequences to create some subsequences """
        year = str(int(date.today().strftime("%Y")) - 1)
        dt = "{}-01-16".format(year)
        f = lambda *a: self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range_3', {})
        assert all(str(x) == f() for x in xrange(1, 5))
        f = lambda *a: self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range_3', {'ir_sequence_date': dt})
        assert all(str(x) == f() for x in xrange(1, 5))
        f = lambda *a: self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range_4', {})
        assert all(str(x) == f() for x in xrange(1, 5))
        f = lambda *a: self.registry('ir.sequence').next_by_code(self.cr, self.uid, 'test_sequence_date_range_4', {'ir_sequence_date': dt})
        assert all(str(x) == f() for x in xrange(1, 5))

    def test_ir_sequence_date_range_3_write(self):
        """swap the implementation method on both"""
        ids = self.registry('ir.sequence').search(self.cr, self.uid, [
            ('code', 'in', ['test_sequence_date_range_3', 'test_sequence_date_range_4'])
        ], {})
        self.registry('ir.sequence').write(self.cr, self.uid, ids, {'implementation': 'standard'})
        self.registry('ir.sequence').write(self.cr, self.uid, ids, {'implementation': 'no_gap'})

    def test_ir_sequence_date_range_4_unlink(self):
        ids = self.registry('ir.sequence').search(self.cr, self.uid, [
            ('code', 'in', ['test_sequence_date_range_3', 'test_sequence_date_range_4'])
        ], {})
        self.registry('ir.sequence').unlink(self.cr, self.uid, ids, {})


if __name__ == '__main__':
    unittest.main()
