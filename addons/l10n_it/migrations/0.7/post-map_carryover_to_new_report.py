from odoo import SUPERUSER_ID, api
from odoo.tools import SQL, split_every, sql
from odoo.tools.constants import IN_MAX


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    vat_report_id = env.ref('l10n_it.tax_report_vat').id
    monthly_vat_report_id = env.ref('l10n_it.tax_monthly_report_vat').id

    external_value_cols = [
        col
        for col in sql.table_columns(env.cr, 'account_report_external_value')
        if col not in ['id', 'carryover_origin_report_line_id', 'target_report_expression_id']
    ]

    cr.execute(SQL("""
        SELECT report.id AS report_id,
               expression.id AS expression_id,
               report_line.code,
               external_value.carryover_origin_report_line_id,
               %s
          FROM account_report AS report
          JOIN account_report_line AS report_line ON report.id = report_line.report_id
          JOIN account_report_expression AS expression ON report_line.id = expression.report_line_id
                                                      AND expression.engine = 'external'
     LEFT JOIN account_report_external_value AS external_value ON expression.id = external_value.target_report_expression_id
         WHERE (
                   report.id = %s
                   AND external_value.company_id IS NOT NULL
               )
            OR report.id = %s
      ORDER BY expression_id
        """,
        SQL(', ').join(SQL.identifier('external_value', col) for col in external_value_cols),
        vat_report_id,
        monthly_vat_report_id,
    ))
    report_info = cr.fetchall()

    code2expression_id = {
        report_line_code: expression_id
        for report_id, expression_id, report_line_code, *_ in report_info
        if report_id == monthly_vat_report_id
    }

    cr.execute("""
        SELECT DISTINCT old_report_line.id AS old_origin,
                        new_report_line.id AS new_origin
                   FROM account_report_external_value external_value
                   JOIN account_report_line AS old_report_line ON old_report_line.id = external_value.carryover_origin_report_line_id
                                                              AND old_report_line.report_id = %s
                   JOIN account_report_line AS new_report_line ON new_report_line.code = old_report_line.code
                                                              AND new_report_line.report_id = %s;
    """, (vat_report_id, monthly_vat_report_id))
    carryover_origin_info = cr.fetchall()
    old2new_origin = dict(carryover_origin_info)
    data_to_insert = [
        (code2expression_id[report_line_code], old2new_origin.get(carryover_origin_report_line_id, carryover_origin_report_line_id), *other_external_vals)
        for report_id, _, report_line_code, carryover_origin_report_line_id, *other_external_vals in report_info
        if report_id == vat_report_id
    ]

    for sub_data in split_every(IN_MAX, data_to_insert, list):
        cr.execute(SQL("""
        INSERT INTO account_report_external_value (
                        target_report_expression_id,
                        carryover_origin_report_line_id,
                        %s
                    )
            SELECT *
            FROM UNNEST(%s)
        ON CONFLICT DO NOTHING
            """,
            SQL(", ").join(SQL.identifier(col) for col in external_value_cols),
            SQL(", ").join(map(list, zip(*sub_data))),
        ))

    # Archive the old report
    cr.execute("""
        UPDATE account_report
           SET active = FALSE
         WHERE id = %s
    """, (vat_report_id,))
