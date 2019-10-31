# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common

class TestNote(common.TransactionCase):

    def test_bug_lp_1156215(self):
        """ ensure any users can create new users """
        demo_user = self.env.ref('base.user_demo')
        group_erp = self.env.ref('base.group_erp_manager')

        demo_user.write({
            'groups_id': [(4, group_erp.id)],
        })

        # must not fail
        demo_user.create({
            'name': 'test bug lp:1156215',
            'login': 'lp_1156215',
        })
