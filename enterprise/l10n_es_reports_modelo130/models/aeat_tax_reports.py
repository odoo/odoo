# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SpanishMod130TaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_es_modelo130.mod130.tax.report.handler'
    _inherit = 'l10n_es.tax.report.handler'
    _description = 'Spanish Tax Report Custom Handler (Mod130)'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        super()._append_boe_button(options, 130)

    def open_boe_wizard(self, options, boe_number):
        result = super().open_boe_wizard(options, boe_number)
        result['res_model'] = 'l10n_es_reports_modelo130.aeat.boe.mod130.export.wizard'
        return result

    def _retrieve_boe_manual_wizard(self, options, modelo_number):
        # As the name of the module is now l10n_es_reports_modelo130 instead of l10n_es_reports,
        # we need to override this function
        return self.env['l10n_es_reports_modelo130.aeat.boe.mod130.export.wizard'].browse(options['l10n_es_reports_boe_wizard_id'])

    def export_boe(self, options):
        period, year = self._get_mod_period_and_year(options)
        # Legal requirement for the export of boe file for modelo 130
        boe_modelo_id = 'T13001000'

        rslt = f"<{boe_modelo_id}>".encode()
        report = self.env['account.report'].browse(options['report_id'])
        report_lines = report._get_lines(options)
        casilla_lines_map = self._retrieve_casilla_lines(report_lines)

        # Wizard with manually-entered data
        boe_wizard = self._retrieve_boe_manual_wizard(options, 130)

        rslt += self._l10n_es_boe_format_string(' ' * 1)
        rslt += self._l10n_es_boe_format_string(f'{boe_wizard.declaration_type}')
        rslt += self._l10n_es_boe_format_string(boe_wizard.taxpayer_id or 'n/a', length=9)
        rslt += self._l10n_es_boe_format_string(boe_wizard.taxpayer_last_name or 'n/a', length=60)
        rslt += self._l10n_es_boe_format_string(boe_wizard.taxpayer_first_name or 'n/a', length=20)
        rslt += self._l10n_es_boe_format_string(year, length=4)
        rslt += self._l10n_es_boe_format_string(period, length=2)

        # Content of the report
        for casilla in casilla_lines_map.values():
            rslt += self._l10n_es_boe_format_number(options, casilla, length=17, decimal_places=2, signed=True, in_currency=True)

        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and 'X' or ' ')
        rslt += self._l10n_es_boe_format_string(boe_wizard.complementary_declaration and boe_wizard.previous_report_number or '', length=13)
        _, iban = self._get_bic_and_iban(boe_wizard.partner_bank_id)
        rslt += self._l10n_es_boe_format_string(iban, length=34)
        rslt += self._l10n_es_boe_format_string(' ' * 96)
        rslt += self._l10n_es_boe_format_string(' ' * 13)

        rslt += self._l10n_es_boe_format_string(f'</{boe_modelo_id}>')

        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': rslt,
            'file_type': 'txt',
        }
