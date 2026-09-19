from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.models.chart_template import AccountChartTemplate
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_prepare_chart_template_data = AccountChartTemplate._prepare_chart_template_data


def _prepare_chart_template_data_with_downpayment(self, template_code):
    data = _prepare_chart_template_data(self, template_code)
    data["template_data"]["downpayment_account_id"] = next(
        xmlid
        for xmlid, vals in data["account.account"].items()
        if vals.get("account_type") == "liability_current"
    )
    return data


@tagged("post_install", "-at_install")
@patch.object(
    AccountChartTemplate,
    "_prepare_chart_template_data",
    _prepare_chart_template_data_with_downpayment,
)
class TestSaleChartTemplate(AccountTestInvoicingCommon):
    def _template_downpayment_account(self, company):
        ChartTemplate = self.env["account.chart.template"].with_company(company)
        template_data = ChartTemplate._prepare_chart_template_data(
            company.account_config_id.chart_template
        )
        return ChartTemplate.ref(
            template_data["template_data"]["downpayment_account_id"]
        )

    def test_loading_a_chart_sets_its_downpayment_account_on_the_company(self):
        company = self._create_company(name="Downpayment company")

        self.assertEqual(
            company.downpayment_account_id,
            self._template_downpayment_account(company),
        )

    def test_reloading_a_chart_keeps_the_downpayment_account_the_company_chose(self):
        company = self._create_company(name="Downpayment company")
        chosen = (
            self.env["account.account"]
            .with_company(company)
            .create(
                {
                    "name": "Chosen downpayments",
                    "code": "299999",
                    "account_type": "liability_current",
                }
            )
        )
        company.downpayment_account_id = chosen

        self.env["account.chart.template"].try_loading(
            company.account_config_id.chart_template,
            company=company,
            install_demo=False,
        )

        self.assertEqual(company.downpayment_account_id, chosen)

    def test_a_branch_takes_the_downpayment_account_of_its_chart(self):
        company = self._create_company(name="Downpayment company")
        branch = self._create_company(name="Downpayment branch", parent_id=company.id)

        self.assertEqual(
            branch.downpayment_account_id,
            self._template_downpayment_account(company),
        )

    def test_a_new_company_does_not_default_to_another_companys_downpayment_account(
        self,
    ):
        company = self._create_company(name="Downpayment company")

        unrelated = (
            self.env["res.company"]
            .with_company(company)
            .create({"name": "Unrelated company"})
        )

        self.assertFalse(unrelated.downpayment_account_id)
