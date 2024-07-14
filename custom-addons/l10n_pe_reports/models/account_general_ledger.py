# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
from io import StringIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import groupby
from odoo.tools.float_utils import float_repr
from odoo.addons.l10n_pe_reports.models.res_company import CHART_OF_ACCOUNTS


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        # Overridden to add export button on GL for Peruvian companies
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        if self.env.company.account_fiscal_country_id.code == "PE":
            options["buttons"].append({
                "name": _("PLE 5.1"),
                "sequence": 30,
                "action": "export_file",
                "action_param": "l10n_pe_export_ple_51_to_txt",
                "file_export_type": _("TXT"),
            })
            options["buttons"].append({
                "name": _("PLE 5.3"),
                "sequence": 35,
                "action": "export_file",
                "action_param": "l10n_pe_export_ple_53_to_txt",
                "file_export_type": _("TXT"),
            })
            options["buttons"].append({
                "name": _("PLE 6.1"),
                "sequence": 40,
                "action": "export_file",
                "action_param": "l10n_pe_export_ple_61_to_txt",
                "file_export_type": _("TXT"),
            })

    def _l10n_pe_get_file_txt(self, options, data, report_number):
        txt_result = ""
        if data:
            csv.register_dialect("pipe_separator", delimiter="|", skipinitialspace=True, lineterminator='|\n')
            output = StringIO()
            writer = csv.DictWriter(output, dialect="pipe_separator", fieldnames=data[0].keys())
            writer.writerows(data)
            txt_result = output.getvalue()

        # The name of the file is based on this link
        # http://orientacion.sunat.gob.pe/index.php/empresas-menu/libros-y-registros-vinculados-asuntos-tributarios-empresas/sistema-de-libros-electronicos-ple/6560-05-nomenclatura-de-libros-electronicos
        date_from = fields.Date.to_date(options["date"]["date_from"])
        has_data = "1" if data else "0"
        report_filename = "LE%s%s%02d00%s00001%s11" % (
            self.env.company.vat, date_from.year, date_from.month, report_number, has_data)

        return {
            "file_name": report_filename,
            "file_content": txt_result.encode(),
            "file_type": "txt",
        }

    @api.model
    def l10n_pe_export_ple_51_to_txt(self, options):
        txt_data = self._l10n_pe_get_txt_data(options)

        return self._l10n_pe_get_file_txt(options, txt_data, "0501")

    @api.model
    def l10n_pe_export_ple_53_to_txt(self, options):
        if self.env.company.account_fiscal_country_id.code != 'PE':
            raise UserError(_("Only Peruvian company can generate PLE 5.3 report."))

        txt_data = self._l10n_pe_get_txt_53_data(options)
        return self._l10n_pe_get_file_txt(options, txt_data, "0503")

    @api.model
    def l10n_pe_export_ple_61_to_txt(self, options):
        txt_data = self._l10n_pe_get_txt_data(options)
        return self._l10n_pe_get_file_txt(options, txt_data, "0601")

    def _l10n_pe_get_txt_data(self, options):
        """ Generates the TXT content for the PLE reports with the entries data """
        def _get_ple_document_type(move_type, country_code, document_type):
            if move_type in ("out_invoice", "out_refund"):
                return "140100"
            if move_type in ("in_invoice", "in_refund") and country_code == "PE" and document_type not in ("91", "97", "98"):
                return "080100"
            if move_type in ("in_invoice", "in_refund") and country_code != "PE" and document_type in ("91", "97", "98"):
                return "080200"
            return ""

        # Retrieve the data from the ledger itself, unfolding every group
        ledger = self.env['account.report'].browse(options['report_id'])
        # Options ---------------------------------
        # We don't need all companies
        options['companies'] = [{'name': self.env.company.name, 'id': self.env.company.id}]

        # Prepare query to get lines
        domain = ledger._get_options_domain(options, "strict_range")

        self.env['account.move.line'].check_access_rights('read')
        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)
        query.left_join('account_move_line', 'move_id', 'account_move', 'id', 'move')
        query.left_join('account_move_line', 'currency_id', 'res_currency', 'id', 'currency')
        query.left_join('account_move_line', 'account_id', 'account_account', 'id', 'account')
        query.left_join('account_move_line', 'journal_id', 'account_journal', 'id', 'journal')
        query.left_join('account_move_line__move', 'partner_id', 'res_partner', 'id', 'partner')

        query.left_join('account_move_line__move__partner', 'country_id', 'res_country', 'id', 'country')
        query.left_join('account_move_line__move', 'l10n_latam_document_type_id', 'l10n_latam_document_type', 'id', 'doctype')
        query.left_join('account_move_line__move__partner', 'l10n_latam_identification_type_id', 'l10n_latam_identification_type', 'id',
                        'idtype')
        query.order = 'account_move_line.date, account_move_line.id'
        qu = query.select('account_move_line.id',
                          'account_move_line.name',
                          'account_move_line.date',
                          'amount_currency',
                          'debit',
                          'credit',
                          'account_move_line__account.code AS account_code',
                          'account_move_line__account.name AS account_name',
                          'account_move_line__journal.name AS journal_name',
                          'account_move_line__move.l10n_pe_sunat_transaction_type',
                          'account_move_line__currency.name AS currency_name',
                          'account_move_line.move_id',
                          'account_move_line__move.date AS move_date',
                          'account_move_line__move.name AS move_name',
                          'account_move_line__move.invoice_date_due AS move_date_due',
                          'account_move_line__move.invoice_date AS move_invoice_date',
                          'account_move_line__move.move_type',
                          'account_move_line__move__doctype.code AS document_type',
                          'account_move_line__move__partner.vat AS partner_vat',
                          'account_move_line__move__partner__idtype.l10n_pe_vat_code AS partner_document_type',
                          'account_move_line__move__partner__country.code AS country_code',
                          )

        self.env.cr.execute(qu)
        lines_data = self._cr.dictfetchall()

        data = []
        ple = self.env["l10n_pe.tax.ple.report.handler"]

        period = options["date"]["date_from"].replace("-", "")
        for _move_id, line_vals in groupby(lines_data, lambda line: line["move_id"]):
            for count, line in enumerate(line_vals, start=1):
                serie_folio = ple._get_serie_folio(line["move_name"]  or "")
                transaction_type = line["l10n_pe_sunat_transaction_type"]
                ple_journal_type = "M" if not transaction_type else ("A" if transaction_type == "opening" else "C" if transaction_type == "closing" else "")
                ple_document_type = _get_ple_document_type(line["move_type"], line["country_code"], line["document_type"])
                data.append(
                    {
                        "period": "%s00" % period[:6],
                        "cuo": line["move_id"],
                        "number": "%s%s" % (ple_journal_type, count),
                        "account": line["account_code"],
                        "code": "",
                        "analytic": "",
                        "currency": line["currency_name"],
                        "partner_type": line["partner_document_type"] or "",
                        "partner_number": line["partner_vat"] or "",
                        "document_type": line["document_type"] if ple_document_type else "00",
                        "serie": serie_folio["serie"].replace(" ", "").replace("/", ""),
                        "folio": serie_folio["folio"].replace(" ", ""),
                        "date": line["date"].strftime("%d/%m/%Y") if line["move_date"] else "",
                        "due_date": line["move_date_due"].strftime("%d/%m/%Y") if line["move_date_due"] else "",
                        "invoice_date": (line["move_invoice_date"] or line["move_date"]).strftime("%d/%m/%Y") if line["move_invoice_date"] or line["date"] else "",
                        "glosa": line["move_name"].replace(" ", "").replace("/", ""),
                        "glosa_ref": "",
                        "debit": float_repr(line["debit"], precision_digits=2),
                        "credit": float_repr(line["credit"], precision_digits=2),
                        "book": "%s&%s&%s&%s" % (
                            ple_document_type,
                            "%s00" % period[:6],
                            line["move_id"],
                            "%s%s" % (ple_journal_type, count)
                        ) if ple_document_type else "",
                        "state": "1",
                    }
                )
        return data

    def _l10n_pe_get_txt_53_data(self, options):
        accounts = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('account_type', '!=', 'equity_unaffected'),
        ])

        data = []
        period = options["date"]["date_from"].replace("-", "")
        chart = self.env.company.l10n_pe_chart_of_accounts
        for account in accounts:
            data.append(
                {
                    "period": period[:8],
                    "code": account.code,
                    "name": account.name[:100],
                    "chart_account_code": (chart or "").zfill(2),
                    "chart_account_name": dict(CHART_OF_ACCOUNTS).get(chart, ""),
                    "corporative_account": "",
                    "corporative_account_name": "",
                    "state": "1",
                }
            )

        return data
