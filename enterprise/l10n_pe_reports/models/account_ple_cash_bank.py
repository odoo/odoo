from odoo import models, _, osv
from odoo.tools import groupby, SQL
from odoo.tools.float_utils import float_repr


class AccountCashFlowReportHandler(models.AbstractModel):
    _inherit = 'account.cash.flow.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        if self.env.company.account_fiscal_country_id.code == 'PE':
            options.setdefault('buttons', []).append(
                {
                    'name': _("TXT PLE 1.1 (Cash)"),
                    'sequence': 20,
                    'action': 'export_file',
                    'action_param': 'l10n_pe_export_ple_11_to_txt',
                    'file_export_type': _("TXT"),
                }
            )
            options.setdefault('buttons', []).append(
                {
                    'name': _("TXT PLE 1.2 (Bank)"),
                    'sequence': 25,
                    'action': 'export_file',
                    'action_param': 'l10n_pe_export_ple_12_to_txt',
                    'file_export_type': _("TXT"),
                }
            )

    def l10n_pe_export_ple_11_to_txt(self, options):
        txt_data = self._l10n_pe_get_txt_11_data(options)

        return self.env['account.general.ledger.report.handler']._l10n_pe_get_file_txt(options, txt_data, '0101')

    def l10n_pe_export_ple_12_to_txt(self, options):
        txt_data = self._l10n_pe_get_txt_12_data(options)

        return self.env['account.general.ledger.report.handler']._l10n_pe_get_file_txt(options, txt_data, '0102')

    def _l10n_pe_get_txt_11_data(self, options):
        """ Generates the TXT content for the PLE reports with the entries data """

        # Retrieve the data from the ledger itself, unfolding every group
        report = self.env['account.report'].browse(options['report_id'])
        # Options ---------------------------------
        # We don't need all companies
        options.pop('multi_company', None)
        options['single_company'] = self.env.company.ids

        # Filter cash journals
        options['journals'] = [journal for journal in options.get('journals', []) if journal.get('type') == 'cash']

        # Prepare query to get lines
        domain = osv.expression.AND([
            report._get_options_domain(options, 'strict_range'),
            [('statement_line_id', '!=', False), ('matching_number', '=', False)],
        ])
        self.env['account.move.line'].check_access('read')
        query = self.env['account.move.line']._where_calc(domain)
        journal_alias = query.join(lhs_alias='account_move_line', lhs_column='journal_id', rhs_table='account_journal', rhs_column='id', link='journal_id')
        account_alias = query.join(lhs_alias=journal_alias, lhs_column='default_account_id', rhs_table='account_account', rhs_column='id', link='default_account_id')
        account_code = self.env['account.account']._field_to_sql(account_alias, 'code', query)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        sql = SQL("""
               SELECT bank_statement_line.id,
                      bank_statement_line.amount,
                      bank_statement_line.payment_ref,
                      %(account_code)s AS account_code,
                      account_move_fr.move_type,
                      bank_statement_move.date,
                      account_move_fr.name AS move_name,
                      account_move_fr.invoice_date,
                      account_move_fr.invoice_date_due,
                      account_move_line.move_id,
                      aml_currency.name AS currency_name,
                      latam_doctype.code AS document_type
                 FROM %(from_clause)s
                 JOIN account_move ON account_move_line.move_id = account_move.id
            LEFT JOIN account_move_line AS account_move_line_bs ON account_move.id = account_move_line_bs.move_id
            LEFT JOIN account_move_line AS account_move_line_fr ON account_move_line_bs.matching_number = account_move_line_fr.matching_number
            LEFT JOIN account_move AS account_move_fr ON account_move_line_fr.move_id = account_move_fr.id
                 JOIN account_bank_statement_line AS bank_statement_line ON account_move_line.statement_line_id = bank_statement_line.id
                 JOIN account_move AS bank_statement_move ON bank_statement_line.move_id = bank_statement_move.id
            LEFT JOIN l10n_latam_document_type AS latam_doctype ON account_move_fr.l10n_latam_document_type_id = latam_doctype.id
            LEFT JOIN res_currency AS aml_currency ON account_move_line.currency_id = aml_currency.id
                WHERE %(where_clause)s
             GROUP BY bank_statement_line.id,
                      bank_statement_line.amount,
                      bank_statement_line.payment_ref,
                      latam_doctype.code,
                      %(account_code)s,
                      account_move_fr.move_type,
                      bank_statement_move.journal_id,
                      bank_statement_move.date,
                      account_move_fr.name,
                      account_move_fr.invoice_date,
                      account_move_fr.invoice_date_due,
                      account_move_line.move_id,
                      aml_currency.name
             ORDER BY bank_statement_move.journal_id, bank_statement_move.date, bank_statement_line.id
            """,
            account_code=account_code,
            from_clause=query.from_clause,
            where_clause=query.where_clause or SQL("TRUE"))
        for model in (
                'account.move.line',
                'account.move',
                'account.bank.statement.line',
                'account.journal',
                'account.account',
                'res.currency',
                'l10n_latam.document.type',
        ):
            self.env[model].flush_model()
        self.env.cr.execute(sql)
        lines_data = self._cr.dictfetchall()

        data = []
        period = options['date']['date_from'].replace('-', '')
        for _move_id, line_vals in groupby(lines_data, lambda line: line['move_id']):
            # Only consider the first line.
            # If are paid more of 1 invoice with the same BSL, only get the values from the first invoice
            line = line_vals[0]
            serie_folio = self.env['l10n_pe.tax.ple.report.handler']._get_serie_folio(line['move_name'] or '')
            serie = serie_folio['serie'].replace(' ', '').replace('/', '')
            if (
                    line['document_type'] and line['document_type'] not in {'01', '03', '07', '08'}
                    or (
                        len(serie) > 4
                        and line['move_type'] in self.env['account.move'].get_purchase_types()
                        and line.get('document_type') in {'01', '03', '07', '08'}
                    )
            ):
                serie = serie[1:]
            data.append(
                {
                    'period': f'{period[:6]}00',
                    'cuo': line['move_id'],
                    'number': 'M1',  # The first digit should be 'M' to denote entries for movements or adjustments within the month. Therefore, 'M1' indicates this is the first such entry.
                    'account_code': line['account_code'],
                    'code': '',
                    'analytic': '',
                    'currency': line['currency_name'],
                    'document_type': line['document_type'] or '00',
                    'serie': serie,
                    'folio': serie_folio['folio'].replace(' ', '') or '000',
                    'date': line['date'].strftime('%d/%m/%Y') if line['date'] else '',
                    'due_date': line['invoice_date_due'].strftime('%d/%m/%Y') if line['invoice_date_due'] else '',
                    'invoice_date': (line['invoice_date'] or line['date']).strftime('%d/%m/%Y') if (line['invoice_date'] or line['date']) else '',
                    'glosa': (line['payment_ref'] or '').replace(' ', '').replace('/', ''),
                    'glosa_ref': (line['payment_ref'] or '').replace(' ', '').replace('/', ''),
                    'debit': float_repr(abs(line['amount']) if line['amount'] and line['amount'] > 0 else 0, precision_digits=2),
                    'credit': float_repr(abs(line['amount']) if line['amount'] and line['amount'] < 0 else 0, precision_digits=2),
                    'book': '',
                    'state': '1',
                }
            )
        return data

    def _l10n_pe_get_txt_12_data(self, options):
        """ Generates the TXT content for the PLE reports with the entries data """

        # Retrieve the data from the ledger itself, unfolding every group
        report = self.env['account.report'].browse(options['report_id'])
        # Options ---------------------------------
        # We don't need all companies
        options.pop('multi_company', None)
        options['single_company'] = self.env.company.ids

        # Filter bank journals
        options['journals'] = [journal for journal in options.get('journals', []) if journal.get('type') == 'bank']

        # Prepare query to get lines
        domain = osv.expression.AND([
            report._get_options_domain(options, 'strict_range'),
            [('statement_line_id', '!=', False), ('matching_number', '=', False)],
        ])
        self.env['account.move.line'].check_access('read')
        query = self.env['account.move.line']._where_calc(domain)

        # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
        self.env['account.move.line']._apply_ir_rules(query)

        sql = SQL("""
               SELECT bank_statement_line.id,
                      bank_statement_line.amount,
                      bank_statement_line.payment_ref,
                      bank_statement_move.date,
                      account_move.name AS move_name,
                      account_move_line.move_id,
                      bank.l10n_pe_edi_code,
                      banc_account.acc_number,
                      partner.vat,
                      partner.name AS partner_name,
                      partner_latam_idtype.l10n_pe_vat_code
                 FROM %s
                 JOIN account_move AS account_move ON account_move_line.move_id = account_move.id
            LEFT JOIN account_move_line AS account_move_line_bs ON account_move.id = account_move_line_bs.move_id
            LEFT JOIN account_move_line AS account_move_line_fr ON account_move_line_bs.matching_number = account_move_line_fr.matching_number
            LEFT JOIN account_move AS account_move_fr ON account_move_line_fr.move_id = account_move_fr.id
                 JOIN account_bank_statement_line AS bank_statement_line ON account_move_line.statement_line_id = bank_statement_line.id
                 JOIN account_move AS bank_statement_move ON bank_statement_line.move_id = bank_statement_move.id
                 JOIN account_journal AS journal ON account_move_line.journal_id = journal.id
            LEFT JOIN res_partner_bank AS banc_account ON journal.bank_account_id = banc_account.id
            LEFT JOIN res_bank AS bank ON banc_account.bank_id = bank.id
            LEFT JOIN res_partner AS partner ON account_move.partner_id = partner.id
            LEFT JOIN l10n_latam_identification_type AS partner_latam_idtype ON partner.l10n_latam_identification_type_id = partner_latam_idtype.id
            LEFT JOIN l10n_latam_document_type AS latam_doctype ON account_move.l10n_latam_document_type_id = latam_doctype.id
            LEFT JOIN res_currency AS aml_currency ON account_move_line.currency_id = aml_currency.id
                WHERE %s
             GROUP BY bank_statement_line.id,
                      bank_statement_line.amount,
                      bank_statement_line.payment_ref,
                      bank_statement_move.journal_id,
                      bank_statement_move.date,
                      account_move.name,
                      account_move_line.move_id,
                      bank.l10n_pe_edi_code,
                      banc_account.acc_number,
                      partner.vat,
                      partner.name,
                      partner_latam_idtype.l10n_pe_vat_code
             ORDER BY bank_statement_move.journal_id, bank_statement_move.date, bank_statement_line.id
        """, query.from_clause, query.where_clause or SQL("TRUE"))
        for model in (
                'account.move.line',
                'account.move',
                'account.bank.statement.line',
                'account.account',
                'res.currency',
                'l10n_latam.document.type',
        ):
            self.env[model].flush_model()
        self.env.cr.execute(sql)
        lines_data = self._cr.dictfetchall()

        data = []
        period = options['date']['date_from'].replace('-', '')
        for _move_id, line_vals in groupby(lines_data, lambda l: l['move_id']):
            # Only consider the first line.
            # If are paid more of 1 invoice with the same BSL, only get the values from the first invoice
            line = line_vals[0]
            data.append(
                {
                    'period': f'{period[:6]}00',
                    'cuo': line['move_id'],
                    'number': 'M1',  # The first digit should be 'M' to denote entries for movements or adjustments within the month. Therefore, 'M1' indicates this is the first such entry.
                    'bank_code': line['l10n_pe_edi_code'] or '99',
                    'bank_account_number': line['acc_number'],
                    'date': line['date'].strftime('%d/%m/%Y') if line['date'] else '',
                    'payment_method': '003',
                    'desc': (line['payment_ref'] or '').replace(' ', '').replace('/', ''),
                    'identification_type': line['l10n_pe_vat_code'] or '-',
                    'partner_vat': line['vat'] or '-',
                    'partner_name': line['partner_name'] or '-',
                    'transaction': (line['move_name'] or '').replace(' ', '').replace('/', ''),
                    'debit': float_repr(abs(line['amount']) if line['amount'] and line['amount'] > 0 else 0, precision_digits=2),
                    'credit': float_repr(abs(line['amount']) if line['amount'] and line['amount'] < 0 else 0, precision_digits=2),
                    'state': '1',
                }
            )
        return data
