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
                '__domain': ['&', ('user_ids', '=', self.users[0].id), ('id', '=', self.tasks[0].id)],
            },
            {   # task of Luigi
                'user_ids': (self.users[1].id, "Luigi"),
                'user_ids_count': 1,
                'name': ["Super Mario Bros."],
                '__domain': ['&', ('user_ids', '=', self.users[1].id), ('id', '=', self.tasks[0].id)],
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
                '__domain': [('user_ids', '=', False)],
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

        # as superuser, ir.rule should not apply
        expected = """
            SELECT
                min("test_read_group_task".id) AS id,
                count("test_read_group_task".id) AS "user_ids_count",
                array_agg("test_read_group_task"."name") AS "name",
                "test_read_group_task__user_ids"."user_id" AS "user_ids"
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids"
                ON ("test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id")
            GROUP BY "test_read_group_task__user_ids"."user_id"
            ORDER BY "user_ids"
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
                '__domain': [('user_ids', '=', False)],
            },
        ])

        # as demo user, ir.rule should apply
        tasks = self.tasks.with_user(self.user_demo)

        # warming up various caches; this avoids extra queries
        tasks.read_group(domain=[], fields=['name:array_agg'], groupby=['user_ids'])

        expected = """
            SELECT
                min("test_read_group_task".id) AS id,
                count("test_read_group_task".id) AS "user_ids_count",
                array_agg("test_read_group_task"."name") AS "name",
                "test_read_group_task__user_ids"."user_id" AS "user_ids"
            FROM "test_read_group_task"
            LEFT JOIN "test_read_group_task_user_rel" AS "test_read_group_task__user_ids"
                ON (
                    "test_read_group_task"."id" = "test_read_group_task__user_ids"."task_id"
                    AND "test_read_group_task__user_ids"."user_id" IN (
                        SELECT "test_read_group_user".id
                        FROM "test_read_group_user"
                        WHERE ("test_read_group_user"."id" = %s)
                    )
                )
            GROUP BY "test_read_group_task__user_ids"."user_id"
            ORDER BY "user_ids"
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
                '__domain': [('user_ids', '=', False)],
            },
        ])

    def test_order_by_many2one_id(self):
        # ordering by a many2one ordered itself by id does not use useless join
        expected_query = '''
            SELECT
              min("test_read_group_order_line".id) AS id,
              count("test_read_group_order_line".id) AS "order_id_count",
              "test_read_group_order_line"."order_id" as "order_id"
            FROM "test_read_group_order_line"
            GROUP BY "test_read_group_order_line"."order_id"
            ORDER BY "order_id"
        '''
        with self.assertQueries([expected_query]):
            self.env["test_read_group.order.line"].read_group(
                [], ["order_id"], "order_id"
            )
        with self.assertQueries([expected_query + ' DESC']):
            self.env["test_read_group.order.line"].read_group(
                [], ["order_id"], "order_id", orderby="order_id DESC"
            )


class unordered(list):
    """ A list where equality is interpreted without ordering. """
    __slots__ = ()

    def __eq__(self, other):
        return sorted(self) == sorted(other)

    def __ne__(self, other):
        return sorted(self) != sorted(other)
