from odoo.tests import common


class TestUnlinkRecord(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Container = cls.env['test_new_api.unlink.container']
        cls.Line = cls.env['test_new_api.unlink.line']

    def test_unlink_lot_of_records_with_translate_related(self):
        nb_line_to_create = self.env.cr.IN_MAX + 1
        container = self.Container.create({'name': 'C'})
        lines = self.Line.create([
            {'container_id': container.id} for __ in range(nb_line_to_create)
        ])

        self.assertEqual(lines.mapped('container_name'), ['C'] * nb_line_to_create)

        lines.unlink()
