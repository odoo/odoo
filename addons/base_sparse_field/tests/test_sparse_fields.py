# -*- coding: utf-8 -*-

from datetime import date, datetime

from odoo.tests import common


class TestSparseFields(common.TransactionCase):

    def test_sparse(self):
        """ test sparse fields. """
        record = self.env['sparse_fields.test'].create({})
        self.assertFalse(record.data)

        partner = self.env.ref('base.main_partner')
        values = [
            ('boolean', True),
            ('char', 'John'),
            ('date', date.today()),
            ('datetime', datetime.now().replace(microsecond=0)),
            ('float', 3.14),
            ('integer', 42),
            ('partner', partner),
            ('reference', partner),
            ('selection', 'two'),
        ]
        data = []
        for key, val in values:
            val = record._fields[key].convert_to_read(val, record, use_name_get=False)
            if key in ('date', 'datetime'):
                val = val.strftime('%Y-%m-%d %H:%M:%S')
            data.append((key, val))

        for n, (key, val) in enumerate(data):
            record.write({key: val})
            self.assertEqual(record.data, dict(data[:n+1]))

        for key, val in values:
            self.assertEqual(record[key], val)

        for n, (key, val) in enumerate(data):
            record.write({key: False})
            self.assertEqual(record.data, dict(data[n+1:]))

        # check reflection of sparse fields in 'ir.model.fields'
        names = [name for name, _ in values]
        domain = [('model', '=', 'sparse_fields.test'), ('name', 'in', names)]
        fields = self.env['ir.model.fields'].search(domain)
        self.assertEqual(len(fields), len(names))
        for field in fields:
            self.assertEqual(field.serialization_field_id.name, 'data')
