# © 2023 David BEAL @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import ValidationError
from odoo.tests import common


class Test(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.user_view = cls.env.ref("base.view_users_form")

    def test_nice(self):
        arch, view = (
            self.env["res.users"]
            .with_context(style="nice")
            ._get_view(view_id=self.user_view.id)
        )
        for field in arch.xpath("//field[@name='partner_id']"):
            self.assertEqual(field.attrib.get("class"), "bg-warning")

    def test_no_dict(self):
        with self.assertRaisesRegex(ValidationError, "_get_field_styles().*"):
            arch, view = (
                self.env["res.users"]
                .with_context(style="no_dict")
                ._get_view(view_id=self.user_view.id)
            )

    def test_no_field_list(self):
        with self.assertRaisesRegex(ValidationError, ".*should be a list of fields.*"):
            arch, view = (
                self.env["res.users"]
                .with_context(style="no_field_list")
                ._get_view(view_id=self.user_view.id)
            )

    def test_empty_dict(self):
        # No effect but no broken code
        arch, view = (
            self.env["res.users"]
            .with_context(style="empty_dict")
            ._get_view(view_id=self.user_view.id)
        )

    def test_no_style(self):
        with self.assertRaisesRegex(ValidationError, ".*should be a dict.*"):
            arch, view = (
                self.env["res.users"]
                .with_context(style="no_style")
                ._get_view(view_id=self.user_view.id)
            )
