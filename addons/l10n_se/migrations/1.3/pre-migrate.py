# Part of Odoo. See LICENSE file for full copyright and licensing details.


def migrate(cr, version):
    """The former 'se' template was a reduced K2 ("K2 mini") and is now a hidden
    base template. Companies using it continue on the full K2 chart.

    The template code must be switched before the chart is reloaded: Odoo treats
    a different template code as a change of chart rather than a reload.
    The affected companies are remembered so end-migrate can add the K2 accounts
    they are missing.
    """
    cr.execute("""
        CREATE TABLE IF NOT EXISTS l10n_se_k2_mini_companies AS
        SELECT id AS company_id FROM res_company WHERE chart_template = 'se'
    """)
    cr.execute("UPDATE res_company SET chart_template = 'se_K2' WHERE chart_template = 'se'")
