from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    vat_report_id = env.ref('l10n_it.tax_report_vat').id
    monthly_vat_report_id = env.ref('l10n_it.tax_monthly_report_vat').id

    cr.execute("""
        SELECT report.id AS report_id,
               expression.id AS expression_id,
               report_line.code,
               external_value.*
        FROM account_report AS report
                 JOIN account_report_line AS report_line
                   ON report.id = report_line.report_id
                 JOIN account_report_expression AS expression
                   ON report_line.id = expression.report_line_id
                  AND expression.engine = 'external'
            LEFT JOIN account_report_external_value AS external_value
                   ON expression.id = external_value.target_report_expression_id
        WHERE (
               report.id = %s
               AND external_value.company_id IS NOT NULL
            )
           OR report.id = %s
        ORDER BY expression_id;
    """, (vat_report_id, monthly_vat_report_id))
    report_info = cr.fetchall()
    new_target = {
        report_line_code: expression_id
        for report_id, expression_id, report_line_code, *_ in report_info
        if report_id == monthly_vat_report_id
    }
    data_to_insert = []

    cr.execute("""
        SELECT DISTINCT old_report_line.id AS old_origin,
                        new_report_line.id AS new_origin
        FROM account_report_external_value external_value
            INNER JOIN account_report_line AS old_report_line
                    ON old_report_line.id = external_value.carryover_origin_report_line_id
            INNER JOIN account_report_line AS new_report_line
                    ON new_report_line.code = old_report_line.code
                   AND new_report_line.id != old_report_line.id;
    """)
    carryover_origin_info = cr.fetchall()
    new_origin = {info[0]: info[1] for info in carryover_origin_info}

    for record in report_info:
        if record[0] == vat_report_id:
            data_to_insert.append((
                new_target[record[2]], record[5], record[6], new_origin[record[7]], record[8], record[9],
                record[10], record[11], record[12], record[13], record[14], record[15], record[16]
            ))

    insert_query = """
        INSERT INTO account_report_external_value(
            target_report_expression_id, company_id, foreign_vat_fiscal_position_id,
            carryover_origin_report_line_id, create_uid, write_uid, name, text_value,
            carryover_origin_expression_label, DATE, create_date, write_date, VALUE
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT DO NOTHING
    """

    cr.executemany(insert_query, data_to_insert)

    # Archive the old report
    cr.execute("""
        UPDATE
            account_report
        SET
            active = FALSE
        WHERE
            id = %s
    """, (vat_report_id,))
