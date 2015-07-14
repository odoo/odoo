import unittest2

import openerp.tests.common as common


class Test_ir_sequence(common.TransactionCase):

    def test_00(self):
        registry, cr, uid = self.registry, self.cr, self.uid

        # test if read statement return the good number_next value (from postgreSQL sequence and not ir_sequence value)
        sequence = registry('ir.sequence')
        # first creation of sequence (normal)
        values = {'number_next': 1,
                  'company_id': 1,
                  'padding': 4,
                  'number_increment': 1,
                  'implementation': 'standard',
                  'name': 'test-sequence-00'}
        seq_id = sequence.create(cr, uid, values)
        # Call get next 4 times
        sequence.next_by_id(cr, uid, seq_id)
        sequence.next_by_id(cr, uid, seq_id)
        sequence.next_by_id(cr, uid, seq_id)
        read_sequence = sequence.next_by_id(cr, uid, seq_id)
        # Read the value of the current sequence
        assert read_sequence == "0004", 'The actual sequence value must be 4. reading : %s' % read_sequence
        # reset sequence to 1 by write method calling
        sequence.write(cr, uid, [seq_id], {'number_next': 1})
        # Read the value of the current sequence
        read_sequence = sequence.next_by_id(cr, uid, seq_id)
        assert read_sequence == "0001", 'The actual sequence value must be 1. reading : %s' % read_sequence

if __name__ == "__main__":
    unittest2.main()
