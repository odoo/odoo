# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountReport(models.Model):
    _inherit = 'account.report'

    @api.model
    def _get_options_all_entries_domain(self, options):
        """For sale reports, must be considered cancelled and posted documents"""
        result = super()._get_options_all_entries_domain(options)
        if self and self != self.env.ref("l10n_pe_reports.tax_report_ple_sales_14_1"):
            return result
        if options.get("all_entries"):
            return []
        return [("parent_state", "in", ("posted", "cancel"))]


class PeruvianTaxPle141ReportCustomHandler(models.AbstractModel):
    _name = "l10n_pe.tax.ple.14.1.report.handler"
    _inherit = "l10n_pe.tax.ple.report.handler"
    _description = "PLE Sales Report 14.1 (Now RVIE 14.2)"

    def _get_report_number(self):
        return "14040002"

    def export_to_txt(self, options):
        def format_float(amount):
            """Avoid -0 on TXT report"""
            if amount == 0:
                return abs(amount)
            return amount

        options.update({"force_all_entries": True})
        lines = self._get_ple_report_data(options, "move_id")
        data = []
        period = options["date"]["date_from"].replace("-", "")
        state_error = []
        for line in lines:
            columns = line[1]
            # Ignore entries on draft
            if columns["status"] == "draft":
                continue
            if (
                (columns["status"] == "posted" and columns["edi_state"] != "sent")
                or (columns["status"] == "cancel" and columns["edi_state"] and columns["edi_state"] != "cancelled")
            ):
                state_error.append(columns["move_name"])
                continue
            serie_folio = self._get_serie_folio(columns["move_name"])
            serie_folio_related = self._get_serie_folio(columns["related_document"])
            cancelled = columns["status"] == "cancel"
            data.append(
                {
                    "ruc": columns["company_vat"],
                    "company_name": columns["company_name"],
                    "period": "%s" % period[:6],
                    "car": "",
                    "invoice_date": columns["invoice_date"].strftime("%d/%m/%Y") if columns["invoice_date"] else "",
                    "date_due": "",
                    "document_type": columns["document_type"],
                    "document_serie": serie_folio["serie"].replace(" ", ""),
                    "document_number": serie_folio["folio"].replace(" ", ""),
                    "payment_number": "",  # Related payment not implemented yet
                    "customer_id": columns["partner_lit_code"],
                    "customer_vat": columns["customer_vat"] or "",
                    "customer": columns["customer"],
                    "base_exp": not cancelled and format_float(columns["base_exp"]) or "0.00",
                    "base_igv": not cancelled and format_float(columns["base_igv"]) or "0.00",
                    "amount_discount": "0.00",
                    "tax_igv": not cancelled and format_float(columns["tax_igv"]) or "0.00",
                    "tax_igv_discount": "0.00",
                    "base_exo": not cancelled and format_float(columns["base_exo"]) or "0.00",
                    "base_ina": not cancelled and format_float(columns["base_ina"]) or "0.00",
                    "tax_isc": not cancelled and format_float(columns["tax_isc"]) or "0.00",
                    "base_ivap": not cancelled and format_float(columns["base_ivap"]) or "0.00",
                    "tax_ivap": not cancelled and format_float(columns["tax_ivap"]) or "0.00",
                    "vat_icbper": not cancelled and format_float(columns["vat_icbper"]) or "0.00",
                    "tax_oth": "0.00",
                    "amount_total": not cancelled and columns["amount_total"] or "0.00",
                    "currency": columns["currency"],
                    "rate": ("%.3f" % abs(columns["rate"])) if columns["currency"] != "PEN" else "",
                    "emission_date_related": columns["emission_date_related"].strftime("%d/%m/%Y") if columns[
                        "emission_date_related"] else "",
                    "document_type_related": columns["document_type_related"] or "",
                    "related_document_serie": serie_folio_related.get("serie", "").replace(" ", ""),
                    "related_document_number": serie_folio_related.get("folio", "").replace(" ", ""),
                    "contract_identification_OSIC": "",  # Exclusive use of operators of irregular companies, consortia
                    "currency_error": "",
                    "canceled_by_payment": "",
                    "final_pipe": "",  # this field is only to print a technical closing pipe
                }
            )

        if state_error:
            raise UserError(_(
                "The state in the next documents is posted/cancelled but not stamped/cancelled in the SUNAT:\n\n%s", '\n'.join(
                    state_error)))

        return self._get_file_txt(options, data)

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['forced_domain'] = [
            *options.get('forced_domain', []),
            ("move_id.move_type", "in", ("out_invoice", "out_refund")),
        ]

    def _report_custom_engine_ple_14_1(
        self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None
    ):
        report = self.env["account.report"].browse(options["report_id"])
        report._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else []) + ([current_groupby] if current_groupby else [])
        )

        return self._get_ple_report_data(options, current_groupby)
