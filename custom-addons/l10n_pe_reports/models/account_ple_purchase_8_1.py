# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PeruvianTaxPle81ReportCustomHandler(models.AbstractModel):
    _name = "l10n_pe.tax.ple.8.1.report.handler"
    _inherit = "l10n_pe.tax.ple.report.handler"
    _description = "PLE Purchase Report 8.1 (Now RCE 8.4)"

    def _get_report_number(self):
        return "08040002"

    def export_to_txt(self, options):
        def format_float(amount):
            """Avoid -0 on TXT report"""
            if amount == 0:
                return abs(amount)
            return amount

        lines = self._get_ple_report_data(options, "move_id")
        data = []
        period = options["date"]["date_from"].replace("-", "")
        for line in lines:
            columns = line[1]
            serie_folio = self._get_serie_folio(columns["move_name"])
            serie_folio_related = self._get_serie_folio(columns["related_document"])
            data.append(
                {
                    "ruc": columns["company_vat"],
                    "company_name": columns["company_name"],
                    "period": "%s" % period[:6],
                    "car": "",
                    "invoice_date": columns["invoice_date"].strftime("%d/%m/%Y") if columns["invoice_date"] else "",
                    "date_due": columns["date_due"].strftime("%d/%m/%Y") if columns["date_due"] else "",
                    "document_type": columns["document_type"],
                    "document_serie": serie_folio["serie"].replace(" ", "")[1:],
                    "dua_dsi_year": columns["invoice_date"].year if columns["invoice_date"] and columns["document_type"] in ("50", "52") else "",
                    "document_number": serie_folio["folio"].replace(" ", "").lstrip("0"),
                    "last_payment_number": "",  # Related payment not implemented yet
                    "customer_id": columns["partner_lit_code"],
                    "customer_vat": columns["customer_vat"] or "",
                    "customer": columns["customer"],
                    "base_igv": format_float(columns["base_igv"]) or "0.0",
                    "tax_igv": format_float(columns["tax_igv"]) or "0.00",
                    "base_igv_mixto": format_float(columns["base_igv_g_ng"]) or "0.00",
                    "tax_igv_mixto": format_float(columns["vat_igv_g_ng"]) or "0.00",
                    "base_igv_ng": format_float(columns["base_igv_ng"]) or "0.00",
                    "vat_igv_ng": format_float(columns["vat_igv_ng"]) or "0.00",
                    "amount_no_taxed": format_float(
                        sum([columns["base_exo"] or 0, columns["base_ina"] or 0, columns["base_free"] or 0])) or "0.00",
                    "tax_isc": format_float(columns["tax_isc"]) or "0.00",
                    "tax_bl": format_float(columns["vat_icbper"]) or "0.00",
                    "vat_other": format_float(columns["vat_other"]) or "0.00",
                    "amount_total": columns["amount_total"] or "0.00",
                    "currency": columns["currency"],
                    "rate": ("%.3f" % abs(columns["rate"])) if columns["currency"] != "PEN" else "",
                    "emission_date_related": columns["emission_date_related"].strftime("%d/%m/%Y") if columns[
                        "emission_date_related"] else "",
                    "document_type_related": columns["document_type_related"] or "",
                    "related_document_serie": serie_folio_related.get("serie", "").replace(" ", "")[1:],
                    "aduana_code": serie_folio["serie"].replace(" ", "")[1:] if columns["document_type"] in ("50", "52") else "",
                    "related_document_number": serie_folio_related.get("folio", "").replace(" ", "").lstrip("0"),
                    "services": "",  # Clasificación de los bienes y servicios adquiridos
                    "contract_identification_OSIC": "",  # Not implemented yet
                    "percentage": "",
                    "tax_mbl": "",
                    "car_cp": "",
                    "date_cdd": columns["detraction_date"].strftime("%d/%m/%Y") if columns["detraction_date"] else "",
                    "name_cdd": columns["detraction_number"] or "",
                    "final_pipe": "",  # this field is only to print a technical closing pipe
                }
            )

        return self._get_file_txt(options, data)

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['forced_domain'] = [
            *options.get('forced_domain', []),
            ("move_id.move_type", "in", ("in_invoice", "in_refund")),
            ("move_id.l10n_latam_document_type_id.code", "not in", ("91", "97", "98")),
            ("move_id.partner_id.country_id.code", "=", "PE"),
        ]

    def _report_custom_engine_ple_81(
        self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None
    ):
        report = self.env["account.report"].browse(options["report_id"])
        report._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else []) + ([current_groupby] if current_groupby else [])
        )

        return self._get_ple_report_data(options, current_groupby)
