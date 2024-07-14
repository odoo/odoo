# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import re
from datetime import datetime
from io import StringIO

from odoo import _, api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError


class PeruvianTaxPleReportCustomHandler(models.AbstractModel):
    _name = "l10n_pe.tax.ple.report.handler"
    _inherit = "account.tax.report.handler"
    _description = "PLE Generic Report"

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault("buttons", []).append(
            {
                "name": _("TXT"),
                "sequence": 30,
                "action": "export_file",
                "action_param": "export_to_txt",
                "file_export_type": _("TXT"),
            }
        )

    @api.model
    def _get_serie_folio(self, number):
        values = {"serie": "", "folio": ""}
        number_matchs = [rn for rn in re.finditer("\\d+", number or "")]
        if number_matchs:
            last_number_match = number_matchs[-1]
            values["serie"] = number[: last_number_match.start()].replace("-", "") or ""
            values["folio"] = last_number_match.group() or ""
        return values

    def _get_ple_report_data(self, options, current_groupby):
        def build_result(query_res_lines):
            def build_result_dict(query_res_lines):
                result = {
                    "document_type": None,
                    "date": None,
                    "customer_vat": None,
                    "customer": None,
                    "amount_total": None,
                    "invoice_date": None,
                    "base_exp": None,
                    "base_igv": None,
                    "tax_igv": None,
                    "base_exo": None,
                    "base_ina": None,
                    "tax_isc": None,
                    "base_ivap": None,
                    "tax_ivap": None,
                    "vat_icbper": None,
                    "vat_igv_g_ng": None,
                    "vat_igv_ng": None,
                    "base_free": None,
                    "vat_other": None,
                    "base_withholdings": None,
                }
                if current_groupby and query_res_lines:
                    sign_total = -1 if query_res_lines[0]["move_type"] in ("out_invoice", "out_refund") else 1
                    rate = (
                        (query_res_lines[0]["amount_currency"] / query_res_lines[0]["total"])
                        if query_res_lines[0]["total"]
                        else 1
                    )
                    refund = query_res_lines[0]["reversed_entry_name"]
                    result = {
                        "move_name": query_res_lines[0]["move_name"],
                        "invoice_date": query_res_lines[0]["invoice_date"],
                        "date": query_res_lines[0]["date"],
                        "date_due": query_res_lines[0]["invoice_date_due"],
                        "document_type": query_res_lines[0]["document_type"],
                        "partner_lit": query_res_lines[0]["partner_lit"],
                        "partner_lit_code": query_res_lines[0]["partner_lit_code"],
                        "id_number": query_res_lines[0]["partner_vat"],
                        "customer_vat": query_res_lines[0]["partner_vat"],
                        "customer": query_res_lines[0]["partner_name"],
                        "amount_total": query_res_lines[0]["amount_currency"] * (sign_total * -1),
                        "currency": query_res_lines[0]["currency_name"],
                        "rate": abs(rate),
                        "base_igv": (query_res_lines[0]["base_igv"] or 0) * sign_total,
                        "tax_igv": (query_res_lines[0]["vat_igv"] or 0) * sign_total,
                        "base_igv_g_ng": query_res_lines[0]["base_igv_g_ng"],
                        "vat_igv_g_ng": query_res_lines[0]["vat_igv_g_ng"],
                        "base_igv_ng": query_res_lines[0]["base_igv_ng"],
                        "vat_igv_ng": query_res_lines[0]["vat_igv_ng"],
                        "base_exo": (query_res_lines[0]["base_exo"] or 0) * sign_total,
                        "base_ina": (query_res_lines[0]["base_ina"] or 0) * sign_total,
                        "base_ivap": (query_res_lines[0]["vat_ivap"] or 0) * sign_total,
                        "base_exp": (query_res_lines[0]["base_exp"] or 0) * sign_total,
                        "tax_ivap": (query_res_lines[0]["vat_ivap"] or 0) * sign_total,
                        "vat_icbper": (query_res_lines[0]["vat_icbper"] or 0) * sign_total,
                        "tax_isc": (query_res_lines[0]["vat_isc"] or 0) * sign_total,
                        "base_free": query_res_lines[0]["base_free"],
                        "vat_other": query_res_lines[0]["vat_other"],
                        "base_withholdings": query_res_lines[0]["base_withholding"],
                        "detraction_date": query_res_lines[0]["detraction_date"],
                        "detraction_number": query_res_lines[0]["detraction_number"],
                        "emission_date_related": query_res_lines[0]["reversed_entry_date"]
                        if refund
                        else query_res_lines[0]["debit_origin_date"],
                        "document_type_related": query_res_lines[0]["reversed_entry_document_type"]
                        if refund
                        else query_res_lines[0]["debit_origin_document_type"],
                        "related_document": query_res_lines[0]["reversed_entry_name"]
                        if refund
                        else query_res_lines[0]["debit_origin_name"],
                        "status": query_res_lines[0]["state"],
                        "edi_state": query_res_lines[0]["edi_state"],
                        "invoice_dua_name": query_res_lines[0]["invoice_dua_name"],
                        "invoice_dua_document_type": query_res_lines[0]["invoice_dua_document_type"],
                        "invoice_dua_date": query_res_lines[0]["invoice_dua_date"],
                        "partner_country_code": query_res_lines[0]["partner_country_code"],
                        "partner_street": query_res_lines[0]["partner_street"],
                        "partner_country_agreement_code": query_res_lines[0]["partner_country_agreement_code"],
                        "usage_type_code": query_res_lines[0]["usage_type_code"],
                        "service_modality": query_res_lines[0]["service_modality"],
                        "company_vat": query_res_lines[0]["company_vat"],
                        "company_name": query_res_lines[0]["company_name"],
                    }
                return result

            if not current_groupby:
                return build_result_dict(query_res_lines)
            result = []

            all_res_per_grouping_key = {}
            for query_res in query_res_lines:
                grouping_key = query_res[current_groupby]
                all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

            for grouping_key, query_res_lines in all_res_per_grouping_key.items():
                result.append((grouping_key, build_result_dict(query_res_lines)))

            return result

        report = self.env["account.report"].browse(options["report_id"])
        _tables, where_clause, where_params = report._query_get(options, 'strict_range')
        if self.env.company.chart_template != 'pe':
            return build_result([])
        ref = self.env.ref
        cid = self.env.company.id
        try:
            tax_group_igv = ref(f"account.{cid}_tax_group_igv").id
            tax_group_igv_g_ng = ref(f"account.{cid}_tax_group_igv_g_ng").id
            tax_group_igv_ng = ref(f"account.{cid}_tax_group_igv_ng").id
            tax_group_exp = ref(f"account.{cid}_tax_group_exp").id
            tax_group_exo = ref(f"account.{cid}_tax_group_exo").id
            tax_group_ina = ref(f"account.{cid}_tax_group_ina").id
            tax_group_ivap = ref(f"account.{cid}_tax_group_ivap").id
            tax_group_icbper = ref(f"account.{cid}_tax_group_icbper").id
            tax_group_isc = ref(f"account.{cid}_tax_group_isc").id
            tax_group_gra = ref(f"account.{cid}_tax_group_gra").id
            tax_group_other = ref(f"account.{cid}_tax_group_other").id
            tax_group_ret = ref(f"account.{cid}_tax_group_ret").id
        except ValueError:
            raise UserError(_("In order to generate the PLE reports, please update l10n_pe module to update the required data."))

        query = f"""
SELECT
    account_move_line__move_id.id,
    account_move_line__move_id.name as move_name,
    account_move_line__move_id.ref as move_ref,
    account_move_line__move_id.edi_state,
    rp.name as partner_name,
    rp.vat as partner_vat,
    rp.street as partner_street,
    lit.name->>'en_US' as partner_lit,
    lit.l10n_pe_vat_code as partner_lit_code,
    rp.country_id as partner_country_id,
    rpc.l10n_pe_code as partner_country_code,
    rpc.l10n_pe_agreement_code as partner_country_agreement_code,
    account_move_line__move_id.currency_id,
    rc.name as currency_name,
    account_move_line__move_id__l10n_latam_document_type_id.code as document_type,
    account_move_line__move_id.l10n_pe_detraction_date as detraction_date,
    account_move_line__move_id.l10n_pe_detraction_number as detraction_number,
    account_move_line__move_id.l10n_pe_service_modality as service_modality,
    account_move_line__move_id.l10n_pe_usage_type_id as usage_type_id,
    lprt.code as usage_type_code,
    account_move_line__move_id.id as move_id,
    account_move_line__move_id.move_type,
    account_move_line__move_id.date,
    account_move_line__move_id.invoice_date,
    account_move_line__move_id.invoice_date_due,
    account_move_line__move_id.partner_id,
    account_move_line__move_id.journal_id,
    account_move_line__move_id.name,
    account_move_line__move_id.l10n_latam_document_type_id as l10n_latam_document_type_id,
    account_move_line__move_id.state,
    account_move_line__move_id.company_id,
    dua.name as invoice_dua_name,
    dua.invoice_date as invoice_dua_date,
    dua.l10n_latam_document_type_id as invoice_dua_document_type_id,
    ldt_dua.code as invoice_dua_document_type,
    reversed_entry.name as reversed_entry_name,
    reversed_entry.invoice_date as reversed_entry_date,
    reversed_entry.l10n_latam_document_type_id as reversed_entry_document_type_id,
    ldt_reversed_entry.code as reversed_entry_document_type,
    debit_origin.name as debit_origin_name,
    debit_origin.invoice_date as debit_origin_date,
    debit_origin.l10n_latam_document_type_id as debit_origin_document_type_id,
    ldt_debit_origin.code as debit_origin_document_type,
    partner_company.vat  AS company_vat,
    company.name AS company_name,
    sum(CASE WHEN btg.id = {tax_group_igv}
        THEN account_move_line.balance ELSE Null END) as base_igv,
    sum(CASE WHEN ntg.id = {tax_group_igv}
        THEN account_move_line.balance ELSE Null END) as vat_igv,
    sum(CASE WHEN btg.id = {tax_group_igv_g_ng}
        THEN account_move_line.balance ELSE Null END) as base_igv_g_ng,
    sum(CASE WHEN ntg.id = {tax_group_igv_g_ng}
        THEN account_move_line.balance ELSE Null END) as vat_igv_g_ng,
    sum(CASE WHEN btg.id = {tax_group_igv_ng}
        THEN account_move_line.balance ELSE Null END) as base_igv_ng,
    sum(CASE WHEN ntg.id = {tax_group_igv_ng}
        THEN account_move_line.balance ELSE Null END) as vat_igv_ng,
    sum(CASE WHEN btg.id = {tax_group_exp}
        THEN account_move_line.balance ELSE Null END) as base_exp,
    sum(CASE WHEN ntg.id = {tax_group_exp}
        THEN account_move_line.balance ELSE Null END) as vat_exp,
    sum(CASE WHEN btg.id = {tax_group_exo}
        THEN account_move_line.balance ELSE Null END) as base_exo,
    sum(CASE WHEN ntg.id = {tax_group_exo}
        THEN account_move_line.balance ELSE Null END) as vat_exo,
    sum(CASE WHEN btg.id = {tax_group_ina}
        THEN account_move_line.balance ELSE Null END) as base_ina,
    sum(CASE WHEN ntg.id = {tax_group_ina}
        THEN account_move_line.balance ELSE Null END) as vat_ina,
    sum(CASE WHEN btg.id = {tax_group_ivap}
        THEN account_move_line.balance ELSE Null END) as base_ivap,
    sum(CASE WHEN ntg.id = {tax_group_ivap}
        THEN account_move_line.balance ELSE Null END) as vat_ivap,
    sum(CASE WHEN btg.id = {tax_group_icbper}
        THEN account_move_line.balance ELSE Null END) as base_icbper,
    sum(CASE WHEN ntg.id = {tax_group_icbper}
        THEN account_move_line.balance ELSE Null END) as vat_icbper,
    sum(CASE WHEN btg.id = {tax_group_isc}
        THEN account_move_line.balance ELSE Null END) as base_isc,
    sum(CASE WHEN ntg.id = {tax_group_isc}
        THEN account_move_line.balance ELSE Null END) as vat_isc,
    sum(CASE WHEN btg.id = {tax_group_gra}
        THEN account_move_line.balance ELSE Null END) as base_free,
    sum(CASE WHEN ntg.id = {tax_group_gra}
        THEN account_move_line.balance ELSE Null END) as vat_free,
    sum(CASE WHEN btg.id = {tax_group_other}
        THEN account_move_line.balance ELSE Null END) as base_other,
    sum(CASE WHEN ntg.id = {tax_group_other}
        THEN account_move_line.balance ELSE Null END) as vat_other,
    sum(CASE WHEN btg.id = {tax_group_ret}
        THEN account_move_line.balance ELSE Null END) as base_withholding,
    sum(CASE WHEN ntg.id = {tax_group_ret}
        THEN account_move_line.balance ELSE Null END) as vat_withholding,
    account_move_line__move_id.amount_total as total,
    account_move_line__move_id.amount_total_signed as amount_currency
FROM
    account_move_line
LEFT JOIN
    account_move as account_move_line__move_id
    ON account_move_line.move_id = account_move_line__move_id.id
LEFT JOIN
    -- nt = net tax
    account_tax AS nt
    ON account_move_line.tax_line_id = nt.id
LEFT JOIN
    account_move_line_account_tax_rel AS account_move_linetr
    ON account_move_line.id = account_move_linetr.account_move_line_id
LEFT JOIN
    -- bt = base tax
    account_tax AS bt
    ON account_move_linetr.account_tax_id = bt.id
LEFT JOIN
    account_tax_group AS btg
    ON btg.id = bt.tax_group_id
LEFT JOIN
    account_tax_group AS ntg
    ON ntg.id = nt.tax_group_id
LEFT JOIN
    res_partner AS rp
    ON rp.id = account_move_line__move_id.commercial_partner_id
LEFT JOIN
    res_country AS rpc
    ON rpc.id = rp.country_id
LEFT JOIN
    l10n_latam_identification_type AS lit
    ON rp.l10n_latam_identification_type_id = lit.id
LEFT JOIN
    res_currency AS rc
    ON rc.id = account_move_line__move_id.currency_id
LEFT JOIN
    l10n_latam_document_type AS account_move_line__move_id__l10n_latam_document_type_id
    ON account_move_line__move_id__l10n_latam_document_type_id.id = account_move_line__move_id.l10n_latam_document_type_id
LEFT JOIN
    account_move AS reversed_entry
    ON reversed_entry.id = account_move_line__move_id.reversed_entry_id
LEFT JOIN
    l10n_latam_document_type AS ldt_reversed_entry
    ON ldt_reversed_entry.id = reversed_entry.l10n_latam_document_type_id
LEFT JOIN
    account_move AS debit_origin
    ON debit_origin.id = account_move_line__move_id.debit_origin_id
LEFT JOIN
    l10n_latam_document_type AS ldt_debit_origin
    ON ldt_debit_origin.id = debit_origin.l10n_latam_document_type_id
LEFT JOIN
    account_move AS dua
    ON dua.id = account_move_line__move_id.l10n_pe_dua_invoice_id
LEFT JOIN
    l10n_latam_document_type AS ldt_dua
    ON ldt_dua.id = dua.l10n_latam_document_type_id
LEFT JOIN
    l10n_pe_ple_usage AS lprt
    ON lprt.id = account_move_line__move_id.l10n_pe_usage_type_id
LEFT JOIN
    account_journal AS aj
    ON aj.id = account_move_line__move_id.journal_id
LEFT JOIN
    res_company AS company
    ON company.id = account_move_line__move_id.company_id
LEFT JOIN
    res_partner AS partner_company
    ON partner_company.id = company.partner_id
WHERE
    {where_clause}
    AND (account_move_line.tax_line_id is not null or btg.l10n_pe_edi_code is not null)
    AND aj.l10n_latam_use_documents
GROUP BY
    account_move_line__move_id.id, rp.id, lit.id, rc.id, account_move_line__move_id__l10n_latam_document_type_id.id,
    reversed_entry.id, ldt_reversed_entry.id, debit_origin.id,
    ldt_debit_origin.id, dua.id, ldt_dua.id, rpc.id, lprt.id, company.id, partner_company.id
ORDER BY
    account_move_line__move_id.date, account_move_line__move_id.name
        """

        self.env.cr.execute(query, where_params)
        query_res_lines = self.env.cr.dictfetchall()

        return build_result(query_res_lines)

    # TODO: To be deprecated
    def _get_document_status(self, state, invoice_date, date):
        """From SUNAT documentation:
        1. Required
        2. Register '0' when the operation (optional annotation without effect in the IGV) corresponds to the period
        3. Register '1' when the operation (taxed sales, exonerated, unaffected and/or exportation)
        corresponds to the period, like the credit and debit notes emitted on the period.
        4. Register '2' when the document has been disabled during the previous period to be delivered, emitted or
        during the emission.
        5. Register '6' when the emission date of the document payment o taxes payment, for operations
        that give right to tax credit, is before to that annotation period and this is inside of the next twelve
        months to the payment emission or tax payment, as appropriate.
        6. Register '8' when the operation (taxed sales, exonerated, unaffected and/or exportations)
        corresponds to the previous period and HAS NOT been registered in that period.
        7. Register '9' when the operation (taxed sales, exonerated, unaffected and/or exportations)
        corresponds to the previous period and HAS BEEN registered in that period."""

        value = 0
        if state == "cancel":
            value = 2
        elif state == "posted" and (invoice_date.month != date.month or invoice_date.year != date.year):
            value = 6
        elif state == "posted":
            value = 1
        return value

    def _get_report_number(self):
        return ""

    def _get_file_txt(self, options, data):
        txt_result = ""
        if data:
            csv.register_dialect("pipe_separator", delimiter="|", skipinitialspace=True)
            output = StringIO()
            writer = csv.DictWriter(output, dialect="pipe_separator", fieldnames=data[0].keys())
            writer.writerows(data)
            txt_result = output.getvalue()

        # The name of the file is based on this link
        # http://orientacion.sunat.gob.pe/index.php/empresas-menu/libros-y-registros-vinculados-asuntos-tributarios-empresas/sistema-de-libros-electronicos-ple/6560-05-nomenclatura-de-libros-electronicos
        date = datetime.strptime(options["date"]["date_from"], DEFAULT_SERVER_DATE_FORMAT)
        has_data = int(bool(data))
        report_filename = "LE%s%s%02d00%s1%s12" % (
            self.env.company.vat, date.year, date.month, self._get_report_number(), has_data)

        return {
            "file_name": report_filename,
            "file_content": txt_result.encode(),
            "file_type": "txt",
        }
