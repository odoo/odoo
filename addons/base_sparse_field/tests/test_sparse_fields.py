# -*- coding: utf-8 -*-

from odoo.tests import common


class TestSparseFields(common.TransactionCase):

    def test_sparse(self):
        """ test sparse fields. """
        record = self.env['sparse_fields.test'].create({})
        self.assertFalse(record.data)

        partner = self.env.ref('base.main_partner')
        values = [
            ('boolean', True),
            ('integer', 42),
            ('float', 3.14),
            ('char', 'John'),
            ('selection', 'two'),
            ('partner', partner.id),
        ]
        for n, (key, val) in enumerate(values):
            record.write({key: val})
            self.assertEqual(record.data, dict(values[:n+1]))

        for key, val in values[:-1]:
            self.assertEqual(record[key], val)
        self.assertEqual(record.partner, partner)

        for n, (key, val) in enumerate(values):
            record.write({key: False})
            self.assertEqual(record.data, dict(values[n+1:]))

        # check reflection of sparse fields in 'ir.model.fields'
        names = [name for name, _ in values]
        domain = [('model', '=', 'sparse_fields.test'), ('name', 'in', names)]
        fields = self.env['ir.model.fields'].search(domain)
        self.assertEqual(len(fields), len(names))
        for field in fields:
            self.assertEqual(field.serialization_field_id.name, 'data')
