# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import division

import re
import logging
from unicodedata import normalize


from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, get_lang

_logger = logging.getLogger(__name__)

def diot_country_adapt(values):
    # In SAT classification some countries have a different country code
    # and others do not exists at all
    # https://blueprints.launchpad.net/openerp-mexico-localization/+spec/diot-mexico
    cc = values.get('country_code')
    non_diot_countries = {
        'CD', 'SS', 'PS', 'XK', 'SX', 'ER', 'RS', 'ME', 'TL', 'MD', 'MF',
        'BL', 'BQ', 'YT', 'AZ', 'MM', 'SK', 'CW', 'GS'
    }
    diot_country_dict = {
        'AM': 'SU', 'BZ': 'BL', 'CZ': 'CS', 'DO': 'DM', 'EE': 'SU',
        'GE': 'SU', 'DE': 'DD', 'GL': 'GJ', 'GG': 'GZ', 'IM': 'IH',
        'JE': 'GZ', 'KZ': 'SU', 'KG': 'SU', 'LV': 'SU', 'LT': 'SU',
        'RU': 'SU', 'WS': 'EO', 'TJ': 'SU', 'TM': 'SU', 'UZ': 'SU',
        'SI': 'YU', 'BA': 'YU', 'HR': 'YU', 'MK': 'YU'
    }

    if cc in non_diot_countries:
        # Country not in DIOT catalog, so we use the special code 'XX'
        # for 'Other' countries
        values['country_code'] = 'XX'
    else:
        # Map the standard country_code to the SAT standard
        values['country_code'] = diot_country_dict.get(cc, cc)
    return values

class MexicanAccountReportCustomHandler(models.AbstractModel):
    _name = 'l10n_mx.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Mexican Account Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        options['columns'] = [column for column in options['columns']]
        options.setdefault('buttons', []).extend((
            {'name': _('DIOT (txt)'), 'sequence': 40, 'action': 'export_file', 'action_param': 'action_get_diot_txt', 'file_export_type': _('DIOT')},
            {'name': _('DPIVA (txt)'), 'sequence': 60, 'action': 'export_file', 'action_param': 'action_get_dpiva_txt', 'file_export_type': _('DPIVA')},
        ))

    def _report_custom_engine_diot_report(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        def build_dict(report, current_groupby, query_res):
            if not current_groupby:
                return query_res[0] if query_res else {k: None for k in report.mapped('line_ids.expression_ids.label')}
            return [(group_res["grouping_key"], group_res) for group_res in query_res]

        report = self.env['account.report'].browse(options['report_id'])
        query_res = self._execute_query(report, current_groupby, options, offset, limit)
        return build_dict(report, current_groupby, query_res)

    def _execute_query(self, report, current_groupby, options, offset, limit):
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        # This report mixes the tax_tags and custom engine.
        # The  results of the custom engine are relevant
        # only when we have a partner. Else, we default to ''.
        if current_groupby != 'partner_id':
            return []

        cash_basis_journal_ids = self.env.companies.filtered('tax_cash_basis_journal_id').tax_cash_basis_journal_id
        tables, where_clause, where_params = report._query_get(options, 'strict_range', domain=[
            ('parent_state', '=', 'posted'),
            ('journal_id', 'in', cash_basis_journal_ids.ids),
        ])
        lang = self.env.user.lang or get_lang(self.env).code
        tags = report.line_ids.expression_ids._get_matching_tags()

        tail_query, tail_params = report._get_engine_query_tail(offset, limit)
        self._cr.execute(f"""
            WITH raw_results as (
                SELECT
                    account_move_line.partner_id AS grouping_key,
                    CASE WHEN country.code = 'MX' THEN '04' ELSE '05' END AS third_party_code,
                    partner.l10n_mx_type_of_operation AS operation_type_code,
                    partner.vat AS partner_vat_number,
                    country.code AS country_code,
                    COALESCE(country.demonym->>'{lang}', country.demonym->>'en_US') AS partner_nationality
                FROM {tables}
                JOIN account_move AS move ON move.id = account_move_line.move_id
                JOIN account_account_tag_account_move_line_rel AS tag_aml_rel ON account_move_line.id = tag_aml_rel.account_move_line_id
                JOIN account_account_tag AS tag ON tag.id = tag_aml_rel.account_account_tag_id AND tag.id IN %s
                JOIN res_partner AS partner ON partner.id = account_move_line.partner_id
                JOIN res_country AS country ON country.id = partner.country_id
                WHERE {where_clause}
                ORDER BY partner.name, account_move_line.date, account_move_line.id
            )
            SELECT
               raw_results.grouping_key AS grouping_key,
               count(raw_results.grouping_key) AS counter,
               raw_results.third_party_code AS third_party_code,
               raw_results.operation_type_code AS operation_type_code,
               COALESCE(raw_results.partner_vat_number, '') AS partner_vat_number,
               raw_results.country_code AS country_code,
               raw_results.partner_nationality AS partner_nationality
            FROM raw_results
            GROUP BY
                raw_results.grouping_key,
                raw_results.third_party_code,
                raw_results.operation_type_code,
                raw_results.partner_vat_number,
                raw_results.country_code,
                raw_results.partner_nationality
           {tail_query}
        """,
            [tuple(tags.ids)] + [
                *where_params,
                *tail_params,
            ],
        )

        return [diot_country_adapt(vals) for vals in self.env.cr.dictfetchall()]

    def action_get_diot_txt(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        partner_and_values_to_report = self._get_diot_values_per_partner(report, options)

        self.check_for_error_on_partner([partner for partner in partner_and_values_to_report])

        lines = []
        for partner, values in partner_and_values_to_report.items():
            if not any([values.get(x) for x in ('paid_16', 'paid_16_non_cred', 'paid_8', 'paid_8_non_cred', 'importation_16', 'paid_0', 'exempt', 'withheld', 'refunds')]):
                # don't report if there isn't any amount to report
                continue

            is_foreign_partner = values['third_party_code'] != '04'
            data = [''] * 25
            data[0] = values['third_party_code']  # Supplier Type
            data[1] = values['operation_type_code']  # Operation Type
            data[2] = values['partner_vat_number'] if not is_foreign_partner else '' # Tax Number
            data[3] = values['partner_vat_number'] if is_foreign_partner else ''  # Tax Number for Foreigners
            data[4] = ''.join(self.str_format(partner.name)).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else ''  # Name
            data[5] = values['country_code'] if is_foreign_partner else '' # Country
            data[6] = ''.join(self.str_format(values['partner_nationality'])).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else '' # Nationality
            data[7] = round(float(values.get('paid_16', 0))) or '' # 16%
            data[9] = round(float(values.get('paid_16_non_cred', 0))) or '' # 16% Non-Creditable
            data[12] = round(float(values.get('paid_8', 0))) or '' # 8%
            data[14] = round(float(values.get('paid_8_non_cred', 0))) or '' # 8% Non-Creditable
            data[15] = round(float(values.get('importation_16', 0))) or '' # 16% - Importation
            data[20] = round(float(values.get('paid_0', 0))) or '' # 0%
            data[21] = round(float(values.get('exempt', 0))) or '' # Exempt
            data[22] = round(float(values.get('withheld', 0))) or '' # Withheld
            data[23] = round(float(values.get('refunds', 0))) or '' # Refunds

            lines.append('|'.join(str(d) for d in data))

        diot_txt_result = '\n'.join(lines)
        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': diot_txt_result.encode(),
            'file_type': 'txt',
        }

    def action_get_dpiva_txt(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        partner_and_values_to_report = self._get_diot_values_per_partner(report, options)

        self.check_for_error_on_partner([partner for partner in partner_and_values_to_report])

        date = fields.datetime.strptime(options['date']['date_from'], DEFAULT_SERVER_DATE_FORMAT)
        month = {
            '01': 'Enero',
            '02': 'Febrero',
            '03': 'Marzo',
            '04': 'Abril',
            '05': 'Mayo',
            '06': 'Junio',
            '07': 'Julio',
            '08': 'Agosto',
            '09': 'Septiembre',
            '10': 'Octubre',
            '11': 'Noviembre',
            '12': 'Diciembre',
        }.get(date.strftime("%m"))

        lines = []
        for partner, values in partner_and_values_to_report.items():
            if not any([values.get(x) for x in ('paid_16', 'paid_16_non_cred', 'paid_8', 'paid_8_non_cred', 'importation_16', 'paid_0', 'exempt', 'withheld', 'refunds')]):
                # don't report if there isn't any amount to report
                continue

            is_foreign_partner = values['third_party_code'] != '04'
            data = [''] * 48
            data[0] = '1.0'  # Version
            data[1] = f"{date.year}"  # Fiscal Year
            data[2] = 'MES'  # Cabling value
            data[3] = month  # Period
            data[4] = '1'  # 1 Because has data
            data[5] = '1'  # 1 = Normal, 2 = Complementary (Not supported now).
            data[8] = values['counter']  # Count the operations
            for num in range(9, 26):
                data[num] = '0'
            data[26] = values['third_party_code']  # Supplier Type
            data[27] = values['operation_type_code']  # Operation Type
            data[28] = values['partner_vat_number'] if not is_foreign_partner else ''  # Federal Taxpayer Registry Code
            data[29] = values['partner_vat_number'] if is_foreign_partner else ''  # Fiscal ID
            data[30] = ''.join(self.str_format(partner.name)).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else ''  # Name
            data[31] = values['country_code'] if is_foreign_partner else ''  # Country
            data[32] = ''.join(self.str_format(values['partner_nationality'])).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else ''  # Nationality
            data[33] = round(float(values.get('paid_16', 0))) or '' # 16%
            data[36] = round(float(values.get('paid_8', 0))) or '' # 8%
            data[39] = round(float(values.get('importation_16', 0))) or '' # 16% - Importation
            data[44] = round(float(values.get('paid_0', 0))) or '' # 0%
            data[45] = round(float(values.get('exempt', 0))) or '' # Exempt
            data[46] = round(float(values.get('withheld', 0))) or '' # Withheld
            data[47] = round(float(values.get('refunds', 0))) or '' # Refunds

            lines.append('|{}|'.format('|'.join(str(d) for d in data)))

        dpiva_txt_result = '\n'.join(lines)
        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': dpiva_txt_result.encode(),
            'file_type': 'txt',
        }

    def _get_diot_values_per_partner(self, report, options):
        options['unfolded_lines'] = []  # This allows to only get the first groupby level: partner_id
        col_group_results = report._compute_expression_totals_for_each_column_group(report.line_ids.expression_ids, options, groupby_to_expand="partner_id")
        if len(col_group_results) != 1:
            raise UserError(_("You can only export one period at a time with this file format!"))
        expression_list = list(col_group_results.values())
        label_dict = {exp.label: v['value'] for d in expression_list for exp, v in d.items()}
        partner_to_label_val = {}
        for label, partner_to_value_list in label_dict.items():
            for partner_id, value in partner_to_value_list:
                partner_to_label_val.setdefault(self.env['res.partner'].browse(partner_id), {})[label] = value
        return dict(sorted(partner_to_label_val.items(), key=lambda item: item[0].name))

    def check_for_error_on_partner(self, partners):
        partner_missing_information = self.env['res.partner']
        for partner in partners:
            if partner.country_id.code == "MX" and not partner.vat:
                partner_missing_information += partner
            if not partner.l10n_mx_type_of_operation:
                partner_missing_information += partner

        if partner_missing_information:
            action_error = {
                'name': _('Partner missing informations'),
                'type': 'ir.actions.act_window',
                'res_model': 'res.partner',
                'view_mode': 'list',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('id', 'in', partner_missing_information.ids)],
            }
            msg = _('The report cannot be generated because some partners are missing a valid RFC or type of operation')
            raise RedirectWarning(msg, action_error, _("See the list of partners"))

    @staticmethod
    def str_format(text):
        if not text:
            return ''
        trans_tab = {
            ord(char): None for char in (
                u'\N{COMBINING GRAVE ACCENT}',
                u'\N{COMBINING ACUTE ACCENT}',
                u'\N{COMBINING DIAERESIS}',
            )
        }
        text_n = normalize('NFKC', normalize('NFKD', text).translate(trans_tab))
        check_re = re.compile(r'''[^A-Za-z\d Ññ]''')
        return check_re.sub('', text_n)
