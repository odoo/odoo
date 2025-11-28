
from odoo.exceptions import MissingError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('at_install', '-post_install')
class TestUnlink(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Container = cls.env['test_orm.unlink']
        cls.Null = cls.env['test_orm.unlink.null']
        cls.Cascade = cls.env['test_orm.unlink.cascade']

        cls.container = cls.Container.create({})

    @mute_logger("odoo.models.unlink")
    def test_unlink_set_null_modified(self):
        null_line = self.Null.create({'container_id': self.container.id})
        self.assertEqual(null_line.has_container, True)

        self.container.unlink()
        self.assertEqual(null_line.has_container, True)  # should be False

    @mute_logger("odoo.models.unlink")
    def test_unlink_cascade_modified(self):
        cascade = self.Cascade.create({'container_id': self.container.id})
        child = self.Cascade.create({'parent_id': cascade.id})
        self.assertEqual(child.has_parent, True)

        self.container.unlink()

        self.assertFalse(cascade.exists())
        self.assertEqual(child.has_parent, True)  # should be False
        with self.assertRaises(MissingError):
            cascade.container_id

    @mute_logger("odoo.models.unlink")
    def test_unlink_parent_path(self):
        cascade = self.Cascade.create({'container_id': self.container.id})
        child = self.Cascade.create({'parent_id': cascade.id})

        self.assertEqual(cascade.parent_path, f'{cascade.id}/')
        self.assertEqual(child.parent_path, f'{cascade.id}/{child.id}/')

        self.container.unlink()

        # should be f'{child.id}/'
        self.assertEqual(child.parent_path, f'{cascade.id}/{child.id}/')

    @mute_logger("odoo.models.unlink")
    def test_unlink_cascade_model_data(self):
        ModelData = self.env['ir.model.data']

        cascade = self.Cascade.create({'container_id': self.container.id})
        ref_name = 'test_orm.test_unlink_cascade_model_data'
        ModelData.create({
            'module': 'test_orm',
            'name': 'test_unlink_cascade_model_data',
            'model': cascade._name,
            'res_id': cascade.id,
        })

        self.assertEqual(ModelData._xmlid_to_res_id(ref_name), cascade.id)

        self.container.unlink()

        # should be False
        self.assertTrue(ModelData._xmlid_to_res_id(ref_name, raise_if_not_found=False))

    def test_unlink_inverse_inside(self):
        # See https://github.com/odoo/odoo/pull/229604
        containers = self.Container.create([
            {'cascade_ids': [Command.create({})]},
            {'cascade_ids': [Command.create({})]},
        ])

        self.assertEqual(len(containers[0].cascade_ids), 1)
        self.assertEqual(len(containers[1].cascade_ids), 1)

        containers.user_command = 'remove lines'

        self.assertEqual(len(containers[0].cascade_ids), 0)
        # should be 0, the issue is because of invalidation between records
        self.assertEqual(len(containers[1].cascade_ids), 1)
