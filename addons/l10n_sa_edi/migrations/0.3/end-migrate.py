from psycopg2.extras import execute_values

EXEMPTION_REASON_MAPPING = [
    ('_sa_local_sales_tax_0', 'VATEX-SA-OOS'),
    ('_sa_export_sales_tax_0', 'VATEX-SA-32'),
    ('_sa_exempt_sales_tax_0', 'VATEX-SA-29'),
]


def migrate(cr, version):
    # Set correct exemption reason codes for Saudi 0% and exempt taxes.
    execute_values(cr, """
        WITH reason_map(rec_name, exemption_code) AS (
            VALUES %s
        )
        UPDATE account_tax AS t
        SET l10n_sa_exemption_reason_code = reason_map.exemption_code
        FROM ir_model_data AS imd
        JOIN reason_map ON imd.name ~ reason_map.rec_name
        WHERE imd.model = 'account.tax'
        AND imd.res_id = t.id;
    """, EXEMPTION_REASON_MAPPING)
