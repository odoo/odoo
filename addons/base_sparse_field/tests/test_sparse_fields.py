# -*- coding: utf-8 -*-

from datetime import date, datetime

from odoo import fields, models

from odoo.tests import common


class TestSparseFields(common.TransactionCase):

    def test_sparse(self):
        """ test sparse fields. """

        class TestSparse(models.TransientModel):
            _name = 'sparse_fields.test'
            _description = 'Sparse fields Test'

            data = fields.Serialized()
            boolean = fields.Boolean(sparse='data')
            char = fields.Char(sparse='data')
            date = fields.Date(sparse='data')
            datetime = fields.Datetime(sparse='data')
            float = fields.Float(sparse='data')
            integer = fields.Integer(sparse='data')
            partner = fields.Many2one('res.partner', sparse='data')
            reference = fields.Reference(
                sparse='data',
                selection=lambda self: [(model.model, model.name) for model in self.env['ir.model'].search([])],
            )
            selection = fields.Selection([('one', 'One'), ('two', 'Two')], sparse='data')

        self.registry.models['sparse_fields.test'] = TestSparse._build_model(
            self.registry, self.cr
        )
        self.registry.setup_models(self.cr)
        self.registry.init_models(
            self.cr, ['sparse_fields.test'], {"module": "test"}, install=True
        )

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
        model_fields = self.env['ir.model.fields'].search(domain)
        self.assertEqual(len(model_fields), len(names))
        for field in model_fields:
            self.assertEqual(field.serialization_field_id.name, 'data')

        self.registry.reset_changes()
