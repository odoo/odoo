# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import division

import re
import logging
from unicodedata import normalize


from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, get_lang, SQL

_logger = logging.getLogger(__name__)


def diot_country_adapt(values):
    # 2025 SAT classification uses 3-letter country codes
    # https://www.fiscalia.com/archivos/2025-02-06-DIOT_2025_Ayuda_Carga_Masiva.pdf
    cc = values.get('country_code')
    diot_country_dict = {
        'MX': 'MEX', None: '',
        'AF': 'AFG', 'AX': 'ALA', 'AL': 'ALB', 'DE': 'DEU', 'AD': 'AND', 'AO': 'AGO', 'AI': 'AIA', 'AQ': 'ATA', 'AG': 'ATG', 'SA': 'SAU',
        'DZ': 'DZA', 'AR': 'ARG', 'AM': 'ARM', 'AW': 'ABW', 'AU': 'AUS', 'AT': 'AUT', 'AZ': 'AZE', 'BS': 'BHS', 'BD': 'BGD', 'BB': 'BRB',
        'BH': 'BHR', 'BE': 'BEL', 'BZ': 'BLZ', 'BJ': 'BEN', 'BM': 'BMU', 'BY': 'BLR', 'MM': 'MMR', 'BO': 'BOL', 'BA': 'BIH', 'BW': 'BWA',
        'BR': 'BRA', 'BN': 'BRN', 'BG': 'BGR', 'BF': 'BFA', 'BI': 'BDI', 'BT': 'BTN', 'CV': 'CPV', 'KH': 'KHM', 'CM': 'CMR', 'CA': 'CAN',
        'QA': 'QAT', 'TD': 'TCD', 'CL': 'CHL', 'CN': 'CHN', 'CY': 'CYP', 'CO': 'COL', 'KM': 'COM', 'KP': 'PRK', 'KR': 'KOR', 'CI': 'CIV',
        'CR': 'CRI', 'HR': 'HRV', 'CU': 'CUB', 'CW': 'CUW', 'DK': 'DNK', 'DM': 'DMA', 'EC': 'ECU', 'EG': 'EGY', 'SV': 'SLV', 'AE': 'ARE',
        'ER': 'ERI', 'SK': 'SVK', 'SI': 'SVN', 'ES': 'ESP', 'US': 'USA', 'EE': 'EST', 'ET': 'ETH', 'PH': 'PHL', 'FI': 'FIN', 'FJ': 'FJI',
        'FR': 'FRA', 'GA': 'GAB', 'GB': 'GBR', 'GM': 'GMB', 'GE': 'GEO', 'GH': 'GHA', 'GI': 'GIB', 'GD': 'GRD', 'GR': 'GRC', 'GL': 'GRL', 'GP': 'GLP',
        'GU': 'GUM', 'GT': 'GTM', 'GF': 'GUF', 'GG': 'GGY', 'GN': 'GIN', 'GW': 'GNB', 'GQ': 'GNY', 'HT': 'HTI', 'HN': 'HND', 'HK': 'HKG',
        'HU': 'HUN', 'IN': 'IND', 'IQ': 'IRQ', 'IR': 'IRN', 'IE': 'IRL', 'BV': 'BVT', 'IM': 'IMN', 'CX': 'CXR', 'NF': 'NFK', 'IS': 'ISL',
        'KY': 'CYM', 'CC': 'CCK', 'CK': 'COK', 'FO': 'FRO', 'GS': 'SGS', 'HM': 'HMD', 'FK': 'FLK', 'MP': 'MNP', 'MH': 'MHL', 'PN': 'PCN',
        'SB': 'SLB', 'TC': 'TCA', 'UM': 'UMI', 'VG': 'VGB', 'VI': 'VIR', 'IL': 'ISR', 'IT': 'ITA', 'JM': 'JAM', 'JP': 'JPN', 'JE': 'JEY',
        'JO': 'JOR', 'KZ': 'KAZ', 'KE': 'KEN', 'KG': 'KGZ', 'KI': 'KIR', 'KW': 'KWT', 'LA': 'LAO', 'LS': 'LSO', 'LV': 'LVA', 'LB': 'LBA',
        'LR': 'LBR', 'LY': 'LBY', 'LI': 'LIE', 'LT': 'LTU', 'LU': 'LUX', 'MO': 'MAC', 'MG': 'MDG', 'MY': 'MYS', 'MW': 'MWI', 'MV': 'MDV',
        'ML': 'MLI', 'MT': 'MLT', 'MA': 'MAR', 'MQ': 'MTQ', 'MU': 'MUS', 'MR': 'MRT', 'YT': 'MYT', 'FM': 'FSM', 'MD': 'MDA', 'MC': 'MCO',
        'MN': 'MNG', 'ME': 'MNE', 'MS': 'MSR', 'MZ': 'MOZ', 'NA': 'NAM', 'NR': 'NRU', 'NP': 'NPL', 'NI': 'NIC', 'NE': 'NER', 'NG': 'NGA',
        'NU': 'NIU', 'NO': 'NOR', 'NC': 'NCL', 'NZ': 'NZL', 'OM': 'OMN', 'NL': 'NLD', 'PK': 'PAK', 'PW': 'PLW', 'PS': 'PSE', 'PA': 'PAN',
        'PG': 'PNG', 'PY': 'PRY', 'PE': 'PER', 'PF': 'PYF', 'PL': 'POL', 'PT': 'PRT', 'PR': 'PRI', 'CF': 'CAF', 'CZ': 'CZE', 'MK': 'MKD',
        'CG': 'COG', 'CD': 'COD', 'DR': 'DOM', 'RE': 'REU', 'RW': 'RWA', 'RO': 'ROU', 'RU': 'RUS', 'EH': 'ESH', 'WS': 'WSM', 'AS': 'ASM',
        'BL': 'BLM', 'KN': 'KNA', 'SM': 'SMR', 'MF': 'MAF', 'PM': 'SPM', 'VC': 'VCT', 'SH': 'SHN', 'LC': 'LCA', 'ST': 'STP', 'SN': 'SEN',
        'RS': 'SRB', 'SC': 'SYC', 'SL': 'SLE', 'SG': 'SGP', 'SX': 'SXM', 'SY': 'SYR', 'SO': 'SOM', 'LK': 'LKA', 'SZ': 'SWZ', 'ZA': 'ZAF',
        'SD': 'SDN', 'SS': 'SSD', 'SE': 'SWE', 'CH': 'CHE', 'SR': 'SUR', 'SJ': 'SJM', 'TH': 'THA', 'TW': 'TWA', 'TZ': 'TZA', 'TJ': 'TJK',
        'IO': 'IOT', 'TF': 'ATF', 'TL': 'TLS', 'TG': 'TGO', 'TK': 'TKL', 'TO': 'TON', 'TT': 'TTO', 'TN': 'TUN', 'TM': 'TKM', 'TR': 'TUR',
        'TV': 'TUV', 'UA': 'UKR', 'UG': 'UGA', 'UY': 'URY', 'UZ': 'UZB', 'VU': 'VUT', 'VA': 'VAT', 'VE': 'VEN', 'VN': 'VNM', 'WF': 'WLF',
        'YE': 'YEM', 'DJ': 'DJY', 'ZM': 'ZMB', 'ZW': 'ZWE'
    }

    if cc not in diot_country_dict:
        # Country not in DIOT catalog, so we use the special code 'ZZZ'
        # for 'Other' countries
        values['country_code'] = 'ZZZ'
    else:
        # Map the standard country_code to the SAT standard
        values['country_code'] = diot_country_dict.get(cc, cc)
    return values


class MexicanAccountReportCustomHandler(models.AbstractModel):
    _name = 'l10n_mx.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Mexican Account Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
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

        query = report._get_report_query(options, 'strict_range', domain=[
            ('parent_state', '=', 'posted'),
        ])
        country_demonym = self.env['res.country']._field_to_sql('country', 'demonym')
        tags = report.line_ids.expression_ids._get_matching_tags()

        tail_query = report._get_engine_query_tail(offset, limit)
        self._cr.execute(SQL(
            """
            WITH raw_results as (
                SELECT
                    account_move_line.partner_id AS grouping_key,
                    CASE WHEN country.code = 'MX' THEN '04' ELSE '05' END AS third_party_code,
                    partner.l10n_mx_type_of_operation AS operation_type_code,
                    partner.vat AS partner_vat_number,
                    country.code AS country_code,
                    %(country_demonym)s AS partner_nationality
                FROM %(table_references)s
                JOIN account_move AS move ON move.id = account_move_line.move_id
                JOIN account_account_tag_account_move_line_rel AS tag_aml_rel ON account_move_line.id = tag_aml_rel.account_move_line_id
                JOIN account_account_tag AS tag ON tag.id = tag_aml_rel.account_account_tag_id AND tag.id IN %(tags)s
                JOIN res_partner AS partner ON partner.id = account_move_line.partner_id
                LEFT JOIN res_country AS country ON country.id = partner.country_id
                WHERE %(search_condition)s
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
                %(groupby_sql)s
            ORDER BY
                %(groupby_sql)s
            %(tail_query)s
            """,
            country_demonym=country_demonym,
            table_references=query.from_clause,
            tags=tuple(tags.ids),
            search_condition=query.where_clause,
            groupby_sql=SQL("""
                raw_results.grouping_key,
                raw_results.third_party_code,
                raw_results.operation_type_code,
                raw_results.partner_vat_number,
                raw_results.country_code,
                raw_results.partner_nationality
            """),
            tail_query=tail_query,
        ))

        return [diot_country_adapt(vals) for vals in self.env.cr.dictfetchall()]

    def action_get_diot_txt(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        partner_and_values_to_report = self._get_diot_values_per_partner(report, options)

        self.check_for_error_on_partner(list(partner_and_values_to_report))

        lines = []
        data_87 = [0] * 54
        for partner, values in partner_and_values_to_report.items():
            if not sum(values.get(x, 0) for x in (
                'paid_8', 'paid_8_non_cred', 'paid_8_tax', 'paid_8_non_cred_tax', 'refunds_8_n',
                'paid_8_s', 'paid_8_s_nc', 'paid_8_s_tax', 'paid_8_s_nc_tax', 'refunds_8_s',
                'paid_16', 'paid_16_non_cred', 'paid_16_tax', 'paid_16_non_cred_tax', 'refunds_16',
                'importation_16', 'paid_16_imp_nc', 'importation_16_tax', 'paid_16_imp_nc_tax', 'refunds_16_imp',
                'paid_16_imp_int', 'paid_16_imp_int_nc', 'paid_16_imp_int_tax', 'paid_16_imp_int_nc_tax', 'refunds_16_imp_int',
                'withheld', 'exempt', 'exempt_imp', 'paid_0', 'no_obj'
            )):
                # don't report if there isn't any amount to report
                continue

            data = [0] * 54
            if values.get('operation_type_code') != '87':
                self.l10n_mx_diot_get_values(values, data, partner)
                for i in range(7, 53):
                    if not data[i]:
                        data[i] = ''
                    if not isinstance(data[i], str):
                        data[i] = str(round(data[i]))
                lines.append('|'.join(str(d) for d in data))
            else:
                self.l10n_mx_diot_get_values(values, data_87, partner)
        # Global Operations
        if any(data_87):
            for i in range(7, 53):
                if not data_87[i]:
                    data_87[i] = ''
                if not isinstance(data_87[i], str):
                    data_87[i] = str(round(data_87[i]))
            lines.append('|'.join(str(d) for d in data_87))

        diot_txt_result = '\n'.join(lines)
        return {
            'file_name': report.get_default_report_filename(options, 'txt'),
            'file_content': diot_txt_result.encode(),
            'file_type': 'txt',
        }

    def l10n_mx_diot_get_values(self, values, data, partner):
        is_foreign_partner = values.get('third_party_code') != '04'
        is_global = values.get('operation_type_code') == '87'
        # Non-numerical
        data[0] = values.get('third_party_code')  # Supplier Type
        data[1] = values.get('operation_type_code')  # Operation Type
        data[2] = 'XAXX010101000' if is_global else (values.get('partner_vat_number') if not is_foreign_partner else '')  # Tax Number
        data[3] = '' if is_global else (values.get('partner_vat_number') if is_foreign_partner else '')  # Tax Number for Foreigners
        data[4] = '' if is_global else (''.join(self.str_format(partner.name)).encode('utf-8').strip().decode('utf-8') if is_foreign_partner else '')  # Name
        data[5] = '' if is_global else (values.get('country_code') if is_foreign_partner else '')  # Country
        data[6] = ''  # Fiscal Jurisdiction specified (for manual entry)
        # Sums and refunds
        data[7] += float(values.get('paid_8_n_wnc', 0))  # 8% Northern +NC paid
        data[8] += float(values.get('refunds_8_n', 0))  # 8% Northern refunds
        data[9] += float(values.get('paid_8_s_wnc', 0))  # 8% Southern +NC paid
        data[10] += float(values.get('refunds_8_s', 0))  # 8% Southern refunds
        data[11] += float(values.get('paid_16_wnc', 0))  # 16% +NC paid
        data[12] += float(values.get('refunds_16', 0))  # 16% refunds
        data[13] += float(values.get('paid_16_imp_wnc', 0))  # 16% imports +NC paid
        data[14] += float(values.get('refunds_16_imp', 0))  # 16% imports refunds
        data[15] += float(values.get('paid_16_imp_int_wnc', 0))  # 16% intangible imports +NC paid
        data[16] += float(values.get('refunds_16_imp_int', 0))  # 16% int imp refunds
        # Creditable VAT
        data[17] += float(values.get('paid_8_tax', 0))  # 8% Northern paid
        data[19] += float(values.get('paid_8_s_tax', 0))  # 8% Southern paid
        data[21] += float(values.get('paid_16_tax', 0))  # 16% VAT exclusive base
        data[23] += float(values.get('importation_16_tax', 0))  # 16% import VAT exclusive base
        data[25] += float(values.get('paid_16_imp_int_tax', 0))  # 16% int imp VAT exclusive base
        # Non-creditable VAT
        data[27] += float(values.get('paid_8_non_cred_tax', 0))  # 8% Northern NC paid
        data[31] += float(values.get('paid_8_s_nc_tax', 0))  # 8% Southern NC paid
        data[35] += float(values.get('paid_16_non_cred_tax', 0))  # 16% NC paid
        data[39] += float(values.get('paid_16_imp_nc_tax', 0))  # 16% imports NC paid
        data[43] += float(values.get('paid_16_imp_int_nc_tax', 0))  # 16% non tangible imports NC paid
        # Additional data
        data[47] += float(values.get('withheld', 0))  # DIOT:Retention base
        data[48] += float(values.get('exempt_imp', 0))  # DIOT:Import Exempt base
        data[49] += float(values.get('exempt', 0))  # DIOT:Exempt base
        data[50] += float(values.get('paid_0', 0))  # 0% payments
        data[51] += float(values.get('no_obj', 0))  # No tax object
        # Declaration
        data[53] = '02' if is_global else '01'  # "Hereby I declare that I rightfully credited VAT"

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
            if not any(values.get(x) for x in (
                'paid_16_tax', 'paid_16_non_cred_tax', 'paid_8_tax', 'paid_8_non_cred_tax', 'importation_16_tax',
                'paid_0', 'exempt', 'withheld', 'refunds_8_n', 'refunds_16', 'refunds_16_imp'
            )):
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
            data[33] = round(float(values.get('paid_16_tax', 0))) or ''  # 16%
            data[36] = round(float(values.get('paid_8_tax', 0))) or ''  # 8%
            data[39] = round(float(values.get('importation_16_tax', 0))) or ''  # 16% - Importation
            data[44] = round(float(values.get('paid_0', 0))) or ''  # 0%
            data[45] = round(float(values.get('exempt', 0))) or ''  # Exempt
            data[46] = round(float(values.get('withheld', 0))) or ''  # Withheld
            data[47] = round(float(values.get('refunds_8_n', 0)) + float(values.get('refunds_16', 0)) + float(values.get('refunds_16_imp', 0))) or ''  # Refunds

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
                if not partner_id:
                    raise UserError(_("The report cannot be generated because there are entries with tax amounts but no partner assigned."))
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
