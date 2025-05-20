from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search([("chart_template", "=", "ca_2023")], order="parent_path"):
        env["account.chart.template"].try_loading("ca_2023", company)
