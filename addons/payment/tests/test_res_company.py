from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestResCompany(PaymentCommon):
    def test_creating_company_duplicates_providers(self):
        """Ensure that installed payment providers of an existing company are correctly duplicated
        when a new company is created."""
        main_company = self.env.company
        main_company_providers_count = self.env["payment.provider"].search_count([
            ("company_id", "=", main_company.id),
            ("module_state", "=", "installed"),
        ])

        new_company = self.env["res.company"].create({"name": "New Company"})
        new_company_providers_count = self.env["payment.provider"].search_count([
            ("company_id", "=", new_company.id),
            ("module_state", "=", "installed"),
        ])

        self.assertEqual(new_company_providers_count, main_company_providers_count)

    def test_providers_are_duplicated_in_batches(self):
        """Creating multiple companies copies all installed providers in one create call."""
        self.dummy_provider.module_id = self.env["ir.module.module"]._get("payment")
        self.dummy_provider.copy()
        installed_provider_count = self.env["payment.provider"].search_count([
            ("company_id", "=", self.env.company.id),
            ("module_state", "=", "installed"),
        ])
        provider_create_batch_sizes = []
        PaymentProvider = self.env.registry["payment.provider"]
        provider_create = PaymentProvider.create

        def capture_provider_create(provider_model, vals_list):
            provider_create_batch_sizes.append(len(vals_list))
            return provider_create(provider_model, vals_list)

        with patch.object(PaymentProvider, "create", capture_provider_create):
            self.env["res.company"].create([
                {"name": "New Company 1"},
                {"name": "New Company 2"},
            ])
        self.assertEqual(provider_create_batch_sizes, [2 * installed_provider_count])
