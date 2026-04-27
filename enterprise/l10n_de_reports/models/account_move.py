import uuid

from odoo import api, fields, models
from odoo.tools.sql import column_exists, create_column


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_de_datev_main_account_id = fields.Many2one('account.account', compute='_get_datev_account', store=True)

    def _auto_init(self):
        if column_exists(self.env.cr, "account_move", "l10n_de_datev_main_account_id"):
            return super()._auto_init()

        cr = self.env.cr
        create_column(cr, "account_move", "l10n_de_datev_main_account_id", "int4")

        dach_companies = self.env['res.company'].search([
            ('account_fiscal_country_id.code', 'in', ('DE', 'AT', 'CH')),
        ])
        if not dach_companies:
            return super()._auto_init()

        # If move has an invoice, return invoice's account_id
        cr.execute(
            """
                UPDATE account_move
                   SET l10n_de_datev_main_account_id = r.aid
                  FROM (
                          SELECT l.move_id mid,
                                 FIRST_VALUE(l.account_id) OVER(PARTITION BY l.move_id ORDER BY l.id DESC) aid
                            FROM account_move_line l
                            JOIN account_move m
                              ON m.id = l.move_id
                            JOIN account_account a
                              ON a.id = l.account_id
                           WHERE m.move_type in ('out_invoice', 'out_refund', 'in_refund', 'in_invoice', 'out_receipt', 'in_receipt')
                             AND a.account_type in ('asset_receivable', 'liability_payable')
                             AND m.company_id IN %(dach_company_ids)s
                       ) r
                WHERE id = r.mid
            """,
            {'dach_company_ids': tuple(dach_companies.ids)},
        )

        # If move belongs to a bank journal, return the journal's account (debit/credit should normally be the same)
        cr.execute(
            """
            UPDATE account_move
               SET l10n_de_datev_main_account_id = r.aid
              FROM (
                    SELECT m.id mid,
                           j.default_account_id aid
                     FROM account_move m
                     JOIN account_journal j
                       ON m.journal_id = j.id
                    WHERE j.type = 'bank'
                      AND j.default_account_id IS NOT NULL
                      AND m.company_id IN %(dach_company_ids)s
                   ) r
             WHERE id = r.mid
               AND l10n_de_datev_main_account_id IS NULL
            """,
            {'dach_company_ids': tuple(dach_companies.ids)},
        )

        # If the move is an automatic exchange rate entry, take the gain/loss account set on the exchange journal
        cr.execute("""
            UPDATE account_move m
               SET l10n_de_datev_main_account_id = r.aid
              FROM (
                    SELECT l.move_id AS mid,
                           l.account_id AS aid
                      FROM account_move_line l
                      JOIN account_move m
                        ON l.move_id = m.id
                      JOIN account_journal j
                        ON m.journal_id = j.id
                      JOIN res_company c
                        ON m.company_id = c.id
                     WHERE j.type='general'
                       AND j.id = c.currency_exchange_journal_id
                       AND l.account_id IN (
                           c.income_currency_exchange_account_id,
                           c.expense_currency_exchange_account_id
                       )
                       AND m.company_id IN %(dach_company_ids)s
                     GROUP BY l.move_id,
                              l.account_id
                    HAVING count(*)=1
                   ) r
             WHERE id = r.mid
               AND l10n_de_datev_main_account_id IS NULL
            """,
            {'dach_company_ids': tuple(dach_companies.ids)},
        )

        # Look for an account used a single time in the move, that has no originator tax
        query = """
            UPDATE account_move m
               SET l10n_de_datev_main_account_id = r.aid
              FROM (
                    SELECT l.move_id AS mid,
                           min(l.account_id) AS aid
                      FROM account_move_line l
                     WHERE {}
                       AND l.company_id IN %(dach_company_ids)s
                     GROUP BY move_id
                    HAVING count(*)=1
                   ) r
             WHERE id = r.mid
               AND m.l10n_de_datev_main_account_id IS NULL
            """
        cr.execute(query.format("l.debit > 0"), {'dach_company_ids': tuple(dach_companies.ids)})
        cr.execute(query.format("l.credit > 0"), {'dach_company_ids': tuple(dach_companies.ids)})
        cr.execute(query.format("l.debit > 0 AND l.tax_line_id IS NULL"), {'dach_company_ids': tuple(dach_companies.ids)})
        cr.execute(query.format("l.credit > 0 AND l.tax_line_id IS NULL"), {'dach_company_ids': tuple(dach_companies.ids)})

        return super()._auto_init()

    @api.depends('journal_id', 'line_ids', 'journal_id.default_account_id')
    def _get_datev_account(self):
        for move in self:
            move.l10n_de_datev_main_account_id = value = False
            if move.country_code not in ('DE', 'AT', 'CH'):
                continue
            # If move has an invoice, return invoice's account_id
            if move.is_invoice(include_receipts=True):
                payment_term_lines = move.line_ids.filtered(
                    lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
                if payment_term_lines:
                    move.l10n_de_datev_main_account_id = payment_term_lines[0].account_id
                continue
            # If move belongs to a bank journal, return the journal's account (debit/credit should normally be the same)
            if move.journal_id.type == 'bank' and move.journal_id.default_account_id:
                move.l10n_de_datev_main_account_id = move.journal_id.default_account_id
                continue
            # If the move is an automatic exchange rate entry, take the gain/loss account set on the exchange journal
            elif move.journal_id.type == 'general' and move.journal_id == self.env.company.currency_exchange_journal_id:
                lines = move.line_ids.filtered(
                    lambda r: r.account_id in (
                        self.env.company.income_currency_exchange_account_id,
                        self.env.company.expense_currency_exchange_account_id
                    )
                )

                if len(lines) == 1:
                    move.l10n_de_datev_main_account_id = lines.account_id
                    continue

            # Look for an account used a single time in the move, that has no originator tax
            aml_debit = move.line_ids.filtered(lambda l: l.debit > 0)
            aml_credit = move.line_ids.filtered(lambda l: l.credit > 0)
            if len(aml_debit.account_id) == 1:
                value = aml_debit.account_id
            elif len(aml_credit.account_id) == 1:
                value = aml_credit.account_id
            else:
                aml_debit_wo_tax_accounts = [a.account_id for a in aml_debit if not a.tax_line_id]
                aml_credit_wo_tax_accounts = [a.account_id for a in aml_credit if not a.tax_line_id]
                if len(aml_debit_wo_tax_accounts) == 1:
                    value = aml_debit_wo_tax_accounts[0]
                elif len(aml_credit_wo_tax_accounts) == 1:
                    value = aml_credit_wo_tax_accounts[0]
                else:
                    # In case the move contains both a revenue and a refund (like the entries generated by POS)
                    # We fallback on the account of receivable/payable line
                    aml_wo_tax_accounts = move.line_ids.filtered(
                        lambda l: not l.tax_ids and not l.tax_line_id and l.account_id.account_type in ['asset_receivable', 'liability_payable']
                    ).mapped("account_id")
                    if len(aml_wo_tax_accounts) == 1:
                        value = aml_wo_tax_accounts[0]
            move.l10n_de_datev_main_account_id = value

    def _l10n_de_datev_get_guid(self):
        """ Get the unique identifier for the move based on the db UUID and the move id """
        self.ensure_one()
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        guid = uuid.uuid5(namespace=uuid.UUID(dbuuid), name=str(self.id))
        return str(guid)
