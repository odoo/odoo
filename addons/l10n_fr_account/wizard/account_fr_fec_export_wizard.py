# -*- coding: utf-8 -*-
# Copyright (C) 2013-2015 Akretion (http://www.akretion.com)
import csv
import io
from itertools import chain
from odoo.tools import float_is_zero, SQL
from odoo import fields, models, api
from odoo.modules.registry import Registry

from odoo.tools.misc import get_lang
from stdnum.fr import siren


class L10n_FrFecExportWizard(models.TransientModel):
    _name = 'l10n_fr.fec.export.wizard'
    _description = 'Fichier Echange Informatise'

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: self.env.context.get('report_dates', {}).get('date_from'))
    date_to = fields.Date(string='End Date', required=True, default=lambda self: self.env.context.get('report_dates', {}).get('date_to'))
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

    def _get_base_domain(self):
        domain = [('company_id', 'in', tuple(self.env.company._accessible_branches().ids)), ('balance', '!=', 0.0)]
        # For official report: only use posted entries
        if self.export_type == "official":
            domain.append(('parent_state', '=', 'posted'))
        if self.excluded_journal_ids:
            domain.append(('journal_id', 'not in', self.excluded_journal_ids.ids))
        return domain

    def _do_query_unaffected_earnings(self):
        """ Compute the sum of ending balances for all accounts that are of a type that does not bring forward the balance in new fiscal years.
            This is needed because we have to display only one line for the initial balance of all expense/revenue accounts in the FEC.
        """
        query = self.env['account.move.line']._search(self._get_base_domain() + [
            ('date', '<', self.date_from),
            ('account_id.include_initial_balance', '=', False),
        ])
        sql_query = query.select(SQL(
            """
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
                replace(CASE WHEN COALESCE(sum(account_move_line.balance), 0) <= 0 THEN '0,00' ELSE to_char(SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Debit,
                replace(CASE WHEN COALESCE(sum(account_move_line.balance), 0) >= 0 THEN '0,00' ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Credit,
                '' AS EcritureLet,
                '' AS DateLet,
                %(formatted_date_from)s AS ValidDate,
                '' AS Montantdevise,
                '' AS Idevise
            """,
            formatted_date_year=self.date_from.year,
            formatted_date_from=fields.Date.to_string(self.date_from).replace('-', ''),
        ))
        self.env.flush_all()
        self.env.cr.execute(sql_query)
        return list(self.env.cr.fetchone())

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
        is_dom_tom = company.account_fiscal_country_id and 'DOM-TOM' in company.account_fiscal_country_id.country_group_codes
        if not company.vat or is_dom_tom:
            return ''
        elif company.country_id.code == 'FR' and len(company.vat) >= 13 and siren.is_valid(company.vat[4:13]):
            return company.vat[4:13]
        else:
            return company.vat

    def _get_fec_stream(self):
        company = self.env.company

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

        def format_row(row):
            with io.StringIO() as buf:
                writer = csv.writer(buf, delimiter='|', lineterminator='\r\n')
                writer.writerow(row)
                return buf.getvalue().encode()

        def stream_header():
            yield format_row(header)

        def stream_initial_balance():
            with Registry(self.env.cr.dbname).cursor() as cr:
                fec = self.with_env(self.env(cr=cr))
                env = fec.env
                # INITIAL BALANCE
                unaffected_earnings_account = env['account.account'].search([
                    *env['account.account']._check_company_domain(company),
                    ('account_type', '=', 'equity_unaffected'),
                ], limit=1)
                unaffected_earnings_line = True  # used to make sure that we add the unaffected earning initial balance only once
                unaffected_earnings_results = None
                if unaffected_earnings_account:
                    # compute the benefit/loss of last year to add in the initial balance of the current year earnings account
                    unaffected_earnings_results = fec._do_query_unaffected_earnings()
                    unaffected_earnings_line = False

                query = env['account.move.line']._search(fec._get_base_domain() + [
                    ('date', '<', fec.date_from),
                    ('account_id.include_initial_balance', '=', True),
                    ('account_id.account_type', 'not in', ['asset_receivable', 'liability_payable']),
                ])
                account = query.table.account_id
                query.groupby = account.id
                sql_query = query.select(SQL(
                    """
                        'OUV' AS JournalCode,
                        'Balance initiale' AS JournalLib,
                        'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                        %(formatted_date_from)s AS EcritureDate,
                        MIN(%(aa_code)s) AS CompteNum,
                        replace(replace(MIN(%(aa_name)s), '|', '/'), '\t', '') AS CompteLib,
                        '' AS CompAuxNum,
                        '' AS CompAuxLib,
                        '-' AS PieceRef,
                        %(formatted_date_from)s AS PieceDate,
                        '/' AS EcritureLib,
                        replace(CASE WHEN sum(account_move_line.balance) <= 0 THEN '0,00' ELSE to_char(SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Debit,
                        replace(CASE WHEN sum(account_move_line.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Credit,
                        '' AS EcritureLet,
                        '' AS DateLet,
                        %(formatted_date_from)s AS ValidDate,
                        '' AS Montantdevise,
                        '' AS Idevise,
                        MIN(%(account_id)s) AS CompteID
                    """,
                    formatted_date_year=fec.date_from.year,
                    formatted_date_from=fields.Date.to_string(fec.date_from).replace('-', ''),
                    aa_code=account.code,
                    aa_name=account.name,
                    account_id=account.id,
                ))
                env.cr.execute(sql_query)

                currency_digits = 2
                for row in env.cr.fetchall():
                    listrow = list(row)
                    account_id = listrow.pop()
                    if not unaffected_earnings_line:
                        account = env['account.account'].browse(account_id)
                        if account.account_type == 'equity_unaffected':
                            # add the benefit/loss of previous fiscal year to the first unaffected earnings account found.
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
                    yield format_row(listrow)

                # if the unaffected earnings account wasn't in the selection yet: add it manually
                if (not unaffected_earnings_line
                    and unaffected_earnings_results
                    and (unaffected_earnings_results[11] != '0,00'
                        or unaffected_earnings_results[12] != '0,00')):
                    # search an unaffected earnings account
                    unaffected_earnings_account = env['account.account'].search([
                        ('account_type', '=', 'equity_unaffected')
                    ], limit=1)
                    if unaffected_earnings_account:
                        unaffected_earnings_results[4] = unaffected_earnings_account.code
                        unaffected_earnings_results[5] = unaffected_earnings_account.name
                    yield format_row(unaffected_earnings_results)

                # INITIAL BALANCE - receivable/payable
                query = env['account.move.line']._search(fec._get_base_domain() + [
                    ('date', '<', fec.date_from),
                    ('account_id.include_initial_balance', '=', True),
                    ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
                ])
                account = query.table.account_id
                partner = query.table.partner_id
                query.groupby = SQL("%s, %s", partner.id, account.id)
                sql_query = query.select(SQL(
                    """
                        'OUV' AS JournalCode,
                        'Balance initiale' AS JournalLib,
                        'OUVERTURE/' || %(formatted_date_year)s AS EcritureNum,
                        %(formatted_date_from)s AS EcritureDate,
                        MIN(%(aa_code)s) AS CompteNum,
                        replace(MIN(%(aa_name)s), '|', '/') AS CompteLib,
                        COALESCE(NULLIF(replace(%(partner_alias)s.ref, '|', '/'), ''), %(partner_alias)s.id::text) AS CompAuxNum,
                        COALESCE(replace(%(partner_alias)s.name, '|', '/'), '') AS CompAuxLib,
                        '-' AS PieceRef,
                        %(formatted_date_from)s AS PieceDate,
                        '/' AS EcritureLib,
                        replace(CASE WHEN sum(account_move_line.balance) <= 0 THEN '0,00' ELSE to_char(SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Debit,
                        replace(CASE WHEN sum(account_move_line.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(account_move_line.balance), '000000000000000D99') END, '.', ',') AS Credit,
                        '' AS EcritureLet,
                        '' AS DateLet,
                        %(formatted_date_from)s AS ValidDate,
                        '' AS Montantdevise,
                        '' AS Idevise,
                        MIN(%(account_id)s) AS CompteID
                    """,
                    formatted_date_year=fec.date_from.year,
                    formatted_date_from=fields.Date.to_string(fec.date_from).replace('-', ''),
                    aa_code=account.code,
                    aa_name=account.name,
                    account_id=account.id,
                    partner_alias=partner.id._table,
                ))
                env.cr.execute(sql_query)

                for row in env.cr.fetchall():
                    listrow = list(row)
                    listrow.pop()
                    yield format_row(listrow)

        def stream_lines():
            with Registry(self.env.cr.dbname).cursor() as cr:
                fec = self.with_env(self.env(cr=cr))
                env = fec.env
                query_limit = env['ir.config_parameter'].sudo().get_int('l10n_fr_fec.batch_size') or 500000  # To prevent memory errors when fetching the results
                query = env['account.move.line']._search(
                    domain=fec._get_base_domain() + [
                        ('date', '>=', fec.date_from),
                        ('date', '<=', fec.date_to),
                    ],
                    limit=query_limit + 1,
                    order='date, move_name, id',
                )
                account = query.table.account_id
                columns = SQL(
                    """
                        REGEXP_REPLACE(replace(%(journal_alias)s.code, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalCode,
                        REGEXP_REPLACE(replace(%(aj_name)s, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS JournalLib,
                        REGEXP_REPLACE(replace(%(move_alias)s.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS EcritureNum,
                        TO_CHAR(%(move_alias)s.date, 'YYYYMMDD') AS EcritureDate,
                        %(aa_code)s AS CompteNum,
                        REGEXP_REPLACE(replace(%(aa_name)s, '|', '/'), '[\\t\\r\\n]', ' ', 'g') AS CompteLib,
                        CASE WHEN %(aa_type)s IN ('asset_receivable', 'liability_payable')
                        THEN
                            CASE WHEN %(partner_alias)s.ref IS null OR %(partner_alias)s.ref = ''
                            THEN %(partner_alias)s.id::text
                            ELSE replace(%(partner_alias)s.ref, '|', '/')
                            END
                        ELSE ''
                        END
                        AS CompAuxNum,
                        CASE WHEN %(aa_type)s IN ('asset_receivable', 'liability_payable')
                            THEN COALESCE(REGEXP_REPLACE(replace(%(partner_alias)s.name, '|', '/'), '[\\t\\r\\n]', ' ', 'g'), '')
                            ELSE ''
                        END AS CompAuxLib,
                        CASE WHEN %(move_alias)s.ref IS null OR %(move_alias)s.ref = ''
                            THEN '-'
                            ELSE REGEXP_REPLACE(replace(%(move_alias)s.ref, '|', '/'), '[\\t\\r\\n]', ' ', 'g')
                        END AS PieceRef,
                        TO_CHAR(COALESCE(%(move_alias)s.invoice_date, %(move_alias)s.date), 'YYYYMMDD') AS PieceDate,
                        CASE WHEN account_move_line.name IS NULL OR account_move_line.name = '' THEN '/'
                            WHEN account_move_line.name SIMILAR TO '[\\t|\\s|\\n]*' THEN '/'
                            ELSE REGEXP_REPLACE(replace(account_move_line.name, '|', '/'), '[\\t\\n\\r]', ' ', 'g') END AS EcritureLib,
                        replace(CASE WHEN account_move_line.debit = 0 THEN '0,00' ELSE to_char(account_move_line.debit, '000000000000000D99') END, '.', ',') AS Debit,
                        replace(CASE WHEN account_move_line.credit = 0 THEN '0,00' ELSE to_char(account_move_line.credit, '000000000000000D99') END, '.', ',') AS Credit,
                        CASE WHEN %(full_alias)s.id IS NULL THEN ''::text ELSE %(full_alias)s.id::text END AS EcritureLet,
                        CASE WHEN account_move_line.full_reconcile_id IS NULL THEN '' ELSE TO_CHAR(%(full_alias)s.create_date, 'YYYYMMDD') END AS DateLet,
                        TO_CHAR(%(move_alias)s.date, 'YYYYMMDD') AS ValidDate,
                        CASE
                            WHEN account_move_line.amount_currency IS NULL OR account_move_line.amount_currency = 0 THEN ''
                            ELSE replace(to_char(account_move_line.amount_currency, '000000000000000D99'), '.', ',')
                        END AS Montantdevise,
                        CASE WHEN account_move_line.currency_id IS NULL THEN '' ELSE %(currency_alias)s.name END AS Idevise
                    """,
                    currency_alias=query.table.currency_id.id._table,
                    full_alias=query.table.full_reconcile_id.id._table,
                    journal_alias=query.table.journal_id.id._table,
                    move_alias=query.table.move_id.id._table,
                    partner_alias=query.table.partner_id.id._table,
                    aa_type=account.account_type,
                    aj_name=query.table.journal_id.name,
                    aa_code=account.code,
                    aa_name=account.name,
                )

                has_more_results = True
                while has_more_results:
                    env.cr.execute(query.select(columns))
                    query.offset += query_limit
                    has_more_results = env.cr.rowcount > query_limit  # we load one more result than the limit to check if there is more
                    query_results = env.cr.fetchall()
                    for row in query_results[:query_limit]:
                        yield format_row(row)

        return chain(stream_header(), stream_initial_balance(), stream_lines())

    def generate_fec(self):
        # We choose to implement the flat file instead of the XML file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move, but Odoo has the label on the account.move.line,
        # so that's a  problem !
        # 2) CSV files are easier to read/use for a regular accountant. So it will be easier for the accountant to check
        # the file before sending it to the fiscal administration
        company = self.env.company
        company_legal_data = self._get_company_legal_data(company)

        end_date = fields.Date.to_string(self.date_to).replace('-', '')
        suffix = ''
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'

        # Set fiscal year lock date to the end date (not in test)
        fiscalyear_lock_date = self.env.company.fiscalyear_lock_date
        if not self.test_file and (not fiscalyear_lock_date or fiscalyear_lock_date < self.date_to):
            self.env.company.write({'fiscalyear_lock_date': self.date_to})

        return {
            'file_name': f"{company_legal_data}FEC{end_date}{suffix}.txt",
            'file_content': self._get_fec_stream(),
            'file_type': 'txt'
        }

    def create_fec_report_action(self):
        # HOOK
        return
