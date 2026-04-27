# Part of Odoo. See LICENSE file for full copyright and licensing details.

import csv
import io
import zipfile
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.tools import SQL


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.company.account_fiscal_country_id.code == "PE":
            options["buttons"].append({
                "name": _("Inventory and Balance"),
                "sequence": 45,
                "action": "export_file",
                "action_param": "l10n_pe_export_lib_to_txt",
                "file_export_type": _("TXT"),
            })

    @api.model
    def l10n_pe_export_lib_to_txt(self, options):
        def get_txt(code, data, company_vat, file_date_to):
            txt_result = ""
            if data:
                output = io.StringIO()
                writer = csv.DictWriter(output, delimiter="|", skipinitialspace=True, lineterminator='|\n', fieldnames=data[0].keys())
                writer.writerows(data)
                txt_result = output.getvalue()
            filename = "LE%s%s%02d%02d%s011111.txt" % (
                company_vat,
                file_date_to.year,
                file_date_to.month,
                file_date_to.day,
                code,
            )
            return filename, txt_result.encode()

        report = self.env.ref('account_reports.general_ledger_report')
        report._init_currency_table(options)
        currency_table_query = {
            'join': report._currency_table_aml_join(options),
            'balance': report._currency_table_apply_rate(SQL("account_move_line.balance")),
            'debit': report._currency_table_apply_rate(SQL("account_move_line.debit")),
            'credit': report._currency_table_apply_rate(SQL("account_move_line.credit")),
            'residual': report._currency_table_apply_rate(SQL("account_move_line.amount_residual")),
        }
        pages_list = [
            ('030100', self._l10n_pe_get_lib_3_1_data),
            ('030200', self._l10n_pe_get_lib_3_2_data),
            ('030300', self._l10n_pe_get_lib_3_3_data),
            ('030400', self._l10n_pe_get_lib_3_4_data),
            ('030500', self._l10n_pe_get_lib_3_5_data),
            ('030600', self._l10n_pe_get_lib_3_6_data),
            ('030700', self._l10n_pe_get_lib_3_7_data),
            ('031100', self._l10n_pe_get_lib_3_11_data),
            ('031200', self._l10n_pe_get_lib_3_12_data),
            ('031300', self._l10n_pe_get_lib_3_13_data),
            ('031400', self._l10n_pe_get_lib_3_14_data),
            ('031500', self._l10n_pe_get_lib_3_15_data),
            ('031601', self._l10n_pe_get_lib_3_16_1_data),
            ('031602', self._l10n_pe_get_lib_3_16_2_data),
            ('031700', self._l10n_pe_get_lib_3_17_data),
            ('031800', self._l10n_pe_get_lib_3_18_data),
            ('032000', self._l10n_pe_get_lib_3_20_data),
            ('032400', self._l10n_pe_get_lib_3_24_data),
            ('032500', self._l10n_pe_get_lib_3_25_data),
        ]
        date_to = fields.Date.to_date(options['date']['date_to'])
        documents = []
        # As we are working with direct queries, flush all models included in the reports beforehand
        self.env['account.move.line'].flush_model()
        self.env['account.move'].flush_model()
        self.env['account.account'].flush_model()
        self.env['res.bank'].flush_model()
        self.env['res.partner.bank'].flush_model()
        self.env['account.journal'].flush_model()
        self.env['l10n_pe_reports_lib.shareholder'].flush_model()
        for page in pages_list:
            documents.append(get_txt(page[0], page[1](options, currency_table_query), self.env.company.vat, date_to))
        with io.BytesIO() as buffer:
            with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zip_file:
                for filename, content in documents:
                    zip_file.writestr(filename, content)
            zip_result = buffer.getvalue()

        return {
            "file_name": "Inventory_and_balance_reports_%s%02d%02d" % (date_to.year, date_to.month, date_to.day),
            "file_content": zip_result,
            "file_type": "zip",
        }

    def _l10n_pe_get_fs_rubric_data(self, options, currency_table_query, fs_rubric_codes):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                res_company.l10n_pe_financial_statement_type AS fs_catalog,
                l10n_pe_reports_lib_financial_rubric.name AS fs_rubric,
                SUM(%(balance_select)s) AS balance,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            JOIN account_account_l10n_pe_reports_lib_financial_rubric_rel
            ON account_account_l10n_pe_reports_lib_financial_rubric_rel.account_account_id = account_account.id
            JOIN l10n_pe_reports_lib_financial_rubric
            ON l10n_pe_reports_lib_financial_rubric.id = account_account_l10n_pe_reports_lib_financial_rubric_rel.l10n_pe_reports_lib_financial_rubric_id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND l10n_pe_reports_lib_financial_rubric.name IN %(fs_rubric_codes)s
            GROUP BY fs_catalog, fs_rubric
            """,
            date=options['date']['date_to'].replace('-', ''),
            balance_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            fs_rubric_codes=fs_rubric_codes,
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            item['balance'] = "%.2f" % item['balance']
        return query_res_lines

    def _l10n_pe_get_moves_data(self, options, currency_table_query, account_codes):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                account_move.name AS move_name,
                account_move.id AS move_number,
                %(account_code_sql)s AS account_code,
                l10n_latam_identification_type.l10n_pe_vat_code AS id_type_code,
                res_partner.vat AS partner_vat,
                res_partner.name AS partner_name,
                account_move.date AS move_date,
                SUM(%(balance_select)s) AS move_amount_residual,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN res_partner ON res_partner.id = account_move_line.partner_id
            JOIN l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND starts_with(%(account_code_sql)s, %(account_codes)s)
            GROUP BY move_name, move_number, account_code, id_type_code, partner_vat, partner_name, move_date
            """,
            date=options['date']['date_to'].replace('-', ''),
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            balance_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
            account_codes=account_codes,
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            item['move_name'] = item['move_name'].replace('/', '')
            item['move_number'] = ("M%9d" % int(item['move_number'])).replace(' ', '0')
            item['move_date'] = (item['move_date'] or options['date']['date_to']).strftime('%d/%m/%Y')
            item['move_amount_residual'] = "%.2f" % item['move_amount_residual']
        return query_res_lines

    def _l10n_pe_get_lib_3_1_data(self, options, currency_table_query):
        fs_rubric_codes = (
            '1D0109', '1D0114', '1D0121', '1D0103', '1D0105', '1D0104', '1D0107', '1D0106', '1D0112', '1D0117',
            '1D0113', '1D0118', '1D0119', '1D0120', '1D0115', '1D01ST', '1D0217', '1D0221', '1D0219', '1D0201',
            '1D0203', '1D0202', '1D0220', '1D0216', '1D0211', '1D0205', '1D0206', '1D0207', '1D0212', '1D0208',
            '1D02ST', '1D020T', '1D0309', '1D0316', '1D0302', '1D0304', '1D0303', '1D0317', '1D0313', '1D0310',
            '1D0311', '1D0314', '1D0315', '1D0312', '1D03ST', '1D0401', '1D0411', '1D0407', '1D0408', '1D0402',
            '1D0403', '1D0409', '1D0406', '1D0404', '1D0410', '1D04ST', '1D040T', '1D0701', '1D0702', '1D0703',
            '1D0711', '1D0712', '1D0707', '1D0708', '1D07ST', '1D070T'
        )
        return self._l10n_pe_get_fs_rubric_data(options, currency_table_query, fs_rubric_codes)

    def _l10n_pe_get_lib_3_2_data(self, options, currency_table_query):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                %(account_code_sql)s AS account_code,
                res_bank.l10n_pe_edi_code AS bank_code,
                CASE
                    WHEN res_bank.l10n_pe_edi_code = '99' THEN NULL
                    WHEN res_bank.l10n_pe_edi_code IS NULL THEN NULL
                ELSE
                    res_partner_bank.acc_number
                END AS bank_account,
                rc_2.name AS account_currency,
                SUM(%(balance_select)s) AS sum_debit,
                'PLACEHOLDER' AS sum_credit,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            JOIN account_move ON account_move.id = account_move_line.move_id
            LEFT JOIN account_journal ON account_journal.default_account_id = account_account.id
            LEFT JOIN res_partner_bank ON res_partner_bank.id = account_journal.bank_account_id
            LEFT JOIN res_bank on res_bank.id = res_partner_bank.bank_id
            LEFT JOIN res_currency rc_2 ON rc_2.id = res_partner_bank.currency_id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND starts_with(%(account_code_sql)s, '10')
            AND account_account.account_type = 'asset_cash'
            GROUP BY report_date, account_code, bank_code, bank_account, account_currency
            """,
            date=options['date']['date_to'].replace('-', ''),
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            balance_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            if not item['bank_code']:
                item['bank_code'] = '99'
                item['bank_account'] = '-'
            if not item['account_currency']:
                item['account_currency'] = 'PEN'
            if item['sum_debit'] >= 0:
                item['sum_debit'] = "%.2f" % (float(item['sum_debit']))
                item['sum_credit'] = '0.00'
            else:
                item['sum_credit'] = "%.2f" % (- float(item['sum_debit']))
                item['sum_debit'] = '0.00'
        return query_res_lines

    def _l10n_pe_get_lib_3_3_data(self, options, currency_table_query):
        query_res_lines = [
            *self._l10n_pe_get_moves_data(options, currency_table_query, '12'),
            *self._l10n_pe_get_moves_data(options, currency_table_query, '13'),
        ]
        for item in query_res_lines:
            del item['account_code']
        return query_res_lines

    def _l10n_pe_get_lib_3_4_data(self, options, currency_table_query):

        def _get_moves_data_int(account_codes_int):
            query = SQL("""
                SELECT DISTINCT
                    %(date)s AS report_date,
                    account_move.name AS move_name,
                    account_move.id AS move_number,
                    l10n_latam_identification_type.l10n_pe_vat_code AS id_type_code,
                    res_partner.vat AS partner_vat,
                    res_partner.name AS partner_name,
                    account_move.date AS move_date,
                    SUM(%(residual_select)s) AS move_amount_residual,
                    '1' AS op_status
                FROM res_company
                JOIN account_move_line ON account_move_line.company_id = res_company.id
                JOIN account_account ON account_account.id = account_move_line.account_id
                JOIN account_move ON account_move.id = account_move_line.move_id
                JOIN res_partner ON res_partner.id = account_move_line.partner_id
                JOIN l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
                %(currency_table_join)s
                WHERE res_company.id IN %(companies)s
                AND account_move_line.date < %(date_to)s
                AND starts_with(%(account_code_sql)s, %(account_codes)s)
                GROUP BY move_name, move_number, id_type_code, partner_vat, partner_name, move_date
                """,
                date=options['date']['date_to'].replace('-', ''),
                account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
                residual_select=currency_table_query['balance'],
                currency_table_join=currency_table_query['join'],
                companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
                date_to=options['date']['date_to'],
                account_codes=account_codes_int,
            )
            self.env.cr.execute(query)
            query_res_lines = self.env.cr.dictfetchall()
            for item in query_res_lines:
                if item['move_date']:
                    md = fields.Datetime.to_string(item['move_date']).split()[0].split('-')
                else:
                    md = fields.Datetime.to_string(options['date']['date_to']).split()[0].split('-')
                item['move_number'] = ("M%9d" % int(item['move_number'])).replace(' ', '0')
                item['move_date'] = '/'.join([md[2], md[1], md[0]])
                item['move_amount_residual'] = "%.2f" % item['move_amount_residual']
            return query_res_lines

        query_res_lines = [
            *_get_moves_data_int('14'),
            *_get_moves_data_int('15'),
        ]
        return query_res_lines

    def _l10n_pe_get_lib_3_5_data(self, options, currency_table_query):
        query_res_lines = [
            *self._l10n_pe_get_moves_data(options, currency_table_query, '16'),
            *self._l10n_pe_get_moves_data(options, currency_table_query, '17'),
        ]
        for item in query_res_lines:
            del item['account_code']
        return query_res_lines

    def _l10n_pe_get_lib_3_6_data(self, options, currency_table_query):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                account_move.name AS move_name,
                account_move.id AS move_number,
                l10n_latam_identification_type.l10n_pe_vat_code AS id_type_code,
                res_partner.vat AS partner_vat,
                res_partner.name AS partner_name,
                l10n_latam_document_type.code AS move_type_code,
                'PLACEHOLDER' AS serie,
                'PLACEHOLDER' AS folio,
                account_move.date AS move_date,
                SUM(%(residual_select)s) AS move_amount_residual,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN res_partner ON res_partner.id = account_move_line.partner_id
            LEFT JOIN l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
            LEFT JOIN l10n_latam_document_type ON account_move.l10n_latam_document_type_id = l10n_latam_document_type.id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND starts_with(%(account_code_sql)s, '19')
            GROUP BY move_name, move_number, id_type_code, move_date, partner_vat, partner_name, move_type_code
            """,
            date=options['date']['date_to'].replace('-', ''),
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            residual_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            sf = self.env["l10n_pe.tax.ple.report.handler"]._get_serie_folio(item['move_name'] or '')
            md = fields.Datetime.to_string(item['move_date']).split()[0].split('-')
            item['move_number'] = ("M%9d" % int(item['move_number'])).replace(' ', '0')
            if item['move_type_code']:
                item['move_type_code'] = '0' * (2 - len(item['move_type_code'])) + item['move_type_code']
            else:
                item['move_type_code'] = '00'
            item['serie'] = sf['serie'].replace(' ', '').replace('/', '')
            item['folio'] = sf['folio'].replace(' ', '')
            item['move_date'] = '/'.join([md[2], md[1], md[0]])
            item['move_amount_residual'] = "%.2f" % (- item['move_amount_residual'])
        return query_res_lines

    def _l10n_pe_get_lib_3_7_data(self, options, currency_table_query):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                '1' AS catalog_code,
                product_template.l10n_pe_type_of_existence AS product_category_type,
                product_product.default_code AS product_default_code,
                '1' AS product_catalog_code,
                product_unspsc_code.code AS product_unspsc_code_b,
                %(product_template_name)s AS product_name,
                uom_uom.l10n_pe_edi_measure_unit_code AS product_uom_code,
                CASE
                    WHEN product_category.property_cost_method->>(res_company.id::TEXT) = 'average' THEN '1'
                    WHEN product_category.property_cost_method->>(res_company.id::TEXT) = 'fifo' THEN '2'
                    WHEN product_category.property_cost_method->>(res_company.id::TEXT) = 'standard' THEN '3'
                ELSE
                    '3'
                END AS product_valuation_code,
                product_product.id as temp_product_id,
                stock_valuation_layer.id as temp_svl_id
            FROM res_company
            JOIN stock_move ON stock_move.company_id = res_company.id
            JOIN product_product ON product_product.id = stock_move.product_id
            JOIN product_template ON product_template.id = product_product.product_tmpl_id
            JOIN uom_uom ON uom_uom.id = product_template.uom_id
            JOIN stock_valuation_layer ON stock_valuation_layer.stock_move_id = stock_move.id
            LEFT JOIN product_unspsc_code ON product_unspsc_code.id = product_template.unspsc_code_id
            LEFT JOIN product_category ON product_category.id = product_template.categ_id
            WHERE res_company.id IN %(companies)s
            AND stock_move.date < %(date_to)s
            AND product_product.default_code IS NOT NULL
            AND product_template.l10n_pe_type_of_existence IS NOT NULL
            """,
            date=options['date']['date_to'].replace('-', ''),
            product_template_name=self.env['product.template']._field_to_sql('product_template', 'name'),
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        new_res_lines = []
        svl_lines_prefetch = self.env['stock.valuation.layer'].browse(tuple(item['temp_svl_id'] for item in query_res_lines))
        for item, product_id in zip(query_res_lines, tuple(item['temp_product_id'] for item in query_res_lines)):
            if any(list_item['temp_product_id'] == item['temp_product_id'] for list_item in new_res_lines):
                continue
            item.pop('temp_svl_id')
            item['product_category_type'] = item['product_category_type'].zfill(2)
            stock_values = [0.0, 0.0]
            for svl_line in svl_lines_prefetch:
                if svl_line.product_id.id == product_id:
                    stock_values = [sum(x) for x in zip(stock_values, [svl_line.quantity, svl_line.value])]
            item.update({
                'stock_quantity': stock_values[0],
                'stock_unit_cost': stock_values[1] / stock_values[0] if stock_values[0] else 0.0,
                'stock_value': stock_values[1],
                'op_status': '1',
            })
            for key in ['stock_quantity', 'stock_unit_cost', 'stock_value']:
                item[key] = "%.2f" % item[key]
            item['product_default_code'] = ''.join(e for e in item['product_default_code'] if e.isalnum())
            if item['stock_quantity'] != '0.00':
                new_res_lines.append(item)
        for item in new_res_lines:
            item.pop('temp_product_id')
        return new_res_lines

    def _l10n_pe_get_lib_3_11_data(self, options, currency_table_query):
        query = SQL("""
            SELECT DISTINCT
                %(date)s AS report_date,
                account_move.name AS move_name,
                account_move.id AS move_number,
                %(account_code_sql)s AS account_code,
                l10n_latam_identification_type.l10n_pe_vat_code AS id_type_code,
                res_partner.vat AS partner_vat,
                res_partner.ref AS partner_ref,
                res_partner.name AS partner_name,
                SUM(%(residual_select)s) AS move_amount_residual,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN res_partner ON res_partner.id = account_move_line.partner_id
            JOIN l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND starts_with(%(account_code_sql)s, %(account_codes)s)
            GROUP BY move_name, move_number, account_code, id_type_code, partner_vat, partner_name, partner_ref
            """,
            date=options['date']['date_to'].replace('-', ''),
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            residual_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
            account_codes='41',
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            item['move_name'] = item['move_name'].replace('/', '')
            item['move_number'] = ("M%9d" % int(item['move_number'])).replace(' ', '0')
            item['move_amount_residual'] = "%.2f" % item['move_amount_residual']
            item['partner_ref'] = item['partner_ref'][:11] if item['partner_ref'] else ''
        return query_res_lines

    def _l10n_pe_get_lib_3_12_data(self, options, currency_table_query):

        def _get_moves_data_int(account_codes_int):
            query = SQL("""
                SELECT DISTINCT
                    %(date)s AS report_date,
                    account_move.name AS move_name,
                    account_move.id AS move_number,
                    l10n_latam_identification_type.l10n_pe_vat_code AS id_type_code,
                    res_partner.vat AS partner_vat,
                    account_move.date AS move_date,
                    res_partner.name AS partner_name,
                    SUM(%(residual_select)s) AS move_amount_residual,
                    '1' AS op_status
                FROM res_company
                JOIN account_move_line ON account_move_line.company_id = res_company.id
                JOIN account_account ON account_account.id = account_move_line.account_id
                JOIN account_move ON account_move.id = account_move_line.move_id
                JOIN res_partner ON res_partner.id = account_move_line.partner_id
                JOIN l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
                %(currency_table_join)s
                WHERE res_company.id IN %(companies)s
                AND account_move_line.date < %(date_to)s
                AND starts_with(%(account_code_sql)s, %(account_codes)s)
                GROUP BY move_name, move_number, id_type_code, partner_vat, partner_name, move_date
                """,
                date=options['date']['date_to'].replace('-', ''),
                account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
                residual_select=currency_table_query['balance'],
                currency_table_join=currency_table_query['join'],
                companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
                date_to=options['date']['date_to'],
                account_codes=account_codes_int,
            )
            self.env.cr.execute(query)
            query_res_lines = self.env.cr.dictfetchall()
            for item in query_res_lines:
                if item['move_date']:
                    md = fields.Datetime.to_string(item['move_date']).split()[0].split('-')
                else:
                    md = fields.Datetime.to_string(options['date']['date_to']).split()[0].split('-')
                item['move_name'] = item['move_name'].replace('/', '')
                item['move_number'] = ("M%9d" % int(item['move_number'])).replace(' ', '0')
                item['move_date'] = '/'.join([md[2], md[1], md[0]])
                item['move_amount_residual'] = "%.2f" % item['move_amount_residual']
            return query_res_lines

        query_res_lines = [
            *_get_moves_data_int('42'),
            *_get_moves_data_int('43')
        ]
        return query_res_lines

    def _l10n_pe_get_lib_3_13_data(self, options, currency_table_query):
        query = SQL("""
            SELECT DISTINCT
                %(date)s AS report_date,
                account_move.name AS move_name,
                account_move.id AS move_number,
                l10n_latam_identification_type.l10n_pe_vat_code AS id_type_code,
                res_partner.vat AS partner_vat,
                account_move.date AS move_date,
                res_partner.name AS partner_name,
                %(account_code_sql)s AS account_code,
                SUM(%(residual_select)s) AS move_amount_residual,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN res_partner ON res_partner.id = account_move_line.partner_id
            JOIN l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND starts_with(%(account_code_sql)s, %(account_codes)s)
            GROUP BY move_name, move_number, account_code, id_type_code, partner_vat, partner_name, move_date
            """,
            date=options['date']['date_to'].replace('-', ''),
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            residual_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
            account_codes='46',
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            if item['move_date']:
                md = fields.Datetime.to_string(item['move_date']).split()[0].split('-')
            else:
                md = fields.Datetime.to_string(options['date']['date_to']).split()[0].split('-')
            item['move_name'] = item['move_name'].replace('/', '')
            item['move_number'] = ("M%9d" % int(item['move_number'])).replace(' ', '0')
            item['move_date'] = '/'.join([md[2], md[1], md[0]])
            item['move_amount_residual'] = "%.2f" % item['move_amount_residual']
        return query_res_lines

    def _l10n_pe_get_lib_3_14_data(self, options, currency_table_query):
        query_res_lines = self._l10n_pe_get_moves_data(options, currency_table_query, '47')
        for item in query_res_lines:
            del item['account_code']
            del item['move_date']
        return query_res_lines

    def _l10n_pe_get_lib_3_15_data(self, options, currency_table_query):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                account_move.name AS move_name,
                account_move.id AS move_number,
                l10n_latam_document_type.code AS move_type_code,
                'PLACEHOLDER' AS serie,
                'PLACEHOLDER' AS folio,
                %(account_code_sql)s AS account_code,
                CASE
                    WHEN account_move.ref IS NOT NULL THEN account_move.ref
                ELSE '-'
                END AS move_ref,
                SUM(%(residual_select)s) AS move_amount_residual,
                '0.00' as additions,
                '0.00' as deductions,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN res_partner ON res_partner.id = account_move_line.partner_id
            LEFT JOIN l10n_latam_document_type ON account_move.l10n_latam_document_type_id = l10n_latam_document_type.id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND (starts_with(%(account_code_sql)s, '37') OR starts_with(%(account_code_sql)s, '49'))
            GROUP BY move_name, move_number, move_type_code, move_ref, account_code
            """,
            date=options['date']['date_to'].replace('-', ''),
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            residual_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            sf = self.env["l10n_pe.tax.ple.report.handler"]._get_serie_folio(item['move_name'] or '')
            item['move_number'] = ("M%9d" % int(item['move_number'])).replace(' ', '0')
            if item['move_type_code']:
                item['move_type_code'] = '0' * (2 - len(item['move_type_code'])) + item['move_type_code']
            else:
                item['move_type_code'] = '00'
            item['serie'] = sf['serie'].replace(' ', '').replace('/', '')
            item['folio'] = sf['folio'].replace(' ', '')
            item['move_amount_residual'] = "%.2f" % item['move_amount_residual']
        return query_res_lines

    def _l10n_pe_get_lib_3_16_1_data(self, options, currency_table_query):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                SUM(%(balance_select)s) AS balance_amount,
                '1' AS nominal_value,
                'PLACEHOLDER' AS balance_number,
                'PLACEHOLDER' AS balance_interest,
                '1' AS op_status
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            AND starts_with(%(account_code_sql)s, '50')
            """,
            date=options['date']['date_to'].replace('-', ''),
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            balance_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=options['date']['date_to'],
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        for item in query_res_lines:
            item['balance_amount'] = "%.2f" % abs(item['balance_amount'] if item['balance_amount'] else 0.0)
            item['balance_number'] = item['balance_amount']
            item['balance_interest'] = item['balance_amount']
        return query_res_lines

    def _l10n_pe_get_lib_3_16_2_data(self, options, currency_table_query):
        query = SQL("""
            SELECT
                %(date)s AS report_date,
                l10n_latam_identification_type.l10n_pe_vat_code AS id_type_code,
                res_partner.vat AS partner_vat,
                l10n_pe_reports_lib_shareholder.participation_type_code AS participation_type_code,
                res_partner.name AS partner_name,
                l10n_pe_reports_lib_shareholder.shares_qty AS shares_qty,
                l10n_pe_reports_lib_shareholder.shares_percentage AS shares_percentage,
                '1' AS op_status
            FROM res_company
            JOIN l10n_pe_reports_lib_shareholder ON l10n_pe_reports_lib_shareholder.company_id = res_company.id
            JOIN res_partner ON res_partner.id = l10n_pe_reports_lib_shareholder.partner_id
            JOIN l10n_latam_identification_type ON res_partner.l10n_latam_identification_type_id = l10n_latam_identification_type.id
            WHERE res_company.id IN %(companies)s
            """,
            date=options['date']['date_to'].replace('-', ''),
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
        )
        self.env.cr.execute(query)
        query_res_lines = self.env.cr.dictfetchall()
        return query_res_lines

    def _l10n_pe_get_lib_3_17_data(self, options, currency_table_query):
        query_1 = SQL("""
            SELECT
                %(account_code_sql)s AS account_code,
                SUM(%(balance_select)s) AS sum_balance
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date < %(date_to)s
            GROUP BY account_code
            """,
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            balance_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_to=fields.Datetime.to_string(fields.Datetime.from_string(options['date']['date_from']) + timedelta(days=1)),
        )
        self.env.cr.execute(query_1)
        query_res_lines_1 = self.env.cr.dictfetchall()

        query_2 = SQL("""
            SELECT
                %(account_code_sql)s AS account_code,
                SUM(%(balance_select)s) AS sum_balance
            FROM res_company
            JOIN account_move_line ON account_move_line.company_id = res_company.id
            JOIN account_account ON account_account.id = account_move_line.account_id
            %(currency_table_join)s
            WHERE res_company.id IN %(companies)s
            AND account_move_line.date >= %(date_from)s
            AND account_move_line.date < %(date_to)s
            GROUP BY account_code
            """,
            account_code_sql=self.env['account.account']._field_to_sql('account_account', 'code'),
            balance_select=currency_table_query['balance'],
            currency_table_join=currency_table_query['join'],
            companies=tuple(self.env.ref('account_reports.general_ledger_report').get_report_company_ids(options)),
            date_from=options['date']['date_from'],
            date_to=options['date']['date_to'],
        )
        self.env.cr.execute(query_2)
        query_res_lines_2 = self.env.cr.dictfetchall()

        query_res_lines = {}
        for line in query_res_lines_1:
            query_res_lines[line['account_code']] = {
                'sum_debit_start': line['sum_balance'] if line['sum_balance'] > 0 else 0.0,
                'sum_credit_start': -line['sum_balance'] if line['sum_balance'] < 0 else 0.0,
                'sum_debit_during': 0.0,
                'sum_credit_during': 0.0,
                'sum_debit_end': line['sum_balance'] if line['sum_balance'] > 0 else 0.0,
                'sum_credit_end': -line['sum_balance'] if line['sum_balance'] < 0 else 0.0,
            }
        for line in query_res_lines_2:
            if (line['account_code']) not in query_res_lines:
                query_res_lines[line['account_code']] = {
                    'sum_debit_start': 0.0,
                    'sum_credit_start': 0.0,
                    'sum_debit_end': 0.0,
                    'sum_credit_end': 0.0,
                }
            query_res_lines[line['account_code']]['sum_debit_during'] = line['sum_balance'] if line['sum_balance'] > 0 else 0.0
            query_res_lines[line['account_code']]['sum_credit_during'] = -line['sum_balance'] if line['sum_balance'] < 0 else 0.0
            query_res_lines[line['account_code']]['sum_debit_end'] += line['sum_balance'] if line['sum_balance'] > 0 else 0.0
            query_res_lines[line['account_code']]['sum_credit_end'] -= line['sum_balance'] if line['sum_balance'] < 0 else 0.0
        query_res_lines = [{
            'report_date': options['date']['date_to'].replace('-', ''),
            'account_code': key,
            'sum_debit_start': "%.2f" % value['sum_debit_start'],
            'sum_credit_start': "%.2f" % value['sum_credit_start'],
            'sum_debit_during': "%.2f" % value['sum_debit_during'],
            'sum_credit_during': "%.2f" % value['sum_credit_during'],
            'sum_debit_end': "%.2f" % value['sum_debit_end'],
            'sum_credit_end': "%.2f" % value['sum_credit_end'],
            'balance_debit_end': "%.2f" % max(value['sum_debit_end'] - value['sum_credit_end'], 0.0),
            'balance_credit_end': "%.2f" % max(value['sum_credit_end'] - value['sum_debit_end'], 0.0),
            'transfers_and_cancellations_debit': '0.00',
            'transfers_and_cancellations_credit': '0.00',
            'balance_sheet_accounts_assets': '0.00',
            'balance_sheet_accounts_liabilities': '0.00',
            'result_by_nature_losses': '0.00',
            'result_by_nature_earnings': '0.00',
            'additions': '0.00',
            'deductions': '0.00',
            'op_status': '1',
        } for key, value in query_res_lines.items()]
        return query_res_lines

    def _l10n_pe_get_lib_3_18_data(self, options, currency_table_query):
        fs_rubric_codes = (
            '3D0101', '3D0112', '3D0110', '3D0117', '3D0104', '3D0109', '3D0118', '3D0105', '3D0119', '3D0108',
            '3D0121', '3D0103', '3D0107', '3D0111', '3D0116', '3D0120', '3D0122', '3D01ST', '3D0220', '3D0218',
            '3D0209', '3D0201', '3D0221', '3D0222', '3D0202', '3D0203', '3D0223', '3D0231', '3D0210', '3D0211',
            '3D0225', '3D0232', '3D0212', '3D0205', '3D0226', '3D0219', '3D0227', '3D0206', '3D0207', '3D0229',
            '3D0233', '3D0234', '3D02ST', '3D0325', '3D0319', '3D0326', '3D0327', '3D0328', '3D0329', '3D0330',
            '3D0322', '3D0321', '3D0331', '3D0310', '3D0323', '3D0311', '3D0305', '3D0332', '3D0333', '3D03ST',
            '3D0401', '3D0404', '3D0405', '3D0402', '3D04ST'
        )
        return self._l10n_pe_get_fs_rubric_data(options, currency_table_query, fs_rubric_codes)

    def _l10n_pe_get_lib_3_20_data(self, options, currency_table_query):
        fs_rubric_codes = (
            '2D01ST', '2D0201', '2D02ST', '2D0302', '2D0301', '2D0407', '2D0403', '2D0404', '2D0412', '2D03ST',
            '2D0401', '2D0402', '2D0410', '2D0414', '2D0411', '2D0413', '2D04ST', '2D0502', '2D0503', '2D0504',
            '2D07ST'
        )
        return self._l10n_pe_get_fs_rubric_data(options, currency_table_query, fs_rubric_codes)

    def _l10n_pe_get_lib_3_24_data(self, options, currency_table_query):
        fs_rubric_codes = (
           '5D0101', '5D0103', '5D0109', '5D0104', '5D0105', '5D0110', '5D0107', '5D0111', '5D0112', '5D01ST',
           '5D0202', '5D0208', '5D0203', '5D0204', '5D0209', '5D0206', '5D0210', '5D0211', '5D02ST', '5D03ST',
           '5D04ST'
        )
        return self._l10n_pe_get_fs_rubric_data(options, currency_table_query, fs_rubric_codes)

    def _l10n_pe_get_lib_3_25_data(self, options, currency_table_query):
        fs_rubric_codes = (
           '3D05ST', '3D0611', '3D0627', '3D0628', '3D0629', '3D0620', '3D0610', '3D0602', '3D0631', '3D0632',
           '3D0634', '3D0635', '3D0605', '3D0618', '3D0608', '3D0835', '3D0804', '3D0813', '3D0818', '3D0833',
           '3D0829', '3D0815', '3D0830', '3D0121', '3D0103', '3D0107', '3D0111', '3D0116', '3D0120', '3D01ST',
           '3D0220', '3D0218', '3D0209', '3D0201', '3D0221', '3D0222', '3D0202', '3D0203', '3D0223', '3D0231',
           '3D0210', '3D0211', '3D0225', '3D0232', '3D0212', '3D0205', '3D0226', '3D0219', '3D0227', '3D0206',
           '3D0207', '3D0229', '3D0233', '3D0234', '3D02ST', '3D0325', '3D0319', '3D0326', '3D0327', '3D0328',
           '3D0329', '3D0330', '3D0322', '3D0321', '3D0331', '3D0310', '3D0323', '3D0311', '3D0305', '3D0332',
           '3D0333', '3D03ST', '3D0401', '3D0404', '3D0405', '3D0402', '3D04ST'
        )
        return self._l10n_pe_get_fs_rubric_data(options, currency_table_query, fs_rubric_codes)
