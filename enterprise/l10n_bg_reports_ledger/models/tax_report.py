from odoo import fields, models
from odoo.tools import float_round, SQL


class L10nBgReportsTaxReportHandler(models.AbstractModel):
    _name = 'l10n_bg_reports.tax.report.handler'
    _inherit = ['account.tax.report.handler']
    _description = 'Tax report handler for Bulgaria'

    TAX_TAGS_PER_TYPE_IN_ORDER = {
        'purchase': ['30', '31', '41', '32', '42'],
        'sale': ['11', '21', '12', '22', '13', '23', '24', '14', '15', '16', '17', '18', '19'],
    }

    FILE_NAME_PER_TYPE = {
        'purchase': 'POKUPKI.txt',
        'sale': 'PRODAGBI.txt',
    }

    def _get_file_name(self, ledger_type):
        assert ledger_type in {'purchase', 'sale'}

        return self.FILE_NAME_PER_TYPE[ledger_type]

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).extend([{
            'name': self._get_file_name(ledger_type),
            'sequence': 15,
            'action': 'export_file',
            'action_param': f'export_{ledger_type}_report_to_txt',
            'file_export_type': 'TXT',
        } for ledger_type in ('purchase', 'sale')])

    def _get_ledger_data(self, options, ledger_type):
        assert ledger_type in {'purchase', 'sale'}

        def build_result(query_res_line, tax_tags):
            result = {
                'vat': self.env.company.vat,
                'date': fields.Date.to_date(options['date']['date_from']).strftime('%Y%m'),
                'branch_code': query_res_line['branch_code'],
                'serial_number': query_res_line['serial_number'],
                'document_type': query_res_line['document_type'],
                'document_name': query_res_line['document_name'],
                'document_date': query_res_line['document_date'],
                'partner_vat': query_res_line['partner_vat'],
                'partner_name': query_res_line['partner_name'],
                'product_type': query_res_line['label'][0][:30].replace('\n', ' '),
                'exemption_reason': query_res_line['exemption_reason'],
                'total_base': 0,
                'total_tax': 0,
            }

            for tax_tag, amount, is_tax_line in zip(query_res_line['tax_tag'], query_res_line['amount_currency'], query_res_line['is_tax_line']):
                if ledger_type == 'sale':
                    result['total_tax' if is_tax_line else 'total_base'] += amount

                tax = tax_tags[tax_tag].name[1:]

                if tax in self.TAX_TAGS_PER_TYPE_IN_ORDER[ledger_type]:
                    result[f'tax_{tax}'] = result.get(f'tax_{tax}', 0) + amount

            return result

        self.env.flush_all()

        report = self.env['account.report'].browse(options['report_id'])

        query_params = report._get_report_query(options, 'strict_range')

        tax_tags_names = tuple(name for tag in self.TAX_TAGS_PER_TYPE_IN_ORDER[ledger_type] for name in (f'+{tag}', f'-{tag}'))
        tax_tags = self.env['account.account.tag'].search([
            ('name', 'in', tax_tags_names),
            ('country_id.code', '=', 'BG'),
        ]).grouped('id')

        query = SQL("""
            SELECT
                row_number() over (ORDER BY account_move.sequence_number DESC) AS serial_number,
                account_move.l10n_bg_document_type AS document_type,
                account_move.name AS document_name,
                account_move.invoice_date AS document_date,
                company_id.l10n_bg_branch_code as branch_code,
                partner.vat AS partner_vat,
                partner.name AS partner_name,
                array_agg(account_move_line.name) AS label,
                array_agg(tag.id ORDER BY tag.id) AS tax_tag,
                account_move.l10n_bg_exemption_reason AS exemption_reason,
                array_agg(CASE WHEN account_move_line.tax_line_id IS NOT NULL THEN TRUE ELSE FALSE END) AS is_tax_line,
                array_agg(ABS(account_move_line.amount_currency)) AS amount_currency
            FROM
                %(table_references)s
                %(currency_table_join)s
                JOIN account_move ON account_move.id = account_move_line.move_id
                LEFT JOIN res_partner partner ON partner.id = account_move_line.partner_id
                LEFT JOIN res_company company_id ON company_id.id = account_move.company_id
                LEFT JOIN account_account_tag_account_move_line_rel aa_tag_aml_rel ON aa_tag_aml_rel.account_move_line_id = account_move_line.id
                LEFT JOIN account_account_tag tag ON aa_tag_aml_rel.account_account_tag_id = tag.id
            WHERE
                %(search_conditions)s
                AND account_move.move_type IN %(move_types)s
                AND tag.id = ANY(%(tag_ids)s)
            GROUP BY account_move.id, partner.id, company_id.id
            ORDER BY serial_number
        """,
            table_references=query_params.from_clause,
            currency_table_join=report._currency_table_aml_join(options),
            search_conditions=query_params.where_clause,
            move_types=('in_invoice', 'in_refund', 'in_receipt') if ledger_type == 'purchase' else ('out_invoice', 'out_refund', 'out_receipt'),
            tag_ids=list(tax_tags.keys()),
        )

        self._cr.execute(query)

        data = []

        for query_res in self._cr.dictfetchall():
            data.append(build_result(query_res, tax_tags))

        return data

    def _export_report_to_txt(self, options, ledger_type):
        assert ledger_type in {'purchase', 'sale'}

        ledger_data = self._get_ledger_data(options, ledger_type)
        file_content = []

        for line in ledger_data:
            line_content = (
                f"{line['vat']:15}"
                f"{line['date']}"
                f"{line['branch_code']:0>4}"
                f"{line['serial_number']:15}"
                f"{line['document_type']:2}"
                f"{line['document_name']:20}"
                f"{line['document_date'].strftime('%d/%m/%Y')}"
                f"{line['partner_vat'] or '':15}"
                f"{line['partner_name'].replace(' ', '-'):50}"
                f"{(line['product_type'] or '')[:30].replace(' ', '-'):30}"
            )

            if ledger_type == 'sale':
                line_content += (
                    f"{float_round(line['total_base'], precision_digits=1) or '':>15}"
                    f"{float_round(line['total_tax'], precision_digits=1) or '':>15}"
                )

            for tag in self.TAX_TAGS_PER_TYPE_IN_ORDER[ledger_type]:
                line_content += f"{line.get(f'tax_{tag}', ''):>15}"

            line_content += f"{(line['exemption_reason'] or ''):2}"

            file_content.append(line_content)

        return {
            'file_name': self._get_file_name(ledger_type),
            'file_content': '\n'.join(file_content).encode(),
            'file_type': 'txt',
        }

    def export_purchase_report_to_txt(self, options):
        return self._export_report_to_txt(options, 'purchase')

    def export_sale_report_to_txt(self, options):
        return self._export_report_to_txt(options, 'sale')
