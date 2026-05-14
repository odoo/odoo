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
