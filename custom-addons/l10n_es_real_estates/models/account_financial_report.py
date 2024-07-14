# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import models, fields


class SpanishMod347TaxReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_es.mod347.tax.report.handler'

    def _get_real_estates_data(self, boe_report_options, currency_id):
        # Overrides the placeholder defined in l10n_reports
        count = self._retrieve_report_expression(boe_report_options, 'l10n_es_real_estates.mod_347_statistics_real_estates_count_balance')
        total = currency_id.round(self._retrieve_report_expression(boe_report_options, 'l10n_es_real_estates.mod_347_real_estates_balance'))
        return {'count': count, 'total': total}

    def export_boe(self, options):
        """ Overridden from l10n_es_reports to append the real estates record at
        the end of the generated BOE file.
        """
        result = super().export_boe(options)
        file_content = result['file_content']
        dummy, year = self._get_mod_period_and_year(options)
        current_company = self.env.company

        boe_report_options = self._build_boe_report_options(options, year)
        boe_wizard = self._retrieve_boe_manual_wizard(options, 347)
        manual_params = boe_wizard.l10n_es_get_partners_manual_parameters_map()
        negocio_required_a = self._get_required_partner_ids_for_boe('real_estates', year + '-01-01', year + '-12-31', boe_wizard, 'A', 'local_negocio')
        file_content += self._call_on_partner_sublines(boe_report_options, 'l10n_es_real_estates.mod_347_operations_real_estates_sold', lambda report_data: self._write_type2_partner_record(report_data, year, current_company, 'A', manual_parameters_map=manual_params, local_negocio=True), required_ids_set=negocio_required_a)

        negocio_required_b = self._get_required_partner_ids_for_boe('real_estates', year + '-01-01', year + '-12-31', boe_wizard, 'B', 'local_negocio')
        file_content += self._call_on_partner_sublines(boe_report_options, 'l10n_es_real_estates.mod_347_operations_real_estates_bought', lambda report_data: self._write_type2_partner_record(report_data, year, current_company, 'B', manual_parameters_map=manual_params, local_negocio=True), required_ids_set=negocio_required_b)

        file_content += self._call_on_partner_sublines(boe_report_options, 'l10n_es_real_estates.mod_347_real_estates', lambda report_data: self._write_type2_real_estates_records(report_data, year, current_company))

        result['file_content'] = file_content
        return result

    def _get_required_partner_ids_for_boe(self, mod_invoice_type, date_from, date_to, boe_wizard, operation_key, operation_class):
        rslt = super()._get_required_partner_ids_for_boe(mod_invoice_type, date_from, date_to, boe_wizard, operation_key, operation_class)

        real_estates_vat_data = boe_wizard.real_estates_vat_mod347_data.filtered(lambda x: x.operation_key == operation_key and x.operation_class == operation_class)
        rslt.update(real_estates_vat_data.mapped('partner_id.id'))

        return rslt

    def _write_type2_real_estates_records(self, report_data, year, current_company):
        line_real_estate = self.env['l10n_es_reports.real.estate'].browse(report_data['line_data']['id'])
        currency_id = current_company.currency_id

        # Group this real estate's invoices per partner
        invoice_partner_map = {}
        for invoice in line_real_estate.invoice_ids:
            partner = invoice.partner_id
            if partner not in invoice_partner_map:
                invoice_partner_map[partner] = []

            invoice_partner_map[partner].append(invoice)

        # This block of data is constant for each of the record associated to
        # this real_estate, so we compute it only once and concatenate it every
        # time in the loop.
        address = self._l10n_es_boe_format_string(line_real_estate.cadastral_reference, length=1)
        address += self._l10n_es_boe_format_string(line_real_estate.street_type, length=5)
        address += self._l10n_es_boe_format_string(line_real_estate.street_name, length=50)
        address += self._l10n_es_boe_format_string(line_real_estate.street_number_type, length=3)
        address += self._l10n_es_boe_format_string(line_real_estate.street_number and str(line_real_estate.street_number) or '', length=5)
        address += self._l10n_es_boe_format_string(line_real_estate.street_number_km_qualifier or '', length=3)
        address += self._l10n_es_boe_format_string(line_real_estate.street_block or '', length=3)
        address += self._l10n_es_boe_format_string(line_real_estate.portal or '', length=3)
        address += self._l10n_es_boe_format_string(line_real_estate.stairs or '', length=3)
        address += self._l10n_es_boe_format_string(line_real_estate.floor or '', length=3)
        address += self._l10n_es_boe_format_string(line_real_estate.door or '', length=3)
        address += self._l10n_es_boe_format_string(line_real_estate.address_complement or '', length=40)
        address += self._l10n_es_boe_format_string(line_real_estate.city or '', length=30)
        address += self._l10n_es_boe_format_string(line_real_estate.municipality, length=30)
        address += self._l10n_es_boe_format_string(line_real_estate.municipality_code, length=5)
        address += self._l10n_es_boe_format_string(line_real_estate.province_code, length=2)
        address += self._l10n_es_boe_format_string(line_real_estate.postal_code, length=5)
        address += self._l10n_es_boe_format_string(' ' * 167)

        # We generate a different record for each of the partners having rent this real estate
        rslt = self._l10n_es_boe_format_string('')
        for (partner, partner_invoices) in invoice_partner_map.items():
            rslt += self._l10n_es_boe_format_number(2)
            rslt += self._l10n_es_boe_format_number(347)
            rslt += self._l10n_es_boe_format_string(year, length=4)
            rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(current_company.partner_id), length=9)
            rslt += self._l10n_es_boe_format_string(self._extract_spanish_tin(partner, except_if_foreign=False), length=9)
            rslt += self._l10n_es_boe_format_string(' ' * 9) # TIN of the legal representative (only useful if under 14 years of age)
            rslt += self._l10n_es_boe_format_string(partner.display_name, length=40)
            rslt += self._l10n_es_boe_format_string('I')
            rslt += self._l10n_es_boe_format_string(' ' * 22) # Blank, constant

            convert = lambda i: i.currency_id._convert(i.amount_total_signed,
                                                       currency_id,
                                                       current_company,
                                                       i.date or fields.Date.today(),
                                                       round=True)
            year_amount_sum = currency_id.round(sum(convert(i) for i in partner_invoices))
            rslt += self._l10n_es_boe_format_number(year_amount_sum, length=16, decimal_places=2, signed=True, sign_pos=' ', in_currency=True)

            rslt += address

        return rslt

    def _report_custom_engine_operations_real_estates_bought(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        domain = [
            ('debit', '>', 0.0),
            ('move_id.l10n_es_reports_mod347_invoice_type', '=', 'real_estates'),
            ('move_id.move_type', 'in', ['in_invoice', 'in_refund'])
        ]

        return self._custom_threshold_common(domain, expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit)

    def _report_custom_engine_operations_real_estates_sold(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        domain = [
            ('debit', '>', 0.0),
            ('move_id.l10n_es_reports_mod347_invoice_type', '=', 'real_estates'),
            ('move_id.move_type', 'in', ['out_invoice', 'out_refund'])
        ]

        return self._custom_threshold_common(domain, expressions, options, date_scope, current_groupby, next_groupby, offset=offset, limit=limit)
