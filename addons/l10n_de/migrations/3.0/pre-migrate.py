# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    tax_report = env.ref("l10n_de.tax_report", raise_if_not_found=False)
    balance_column = env.ref('l10n_de.tax_report_balance', raise_if_not_found=False)
    report_lines = [f"l10n_de.tax_report_de_tax_tag_{btw}" for btw in ["17", "18", "19", "31", "46", "55", "64"]] + [
        f"l10n_de.tax_report_de_tag_{btw}" for btw in
        ["01", "02", "17", "18", "19", "25", "26", "27", "31", "33",
         "34", "36", "37", "46", "47", "71", "74", "80", "85", "96",
         "98"]]
    report_lines = [env.ref(line, raise_if_not_found=False) for line in report_lines]
    report_line_ids = tuple(line.id for line in report_lines if line)

    if balance_column:
        cr.execute("DELETE FROM account_report_column WHERE id = %s", (balance_column.id,))
    if report_line_ids:
        cr.execute("DELETE FROM account_report_line WHERE id IN %s", (report_line_ids,))
    if tax_report:
        cr.execute("UPDATE account_report_line SET code = NULL WHERE report_id = %s", (tax_report.id,))
