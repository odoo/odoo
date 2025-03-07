from odoo.addons.account.models.chart_template import update_taxes_from_templates

def migrate(cr, version):
    update_taxes_from_templates(cr, 'l10n_nz.l10n_nz_chart_template')
    cr.execute(
        """
        UPDATE tmp_nzbox_manual_expr
        SET target_report_expression_id = manual_expr.id
        FROM (
            SELECT report_expression.id
            FROM account_report_expression report_expression
            JOIN account_report_line report_line ON report_expression.report_line_id=report_line.id
            WHERE report_line.code='NZBOX13_manual'
        ) manual_expr;

        INSERT INTO account_report_external_value
        SELECT *
        FROM tmp_nzbox_manual_expr;

        DROP TABLE tmp_nzbox_manual_expr;
        """
    )
