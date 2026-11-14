import json

from odoo.tools import SQL


def migrate(cr, version):
    rename_map = {
        "1. Standard Rates 15% (Base)": "1(B)",
        "1. Standard Rates 15% (Tax)": "1(T)",
        "3. Local Sales Subject to 0% (Base)": "3(B)",
        "4. Export Sales (Base)": "4(B)",
        "5. Exempt Sales (Base)": "5(B)",
        "7. Standard rated 15% Purchases (Base)": "7(B)",
        "7. Standard rated 15% Purchases (Tax)": "7(T)",
        "9. Imports subject to reverse charge mechanism (Base)": "9(B)",
        "9. Imports subject to reverse charge mechanism (Tax)": "9(T)",
        "8. Taxable Imports 15% Paid to Customs (Base)": "8(B)",
        "8. Taxable Imports 15% Paid to Customs (Tax)": "8(T)",
        "10. Zero Rated Purchases (Base)": "10(B)",
        "11. Exempt Purchases (Base)": "11(B)",
        "Withholding Tax 5% (Rental) (Base)": "1(B)_W_G",
        "Withholding Tax 5% (Rental) (Tax)": "1(T)_W_G",
        "Withholding Tax 5% (Tickets or Air Freight) (Base)": "2(B)_W_G",
        "Withholding Tax 5% (Tickets or Air Freight) (Tax)": "2(T)_W_G",
        "Withholding Tax 5% (International Telecommunication)(Base)": "3(B)_W_G",
        "Withholding Tax 5% (International Telecommunication)(Tax)": "3(T)_W_G",
        "Withholding Tax 5% (Distributed Profits) (Base)": "4(B)_W_G",
        "Withholding Tax 5% (Distributed Profits) (Tax)": "4(T)_W_G",
        "Withholding Tax 5% (Insurance & Reinsurance) (Base)": "5(B)_W_G",
        "Withholding Tax 5% (Insurance & Reinsurance) (Tax)": "5(T)_W_G",
        "Withholding Tax 15% (Royalties)(Base)": "6(B)_W_G",
        "Withholding Tax 15% (Royalties)(Tax)": "6(T)_W_G",
        "Withholding Tax 15% (Others)(Base)": "7(B)_W_G",
        "Withholding Tax 15% (Others)(Tax)": "7(T)_W_G",
        "Withholding Tax 20% (Managerial)(Base)": "8(B)_W_G",
        "Withholding Tax 20% (Managerial)(Tax)": "8(T)_W_G",
    }

    sql_name_mappings_list = []
    for old_name, new_name in rename_map.items():
        sql_name_mappings_list.append(
            SQL(
                "WHEN %s THEN jsonb_build_object('en_US', %s)",
                old_name,
                new_name,
            )
        )

    rename_json = json.dumps(rename_map)

    # DBs that have both the old and the new tag (duplicates): old_id -> new_id
    cr.execute(
        """
        SELECT old_t.id, new_t.id
          FROM jsonb_each_text(%s::jsonb) AS v(old_name, new_name)
          JOIN account_account_tag AS old_t
            ON old_t.name->>'en_US' = v.old_name
           AND old_t.applicability = 'taxes'
          JOIN res_country AS c
            ON c.id = old_t.country_id
           AND c.code = 'SA'
          JOIN account_account_tag AS new_t
            ON new_t.name->>'en_US' = v.new_name
           AND new_t.applicability = old_t.applicability
           AND new_t.country_id = old_t.country_id
        """,
        [rename_json],
    )
    id_map = dict(cr.fetchall())

    if id_map:
        old_ids = list(id_map)
        new_ids = list(id_map.values())

        for rel_table, other_column in (
            ("account_account_tag_account_move_line_rel", "account_move_line_id"),
            ("account_account_tag_account_tax_repartition_line_rel", "account_tax_repartition_line_id"),
        ):
            cr.execute(
                SQL(
                    """
                    INSERT INTO %(rel)s (account_account_tag_id, %(other)s)
                    SELECT m.new_id, rel.%(other)s
                      FROM %(rel)s AS rel
                      JOIN UNNEST(%(old_ids)s::int[], %(new_ids)s::int[]) AS m(old_id, new_id)
                        ON rel.account_account_tag_id = m.old_id
                    ON CONFLICT DO NOTHING
                    """,
                    rel=SQL.identifier(rel_table),
                    other=SQL.identifier(other_column),
                    old_ids=old_ids,
                    new_ids=new_ids,
                )
            )
            cr.execute(
                SQL(
                    """
                    DELETE FROM %(rel)s
                          WHERE account_account_tag_id = ANY(%(old_ids)s)
                    """,
                    rel=SQL.identifier(rel_table),
                    old_ids=old_ids,
                )
            )

        # Delete the old (duplicate) tags
        cr.execute(
            "DELETE FROM account_account_tag WHERE id = ANY(%s)",
            [old_ids],
        )

    cr.execute(
        SQL(
            """
            UPDATE account_account_tag
                SET name = CASE name->>'en_US'
                %s
                ELSE name
                END
                WHERE applicability = 'taxes'
                AND country_id = (SELECT id FROM res_country WHERE code = 'SA')
            """,
            SQL("\n").join(sql_name_mappings_list),
        ),
    )
