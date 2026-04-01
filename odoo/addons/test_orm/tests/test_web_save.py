from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.test_mimetypes import JPG, SVG


class TestWebSave(TransactionCase):

    def test_web_save_create(self):
        ''' Test the web_save method on a new record. '''
        # Create a new record, without unity specification (it should return only the id)
        self.env['test_orm.person'].search([]).unlink()
        result = self.env['test_orm.person'].web_save({'name': 'ged'}, {})
        person = self.env['test_orm.person'].search([])
        self.assertTrue(person.exists())
        self.assertEqual(person.name, 'ged')
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'id': person.id}])

        # Create a new record, with unity specification
        result = self.env['test_orm.person'].web_save({'name': 'ged'}, {'display_name': {}})
        person = self.env['test_orm.person'].browse(result[0]['id'])
        self.assertTrue(person.exists())
        self.assertEqual(result, [{'id': person.id, 'display_name': 'ged'}])

    def test_web_save_write(self):
        ''' Test the web_save method on an existing record. '''

        person = self.env['test_orm.person'].create({'name': 'ged'})

        # Modify an existing record, without unity specification (it should return only the id)
        result = person.web_save({'name': 'aab'}, {})
        self.assertEqual(person.name, 'aab')
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [{'id': person.id}])

        # Modify an existing record, with unity specification
        result = person.web_save({'name': 'lpe'}, {'display_name': {}})
        self.assertEqual(result, [{'id': person.id, 'display_name': 'lpe'}])

    def test_web_save_computed_stored_binary(self):
        [result] = self.env['test_orm.binary_svg'].web_save(
            {'name': 'test', 'image_wo_attachment': SVG},
            {'image_wo_attachment': {}, 'image_wo_attachment_related': {}},
        )
        self.assertEqual(result['image_wo_attachment'], '400 bytes')  # From PostgreSQL
        self.assertEqual(result['image_wo_attachment_related'], b'400.00 bytes')  # From human_size

        # check cache values
        record = self.env['test_orm.binary_svg'].browse(result['id'])
        self.assertEqual(record.image_wo_attachment, SVG)
        self.assertEqual(record.image_wo_attachment, record.image_wo_attachment_related)

        # check database values
        self.env.invalidate_all()
        self.assertEqual(record.image_wo_attachment, SVG)
        self.assertEqual(record.image_wo_attachment, record.image_wo_attachment_related)

        # check web_save() on existing record
        self.env.invalidate_all()
        [result] = record.web_save(
            {'image_wo_attachment': JPG},
            {'image_wo_attachment': {}, 'image_wo_attachment_related': {}},
        )
        self.assertEqual(result['image_wo_attachment'], '727 bytes')  # From PostgreSQL
        self.assertEqual(result['image_wo_attachment_related'], b'727.00 bytes')  # From human_size

        # check cache values
        self.assertEqual(record.image_wo_attachment, JPG.encode())
        self.assertEqual(record.image_wo_attachment, record.image_wo_attachment_related)

        # check database values
        self.env.invalidate_all()
        self.assertEqual(record.image_wo_attachment, JPG.encode())
        self.assertEqual(record.image_wo_attachment, record.image_wo_attachment_related)

    def test_web_save_multi(self):
        Model = self.env['test_orm.mixed']
        records = Model.create([
            {'foo': 'Record 1', 'count': 100, 'number': 2.5},
            {'foo': 'Record 2', 'count': 200, 'number': 3.5},
        ])

        vals = [
            {"foo": "Updated 1", "count": 150, "number": 1.1},
            {"count": 250, "number": 1.1},
        ]
        specification = {
            "foo": {},
            "count": {},
        }
        result = records.web_save_multi(vals, specification)

        self.assertEqual(result, [
            {'id': records[0].id, 'foo': 'Updated 1', 'count': 150},
            {'id': records[1].id, 'foo': 'Record 2', 'count': 250},
        ])
