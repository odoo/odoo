# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common

class TestNote(common.TransactionCase):

    def test_bug_lp_1156215(self):
        """ensure any users can create new users"""
        cr, uid = self.cr, self.uid
        IMD = self.registry('ir.model.data')
        Users = self.registry('res.users')

        _, demo_user = IMD.get_object_reference(cr, uid, 'base', 'user_demo')
        _, group_id = IMD.get_object_reference(cr, uid, 'base', 'group_erp_manager')

        Users.write(cr, uid, [demo_user], {
            'groups_id': [(4, group_id)],
        })

        # must not fail
        Users.create(cr, demo_user, {
            'name': 'test bug lp:1156215',
            'login': 'lp_1156215',
        })
