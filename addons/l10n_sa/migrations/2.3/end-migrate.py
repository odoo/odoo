from odoo import SUPERUSER_ID, api


def migrate(cr, version):
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
