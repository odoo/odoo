from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon


@tagged('-at_install', 'post_install')
class TestResCompany(PaymentCommon):

    def test_creating_company_duplicates_providers(self):
        """Ensure that payment providers of an existing company are correctly duplicated
        when a new company is created."""
        main_company = self.env.company
        main_company_providers_count = self.env['payment.provider'].search_count(
            [('company_id', '=', main_company.id)]
        )

        new_company = self.env['res.company'].create({'name': 'New Company'})
        new_company_providers_count = self.env['payment.provider'].search_count(
            [('company_id', '=', new_company.id)]
        )

        self.assertEqual(new_company_providers_count, main_company_providers_count)
