# -*- coding: utf-8 -*-
# Copyright (C) 2013-2015 Akretion (http://www.akretion.com)

import io
from odoo.tools import float_is_zero, pycompat, SQL
from odoo import fields, models, api
from odoo.tools.misc import get_lang
from stdnum.fr import siren


class FecExportWizard(models.TransientModel):
    _name = 'l10n_fr.fec.export.wizard'
    _description = 'Fichier Echange Informatise'

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: self._context.get('report_dates', {}).get('date_from'))
    date_to = fields.Date(string='End Date', required=True, default=lambda self: self._context.get('report_dates', {}).get('date_to'))
    filename = fields.Char(string='Filename', size=256, readonly=True)
    test_file = fields.Boolean()
    export_type = fields.Selection([
        ('official', 'Official FEC report (posted entries only)'),
        ('nonofficial', 'Non-official FEC report (posted and unposted entries)'),
    ], string='Export Type', required=True, default='official')
    excluded_journal_ids = fields.Many2many('account.journal', string="Excluded Journals",
                                            domain="[('company_id', 'parent_of', current_company_id)]")

    @api.onchange('test_file')
    def _onchange_export_file(self):
        if not self.test_file:
            self.export_type = 'official'

    def _get_where_query(self) -> SQL:
        search_conditions = [SQL("am.company_id = %s\n", self.env.company.id)]
        # For official report: only use posted entries
        if self.export_type == "official":
            search_conditions.append(SQL("am.state = 'posted'\n"))
        if self.excluded_journal_ids:
            search_conditions.append(SQL("am.journal_id NOT IN %s\n", tuple(self.excluded_journal_ids.ids)))
        return SQL("AND ").join(search_conditions)

    def _do_query_unaffected_earnings(self):
        """ Compute the sum of ending balances for all accounts that are of a type that does not bring forward the balance in new fiscal years.
            This is needed because we have to display only one line for the initial balance of all expense/revenue accounts in the FEC.
        """
        sql_query = SQL(
            '''
            SELECT
                'OUV' AS JournalCode,
                'Balance initiale' AS JournalLib,
                'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                %(formatted_date_from)s AS EcritureDate,
                '120/129' AS CompteNum,
                'Benefice (perte) reporte(e)' AS CompteLib,
                '' AS CompAuxNum,
                '' AS CompAuxLib,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(CASE WHEN COALESCE(sum(aml.balance), 0) <= 0 THEN '0,00' ELSE to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN COALESCE(sum(aml.balance), 0) >= 0 THEN '0,00' ELSE to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise
            FROM
                account_move_line aml
                LEFT JOIN account_move am ON am.id=aml.move_id
                JOIN account_account aa ON aa.id = aml.account_id
            WHERE
                %(where_query)s
                AND am.date < %(date_from)s
                AND aa.include_initial_balance IS NOT TRUE
            ''',
            formatted_date_year=self.date_from.year,
            formatted_date_from=fields.Date.to_string(self.date_from).replace('-', ''),
            where_query=self._get_where_query(),
            date_from=self.date_from,
        )
        self.env.flush_all()
        self._cr.execute(sql_query)
        return list(self._cr.fetchone())

    def _get_company_legal_data(self, company):
        """
        Dom-Tom are excluded from the EU's fiscal territory
        Those regions do not have SIREN
        sources:
            https://www.service-public.fr/professionnels-entreprises/vosdroits/F23570
            http://www.douane.gouv.fr/articles/a11024-tva-dans-les-dom

        * Returns the siren if the company is french or an empty siren for dom-tom
        * For non-french companies -> returns the complete vat number
        """
        dom_tom_group = self.env.ref('l10n_fr.dom-tom')
        is_dom_tom = company.account_fiscal_country_id.code in dom_tom_group.country_ids.mapped('code')
        if not company.vat or is_dom_tom:
            return ''
        elif company.country_id.code == 'FR' and len(company.vat) >= 13 and siren.is_valid(company.vat[4:13]):
            return company.vat[4:13]
        else:
            return company.vat

    def generate_fec(self):
        # We choose to implement the flat file instead of the XML file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move, but Odoo has the label on the account.move.line,
        # so that's a  problem !
        # 2) CSV files are easier to read/use for a regular accountant. So it will be easier for the accountant to check
        # the file before sending it to the fiscal administration
        company = self.env.company
        company_legal_data = self._get_company_legal_data(company)

        header = [
            u'JournalCode',    # 0
            u'JournalLib',     # 1
            u'EcritureNum',    # 2
            u'EcritureDate',   # 3
            u'CompteNum',      # 4
            u'CompteLib',      # 5
            u'CompAuxNum',     # 6  We use partner.id
            u'CompAuxLib',     # 7
            u'PieceRef',       # 8
            u'PieceDate',      # 9
            u'EcritureLib',    # 10
            u'Debit',          # 11
            u'Credit',         # 12
            u'EcritureLet',    # 13
            u'DateLet',        # 14
            u'ValidDate',      # 15
            u'Montantdevise',  # 16
            u'Idevise',        # 17
            ]

        rows_to_write = [header]
        # INITIAL BALANCE
        unaffected_earnings_account = self.env['account.account'].search([
            *self.env['account.account']._check_company_domain(company),
            ('account_type', '=', 'equity_unaffected'),
        ], limit=1)
        unaffected_earnings_line = True  # used to make sure that we add the unaffected earning initial balance only once
        if unaffected_earnings_account:
            #compute the benefit/loss of last year to add in the initial balance of the current year earnings account
            unaffected_earnings_results = self._do_query_unaffected_earnings()
            unaffected_earnings_line = False

        lang = self.env.user.lang or get_lang(self.env).code
        aa_name = self.with_context(lang=lang).env['account.account']._field_to_sql('aa', 'name')
        where_query = self._get_where_query()

        sql_query = SQL(
            '''
            SELECT
                'OUV' AS JournalCode,
                'Balance initiale' AS JournalLib,
                'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                %(formatted_date_from)s AS EcritureDate,
                MIN(aa.code) AS CompteNum,
                replace(replace(MIN(%(aa_name)s), '|', '/'), '\t', '') AS CompteLib,
                '' AS CompAuxNum,
                '' AS CompAuxLib,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' ELSE to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise,
                MIN(aa.id) AS CompteID
            FROM
                account_move_line aml
                LEFT JOIN account_move am ON am.id=aml.move_id
                JOIN account_account aa ON aa.id = aml.account_id
            WHERE
                %(where_query)s
                AND am.date < %(date_from)s
                AND aa.include_initial_balance = 't'
            GROUP BY aml.account_id, aa.account_type
            HAVING aa.account_type not in ('asset_receivable', 'liability_payable')
            ''',
            formatted_date_year=self.date_from.year,
            formatted_date_from=fields.Date.to_string(self.date_from).replace('-', ''),
            aa_name=aa_name,
            where_query=where_query,
            date_from=self.date_from,
        )
        self._cr.execute(sql_query)

        currency_digits = 2
        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            if not unaffected_earnings_line:
                account = self.env['account.account'].browse(account_id)
                if account.account_type == 'equity_unaffected':
                    #add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
                    unaffected_earnings_line = True
                    current_amount = float(listrow[11].replace(',', '.')) - float(listrow[12].replace(',', '.'))
                    unaffected_earnings_amount = float(unaffected_earnings_results[11].replace(',', '.')) - float(unaffected_earnings_results[12].replace(',', '.'))
                    listrow_amount = current_amount + unaffected_earnings_amount
                    if float_is_zero(listrow_amount, precision_digits=currency_digits):
                        continue
                    if listrow_amount > 0:
                        listrow[11] = str(listrow_amount).replace('.', ',')
                        listrow[12] = '0,00'
                    else:
                        listrow[11] = '0,00'
                        listrow[12] = str(-listrow_amount).replace('.', ',')
            rows_to_write.append(listrow)

        #if the unaffected earnings account wasn't in the selection yet: add it manually
        if (not unaffected_earnings_line
            and unaffected_earnings_results
            and (unaffected_earnings_results[11] != '0,00'
                 or unaffected_earnings_results[12] != '0,00')):
            #search an unaffected earnings account
            unaffected_earnings_account = self.env['account.account'].search([
                ('account_type', '=', 'equity_unaffected')
            ], limit=1)
            if unaffected_earnings_account:
                unaffected_earnings_results[4] = unaffected_earnings_account.code
                unaffected_earnings_results[5] = unaffected_earnings_account.name
            rows_to_write.append(unaffected_earnings_results)

        # INITIAL BALANCE - receivable/payable
        sql_query = SQL(
            '''
            SELECT
                'OUV' AS JournalCode,
                'Balance initiale' AS JournalLib,
                'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                %(formatted_date_from)s AS EcritureDate,
                MIN(aa.code) AS CompteNum,
                replace(MIN(%(aa_name)s), '|', '/') AS CompteLib,
                CASE WHEN MIN(aa.account_type) IN ('asset_receivable', 'liability_payable')
                THEN
                    CASE WHEN rp.ref IS null OR rp.ref = ''
                    THEN rp.id::text
                    ELSE replace(rp.ref, '|', '/')
                    END
                ELSE ''
                END
                AS CompAuxNum,
                CASE WHEN aa.account_type IN ('asset_receivable', 'liability_payable')
                THEN COALESCE(replace(rp.name, '|', '/'), '')
                ELSE ''
                END AS CompAuxLib,
                '-' AS PieceRef,
                %(formatted_date_from)s AS PieceDate,
                '/' AS EcritureLib,
                replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' ELSE to_char(SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(aml.balance), '000000000000000D99') END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise,
                MIN(aa.id) AS CompteID
            FROM
                account_move_line aml
                LEFT JOIN account_move am ON am.id=aml.move_id
                LEFT JOIN res_partner rp ON rp.id=aml.partner_id
                JOIN account_account aa ON aa.id = aml.account_id
            WHERE
                %(where_query)s
                AND am.date < %(date_from)s
                AND aa.include_initial_balance = 't'
            GROUP BY aml.account_id, aa.account_type, rp.ref, rp.id
            HAVING aa.account_type in ('asset_receivable', 'liability_payable')
            ''',
            formatted_date_year=self.date_from.year,
            formatted_date_from=fields.Date.to_string(self.date_from).replace('-', ''),
            aa_name=aa_name,
            where_query=where_query,
            date_from=self.date_from,
        )
        self._cr.execute(sql_query)

        for row in self._cr.fetchall():
            listrow = list(row)
            account_id = listrow.pop()
            rows_to_write.append(listrow)

        # LINES
        lang = self.env.user.lang or get_lang(self.env).code
        aj_name = self.with_context(lang=lang).env['account.journal']._field_to_sql('aj', 'name')

        query_limit = int(self.env['ir.config_parameter'].sudo().get_param('l10n_fr_fec.batch_size', 500000)) # To prevent memory errors when fetching the results

        sql_query = SQL(
            '''
            SELECT
                REGEXP_REPLACE(replace(aj.code, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalCode,
                REGEXP_REPLACE(replace(%(aj_name)s, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalLib,
                REGEXP_REPLACE(replace(am.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS EcritureNum,
                TO_CHAR(am.date, 'YYYYMMDD') AS EcritureDate,
                aa.code AS CompteNum,
                REGEXP_REPLACE(replace(%(aa_name)s, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS CompteLib,
                CASE WHEN aa.account_type IN ('asset_receivable', 'liability_payable')
                THEN
                    CASE WHEN rp.ref IS null OR rp.ref = ''
                    THEN rp.id::text
                    ELSE replace(rp.ref, '|', '/')
                    END
                ELSE ''
                END
                AS CompAuxNum,
                CASE WHEN aa.account_type IN ('asset_receivable', 'liability_payable')
                THEN COALESCE(REGEXP_REPLACE(replace(rp.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g'), '')
                ELSE ''
                END AS CompAuxLib,
                CASE WHEN am.ref IS null OR am.ref = ''
                THEN '-'
                ELSE REGEXP_REPLACE(replace(am.ref, '|', '/'), '[\\t\\r\\n]', ' ', 'g')
                END
                AS PieceRef,
                TO_CHAR(COALESCE(am.invoice_date, am.date), 'YYYYMMDD') AS PieceDate,
                CASE WHEN aml.name IS NULL OR aml.name = '' THEN '/'
                    WHEN aml.name SIMILAR TO '[\\t|\\s|\\n]*' THEN '/'
                    ELSE REGEXP_REPLACE(replace(aml.name, '|', '/'), '[\\t\\n\\r]', ' ', 'g') END AS EcritureLib,
                replace(CASE WHEN aml.debit = 0 THEN '0,00' ELSE to_char(aml.debit, '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN aml.credit = 0 THEN '0,00' ELSE to_char(aml.credit, '000000000000000D99') END, '.', ',') AS Credit,
                CASE WHEN rec.id IS NULL THEN ''::text ELSE rec.id::text END AS EcritureLet,
                CASE WHEN aml.full_reconcile_id IS NULL THEN '' ELSE TO_CHAR(rec.create_date, 'YYYYMMDD') END AS DateLet,
                TO_CHAR(am.date, 'YYYYMMDD') AS ValidDate,
                CASE
                    WHEN aml.amount_currency IS NULL OR aml.amount_currency = 0 THEN ''
                    ELSE replace(to_char(aml.amount_currency, '000000000000000D99'), '.', ',')
                END AS Montantdevise,
                CASE WHEN aml.currency_id IS NULL THEN '' ELSE rc.name END AS Idevise
            FROM
                account_move_line aml
                LEFT JOIN account_move am ON am.id=aml.move_id
                LEFT JOIN res_partner rp ON rp.id=aml.partner_id
                JOIN account_journal aj ON aj.id = am.journal_id
                JOIN account_account aa ON aa.id = aml.account_id
                LEFT JOIN res_currency rc ON rc.id = aml.currency_id
                LEFT JOIN account_full_reconcile rec ON rec.id = aml.full_reconcile_id
            WHERE
                %(where_query)s
                AND am.date >= %(date_from)s
                AND am.date <= %(date_to)s
            ORDER BY
                am.date,
                am.name,
                aml.id
            LIMIT %(limit)s
            ''',
            aj_name=aj_name,
            aa_name=aa_name,
            where_query=where_query,
            date_from=self.date_from,
            date_to=self.date_to,
            limit=query_limit + 1,
        )

        with io.BytesIO() as fecfile:
            csv_writer = pycompat.csv_writer(fecfile, delimiter='|', lineterminator='')

            # Write header and initial balances
            for initial_row in rows_to_write:
                initial_row = list(initial_row)
                # We don't skip \n at then end of the file if there are only initial balances, for simplicity. An empty period export shouldn't happen IRL.
                initial_row[-1] += u'\r\n'
                csv_writer.writerow(initial_row)

            # Write current period's data
            query_offset = 0
            has_more_results = True
            while has_more_results:
                self._cr.execute(SQL('%s OFFSET %s', sql_query, query_offset))
                query_offset += query_limit
                has_more_results = self._cr.rowcount > query_limit # we load one more result than the limit to check if there is more
                query_results = self._cr.fetchall()
                for i, row in enumerate(query_results[:query_limit]):
                    if i < len(query_results) - 1:
                        # The file is not allowed to end with an empty line, so we can't use lineterminator on the writer
                        row = list(row)
                        row[-1] += u'\r\n'
                    csv_writer.writerow(row)
            content = fecfile.getvalue()


        end_date = fields.Date.to_string(self.date_to).replace('-', '')
        suffix = ''
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'

        # Set fiscal year lock date to the end date (not in test)
        fiscalyear_lock_date = self.env.company.fiscalyear_lock_date
        if not self.test_file and (not fiscalyear_lock_date or fiscalyear_lock_date < self.date_to):
            self.env.company.write({'fiscalyear_lock_date': self.date_to})

        return {
            'file_name': f"{company_legal_data}FEC{end_date}{suffix}.csv",
            'file_content': content,
            'file_type': 'csv'
        }

    def create_fec_report_action(self):
        # HOOK
        return

