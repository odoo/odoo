# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestIrSequenceConstraints(TransactionCase):

    def setUp(self):
        super(TestIrSequenceConstraints, self).setUp()
        self.journal = self.env['account.journal']

    def test_validate_sequence_of_journals(self):

        # Create a journal with restrict_mode_hash_table=True
        journal = self.journal.create({
            'name' : 'Test Sequence Journal',
            'code' : 'tsj',
            'type' : 'sale',
            'restrict_mode_hash_table' : True
        })

        sequence = journal.secure_sequence_id

        # Update a sequence with a numeric prefix and suffix
        sequence.write({'prefix' : '123', 'suffix' : '456'})

        # Update a sequence with non-numeric prefix and numeric suffix
        with self.assertRaises(ValidationError):
            sequence.write({'prefix': 'test', 'suffix': '111'})

        # Update a sequence with numeric prefix and non-numeric suffix
        with self.assertRaises(ValidationError):
            sequence.write({'prefix' : '111', 'suffix' : 'Abc'})

        # Update a sequence with non-numeric prefix
        with self.assertRaises(ValidationError):
            sequence.write({'prefix' : 'test'})

        # Update a sequence with non-numeric suffix
        with self.assertRaises(ValidationError):
            sequence.write({'suffix' : 'Test'})

        sequence.write({'prefix' : '001'})

        # Make sure the sequence is updated sucessfully
        self.assertEqual(sequence.prefix, '001')
        self.assertEqual(sequence.suffix, '456')
