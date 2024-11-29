
from odoo.tests import common

class TestRelatedReadGroup(common.TransactionCase):

    def test_read_group_related(self):
        base_user = common.new_test_user(self.env, login='Base User', groups='base.group_user')

        RelatedBar = self.env['test_read_group.related_bar']
        RelatedFoo = self.env['test_read_group.related_foo']
        RelatedBase = self.env['test_read_group.related_base']

        bars = RelatedBar.create([
            {'name': 'bar_a'},
            {'name': False},
        ])

        foos = RelatedFoo.create([
            {'name': 'foo_a_bar_a', 'bar_id': bars[0].id},
            {'name': 'foo_b_bar_false', 'bar_id': bars[1].id},
            {'name': False, 'bar_id': bars[0].id},
            {'name': False},
        ])

        RelatedBase.create([
            {'name': 'base_foo_a_1', 'foo_id': foos[0].id},
            {'name': 'base_foo_a_2', 'foo_id': foos[0].id},
            {'name': 'base_foo_b_bar_false', 'foo_id': foos[1].id},
            {'name': 'base_false_foo_bar_a', 'foo_id': foos[2].id},
            {'name': 'base_false_foo', 'foo_id': foos[3].id},
        ])

        # env.su => false
        RelatedBase = RelatedBase.with_user(base_user)

        result_read_group = RelatedBase.read_group([], ['__count'], ['foo_id_bar_id_name'], lazy=False)
        self.assertEqual(
            result_read_group,
            [
                {
                    '__count': 3,
                    '__domain': [('foo_id_bar_id_name', '=', 'bar_a')],
                    'foo_id_bar_id_name': 'bar_a',
                },
                {
                    '__count': 2,
                    '__domain': [('foo_id_bar_id_name', '=', False)],
                    'foo_id_bar_id_name': False,
                },
            ],
        )
        for group in result_read_group:
            self.assertEqual(
                RelatedBase.search_count(group['__domain']),
                group['__count'],
            )
