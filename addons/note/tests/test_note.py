# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.fields import X2ManyCmd


class TestNote(TransactionCaseWithUserDemo):

    def test_bug_lp_1156215(self):
        """ ensure any users can create new users """
        demo_user = self.user_demo
        group_erp = self.env.ref('base.group_erp_manager')

        demo_user.write({
            'groups_id': [(X2ManyCmd.LINK, group_erp.id)],
        })

        # must not fail
        demo_user.create({
            'name': 'test bug lp:1156215',
            'login': 'lp_1156215',
        })
