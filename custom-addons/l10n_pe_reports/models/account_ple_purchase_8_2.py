# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PeruvianTaxPle82ReportCustomHandler(models.AbstractModel):
    _name = "l10n_pe.tax.ple.8.2.report.handler"
    _inherit = "l10n_pe.tax.ple.report.handler"
    _description = "PLE Purchase Report 8.2 (Now RCE 8.5)"

    def _get_report_number(self):
        return "08050000"

    def export_to_txt(self, options):
        def format_float(amount):
            """Avoid -0 on TXT report"""
            if amount == 0:
                return abs(amount)
            return amount

        def _get_invoice_name(name, code):
            if not name or not code:
                return name
            return name.replace('%s ' % code, '')

        lines = self._get_ple_report_data(options, "move_id")
        data = []
        period = options["date"]["date_from"].replace("-", "")
        for line in lines:
            columns = line[1]
            serie_folio = self._get_serie_folio(columns["move_name"])
            serie_folio_dua = self._get_serie_folio(
                _get_invoice_name(columns["invoice_dua_name"], columns["invoice_dua_document_type"]))
            data.append(
                {
                    "period": "%s" % period[:6],
                    "car": "",
                    "invoice_date": columns["invoice_date"].strftime("%d/%m/%Y") if columns["invoice_date"] else "",
                    "document_type": columns["document_type"],
                    "document_serie": serie_folio["serie"].replace(" ", "")[1:],
                    "document_number": serie_folio["folio"].replace(" ", "").lstrip("0"),
                    "base_igv": format_float(columns["base_igv"]) or "0.0",
                    "other_concepts": "",  # Otros conceptos adicionales
                    "amount_total": columns["amount_total"] or "",
                    "dua_type": columns["invoice_dua_document_type"] or "",
                    "dua_serie": self._get_serie_folio(serie_folio_dua["serie"])["folio"].replace(" ", "")[1:],
                    "dua_dsi_year": columns["invoice_dua_date"].year if columns["invoice_dua_date"] else "",
                    "dua_number": serie_folio_dua["folio"].lstrip("0"),
                    "tax_igv": format_float(columns["tax_igv"]) or "",
                    "currency": columns["currency"],
                    "rate": ("%.3f" % abs(columns["rate"])) if columns["currency"] != "PEN" else "",
                    "client_country": columns["partner_country_code"] or "",
                    "customer": columns["customer"],
                    "client_address": (columns["partner_street"] or "")[:100],
                    "customer_vat": columns["customer_vat"] or "",
                    "payment_identification_number": "",
                    "payment_name": "",
                    "payment_country": "",
                    "relation": "",
                    "rent": "0.00",  # Renta Bruta
                    "deduction": "0.00",  # Deducción / Costo de Enajenación de bienes de capital
                    "rent_net": "0.00",  # Renta Neta
                    "withholding_rate": "0.00",  # Tasa de retención
                    "withholding_tax": "0.00",  # Impuesto retenido
                    "agreement": (columns["partner_country_agreement_code"] or "00").zfill(2),
                    "amount_exonerated_total": format_float(columns["base_exo"]) or "",
                    "rent_type": columns["usage_type_code"] or "",
                    "modality": columns["service_modality"] or "",
                    "art_76": "",  # Aplicación del penultimo parrafo del Art. 76° de la Ley del Impuesto a la Renta
                    "car_cp": "",
                    "final_pipe": "",  # this field is only to print a technical closing pipe
                }
            )

        return self._get_file_txt(options, data)

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['forced_domain'] = [
            *options.get('forced_domain', []),
            ("move_id.move_type", "in", ("in_invoice", "in_refund")),
            ("move_id.l10n_latam_document_type_id.code", "in", ("91", "97", "98")),
            ("move_id.partner_id.country_id.code", "!=", "PE"),
        ]

    def _report_custom_engine_ple_82(
        self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None
    ):
        report = self.env["account.report"].browse(options["report_id"])
        report._check_groupby_fields(
            (next_groupby.split(",") if next_groupby else []) + ([current_groupby] if current_groupby else [])
        )

        return self._get_ple_report_data(options, current_groupby)
