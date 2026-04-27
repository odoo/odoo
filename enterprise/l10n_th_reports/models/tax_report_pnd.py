# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools import SQL


def _csv_row(*data, delimiter=","):
    # return a csv formatted file and add newline by the end
    return delimiter.join(data) + '\n'


class TaxReportPND(models.AbstractModel):
    _name = "l10n_th.pnd.report.handler"
    _inherit = "account.generic.tax.report.handler"
    _description = "Abstract Tax Report PND Handler"

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        return []

    def _headers(self):
        # Excel file headers
        return [_('No.'), _('Tax ID'), _('Title'), _('Contact Name'), _('Street'), _('Street2'), _('City'), _('State'), _('Zip'), _('Branch Number'), _('Invoice/Bill Date'), _('Tax Rate'),
                _('Total Amount'), _('WHT Amount'), _('WHT Condition'), _('Tax Type')]

    def _rows(self, options, report, domain, title=''):
        query = report._get_report_query(options, 'strict_range', domain)

        dp = self.env.company.currency_id.decimal_places

        query = SQL(
            """
            SELECT
                CAST(ROW_NUMBER() OVER(ORDER BY account_move_line__move_id.date, partner.name, account_move_line__move_id.name, account_move_line.id) AS TEXT) as rnum,
                COALESCE(partner.vat, '') as vat,
                %(title)s as title,
                COALESCE(partner.name, '') as name,
                COALESCE(partner.street, '') as street,
                COALESCE(partner.street2, '') as street2,
                COALESCE(partner.city, '') as city,
                COALESCE(state.name, '') as state_name,
                COALESCE(partner.zip, '') as zip,
                COALESCE(partner.company_registry, '') as branch_number,
                TO_CHAR(account_move_line__move_id.date, 'dd/mm/YYYY') as date,
                ROUND(ABS(tax.amount), %(decimal_precision)s)::text as tax_amount,
                ROUND(ABS(account_move_line.tax_base_amount), %(decimal_precision)s)::text as tax_base_amount,
                ROUND(ABS(tax.amount * account_move_line.tax_base_amount / 100), %(decimal_precision)s)::text as wht_amount,
                '1' as wht_condition,
                CASE tax.amount
                    WHEN -1 THEN 'Transportation'
                    WHEN -2 THEN 'Advertising'
                    WHEN -3 THEN 'Service'
                    WHEN -5 THEN 'Rental'
                    ELSE ''
                END tax_type
            FROM %(table_references)s
                LEFT JOIN res_partner partner on partner.id = account_move_line__move_id.partner_id
                JOIN account_tax tax on tax.id = account_move_line.tax_line_id
                LEFT JOIN res_country_state state on partner.state_id = state.id
            WHERE %(search_condition)s
         ORDER BY rnum
            """,
            title=title,
            decimal_precision=dp,
            table_references=query.from_clause,
            search_condition=query.where_clause,
        )

        self._cr.execute(query)
        res = self._cr.fetchall()

        return res


class TaxReportPND53(models.AbstractModel):
    _name = "l10n_th.pnd53.report.handler"
    _inherit = "l10n_th.pnd.report.handler"
    _description = "Thai Tax Report (PND53) Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).extend((
            {
                'name': _('PND53'),
                'action': 'export_file',
                'action_param': 'l10n_th_print_pnd_tax_report_pnd53',
                'sequence': 80,
                'file_export_type': _('CSV')
            },
        ))

    def l10n_th_print_pnd_tax_report_pnd53(self, options):
        report = self.env.ref('l10n_th.tax_report_pnd53')
        tag_templates = (
            self.env.ref("l10n_th.tax_report_total_income_pnd53")
            + self.env.ref("l10n_th.tax_report_total_remittance_pnd53")
            + self.env.ref("l10n_th.tax_report_surcharge_pnd53")
        )
        data = self._rows(options, report, [('tax_tag_ids', 'in', tag_templates._get_matching_tags().ids)], title='บริษัท')

        output = _csv_row(*(self._headers()))
        for row in data:
            output += _csv_row(*row)

        return {
            "file_name": "Tax Report PND53",
            "file_content": output.encode(),
            "file_type": "csv"
        }


class TaxReportPND3(models.AbstractModel):
    _name = "l10n_th.pnd3.report.handler"
    _inherit = "l10n_th.pnd.report.handler"
    _description = "Thai Tax Report (PND3) Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options.setdefault('buttons', []).extend((
            {
                'name': _('PND3'),
                'action': 'export_file',
                'action_param': 'l10n_th_print_pnd_tax_report_pnd3',
                'sequence': 80,
                'file_export_type': _('CSV')
            },
        ))

    def l10n_th_print_pnd_tax_report_pnd3(self, options):
        report = self.env.ref("l10n_th.tax_report_pnd3")
        tag_templates = (
            self.env.ref("l10n_th.tax_report_total_income_pnd3")
            + self.env.ref("l10n_th.tax_report_total_remittance_pnd3")
            + self.env.ref("l10n_th.tax_report_surcharge_pnd3")
        )
        data = self._rows(options, report, [('tax_tag_ids', 'in', tag_templates._get_matching_tags().ids)])

        output = _csv_row(*(self._headers()))
        for row in data:
            output += _csv_row(*row)

        return {
            "file_name": "Tax Report PND3",
            "file_content": output.encode(),
            "file_type": "csv"
        }
