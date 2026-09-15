from . import models
from . import wizards
from . import controllers


def post_init_hook(env):
    for company in env["res.company"].search(
        [("chart_template", "!=", False), ("parent_id", "=", False)]
    ):
        ChartTemplate = env["account.chart.template"].with_company(company)
        accounts = {
            xmlid: filtered_vals
            for xmlid, vals in ChartTemplate._get_account_account(
                company.chart_template
            ).items()
            if (
                filtered_vals := {
                    fname: value
                    for fname, value in vals.items()
                    if fname in ["create_asset", "depreciation_profile_ids"]
                }
            )
            and ChartTemplate.ref(xmlid, raise_if_not_found=False)
        }
        profiles = {
            xmlid: filtered_vals
            for xmlid, vals in ChartTemplate._get_account_depreciation_profile(
                company.chart_template
            ).items()
            if (
                filtered_vals := {
                    fname: value
                    for fname, value in vals.items()
                    if fname
                    not in [
                        "account_asset_id",
                        "account_depreciation_id",
                        "account_depreciation_expense_id",
                    ]
                    or value in accounts
                    or ChartTemplate.ref(value, raise_if_not_found=False)
                }
            )
        }
        ChartTemplate._load_data(
            {"account.depreciation.profile": profiles, "account.account": accounts}
        )
