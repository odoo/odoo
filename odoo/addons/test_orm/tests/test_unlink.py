from odoo.exceptions import MissingError
from odoo.fields import Command
from odoo.tests import TransactionCase
from odoo.tools import mute_logger


class TestUnlink(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Container = cls.env['test_orm.unlink']
        cls.NullLine = cls.env['test_orm.unlink.null.line']
        cls.CascadeLine = cls.env['test_orm.unlink.cascade.line']
        cls.ModelData = cls.env['ir.model.data']

        cls.container = cls.Container.create({})

    @mute_logger("odoo.models.unlink")
    def test_unlink_set_null_modified(self):
        null_line = self.NullLine.create({'container_id': self.container.id})

        self.assertEqual(null_line.has_container, True)
        self.container.unlink()
        self.assertEqual(null_line.has_container, False)

    @mute_logger("odoo.models.unlink")
    def test_unlink_cascade_modified(self):
        cascade_line = self.CascadeLine.create({'container_id': self.container.id})
        child_cascade_line = self.CascadeLine.create({'parent_id': cascade_line.id})

        self.assertEqual(child_cascade_line.has_parent, True)
        self.container.unlink()

        self.assertFalse(cascade_line.exists())
        self.assertEqual(child_cascade_line.has_parent, False)
        with self.assertRaises(MissingError):
            cascade_line.container_id

    @mute_logger("odoo.models.unlink")
    def test_unlink_parent_path(self):
        cascade_line = self.CascadeLine.create({'container_id': self.container.id})
        child_cascade_line = self.CascadeLine.create({'parent_id': cascade_line.id})

        self.assertEqual(child_cascade_line.parent_path, f'{cascade_line.id}/{child_cascade_line.id}/')
        self.assertEqual(cascade_line.parent_path, f'{cascade_line.id}/')

        self.container.unlink()

        self.assertEqual(child_cascade_line.parent_path, f'{child_cascade_line.id}/')

    @mute_logger("odoo.models.unlink")
    def test_unlink_cascade_model_data(self):
        cascade_line = self.CascadeLine.create({'container_id': self.container.id})

        model_data = self.ModelData.create({
            'name': 'test_unlink_cascade_model_data',
            'module': 'test_orm',
            'model': cascade_line._name,
            'res_id': cascade_line.id,
        })
        ref_name = model_data.complete_name

        self.assertEqual(self.ModelData._xmlid_to_res_id(ref_name), cascade_line.id)

        self.container.unlink()

        self.assertFalse(self.ModelData._xmlid_to_res_id(ref_name, raise_if_not_found=False))

    @mute_logger("odoo.models.unlink")
    def test_unlink_inverse_inside(self):
        # See https://github.com/odoo/odoo/pull/229604
        containers = self.Container.create([
            {'cascade_line_ids': [Command.create({})]},
            {'cascade_line_ids': [Command.create({})]},
        ])

        self.assertEqual(len(containers[0].cascade_line_ids), 1)
        self.assertEqual(len(containers[1].cascade_line_ids), 1)

        containers.user_command = 'remove lines'

        self.assertEqual(len(containers[0].cascade_line_ids), 0)
        self.assertEqual(len(containers[1].cascade_line_ids), 0, "The unlink inside the inverse shouldn't invalidate the inverse value of the second record")

    @mute_logger("odoo.models.unlink")
    def test_unlink_simple_graph_1(self):
        # container <==== cascade_line <---- child_cascade_line
        container = self.Container.create({
            'cascade_line_ids': [
                Command.create({
                    'childs_ids': [Command.create({})],
                }),
            ],
        })

        child_cascade_line = container.cascade_line_ids.childs_ids

        self.assertEqual(child_cascade_line.has_parent, True)
        cascade_line_ids = container.cascade_line_ids

        container.unlink()

        self.assertFalse(container.exists(), False)
        self.assertFalse(cascade_line_ids.exists(), False)

        self.assertFalse(child_cascade_line.parent_id)
        self.assertEqual(child_cascade_line.has_parent, False)
        self.assertEqual(child_cascade_line.parent_path, f'{child_cascade_line.id}/')

    @mute_logger("odoo.models.unlink")
    def test_unlink_simple_graph_2(self):
        # container <== cascade_line <---- child_cascade_line
        #        ^                              ║
        #        ╚==============================╝
        container = self.Container.create({
            'cascade_line_ids': [
                Command.create({}),
                Command.create({}),
            ],
        })
        child_cascade_line = container.cascade_line_ids[1]
        child_cascade_line.parent_id = container.cascade_line_ids[0]

        self.assertEqual(child_cascade_line.has_parent, True)
        cascade_line_ids = container.cascade_line_ids

        container.unlink()
        self.assertFalse(container.exists(), False)
        self.assertFalse(cascade_line_ids.exists(), False)
        self.assertFalse(child_cascade_line.exists(), False)

        with self.assertRaises(MissingError):
            child_cascade_line.parent_id

    @mute_logger("odoo.models.unlink")
    def test_unlink_simple_graph_3(self):
        #        ╔========== cascade_line_1
        #        v
        # container <======= cascade_line_2
        #     ^  ^              ^
        #     |  |              ┃    <override _delete_collect_extra>
        #     |  └---------- null_line_1
        #     |
        #     └------------- null_line_2

        container = self.Container.create({
            'cascade_line_ids': [
                Command.create({}),
                Command.create({}),
            ],
            'null_line_ids': [
                Command.create({}),
                Command.create({}),
            ],
        })
        # null_line_ids should be deleted too
        container.cascade_line_ids[0].hard_sibling_id = container.null_line_ids[0]
        cascade_line_ids = container.cascade_line_ids
        null_line_ids = container.null_line_ids

        container.unlink()
        self.assertFalse(container.exists(), False)
        self.assertFalse(cascade_line_ids.exists(), False)
        self.assertFalse(null_line_ids[0].exists(), False)
        with self.assertRaises(MissingError):
            null_line_ids[0].container_id

        self.assertTrue(null_line_ids[1].exists())
        self.assertFalse(null_line_ids[1].container_id)

    @mute_logger("odoo.models.unlink")
    def test_unlink_performance(self):
        container = self.Container.create(
            [
                {
                    'cascade_line_ids': [
                        Command.create({}),
                        Command.create({}),
                    ],
                    'null_line_ids': [
                        Command.create({}),
                        Command.create({}),
                    ],
                }
                for __ in range(50)
            ],
        )
        self.env.flush_all()

        # 3 +3 queries : search ir data / ir attachment / ir default for cascade_line_ids + unlink
        # 1 Query for delete
        # 1 query to update has_container of null_line_ids
        with self.assertQueryCount(8):
            container.unlink()
