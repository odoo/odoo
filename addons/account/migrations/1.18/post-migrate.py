from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    root_annual_statements = env.ref(
        "account.annual_statements", raise_if_not_found=False
    )
    if not root_annual_statements:
        return
    Report = env["report.formula"].with_context(active_test=False)
    Report.search(
        Report._get_domain_asr_sections(root_annual_statements)
    )._link_annual_statements(root_annual_statements)
