from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    report_lines = [f"l10n_ro.account_tax_report_ro_baza_rd{code}" for code in ["91", "92", "101", "102", "111", "112", "123", "241", "242", "251", "252", "26", "261", "262", "273"]] + [
                    f"l10n_ro.account_tax_report_ro_tva_rd{code}" for code in ["91", "92", "101", "102", "111", "112", "123", "241", "242", "251", "252", "26", "261", "262", "273"]]

    remove_aggregation_lines = [f"l10n_ro.account_tax_report_ro_baza_rd{code}" for code in ["24", "25", "26"]] + [
                                f"l10n_ro.account_tax_report_ro_tva_rd{code}" for code in ["24", "25", "26"]]

    report_line_ids = [env.ref(line, raise_if_not_found=False) for line in report_lines]
    report_line_ids = tuple(line.id for line in report_line_ids if line)
    remove_aggregation_line_ids = [env.ref(line, raise_if_not_found=False) for line in remove_aggregation_lines]
    remove_aggregation_line_ids = tuple(line.id for line in remove_aggregation_line_ids if line)

    if report_line_ids:
        cr.execute("DELETE FROM account_report_line WHERE id IN %s", (report_line_ids,))
    if remove_aggregation_line_ids:
        cr.execute("DELETE FROM account_report_expression where report_line_id IN %s", (remove_aggregation_line_ids,))
