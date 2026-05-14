from psycopg2.extras import execute_values

from odoo import SUPERUSER_ID, api

# (rec_name_regex, name_en, desc_en, desc_ar, notes_en, tax_scope)
TAX_VALUES_MAPPING = [
    (
        r'^\d+_sa_local_sales_tax_0$',
        '0%',
        'Not Subject to VAT',
        'غير خاضعة لضريبة القيمة المضافة.',
        'Not Subject to VAT.',
        None,
    ),
    (
        r'^\d+_sa_export_sales_tax_0$',
        '0% EX G',
        'Zero-rated exports - Export of Goods',
        'تصدير البضائع.',
        'Export of Goods.',
        'consu',
    ),
    (
        r'^\d+_sa_exempt_sales_tax_0$',
        '0% EXT FS',
        'Exempt - Financial services mentioned in Article 29 of the VAT Regulations',
        'الخدمات المالية المذكورة في القانون 29 في لوائح ضريبة القيمة المضافة.',
        'Financial services mentioned in Article 29 of the VAT Regulations.',
        None,
    ),
]


def migrate(cr, version):
    # Update names, descriptions, legal notes and JSONB translations
    execute_values(cr, """
        WITH data(rec_name, name_en, desc_en, desc_ar, notes_en, tax_scope) AS (
            VALUES %s
        )
        UPDATE account_tax AS t
        SET
            name = jsonb_build_object('en_US', data.name_en),
            description = jsonb_build_object('en_US', data.desc_en, 'ar_001', data.desc_ar),
            invoice_legal_notes = jsonb_build_object('en_US', data.notes_en),
            tax_scope = COALESCE(data.tax_scope, t.tax_scope)
        FROM ir_model_data AS imd
        JOIN data ON imd.name ~ data.rec_name
        WHERE imd.model = 'account.tax'
        AND imd.res_id = t.id;
    """, TAX_VALUES_MAPPING)

    """ Remove the tags on these taxes to avoid having clearly misconfigured ones """
    tax_xmlid_regex = "_sa_(?:local_sales_tax_0|export_sales_tax_0|exempt_sales_tax_0|purchases_tax_0|exempt_purchases_tax|rcp_tax_15)$"
    cr.execute(
        """
        WITH tags_to_delete AS (
            SELECT tag_rel.*
                FROM account_account_tag_account_tax_repartition_line_rel AS tag_rel
                JOIN account_tax_repartition_line AS rep_line
                  ON rep_line.id = tag_rel.account_tax_repartition_line_id
                JOIN account_tax AS tax
                  ON tax.id = rep_line.tax_id
                JOIN ir_model_data AS imd_taxes
                  ON imd_taxes.res_id = tax.id
                 AND imd_taxes.model = 'account.tax'
                 AND imd_taxes.module = 'account'
                JOIN res_company company
                  ON company.chart_template = 'sa'
               WHERE rep_line.repartition_type = 'tax'
                 AND imd_taxes.name ~ ('^' || company.id || %s)
        )
        DELETE
            FROM account_account_tag_account_tax_repartition_line_rel AS tag_rel
           USING tags_to_delete t
           WHERE tag_rel.account_tax_repartition_line_id = t.account_tax_repartition_line_id
             AND tag_rel.account_account_tag_id = t.account_account_tag_id;
        """,
        [tax_xmlid_regex],
    )

    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search([("chart_template", "=", "sa")], order="parent_path"):
        env["account.chart.template"].try_loading("sa", company)
