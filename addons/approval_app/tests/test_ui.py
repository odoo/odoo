from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("-at_install", "post_install")
class TestUi(HttpCaseWithUserDemo):
    def test_ui(self):
        self.env.ref("base.user_admin").write(
            {
                "email": "mitchell.admin@example.com",
            }
        )
        category = self.env.ref("approval_app.approval_category_data_business_trip")
        admin = self.env.ref("base.user_admin")
        if category.step_ids:
            decided_steps = category.step_ids
            self.env["approval.category.step"].create(
                {
                    "category_id": category.id,
                    "name": "Approvers",
                    "minimum": 1,
                    "counts_added_approvers": True,
                }
            )
            decided_steps.active = False
        else:
            category.write(
                {
                    "approval_minimum": 1,
                }
            )
        category.allow_self_approval = True
        category._add_approver(admin)
        self.start_tour("/odoo", "approvals_tour", login="admin")
