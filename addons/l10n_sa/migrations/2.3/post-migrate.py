from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Make Saudi companies use round globally"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search([("chart_template", "=", "sa")], order="parent_path"):
        company.tax_calculation_rounding_method = "round_globally"
