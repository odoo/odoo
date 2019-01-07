# -*- coding: utf-8 -*-
"""
    Non-Regression Tests
"""

from openerp.tests.common import TransactionCase


class TestNR(TransactionCase):
    def test_issue26036(self):
        U = self.env["res.users"]
        G = self.env["res.groups"]

        group_A = G.create({"name": "A"})
        group_AA = G.create({"name": "AA", "implied_ids": [(6, 0, [group_A.id])]})
        group_B = G.create({"name": "B"})
        group_BB = G.create({"name": "BB", "implied_ids": [(6, 0, [group_B.id])]})
        group_C = G.create({"name": "C"})

        user_a = U.create({"name": "a", "login": "a", "groups_id": [(6, 0, [group_AA.id])]})
        user_b = U.create({"name": "b", "login": "b", "groups_id": [(6, 0, [group_BB.id])]})

        (user_a + user_b).write({"groups_id": [(4, group_C.id)]})

        self.assertEqual(user_a.groups_id, (group_AA + group_A + group_C))
        self.assertEqual(user_b.groups_id, (group_BB + group_B + group_C))
