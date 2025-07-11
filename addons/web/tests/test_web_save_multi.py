from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWebSaveMulti(HttpCase):

    def test_web_save_multi(self):
        partner1 = self.env['res.partner'].create({'name': 'Test Partner 1', 'credit_limit': 100.0})
        partner2 = self.env['res.partner'].create({'name': 'Test Partner 2', 'credit_limit': 200.0})

        self.authenticate('admin', 'admin')

        vals_list = [
            {"id": partner1.id, "name": "Updated Partner 1", "credit_limit": 150.0},
            {"name": "New Partner 3", "credit_limit": 300.0},
            {"id": partner2.id, "credit_limit": 250.0}
        ]

        specification = {
            "name": {"type": "char"},
            "credit_limit": {"type": "float"},
        }

        result = self.env['res.partner'].web_save_multi(vals_list, specification)

        names = [rec["name"] for rec in result]
        credit_limits = {rec["name"]: rec["credit_limit"] for rec in result}

        self.assertIn("Updated Partner 1", names)
        self.assertIn("New Partner 3", names)
        self.assertIn("Test Partner 2", names)

        self.assertEqual(credit_limits["Updated Partner 1"], 150.0)
        self.assertEqual(credit_limits["New Partner 3"], 300.0)
        self.assertEqual(credit_limits["Test Partner 2"], 250.0)
