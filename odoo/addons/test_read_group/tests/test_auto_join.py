# -*- coding: utf-8 -*-
from odoo.tests import common


class TestAutoJoin(common.TransactionCase):
    """ Test what happens when grouping with a domain using a one2many field with auto_join. """

    def test_auto_join(self):
        model = self.env['test_read_group.order']
        records = model.create([{
            'line_ids': [(0, 0, {'value': 1}), (0, 0, {'value': 2})],
        }, {
            'line_ids': [(0, 0, {'value': 1})],
        }])

        domain1 = [('id', 'in', records.ids), ('line_ids.value', '=', 1)]
        domain2 = [('id', 'in', records.ids), ('line_ids.value', '>', 0)]

        # reference results
        self.assertEqual(len(model.search(domain1)), 2)
        self.assertEqual(len(model.search(domain2)), 2)

        result1 = model.read_group(domain1, [], [])
        self.assertEqual(len(result1), 1)
        self.assertEqual(result1[0]['__count'], 2)

        result2 = model.read_group(domain2, [], [])
        self.assertEqual(len(result2), 1)
        self.assertEqual(result2[0]['__count'], 2)

        # same requests, with auto_join
        self.patch(type(model).line_ids, 'auto_join', True)

        self.assertEqual(len(model.search(domain1)), 2)
        self.assertEqual(len(model.search(domain2)), 2)

        result1 = model.read_group(domain1, [], [])
        self.assertEqual(len(result1), 1)
        self.assertEqual(result1[0]['__count'], 2)

        result2 = model.read_group(domain2, [], [])
        self.assertEqual(len(result2), 1)
        self.assertEqual(result2[0]['__count'], 2)
