def migrate(cr, version):
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
