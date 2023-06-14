""" Test the comprehensiveness of domains returned
by read_group when grouping with many2many fields """

from odoo.fields import Command
from odoo.tests import common

@common.tagged('test_read_group_domains')
class TestReadGroupDomains(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = cls.env['res.users'].create([
            {'name': 'Mario', 'login': 'mario'},
            {'name': 'Luigi', 'login': 'luigi'},
        ])
        cls.tasks = cls.env['test_new_api.simple.task'].create([
            {   # public task 1
                'name': "Super Mario Bros.",
            },
            {   # public task 2
                'name': "Paper Mario",
            },
            {   # luigi only
                'name': "Buy Mario a gift",
                'user_id': cls.users[1].id,
            },
            {   # mario only
                'name': 'Donkey Kong',
                'user_id': cls.users[0].id,
            },
        ])

    def test_groupby_m2m_with_limited_read_access(self):
        # setting a sibling that only luigi can access to a public task
        task_luigi = self.env['test_new_api.simple.task'].search([('name', 'ilike', 'Buy Mario a gift')])
        public_task = self.env['test_new_api.simple.task'].search([('name', 'ilike', 'Paper Mario')])
        public_task.sibling_ids = [Command.set(task_luigi.ids)]

        # group_by siblings as Mario
        tasks_by_siblings = self.tasks.with_user(self.users[0]).read_group(
            domain=[],
            fields=['name'],
            groupby=['sibling_ids'],
        )
        for group in tasks_by_siblings:
            # Problem here: a search with [('m2m', '=', False)] does not returns enough records as it does not take access rights into account
            self.assertEqual(group['sibling_ids_count'],
                self.tasks.with_user(self.users[0]).search_count(group['__domain']),
                'A search using the domain returned by the read_group should give the same number of records as counted in the group')
