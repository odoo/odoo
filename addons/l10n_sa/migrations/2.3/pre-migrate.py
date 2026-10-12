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

    cr.execute(
        SQL(
            """
            WITH rename_cte(old_name, new_name) AS (VALUES %s)
            SELECT old_name, new_name
              INTO TEMP TABLE tmp_account_tag_rename
              FROM rename_cte
            """,
            SQL(", ").join(
                SQL("(%s, %s)", old_name, new_name)
                for old_name, new_name in rename_map.items()
            ),
        ),
    )

    cr.execute(
        """
        UPDATE account_account_tag AS t
           SET name = jsonb_build_object('en_US', v.new_name)
          FROM tmp_account_tag_rename AS v
         WHERE t.name->>'en_US' = v.old_name
           AND t.applicability = 'taxes'
           AND t.country_id = (SELECT id FROM res_country WHERE code = 'SA')
           AND NOT EXISTS (
               SELECT 1
                 FROM account_account_tag AS t2
                WHERE t2.id != t.id
                  AND t2.applicability = t.applicability
                  AND t2.country_id = t.country_id
                  AND t2.name->>'en_US' = v.new_name
           )
        """
    )
