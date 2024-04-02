from .common import AccountTestInvoicingCommon
from odoo.tests.common import Form, tagged, new_test_user
from odoo import Command


@tagged("post_install", "-at_install")
class AccountProductCase(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)
        cls.internal_user = new_test_user(
            cls.env, login="internal_user", groups="base.group_user"
        )

    def test_internal_user_can_read_product_with_tax_and_tags(self):
        """Internal users need read access to products, no matter their taxes."""
        # Add a tag to product_a's default tax
        self.company_data["company"].country_id = self.env.ref("base.us")
        tax_line_tag = self.env["account.account.tag"].create(
            {
                "name": "Tax tag",
                "applicability": "taxes",
                "country_id": self.company_data["company"].country_id.id,
            }
        )
        repartition_lines = (
            self.product_a.taxes_id.invoice_repartition_line_ids
            | self.product_a.taxes_id.refund_repartition_line_ids
        ).filtered_domain([("repartition_type", "=", "tax")])
        repartition_lines.write({"tag_ids": [Command.link(tax_line_tag.id)]})
        # Check that internal user can read product_a
        with Form(
            self.product_a.with_user(self.internal_user).with_context(lang="en_US")
        ) as form_a:
            # The tax string itself is not very important here; we just check
            # it has a value and we can read it, so there were no access errors
            self.assertTrue(form_a.tax_string)
