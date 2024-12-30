from odoo import models, fields
from odoo.tests import common
from odoo.tools import mute_logger


class TestSparseFields(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class SparseFieldsTest(models.TransientModel):
            _name = 'sparse_fields.test'
            _description = 'Sparse fields Test'

            data = fields.Json()
            boolean = fields.Boolean(sparse='data')
            integer = fields.Integer(sparse='data')
            float = fields.Float(sparse='data')
            char = fields.Char(sparse='data')
            selection = fields.Selection([('one', 'One'), ('two', 'Two')], sparse='data')
            partner = fields.Many2one('res.partner', sparse='data')


        SparseFieldsTest._build_model(cls.registry, cls.env.cr)
        cls.registry.setup_models(cls.env.cr)
        cls.registry.init_models(cls.env.cr, [SparseFieldsTest._name], cls.env.context)

    @classmethod
    def tearDownClass(cls):
        with mute_logger('odoo.models.unlink'):
            del cls.env.registry['sparse_fields.test']
            cls.env.registry.reset_changes()

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

        for n, (key, _val) in enumerate(values):
            record.write({key: False})
            self.assertEqual(record.data or {}, dict(values[n+1:]))

        # check reflection of sparse fields in 'ir.model.fields'
        names = [name for name, _ in values]
        domain = [('model', '=', 'sparse_fields.test'), ('name', 'in', names)]
        fields = self.env['ir.model.fields'].search(domain)
        self.assertEqual(len(fields), len(names))
        for field in fields:
            self.assertEqual(field.serialization_field_id.name, 'data')
