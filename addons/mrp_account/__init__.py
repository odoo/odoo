from . import models
from . import reports
from . import wizards


def _configure_journals(env):
    for company in env["res.company"].search(
        [("chart_template", "!=", False)], order="parent_path"
    ):
        ChartTemplate = env["account.chart.template"].with_company(company)
        template_code = company.chart_template
        template_data = ChartTemplate._prepare_chart_template_data(template_code)[
            "template_data"
        ]
        if "property_stock_account_production_cost_id" in template_data:
            data = {
                "property_stock_account_production_cost_id": template_data[
                    "property_stock_account_production_cost_id"
                ]
            }
            ChartTemplate._post_load_data(template_code, company, data)
