from odoo.addons.report_formula import rename_account_report_models


def migrate(cr, version):
    if not version:
        return
    rename_account_report_models(cr)
