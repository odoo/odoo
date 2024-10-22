def migrate(cr, version):
    cr.execute("""
        UPDATE account_report_expression
        SET label = 'temporary_label'
        WHERE label = 'balance'
        AND report_line_id in (
            SELECT id
            FROM account_report_line
            WHERE code = 'NZBOX13'
        );
    """)
