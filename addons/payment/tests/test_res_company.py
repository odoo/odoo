from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged("-at_install", "post_install")
class TestResCompany(PaymentCommon):
    def test_creating_company_duplicates_providers(self):
        """Ensure that installed payment providers of an existing company are correctly duplicated
        when a new company is created."""
        main_company = self.env.company
        module_payment = self.env["ir.module.module"]._get("payment")
        providers = self.env["payment.provider"].create([
            {
                "name": "Company Copy Provider 1",
                "code": "none",
                "company_id": main_company.id,
                "module_id": module_payment.id,
            },
            {
                "name": "Company Copy Provider 2",
                "code": "none",
                "company_id": main_company.id,
                "module_id": module_payment.id,
            },
        ])
        primary_pms = self.env["payment.method"].create([
            {
                "name": f"Primary {index}",
                "code": f"company_copy_primary_{index}",
                "provider_id": provider.id,
            }
            for index, provider in enumerate(providers)
        ])
        brands = self.env["payment.method"].create([
            {
                "name": f"Brand {index}",
                "code": f"company_copy_brand_{index}",
                "provider_id": provider.id,
                "primary_payment_method_id": primary_pm.id,
            }
            for index, (provider, primary_pm) in enumerate(zip(providers, primary_pms))
        ])

        installed_provider_count = self.env["payment.provider"].search_count([
            ("company_id", "=", main_company.id),
            ("module_state", "=", "installed"),
        ])
        provider_create_batch_sizes = []
        PaymentProvider = self.env.registry["payment.provider"]
        provider_create = PaymentProvider.create

        def capture_provider_create(provider_model, vals_list):
            provider_create_batch_sizes.append(len(vals_list))
            return provider_create(provider_model, vals_list)

        with patch.object(PaymentProvider, "create", capture_provider_create):
            new_companies = self.env["res.company"].create([
                {"name": "New Company 1"},
                {"name": "New Company 2"},
            ])

        self.assertEqual(provider_create_batch_sizes, [2 * installed_provider_count])

        for new_company in new_companies:
            new_providers = self.env["payment.provider"].search([
                ("company_id", "=", new_company.id),
                ("name", "in", providers.mapped("name")),
            ])
            self.assertEqual(set(new_providers.mapped("name")), set(providers.mapped("name")))
            for provider, primary_pm, brand in zip(providers, primary_pms, brands):
                new_provider = new_providers.filtered(lambda p: p.name == provider.name)
                new_primary_pm = new_provider.payment_method_ids.filtered(
                    lambda pm: pm.code == primary_pm.code
                )
                new_brand = new_provider.payment_method_ids.filtered(
                    lambda pm: pm.code == brand.code
                )
                self.assertEqual(len(new_primary_pm), 1)
                self.assertEqual(new_brand.primary_payment_method_id, new_primary_pm)
