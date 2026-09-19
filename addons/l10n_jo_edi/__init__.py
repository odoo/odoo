from . import models


def _post_init_hook(env):
    """Make Jordan companies use round globally"""
    if jo_companies := env["res.company"].search(
        [("account_config_id.chart_template", "=", "jo_standard")], order="parent_path"
    ):
        for company in jo_companies:
            company.account_config_id.tax_calculation_rounding_method = "round_globally"
