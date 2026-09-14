from odoo.tests import tagged
from odoo.tests.common import TransactionCase

SUITE_MODULES = (
    "credential",
    "integration",
    "gateway_ml",
)


@tagged("post_install", "-at_install")
class TestSecurityTopology(TransactionCase):
    def _suite_privileges(self):
        data = self.env["ir.model.data"].search(
            [
                ("model", "=", "res.groups.privilege"),
                ("module", "in", list(SUITE_MODULES)),
            ]
        )
        return self.env["res.groups.privilege"].browse(data.mapped("res_id")).exists()

    def test_every_suite_privilege_shares_one_category(self):
        privileges = self._suite_privileges()
        self.assertTrue(privileges, "no suite privileges installed")
        categories = privileges.mapped("category_id")
        self.assertEqual(
            len(categories),
            1,
            "the integration suite must occupy one section of the user form, "
            f"not {len(categories)}: {sorted(categories.mapped('name'))}",
        )
        self.assertEqual(
            categories.name,
            "Integrations",
            "the shared category is credential.module_category_integration",
        )

    def test_no_suite_privilege_is_uncategorised(self):
        without = self._suite_privileges().filtered(lambda p: not p.category_id)
        self.assertFalse(
            without,
            f"privileges with no category are invisible in the user form: "
            f"{without.mapped('name')}",
        )

    def test_the_ladder_reaches_every_module(self):
        ladder = self.env.ref("credential.group_integration_admin")
        reached = ladder
        frontier = ladder
        while frontier:
            frontier = frontier.implied_ids - reached
            reached |= frontier

        installed = self.env["ir.module.module"].search(
            [("name", "in", list(SUITE_MODULES)), ("state", "=", "installed")]
        )
        for module in installed.mapped("name"):
            data = self.env["ir.model.data"].search(
                [
                    ("model", "=", "res.groups"),
                    ("module", "=", module),
                ]
            )
            groups = self.env["res.groups"].browse(data.mapped("res_id")).exists()
            if not groups:
                continue
            self.assertTrue(
                groups & reached,
                f"{module} declares groups that the suite-wide Integrations "
                f"ladder does not reach, so granting Integration Administrator "
                f"silently omits it",
            )
