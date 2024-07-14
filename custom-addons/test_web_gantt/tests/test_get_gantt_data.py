from odoo.tests.common import TransactionCase


class TestUnityWebReadGroupGantt(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pill_1, cls.pill_2 = cls.env['test.web.gantt.pill'].create([
            {'name': 'PillParent1'},
            {'name': 'PillParent2'},
        ])
        cls.dependency_pills = cls.env['test.web.gantt.pill'].create([
            {'name': 'Tag 1'},
            {'name': 'Tag 2'},
            {'name': 'Tag 3'},
            {'name': 'Tag 4'},
        ])
        cls.pills = cls.env['test.web.gantt.pill'].create([
            {'name': 'one', 'parent_id': cls.pill_1.id, 'dependency_field': cls.dependency_pills[0]},
            {'name': 'two', 'parent_id': cls.pill_2.id, 'dependency_field': cls.dependency_pills[:2]},
            {'name': 'there', 'parent_id': cls.pill_2.id},
            {'name': 'four', 'parent_id': cls.pill_2.id},
            {'name': 'four', 'parent_id': cls.pill_2.id, 'dependency_field': cls.dependency_pills[1:3]},
            {'name': 'six', 'parent_id': cls.pill_1.id, 'dependency_field': cls.dependency_pills[:3]},
        ])

    # Test (limit/offset of group) * (groupby 0/1/2) * (groupby many2one/many2many/char) (no limit by groups)

    def test_get_gantt_data_without_limit(self):
        self.env.invalidate_all()
        with self.assertQueryCount(2):  # One for read_group + One for reading name to compute display_name
            result = self.env['test.web.gantt.pill'].get_gantt_data(
                [('id', 'in', self.pills.ids)], [], {'display_name': {}},
            )
            self.assertEqual(result, {
                'groups': [{'__record_ids': self.pills.ids}],
                'records': [
                    {'id': self.pills[0].id, 'display_name': 'one'},
                    {'id': self.pills[1].id, 'display_name': 'two'},
                    {'id': self.pills[2].id, 'display_name': 'there'},
                    {'id': self.pills[3].id, 'display_name': 'four'},
                    {'id': self.pills[4].id, 'display_name': 'four'},
                    {'id': self.pills[5].id, 'display_name': 'six'},
                ],
                'length': 1,
            })

        self.env.invalidate_all()
        # 1 SQL for read_group + 1 SQL for reading name of groups + 1 SQL reading records
        with self.assertQueryCount(3):
            result = self.env['test.web.gantt.pill'].get_gantt_data(
                [('id', 'in', self.pills.ids)], ['dependency_field'], {'display_name': {}},
            )
            self.assertEqual(result, {
                'groups': [
                    {
                        'dependency_field': (self.dependency_pills[0].id, 'Tag 1'),
                        '__record_ids': [
                            self.pills[0].id,
                            self.pills[1].id,
                            self.pills[5].id,
                        ],
                    },
                    {
                        'dependency_field': (self.dependency_pills[1].id, 'Tag 2'),
                        '__record_ids': [
                            self.pills[1].id,
                            self.pills[4].id,
                            self.pills[5].id,
                        ],
                    },
                    {
                        'dependency_field': (self.dependency_pills[2].id, 'Tag 3'),
                        '__record_ids': [
                            self.pills[4].id,
                            self.pills[5].id,
                        ],
                    },
                    {
                        'dependency_field': False,
                        '__record_ids': [
                            self.pills[2].id,
                            self.pills[3].id,
                        ],
                    },
                ],
                'records': [
                    {'id': self.pills[0].id, 'display_name': 'one'},
                    {'id': self.pills[1].id, 'display_name': 'two'},
                    {'id': self.pills[2].id, 'display_name': 'there'},
                    {'id': self.pills[3].id, 'display_name': 'four'},
                    {'id': self.pills[4].id, 'display_name': 'four'},
                    {'id': self.pills[5].id, 'display_name': 'six'},
                ],
                'length': 4,
            })

    def test_get_gantt_data_with_limit(self):
        self.env.invalidate_all()
        # 1 SQL for read_group + 1 SQL to count the number of group (because limit isn't reached)
        # + 1 SQL for reading name of parent_id + 1 SQL reading records
        with self.assertQueryCount(4):  # One for read_group + One for reading name (+order)
            result = self.env['test.web.gantt.pill'].get_gantt_data(
                [('id', 'in', self.pills.ids)], ['parent_id', 'name'], {'display_name': {}}, limit=2
            )
            self.assertEqual(result, {
                'groups': [
                    {
                        'parent_id': (self.pill_1.id, 'PillParent1'),
                        'name': 'one',
                        '__record_ids': [self.pills[0].id],
                    },
                    {
                        'parent_id': (self.pill_1.id, 'PillParent1'),
                        'name': 'six',
                        '__record_ids': [self.pills[5].id],
                    },
                ],
                'records': [
                    {'id': self.pills[0].id, 'display_name': 'one'},
                    {'id': self.pills[5].id, 'display_name': 'six'},
                ],
                'length': 5,
            })

        self.env.invalidate_all()
        # 1 SQL for read_group + 1 SQL to count the number of group (because limit isn't reached)
        # + 1 SQL for reading name of parent_id + 1 SQL reading records
        with self.assertQueryCount(4):
            result = self.env['test.web.gantt.pill'].get_gantt_data(
                [('id', 'in', self.pills.ids)], ['parent_id', 'name'], {'display_name': {}}, limit=2, offset=1,
            )
            self.assertEqual(result, {
                'groups': [
                    {
                        'parent_id': (self.pill_1.id, 'PillParent1'),
                        'name': 'six',
                        '__record_ids': [self.pills[5].id],
                    },
                    {
                        'parent_id': (self.pill_2.id, 'PillParent2'),
                        'name': 'four',
                        '__record_ids': [self.pills[3].id, self.pills[4].id],
                    },
                ],
                'records': [
                    {'id': self.pills[3].id, 'display_name': 'four'},
                    {'id': self.pills[4].id, 'display_name': 'four'},
                    {'id': self.pills[5].id, 'display_name': 'six'},
                ],
                'length': 5,
            })
