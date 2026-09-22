from odoo.tests import tagged

from odoo.addons.l10n_mx.tests.common import TestMxCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestMxWithholdingPriority(TestMxCommon):
    """Where the RESICO withholding sits in the tax order, and what that costs.

    `account.tax._order` is "sequence,id" and `_flatten_taxes_and_sort_them`
    sorts on that same key before evaluating, so the sequence carried by the
    template rows decides the base each tax sees. Every `ieps_*` row sets
    `include_base_amount`, which means an IEPS evaluated first inflates the
    base of everything that follows it.
    """

    def _template_record(self, xmlid):
        company = self.company_data["company"]
        return self.env.ref(f"account.{company.id}_{xmlid}")

    def test_resico_withholding_is_computed_on_the_pre_ieps_base(self):
        company = self.company_data["company"]
        ieps = self._template_record("ieps_8_purchase")
        resico = self._template_record("mx_wh_1_25")

        result = (ieps + resico).compute_all(
            1000.0, currency=company.currency_id, quantity=1.0
        )
        amounts = {tax["id"]: tax["amount"] for tax in result["taxes"]}

        # The withholding is 1.25% of the 1000 the supplier actually invoiced,
        # not of the 1080 an IEPS evaluated first would leave behind.
        self.assertEqual(amounts[ieps.id], 80.0)
        self.assertEqual(amounts[resico.id], -12.5)

    def test_the_company_default_taxes_are_still_vat(self):
        """Regression guard, not the proof.

        The withholding now leads the tax list, and `_default_tax_for` picks a
        tax with `search(..., limit=1)` over that same order. It never runs
        here because `template_mx.py` sets both defaults explicitly, so
        `_post_load_default_taxes` finds them already filled. If that ever
        stops being true, a -1.25% withholding becomes the default purchase
        tax and this test says so.

        The two defaults live on `account.config`, not on `res.company`:
        this fork moved the accounting configuration off the company.
        """
        config = self.company_data["company"].account_config_id
        self.assertEqual(config.account_purchase_tax_id, self._template_record("tax14"))
        self.assertEqual(config.account_sale_tax_id, self._template_record("tax12"))
