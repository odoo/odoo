from odoo.tests import tagged

from odoo.addons.account_payment_provider.const import REPORT_REASONS_MAPPING
from odoo.addons.account_payment_provider.tests.common import AccountPaymentCommon


@tagged("-at_install", "post_install")
class TestPaymentProvider(AccountPaymentCommon):
    def test_duplicate_provider_child_company_no_journal_id(self):
        """Test that duplicating a provider into a child company leaves `journal_id` unset until
        that company has a bank journal."""
        child_company = self.env["res.company"].create(
            {
                "name": "Child Company",
                "parent_id": self.env.company.id,
            }
        )
        with self.mocked_get_payment_method_information():
            provider_duplicated = self.dummy_provider.copy(
                default={
                    "name": "Duplicated Provider",
                    "company_id": child_company.id,
                    "state": "test",
                }
            )
            self.assertFalse(provider_duplicated.journal_id)

            bank_journal = self.env["account.journal"].create(
                {
                    "name": "Bank Journal",
                    "type": "bank",
                    "company_id": child_company.id,
                }
            )
            provider_duplicated.invalidate_recordset(fnames=["journal_id"])
            self.assertEqual(provider_duplicated.journal_id, bank_journal)

    def test_provider_restricted_to_pricelists_it_does_not_serve(self):
        """A provider listing pricelists is offered only to partners on one of them.

        Leaving the list empty must keep the provider available to everyone, so the
        restriction is opt-in.
        """
        pricelist_public, pricelist_credit = self.env["product.pricelist"].create(
            [
                {"name": "Public", "currency_id": self.currency_euro.id},
                {"name": "Credit", "currency_id": self.currency_euro.id},
            ]
        )
        self.partner.property_product_pricelist = pricelist_credit

        def compatible_providers(report=None):
            return (
                self.env["payment.provider"]
                .sudo()
                ._get_compatible_providers(
                    self.company.id, self.partner.id, self.amount, report=report
                )
            )

        # An empty list restricts nothing.
        self.assertIn(self.provider, compatible_providers())

        # A list the partner's pricelist is on still allows the provider through.
        self.provider.available_pricelist_ids = pricelist_credit
        self.assertIn(self.provider, compatible_providers())

        # A list the partner's pricelist is absent from excludes it, with a reason.
        report = {}
        self.provider.available_pricelist_ids = pricelist_public
        self.assertNotIn(self.provider, compatible_providers(report=report))
        # Compared as a dict, not field by field: the reason is a lazy translation,
        # whose `__eq__` raises. Dict comparison shortcuts on identity instead, which
        # is how `payment`'s own report tests assert it (`test_payment_provider.py:429`).
        self.assertDictEqual(
            report["providers"][self.provider],
            {
                "available": False,
                "reason": REPORT_REASONS_MAPPING["pricelist_not_allowed"],
            },
        )
