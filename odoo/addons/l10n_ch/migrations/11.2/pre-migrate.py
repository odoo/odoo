# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute("SELECT res_id FROM ir_model_data WHERE module = 'l10n_ch' AND name='account_tax_report_line_chtax_solde_formula'")

    expression_id = cr.fetchone()

    if expression_id:
        cr.execute(
            "DELETE FROM account_report_external_value WHERE target_report_expression_id = %s",
            [expression_id[0]]
        )
