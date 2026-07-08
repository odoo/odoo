from odoo import models
from odoo.tools import SQL

# Mapping field names to corresponding column names
OPTIONAL_COLUMNS = {
    "aml_id": "aml.id",
    "aml_name": "aml.name",
    "aml_sequence": "aml.sequence",
    "move_ref": "move.ref",
    "product_id": "aml.product_id",
    "reversed_entry_id": "move.reversed_entry_id",
    "debit_origin_id": "move.debit_origin_id",
    "l10n_in_account_return_id": "move.l10n_in_account_return_id",
    "l10n_in_gstr2b_reconciliation_status": "move.l10n_in_gstr2b_reconciliation_status",
    "account_id": "aml.account_id",
    "currency_amount": "aml.amount_currency",
    "currency_id": "aml.currency_id",
    "l10n_in_shipping_bill_number": "move.l10n_in_shipping_bill_number",
    "l10n_in_shipping_bill_date": "move.l10n_in_shipping_bill_date",
    "l10n_in_shipping_port_code_id": "move.l10n_in_shipping_port_code_id",
}


class AccountTaxHelper(models.AbstractModel):
    _name = "account.tax.helper"
    _description = "Account Tax Helper"

    def _get_tax_details(
        self,
        domain,
        fields_to_include=(),
        include_non_itc=False,
    ):
        domain_query = self.env["account.move.line"]._search(domain)
        fields_to_include = set(fields_to_include)
        selected_columns = [
            (field_name, OPTIONAL_COLUMNS[field_name])
            for field_name in fields_to_include
            if field_name in OPTIONAL_COLUMNS
        ]
        optional_columns_sql = self._build_optional_columns_sql(selected_columns)
        non_itc_query = (
            SQL(
                '''
                HAVING BOOL_OR(CASE
                    WHEN rel.account_account_tag_id IN (%(non_itc_tag)s, %(other_non_itc_tag)s)
                    THEN TRUE
                    ELSE FALSE
                END) = TRUE;
                '''
                ,
                non_itc_tag=self.env.ref("l10n_in.tax_tag_non_itc").id,
                other_non_itc_tag=self.env.ref("l10n_in.tax_tag_other_non_itc").id,
            )
            if include_non_itc
            else SQL(";")
        )
        non_itc_tag_query = (
            SQL(
                '''
                , %(non_itc_tag)s
                , %(other_non_itc_tag)s
                ''',
                non_itc_tag=self.env.ref("l10n_in.tax_tag_non_itc").id,
                other_non_itc_tag=self.env.ref("l10n_in.tax_tag_other_non_itc").id,
            )
            if include_non_itc
            else SQL("")
        )

        self.env.cr.execute(
            SQL(
                '''
            DROP TABLE IF EXISTS gst_tax_details_by_base_lines;

            CREATE TEMPORARY TABLE gst_tax_details_by_base_lines ON COMMIT DROP AS
            SELECT aml.id AS base_line_id,
                   ANY_VALUE(aml.balance) AS base_amount,
                   ANY_VALUE(aml.move_id) AS move_id,
                   ANY_VALUE(aml.l10n_in_gstr_section) AS l10n_in_gstr_section,
                   ANY_VALUE(aml.l10n_in_hsn_code) AS l10n_in_hsn_code,
                   ANY_VALUE(aml.quantity) AS quantity,
                   ANY_VALUE(aml.product_uom_id) AS product_uom_id,
                   ANY_VALUE(move.commercial_partner_id) AS move_commercial_partner_id,
                   ANY_VALUE(move.name) AS move_name,
                   ANY_VALUE(move.move_type) AS move_type,
                   ANY_VALUE(move.invoice_date) AS invoice_date,
                   ANY_VALUE(move.amount_total_signed) AS amount_total_signed,
                   ANY_VALUE(move.l10n_in_state_id) AS l10n_in_state_id,
                   ANY_VALUE(move.l10n_in_gst_treatment) AS l10n_in_gst_treatment,
                   SUM(CASE
                           WHEN rel.account_account_tag_id = %(igst_tag)s
                           THEN td.tax_amount
                           ELSE 0
                       END) AS igst,
                   SUM(CASE
                           WHEN rel.account_account_tag_id = %(cgst_tag)s
                           THEN td.tax_amount
                           ELSE 0
                       END) AS cgst,
                   SUM(CASE
                           WHEN rel.account_account_tag_id = %(sgst_tag)s
                           THEN td.tax_amount
                           ELSE 0
                       END) AS sgst,
                   SUM(CASE
                           WHEN rel.account_account_tag_id = %(cess_tag)s
                           THEN td.tax_amount
                           ELSE 0
                       END) AS cess,
                   COALESCE(MAX(CASE WHEN rel.account_account_tag_id = %(igst_tag)s THEN tax.amount END), 0)
                   + COALESCE(MAX(CASE WHEN rel.account_account_tag_id = %(cgst_tag)s THEN tax.amount END), 0)
                   + COALESCE(MAX(CASE WHEN rel.account_account_tag_id = %(sgst_tag)s THEN tax.amount END), 0)
                   AS gst_tax_rate
                   %(optional_columns_sql)s
            FROM (
                SELECT account_move_line.*
                FROM %(aml_from_clause)s
                WHERE %(aml_where_clause)s
                  AND account_move_line.tax_repartition_line_id IS NULL
             ) as aml
             LEFT JOIN (%(tax_details_query)s) AS td
               ON td.base_line_id = aml.id
             LEFT JOIN account_tax tax
               ON tax.id = td.tax_id
             LEFT JOIN account_account_tag_account_tax_repartition_line_rel rel
               ON (
                   rel.account_tax_repartition_line_id = td.tax_repartition_line_id
                   AND rel.account_account_tag_id IN (
                       %(igst_tag)s,
                       %(cgst_tag)s,
                       %(sgst_tag)s,
                       %(cess_tag)s
                       %(non_itc_tag_query)s
                   )
              )
             JOIN account_move move
               ON move.id = aml.move_id
            GROUP BY aml.id
            %(non_itc_query)s
            ANALYZE gst_tax_details_by_base_lines
            ''',
                tax_details_query=self.env[
                    "account.move.line"
                ]._get_query_tax_details_from_domain(domain),
                aml_from_clause=domain_query.from_clause,
                aml_where_clause=domain_query.where_clause,
                igst_tag=self.env.ref("l10n_in.tax_tag_igst").id,
                cgst_tag=self.env.ref("l10n_in.tax_tag_cgst").id,
                sgst_tag=self.env.ref("l10n_in.tax_tag_sgst").id,
                cess_tag=self.env.ref("l10n_in.tax_tag_cess").id,
                non_itc_query=non_itc_query,
                non_itc_tag_query=non_itc_tag_query,
                optional_columns_sql=optional_columns_sql,
            )
        )

    def _build_optional_columns_sql(self, columns):
        fragments = [
            SQL(", ANY_VALUE(%s) AS %s", SQL.identifier(*column_name.split('.')), SQL.identifier(field_name))
            for field_name, column_name in columns
        ]
        return SQL("").join(fragments)
