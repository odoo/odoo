from lxml import etree

from odoo import api, models, _
from odoo.tools.float_utils import float_round
from odoo.tools import SQL


class AccountIntrastatServicesReportHandler(models.AbstractModel):
    _inherit = 'account.intrastat.services.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'FR':
            return

        # Remove the XML export button for goods
        if xml_goods_button := next(button for button in options.get('buttons', []) if button.get('name') == 'XML (DEBWEB2)'):
            options['buttons'].remove(xml_goods_button)

        options.setdefault('buttons', []).append({
            'name': _('XML (DES)'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_fr_intrastat_services_export_to_xml',
            'file_export_type': 'XML',
        })

    def _get_exporting_query_data(self):
        res = super()._get_exporting_query_data()
        return SQL('%s %s', res, SQL(" account_move_line.move_id AS move_id, "))

    def _get_exporting_dict_data(self, report_data: dict, query_res: dict):
        super()._get_exporting_dict_data(report_data, query_res)
        if self.env.company.account_fiscal_country_id.code == 'FR':
            report_data.update({
                'move_id': query_res['move_id'],
            })
        return report_data

    @api.model
    def l10n_fr_intrastat_services_export_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        options = report.get_options(previous_options={**options, 'export_mode': 'file'})

        report._init_currency_table(options)
        expressions = report.line_ids.expression_ids
        results = self._report_custom_engine_intrastat(
            expressions=expressions,
            options=options,
            date_scope=None,
            current_groupby='id',
            next_groupby=None,
        )
        move_ids = {item['move_id'] for _grouping_key, item in results}
        moves = self.env['account.move'].browse(move_ids)

        values = {'declarations': []}

        for num_declaration, move in enumerate(moves, start=1):
            declaration = {
                'declaration_number': str(num_declaration).rjust(5, '0'),
                'vat': move.company_id.vat,
                'invoice_date_month': move.invoice_date.strftime('%m'),
                'invoice_date_year': move.invoice_date.strftime('%Y'),
                'items': [],
            }

            for num_line, invoice_line in enumerate(move.invoice_line_ids, start=1):
                if invoice_line.product_id.type != 'service':
                    continue

                # As we need to have negative amount for outbound moves, we do that to invert the sign for those moves
                amount = invoice_line.price_subtotal * -move.direction_sign
                declaration['items'].append({
                    'line_number': str(num_line).rjust(6, '0'),
                    'amount': int(float_round(amount, precision_digits=0)),
                    'partner_vat': invoice_line.partner_id.vat,
                })

            values['declarations'].append(declaration)

        file_content = self.env['ir.qweb']._render('l10n_fr_intrastat_services.intrastat_report_export_xml_services', values)

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': etree.tostring(etree.fromstring(file_content), xml_declaration=True, encoding='utf-8', pretty_print=True),
            'file_type': 'xml',
        }
