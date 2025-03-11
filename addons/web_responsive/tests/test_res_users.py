# Copyright 2023 Taras Shabaranskyi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo.tests import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestResUsers(BaseCommon):
    def test_compute_redirect_home(self):
        record = new_test_user(self.env, login="jeant@mail.com")
        self.assertFalse(record.is_redirect_home)
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "Test Action",
                "type": "ir.actions.act_window",
                "res_model": record._name,
            }
        )
        record.action_id = action.id
        self.assertFalse(record.is_redirect_home)
        record.action_id = False
        record.is_redirect_home = True
        self.assertTrue(record.is_redirect_home)
