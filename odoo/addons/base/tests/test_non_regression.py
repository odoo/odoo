# -*- coding: utf-8 -*-
"""
    Non-Regression Tests
"""

from openerp.tests.common import TransactionCase


class TestNR(TransactionCase):
    def test_issue26036(self):
        # Coming from https://github.com/odoo/odoo/pull/26036
        U = self.env["res.users"]
        G = self.env["res.groups"]
        group_user = self.env.ref('base.group_user')
        group_no_one = self.env.ref('base.group_no_one')

        group_A = G.create({"name": "A"})
        group_AA = G.create({"name": "AA", "implied_ids": [(6, 0, [group_A.id])]})
        group_B = G.create({"name": "B"})
        group_BB = G.create({"name": "BB", "implied_ids": [(6, 0, [group_B.id])]})
        group_C = G.create({"name": "C"})

        user_a = U.create({"name": "a", "login": "a", "groups_id": [(6, 0, [group_AA.id, group_user.id])]})
        user_b = U.create({"name": "b", "login": "b", "groups_id": [(6, 0, [group_BB.id])]})

        self.assertEqual(user_a.groups_id, (group_AA + group_A + group_user + group_no_one))

        (user_a + user_b).write({"groups_id": [(4, group_C.id)]})

        self.assertEqual(user_a.groups_id, (group_AA + group_A + group_C + group_user + group_no_one))
        # As user_b is not an internal user, all its groups are removed
        self.assertEqual(user_b.groups_id, group_C)
