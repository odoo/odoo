from odoo.tests.common import TransactionCase, tagged
from odoo.tools.module_data import rename_in_stored_expressions


@tagged("post_install", "-at_install")
class TestRenameInViewArches(TransactionCase):
    def _view(self, model, arch):
        self.env.cr.execute(
            "INSERT INTO ir_ui_view "
            "(name, model, type, arch_db, active, priority, mode) "
            "VALUES ('probe', %s, 'form', jsonb_build_object('en_US', %s::text), "
            "true, 16, 'primary') RETURNING id",
            [model, arch],
        )
        return self.env.cr.fetchone()[0]

    def _arch(self, view_id):
        self.env.cr.execute(
            "SELECT arch_db->>'en_US' FROM ir_ui_view WHERE id = %s", [view_id]
        )
        return self.env.cr.fetchone()[0]

    def test_a_subview_field_of_the_comodel_keeps_its_name(self):
        view = self._view(
            "res.partner",
            "<form><field name='comment'/>"
            "<field name='child_ids'><list><field name='comment'/></list></field>"
            "</form>",
        )
        rename_in_stored_expressions(
            self.env.cr, "comment", "notes", model="res.partner"
        )
        arch = self._arch(view)
        self.assertEqual(arch.count('name="notes"'), 2)
        self.assertEqual(arch.count("comment"), 0)

    def test_a_subview_field_of_another_model_is_left_alone(self):
        view = self._view(
            "res.company",
            "<form><field name='name'/>"
            "<field name='user_ids'><list><field name='name'/></list></field>"
            "</form>",
        )
        rename_in_stored_expressions(self.env.cr, "name", "label", model="res.company")
        arch = self._arch(view)
        self.assertEqual(arch.count('name="label"'), 1)
        self.assertEqual(arch.count('name="name"'), 1)

    def test_an_xpath_into_a_subview_edits_the_comodel(self):
        view = self._view(
            "res.company",
            "<data><xpath expr=\"//field[@name='user_ids']//field[@name='login']\" "
            "position='after'><field name='name'/></xpath></data>",
        )
        rename_in_stored_expressions(self.env.cr, "name", "label", model="res.company")
        self.assertNotIn("label", self._arch(view))

    def test_an_xpath_after_a_relational_field_edits_the_view_model(self):
        view = self._view(
            "res.company",
            "<data><xpath expr=\"//field[@name='user_ids']\" position='after'>"
            "<field name='name'/></xpath></data>",
        )
        rename_in_stored_expressions(self.env.cr, "name", "label", model="res.company")
        self.assertIn('name="label"', self._arch(view))

    def test_an_expression_is_rewritten_in_the_scope_it_reads(self):
        view = self._view(
            "res.company",
            "<form><field name='name' invisible=\"name == 'x'\"/>"
            "<field name='user_ids'><list>"
            "<field name='login' invisible=\"name == 'x'\"/></list></field></form>",
        )
        rename_in_stored_expressions(self.env.cr, "name", "label", model="res.company")
        arch = self._arch(view)
        self.assertIn("label == 'x'", arch)
        self.assertIn("name == 'x'", arch)
