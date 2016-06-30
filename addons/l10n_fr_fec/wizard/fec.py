# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2013-2015 Akretion (http://www.akretion.com)

from openerp import models, fields, api, _
from openerp.exceptions import Warning
import base64
import StringIO
import csv


class AccountFrFec(models.TransientModel):
    _name = 'account.fr.fec'
    _description = 'Ficher Echange Informatise'

    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    fec_data = fields.Binary('FEC File', readonly=True)
    filename = fields.Char(string='Filename', size=256, readonly=True)
    export_type = fields.Selection([
        ('official', 'Official FEC report (posted entries only)'),
        ('nonofficial', 'Non-official FEC report (posted and unposted entries)'),
        ], string='Export Type', required=True, default='official')

    @api.multi
    def generate_fec(self):
        self.ensure_one()
        # We choose to implement the flat file instead of the XML
        # file for 2 reasons :
        # 1) the XSD file impose to have the label on the account.move
        # but Odoo has the label on the account.move.line, so that's a
        # problem !
        # 2) CSV files are easier to read/use for a regular accountant.
        # So it will be easier for the accountant to check the file before
        # sending it to the fiscal administration
        header = [
            'JournalCode',    # 0
            'JournalLib',     # 1
            'EcritureNum',    # 2
            'EcritureDate',   # 3
            'CompteNum',      # 4
            'CompteLib',      # 5
            'CompAuxNum',     # 6  We use partner.id
            'CompAuxLib',     # 7
            'PieceRef',       # 8
            'PieceDate',      # 9
            'EcritureLib',    # 10
            'Debit',          # 11
            'Credit',         # 12
            'EcritureLet',    # 13
            'DateLet',        # 14
            'ValidDate',      # 15
            'Montantdevise',  # 16
            'Idevise',        # 17
            ]

        company = self.env.user.company_id
        if not company.vat:
            raise Warning(
                _("Missing VAT number for company %s") % company.name)
        if company.vat[0:2] != 'FR':
            raise Warning(
                _("FEC is for French companies only !"))

        fecfile = StringIO.StringIO()
        w = csv.writer(fecfile, delimiter='|')
        w.writerow(header)

        # INITIAL BALANCE
        sql_query = '''
        SELECT
            'OUV' AS JournalCode,
            'Balance initiale' AS JournalLib,
            'Balance initiale ' || MIN(aa.name) AS EcritureNum,
            %s AS EcritureDate,
            MIN(aa.code) AS CompteNum,
            replace(MIN(aa.name), '|', '/') AS CompteLib,
            '' AS CompAuxNum,
            '' AS CompAuxLib,
            '-' AS PieceRef,
            %s AS PieceDate,
            '/' AS EcritureLib,
            replace(CASE WHEN sum(aml.balance) <= 0 THEN '0,00' ELSE to_char(SUM(aml.balance), '999999999999999D99') END, '.', ',') AS Debit,
            replace(CASE WHEN sum(aml.balance) >= 0 THEN '0,00' ELSE to_char(-SUM(aml.balance), '999999999999999D99') END, '.', ',') AS Credit,
            '' AS EcritureLet,
            '' AS DateLet,
            %s AS ValidDate,
            '' AS Montantdevise,
            '' AS Idevise
        FROM
            account_move_line aml
            LEFT JOIN account_move am ON am.id=aml.move_id
            JOIN account_account aa ON aa.id = aml.account_id
        WHERE
            am.date < %s
            AND am.company_id = %s
            AND (aml.debit != 0 OR aml.credit != 0)
        '''

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += '''
            AND am.state = 'posted'
            '''

        sql_query += '''
        GROUP BY aml.account_id
        '''
        formatted_date_from = self.date_from.replace('-', '')
        self._cr.execute(
            sql_query, (formatted_date_from, formatted_date_from, formatted_date_from, self.date_from, company.id))

        for row in self._cr.fetchall():
            listrow = list(row)
            w.writerow([s.encode("utf-8") for s in listrow])

        # LINES
        sql_query = '''
        SELECT
            replace(aj.code, '|', '/') AS JournalCode,
            replace(aj.name, '|', '/') AS JournalLib,
            replace(am.name, '|', '/') AS EcritureNum,
            TO_CHAR(am.date, 'YYYYMMDD') AS EcritureDate,
            aa.code AS CompteNum,
            replace(aa.name, '|', '/') AS CompteLib,
            CASE WHEN rp.ref IS null OR rp.ref = ''
            THEN COALESCE('ID ' || rp.id, '')
            ELSE rp.ref
            END
            AS CompAuxNum,
            COALESCE(replace(rp.name, '|', '/'), '') AS CompAuxLib,
            CASE WHEN am.ref IS null OR am.ref = ''
            THEN '-'
            ELSE replace(am.ref, '|', '/')
            END
            AS PieceRef,
            TO_CHAR(am.date, 'YYYYMMDD') AS PieceDate,
            CASE WHEN aml.name IS NULL THEN '/' ELSE replace(aml.name, '|', '/') END AS EcritureLib,
            replace(CASE WHEN aml.debit = 0 THEN '0,00' ELSE to_char(aml.debit, '999999999999999D99') END, '.', ',') AS Debit,
            replace(CASE WHEN aml.credit = 0 THEN '0,00' ELSE to_char(aml.credit, '999999999999999D99') END, '.', ',') AS Credit,
            CASE WHEN rec.name IS NULL THEN '' ELSE rec.name END AS EcritureLet,
            CASE WHEN aml.full_reconcile_id IS NULL THEN '' ELSE TO_CHAR(rec.create_date, 'YYYYMMDD') END AS DateLet,
            TO_CHAR(am.date, 'YYYYMMDD') AS ValidDate,
            CASE
                WHEN aml.amount_currency IS NULL OR aml.amount_currency = 0 THEN ''
                ELSE replace(to_char(aml.amount_currency, '999999999999999D99'), '.', ',')
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
            am.date >= %s
            AND am.date <= %s
            AND am.company_id = %s
            AND (aml.debit != 0 OR aml.credit != 0)
        '''

        # For official report: only use posted entries
        if self.export_type == "official":
            sql_query += '''
            AND am.state = 'posted'
            '''

        sql_query += '''
        ORDER BY
            am.date,
            am.name,
            aml.id
        '''
        self._cr.execute(
            sql_query, (self.date_from, self.date_to, company.id))

        for row in self._cr.fetchall():
            listrow = list(row)
            w.writerow([s.encode("utf-8") for s in listrow])

        siren = company.vat[4:13]
        end_date = self.date_to.replace('-', '')
        suffix = ''
        if self.export_type == "nonofficial":
            suffix = '-NONOFFICIAL'
        fecvalue = fecfile.getvalue()
        self.write({
            'fec_data': base64.encodestring(fecvalue),
            # Filename = <siren>FECYYYYMMDD where YYYMMDD is the closing date
            'filename': '%sFEC%s%s.csv' % (siren, end_date, suffix),
            })
        fecfile.close()

        action = {
            'name': 'FEC',
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=account.fr.fec&id=" + str(self.id) + "&filename_field=filename&field=fec_data&download=true&filename=" + self.filename,
            'target': 'self',
            }
        return action
