from psycopg2.extras import execute_values

# (rec_name_regex, name_en, desc_en, desc_ar, tax_scope)
TAX_VALUES_MAPPING = [
    (
        r'^\d+_sa_local_sales_tax_0$',
        '0%',
        'Not Subject to VAT',
        'غير خاضعة لضريبة القيمة المضافة.',
        None,
    ),
    (
        r'^\d+_sa_export_sales_tax_0$',
        '0% EX G',
        'Zero-rated exports - Export of Goods',
        'تصدير البضائع.',
        'consu',
    ),
    (
        r'^\d+_sa_exempt_sales_tax_0$',
        '0% EXT FS',
        'Exempt - Financial services mentioned in Article 29 of the VAT Regulations',
        'الخدمات المالية المذكورة في القانون 29 في لوائح ضريبة القيمة المضافة.',
        None,
    ),
]


def migrate(cr, version):
    # Update names, descriptions and JSONB translations
    execute_values(cr, """
        WITH data(rec_name, name_en, desc_en, desc_ar, tax_scope) AS (
            VALUES %s
        )
        UPDATE account_tax AS t
        SET
            name = jsonb_build_object('en_US', data.name_en),
            description = jsonb_build_object('en_US', data.desc_en, 'ar_001', data.desc_ar),
            tax_scope = COALESCE(data.tax_scope, t.tax_scope)
        FROM ir_model_data AS imd
        JOIN data ON imd.name ~ data.rec_name
        WHERE imd.model = 'account.tax'
        AND imd.res_id = t.id;
    """, TAX_VALUES_MAPPING)
