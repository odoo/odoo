# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import BaseCase
from odoo.addons.web.controllers.utils import fix_view_modes


class ActionMungerTest(BaseCase):
    def test_actual_treeview(self):
        action = {
            "views": [[False, "tree"], [False, "form"],
                      [False, "calendar"]],
            "view_type": "tree",
            "view_id": False,
            "view_mode": "tree,form,calendar"
        }
        changed = action.copy()
        del action['view_type']
        fix_view_modes(changed)

        self.assertEqual(changed, action)

    def test_list_view(self):
        action = {
            "views": [[False, "tree"], [False, "form"],
                      [False, "calendar"]],
            "view_type": "form",
            "view_id": False,
            "view_mode": "tree,form,calendar"
        }
        fix_view_modes(action)

        self.assertEqual(action, {
            "views": [[False, "list"], [False, "form"],
                      [False, "calendar"]],
            "view_id": False,
            "view_mode": "list,form,calendar"
        })

    def test_redundant_views(self):

        action = {
            "views": [[False, "tree"], [False, "form"],
                      [False, "calendar"], [42, "tree"]],
            "view_type": "form",
            "view_id": False,
            "view_mode": "tree,form,calendar"
        }
        fix_view_modes(action)

        self.assertEqual(action, {
            "views": [[False, "list"], [False, "form"],
                      [False, "calendar"], [42, "list"]],
            "view_id": False,
            "view_mode": "list,form,calendar"
        })
