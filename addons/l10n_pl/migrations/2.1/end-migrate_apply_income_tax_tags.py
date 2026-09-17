from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    # The K_1..K_8 income-tax tags arrive with this version; a chart already
    # loaded has to take them onto its accounts, and only a reload does that.
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search(
        [("chart_template", "=", "pl"), ("parent_id", "=", False)],
        order="parent_path",
    ):
        env["account.chart.template"].try_loading("pl", company, force_create=False)
