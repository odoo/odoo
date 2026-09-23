from odoo.modules.module import get_module_path, load_script
from odoo.tests import TransactionCase, tagged

from odoo.addons.base.models.ir_access_convert import (
    converted_row_ids,
    normalize_domain,
)


@tagged("post_install", "-at_install")
class TestVersionRuleRelationships(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.script = load_script(
            f"{get_module_path('hr')}/migrations/1.27/"
            "post-migrate_version_rule_relationships.py",
            "hr_1_27_post_migrate",
        )
        cls.rows = cls.env["ir.access"].browse(
            converted_row_ids(cls.env.cr, "hr", "ir_rule_hr_contract_multi_company")
        )

    def _as_the_production_dump_holds_it(self, domain):
        # base 1.97 converted the noupdate rule as the database held it: the
        # company-only domain, normalized, under the rule's own external id
        self.env.cr.execute(
            "UPDATE ir_access SET domain = %s WHERE id = ANY(%s)",
            [normalize_domain(domain), self.rows.ids],
        )
        self.rows.invalidate_recordset(["domain"])

    def test_the_converted_company_rule_grants_the_relationships(self):
        self.assertTrue(self.rows)
        self._as_the_production_dump_holds_it(self.script.OLD_DOMAIN)

        self.script.migrate(self.env.cr, "1.26")

        self.rows.invalidate_recordset(["domain"])
        self.assertEqual(
            set(self.rows.mapped("domain")),
            {normalize_domain(self.script.NEW_DOMAIN)},
        )
        self.assertIn("employee_id.parent_id.user_id", self.rows[0].domain)

    def test_a_domain_edited_on_the_database_is_left_alone(self):
        edited = "[('company_id', 'in', company_ids)]"
        self._as_the_production_dump_holds_it(edited)

        self.script.migrate(self.env.cr, "1.26")

        self.rows.invalidate_recordset(["domain"])
        self.assertEqual(set(self.rows.mapped("domain")), {normalize_domain(edited)})
