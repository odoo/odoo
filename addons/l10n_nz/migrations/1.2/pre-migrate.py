def migrate(cr, version):
    cr.execute(
        """
        CREATE TABLE tmp_nzbox_manual_expr AS
            SELECT ext_value.*
            FROM account_report_external_value ext_value
            JOIN account_report_expression expr ON ext_value.target_report_expression_id=expr.id
            JOIN account_report_line report_line ON expr.report_line_id=report_line.id
            WHERE report_line.code='NZBOX13';

        DELETE FROM account_report_expression
        WHERE report_line_id in (
            SELECT id
            FROM account_report_line
            WHERE code='NZBOX13'
        )
        """
    )
