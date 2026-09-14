from odoo.tests import TransactionCase, tagged

FREE_FORM_CATEGORIES = frozenset({"custom"})


@tagged("post_install", "-at_install")
class TestEveryCategoryDeclaresItsFields(TransactionCase):
    def test_every_installed_category_but_the_free_form_one_declares_a_field(self):
        undeclared = (
            self.env["credential.category"]
            .with_context(active_test=False)
            .search([("code", "not in", list(FREE_FORM_CATEGORIES))])
            .filtered(lambda category: not category.field_ids)
        )
        self.assertFalse(
            undeclared.mapped("code"),
            "a category must declare the credential.category.field rows its "
            "payload holds, or nothing checks what a credential of it stores",
        )
