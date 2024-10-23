# Part of Odoo. See LICENSE file for full copyright and licensing details.

def migrate(cr, version):
    cr.execute("""
        SELECT ar.name as report_name, arex.id as expression_id, arl.code, arev.*
        FROM account_report as ar
        inner join account_report_line as arl on ar.id = arl.report_id
        inner join account_report_expression as arex on arl.id = arex.report_line_id and arex.engine = 'external'
        left join account_report_external_value as arev on arex.id = arev.target_report_expression_id
        WHERE ar.country_id = 109
        AND ((ar.name->>'en_US' = 'VAT Report' and arev.company_id is not null) OR ar.name->>'en_US' = 'Monthly VAT Report')
        Order by expression_id;
    """)
    report_info = cr.fetchall()
    new_target = {info[2]: info[1] for info in report_info if info[0] == {'en_US': 'Monthly VAT Report'}}
    data_to_insert = []

    cr.execute("""
        SELECT DISTINCT arl.id as old_origin, tarl.id as new_origin
        FROM account_report_external_value arev
        inner join account_report_line as arl on arl.id = arev.carryover_origin_report_line_id
        inner join account_report_line as tarl on tarl.code = arl.code and tarl.id != arl.id;
    """)
    carryover_origin_info = cr.fetchall()
    new_origin = {info[0]: info[1] for info in carryover_origin_info}

    for record in report_info:
        if record[0] == {'en_US': 'VAT Report'}:
            data_to_insert.append((
                new_target[record[2]], record[5], record[6], new_origin[record[7]], record[8], record[9],
                record[10], record[11], record[12], record[13], record[14], record[15], record[16]
            ))

    insert_query = """
        INSERT INTO account_report_external_value(
            target_report_expression_id, company_id, foreign_vat_fiscal_position_id, carryover_origin_report_line_id,
            create_uid, write_uid, name, text_value, carryover_origin_expression_label, date, create_date, write_date, value
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """

    cr.executemany(insert_query, data_to_insert)

    # Archive the old report
    cr.execute("UPDATE account_report SET ACTIVE = false WHERE country_id = 109 and name->>'en_US' = 'VAT Report'")
