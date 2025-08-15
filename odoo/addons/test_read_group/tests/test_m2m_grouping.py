""" Test read_group grouping with many2many fields """


from odoo.fields import Command
from odoo.tests import common
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@common.tagged('test_m2m_read_group')
class TestM2MGrouping(TransactionCaseWithUserDemo):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = cls.env['test_read_group.user'].create([
            {'name': 'Mario'},
            {'name': 'Luigi'},
        ])
        cls.tasks = cls.env['test_read_group.task'].create([
            {   # both users
                'name': "Super Mario Bros.",
                'user_ids': [Command.set(cls.users.ids)],
            },
            {   # mario only
                'name': "Paper Mario",
                'user_ids': [Command.set(cls.users[0].ids)],
            },
            {   # luigi only
                'name': "Luigi's Mansion",
                'user_ids': [Command.set(cls.users[1].ids)],
            },
            {   # no user
                'name': 'Donkey Kong',
                'user_ids': [Command.set([])],
            },
        ])

    def test_base_users(self):
        # group users
        user_by_tasks = self.users.read_group(
            domain=[],
            fields=['name:array_agg'],
            groupby=['task_ids'],
        )
        self.assertEqual(user_by_tasks, [
            {   # first task: both users
                'task_ids': (self.tasks[0].id, "Super Mario Bros."),
                'task_ids_count': 2,
                'name': ['Mario', 'Luigi'],
                '__domain': [('task_ids', '=', self.tasks[0].id)],
            },
            {   # second task: Mario only
                'task_ids': (self.tasks[1].id, "Paper Mario"),
                'task_ids_count': 1,
                'name': ['Mario'],
                '__domain': [('task_ids', '=', self.tasks[1].id)],
            },
            {   # third task: Luigi only
                'task_ids': (self.tasks[2].id, "Luigi's Mansion"),
                'task_ids_count': 1,
                'name': ['Luigi'],
                '__domain': [('task_ids', '=', self.tasks[2].id)],
            },
        ])

    def test_base_tasks(self):
        # consider the simplest case first: one task with two users
        task_by_users = self.tasks.read_group(
            domain=[('id', '=', self.tasks[0].id)],
            fields=['name:array_agg'],
            groupby=['user_ids'],
        )
        self.assertEqual(task_by_users, [
            {   # task of Mario
                'user_ids': (self.users[0].id, "Mario"),
                'user_ids_count': 1,
                'name': ["Super Mario Bros."],
                '__domain': ['&', ('id', '=', self.tasks[0].id), ('user_ids', '=', self.users[0].id)],
            },
            {   # task of Luigi
                'user_ids': (self.users[1].id, "Luigi"),
                'user_ids_count': 1,
                'name': ["Super Mario Bros."],
                '__domain': ['&', ('id', '=', self.tasks[0].id), ('user_ids', '=', self.users[1].id)],
            },
        ])

        # now consider the full case: all tasks, with all user combinations
        task_by_users = self.tasks.read_group(
            domain=[],
            fields=['name:array_agg'],
            groupby=['user_ids'],
        )
        self.assertEqual(task_by_users, [
            {   # tasks of Mario
                'user_ids': (self.users[0].id, "Mario"),
                'user_ids_count': 2,
                'name': unordered(["Super Mario Bros.", "Paper Mario"]),
                '__domain': [('user_ids', '=', self.users[0].id)],
            },
            {   # tasks of Luigi
                'user_ids': (self.users[1].id, "Luigi"),
                'user_ids_count': 2,
                'name': unordered(["Super Mario Bros.", "Luigi's Mansion"]),
                '__domain': [('user_ids', '=', self.users[1].id)],
            },
            {   # tasks of nobody
                'user_ids': False,
                'user_ids_count': 1,
                'name': unordered(["Donkey Kong"]),
                '__domain': [('user_ids', 'not any', [(1, '=', 1)])],
            },
        ])

        # check that the domain returned by read_group is valid
        tasks_from_domain = self.tasks.search(task_by_users[0]['__domain'])
        self.assertEqual(tasks_from_domain, self.tasks[:2])

        tasks_from_domain = self.tasks.search(task_by_users[1]['__domain'])
        self.assertEqual(tasks_from_domain, self.tasks[0] + self.tasks[2])

        tasks_from_domain = self.tasks.search(task_by_users[2]['__domain'])
        self.assertEqual(tasks_from_domain, self.tasks[3])

    def test_complex_case(self):
        # group tasks with some ir.rule on users
        users_model = self.env['ir.model']._get(self.users._name)
        self.env['ir.rule'].create({
            'name': "Only The Lone Wanderer allowed",
            'model_id': users_model.id,
            'domain_force': [('id', '=', self.users[0].id)],
        })

        # warmup
        as_admin = self.tasks.read_group(
            domain=[],
            fields=['name:array_agg'],
            groupby=['user_ids'],
        )

        # as superuser, ir.rule should not apply
        expected = """
            SELECT
                "test_read_group_task__user_ids"."user_id",
                COUNT(*),
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids" ON ("test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id")
            GROUP BY "test_read_group_task__user_ids"."user_id"
            ORDER BY "test_read_group_task__user_ids"."user_id" ASC
        """
        with self.assertQueries([expected]):
            as_admin = self.tasks.read_group(
                domain=[],
                fields=['name:array_agg'],
                groupby=['user_ids'],
            )
        self.assertEqual(as_admin, [
            {   # tasks of Mario
                'user_ids': (self.users[0].id, "Mario"),
                'user_ids_count': 2,
                'name': unordered(["Super Mario Bros.", "Paper Mario"]),
                '__domain': [('user_ids', '=', self.users[0].id)],
            },
            {   # tasks of Luigi
                'user_ids': (self.users[1].id, "Luigi"),
                'user_ids_count': 2,
                'name': unordered(["Super Mario Bros.", "Luigi's Mansion"]),
                '__domain': [('user_ids', '=', self.users[1].id)],
            },
            {   # tasks of nobody
                'user_ids': False,
                'user_ids_count': 1,
                'name': unordered(["Donkey Kong"]),
                '__domain': [('user_ids', 'not any', [(1, '=', 1)])],
            },
        ])

        # as demo user, ir.rule should apply
        tasks = self.tasks.with_user(self.user_demo)

        # warming up various caches; this avoids extra queries
        tasks.read_group(domain=[], fields=['name:array_agg'], groupby=['user_ids'])

        expected = """
            SELECT
                "test_read_group_task__user_ids"."user_id",
                COUNT(*),
                ARRAY_AGG("test_read_group_task"."name" ORDER BY "test_read_group_task"."id")
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids"
                ON (
                    "test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id"
                    AND "test_read_group_task__user_ids"."user_id" IN (
                        SELECT "test_read_group_user"."id"
                        FROM "test_read_group_user"
                        WHERE ("test_read_group_user"."id" = %s)
                    )
                )
            GROUP BY "test_read_group_task__user_ids"."user_id"
            ORDER BY "test_read_group_task__user_ids"."user_id" ASC
        """
        with self.assertQueries([expected]):
            as_demo = tasks.read_group(
                domain=[],
                fields=['name:array_agg'],
                groupby=['user_ids'],
            )
        self.assertEqual(as_demo, [
            {   # tasks of Mario
                'user_ids': (self.users[0].id, "Mario"),
                'user_ids_count': 2,
                'name': unordered(['Super Mario Bros.', 'Paper Mario']),
                '__domain': [('user_ids', '=', self.users[0].id)],
            },
            {   # tasks of Luigi and no user
                'user_ids': False,
                'user_ids_count': 2,
                'name': unordered(["Luigi's Mansion", 'Donkey Kong']),
                '__domain': [('user_ids', 'not any', [(1, '=', 1)])],
            },
        ])

        for group in as_demo:
            self.assertEqual(
                group['user_ids_count'],
                tasks.search_count(group['__domain']),
                'A search using the domain returned by the read_group should give the '
                'same number of records as counted in the group',
            )

    def test_ordered_tasks(self):
        """
            Depending on the order of the group_by, you may obtain non-desired behavior.
            In this test, we check the operation of read_group in the event that the first
            group (defined by orderby) contains no results.

            Default order is 'users_ids ASC'
            So we reverse the order to have the spot without users in first position.
        """
        tasks_by_users = self.tasks.read_group(
            domain=[],
            fields=['name'],
            groupby=['user_ids'],
            orderby='user_ids DESC',
        )

        self.assertEqual(tasks_by_users, [
            {   # tasks of no one
                'user_ids': False,
                'user_ids_count': 1,
                '__domain': [('user_ids', 'not any', [(1, '=', 1)])],
            },
            {   # tasks of Luigi
                'user_ids': (self.users[1].id, 'Luigi'),
                'user_ids_count': 2,
                '__domain': [('user_ids', '=', self.users[1].id)],
            },
            {   # tasks of Mario
                'user_ids': (self.users[0].id, 'Mario'),
                'user_ids_count': 2,
                '__domain': [('user_ids', '=', self.users[0].id)],
            },
        ])

class unordered(list):
    """ A list where equality is interpreted without ordering. """
    __slots__ = ()

    def __eq__(self, other):
        return sorted(self) == sorted(other)

    def __ne__(self, other):
        return sorted(self) != sorted(other)
