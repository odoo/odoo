# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class account_fiscalyear_close(models.TransientModel):
    """
    Closes Account Fiscalyear and Generate Opening entries for New Fiscalyear
    """
    _name = "account.fiscalyear.close"
    _description = "Fiscalyear Close"

    fy_id = fields.Many2one('account.fiscalyear', \
                             string='Fiscal Year to close', required=True, help="Select a Fiscal year to close")
    fy2_id = fields.Many2one('account.fiscalyear', \
                             string='New Fiscal Year', required=True)
    journal_id = fields.Many2one('account.journal', string='Opening Entries Journal', domain=[('type', '=', 'situation')], required=True,
        help='The best practice here is to use a journal dedicated to contain the opening entries of all fiscal years. Note that you should define it with default debit/credit accounts, of type \'situation\' and with a centralized counterpart.')
    date_account = fields.Date(string='Opening Entries Account Date', required=True, default=fields.Date.context_today)
    report_name = fields.Char(string='Name of new entries', required=True, help="Give name of the new entries",
        default=lambda self: _('End of Fiscal Year Entry'))

    @api.multi
    def data_save(self):
        """
        This function close account fiscalyear and create entries in new fiscalyear

        """
        def _reconcile_fy_closing(cr, uid, ids, context=None):
            """
            This private function manually do the reconciliation on the account_move_line given as `ids´, and directly
            through psql. It's necessary to do it this way because the usual `reconcile()´ function on account.move.line
            object is really resource greedy (not supposed to work on reconciliation between thousands of records) and
            it does a lot of different computation that are useless in this particular case.
            """
            #check that the reconcilation concern journal entries from only one company
            cr.execute('select distinct(company_id) from account_move_line where id in %s',(tuple(ids),))
            if len(cr.fetchall()) > 1:
                raise Warning(_('The entries to reconcile should belong to the same company.'))
            r_id = self.env['account.move.reconcile'].create(cr, uid, {'type': 'auto', 'opening_reconciliation': True})
            cr.execute('update account_move_line set reconcile_id = %s where id in %s',(r_id.id, tuple(ids),))
            obj_acc_move_line.invalidate_cache(cr, uid, ['reconcile_id'], ids, context=context)
            return r_id

        obj_acc_move = self.env['account.move']
        obj_acc_move_line = self.env['account.move.line']

        cr = self._cr

        date_account = self.date_account
        new_fyear = self.fy2_id
        old_fyear = self.fy_id

        new_journal = self.journal_id
        company_id = new_journal.company_id.id

        if not new_journal.default_credit_account_id or not new_journal.default_debit_account_id:
            raise Warning(_('The journal must have default credit and debit account.'))
        if (not new_journal.centralisation) or new_journal.entry_posted:
            raise Warning(_('The journal must have centralized counterpart without the Skipping draft state option checked.'))

        #delete existing move and move lines if any
        move_ids = obj_acc_move.search([('journal_id', '=', new_journal.id), ('date_account', '=', date_account)])
        if move_ids:
            move_line_ids = obj_acc_move_line.search([('move_id', 'in', move_ids.ids)])
            move_line_ids._remove_move_reconcile(opening_reconciliation=True)
            move_line_ids.unlink()
            move_ids.unlink()

        cr.execute("SELECT id FROM account_fiscalyear WHERE date_stop < %s", (str(new_fyear.date_start),))
        result = cr.dictfetchall()
        fy_ids = ','.join([str(x['id']) for x in result])
        ctx = {'fiscalyear': fy_ids}
        query_line = obj_acc_move_line.with_context(ctx)._query_get(obj='account_move_line')
        #create the opening move
        vals = {
            'name': '/',
            'ref': '',
            'date_account': date_account,
            'date': date_account,
            'journal_id': new_journal.id,
        }
        move_id = obj_acc_move.create(vals)

        #1. report of the accounts with defferal method == 'unreconciled'
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type = t.id)
            WHERE a.deprecated = 'f'
              AND a.type not in ('view', 'consolidation')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'unreconciled', ))
        account_ids = map(lambda x: x[0], cr.fetchall())
        if account_ids:
            cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, date_account, date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT name, create_uid, create_date, write_uid, write_date,
                     statement_id, %s,currency_id, date_maturity, partner_id,
                     blocked, credit, 'draft', debit, ref, account_id,
                     %s, (%s) AS date, %s, amount_currency, quantity, product_id, company_id
                   FROM account_move_line
                   WHERE account_id IN %s
                     AND ''' + query_line + '''
                     AND reconcile_id IS NULL)''', (new_journal.id, date_account, date_account, move_id.id, tuple(account_ids),))

            #We have also to consider all move_lines that were reconciled
            #on another fiscal year, and report them too
            cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, date_account, date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT
                     b.name, b.create_uid, b.create_date, b.write_uid, b.write_date,
                     b.statement_id, %s, b.currency_id, b.date_maturity,
                     b.partner_id, b.blocked, b.credit, 'draft', b.debit,
                     b.ref, b.account_id, (%s) AS date, %s, b.amount_currency,
                     b.quantity, b.product_id, b.company_id
                     FROM account_move_line b
                     WHERE b.account_id IN %s
                       AND b.reconcile_id IS NOT NULL
                       AND b.date_account = ('''+date_account+''')
                       AND b.reconcile_id IN (SELECT DISTINCT(reconcile_id)
                                          FROM account_move_line a
                                          WHERE a.date_account = ('''+date_account+''')))''', (new_journal.id, date_account, move_id.id, tuple(account_ids),))
            self.invalidate_cache()

        #2. report of the accounts with defferal method == 'detail'
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type = t.id)
            WHERE a.deprecated = 'f'
              AND a.type not in ('view', 'consolidation')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'detail', ))
        account_ids = map(lambda x: x[0], cr.fetchall())

        if account_ids:
            cr.execute('''
                INSERT INTO account_move_line (
                     name, create_uid, create_date, write_uid, write_date,
                     statement_id, journal_id, currency_id, date_maturity,
                     partner_id, blocked, credit, state, debit,
                     ref, account_id, date_account, date, move_id, amount_currency,
                     quantity, product_id, company_id)
                  (SELECT name, create_uid, create_date, write_uid, write_date,
                     statement_id, %s,currency_id, date_maturity, partner_id,
                     blocked, credit, 'draft', debit, ref, account_id,
                    (%s) AS date, %s, amount_currency, quantity, product_id, company_id
                   FROM account_move_line
                   WHERE account_id IN %s
                     AND ''' + query_line + ''')
                     ''', (new_journal.id, date_account, move_id.id, tuple(account_ids),))
            self.invalidate_cache()

        #3. report of the accounts with defferal method == 'balance'
        cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type = t.id)
            WHERE a.deprecated = 'f'
              AND a.type not in ('view', 'consolidation')
              AND a.company_id = %s
              AND t.close_method = %s''', (company_id, 'balance', ))
        account_ids = map(lambda x: x[0], cr.fetchall())

        query_1st_part = """
                INSERT INTO account_move_line (
                     debit, credit, name, date, move_id, journal_id, date_account,
                     account_id, currency_id, amount_currency, company_id, state) VALUES
        """
        query_2nd_part = ""
        query_2nd_part_args = []
        ctx = {'fiscalyear': self.fy_id.id}
        for account in self.env['account.account'].with_context(ctx).browse(account_ids):
            company_currency_id = self.env.user.company_id.currency_id
            if not company_currency_id.is_zero(abs(account.balance)):
                if query_2nd_part:
                    query_2nd_part += ','
                query_2nd_part += "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                query_2nd_part_args += (account.balance > 0 and account.balance or 0.0,
                       account.balance < 0 and -account.balance or 0.0,
                       self.report_name,
                       date_account,
                       move_id.id,
                       new_journal.id,
                       account.id,
                       account.currency_id and account.currency_id.id or None,
                       account.foreign_balance if account.currency_id else 0.0,
                       account.company_id.id,
                       'draft')
        if query_2nd_part:
            cr.execute(query_1st_part + query_2nd_part, tuple(query_2nd_part_args))
            self.invalidate_cache()

        #validate and centralize the opening move
        move_id.validate()

        #reconcile all the move.line of the opening move
        ids = obj_acc_move_line.search([('journal_id', '=', new_journal.id)])
        if ids:
            reconcile_id = _reconcile_fy_closing(self._cr, self._uid, ids.ids, context=self._context)
            #set the creation date of the reconcilation at the first day of the new fiscalyear, in order to have good figures in the aged trial balance
            reconcile_id.write({'create_date': new_fyear.date_start})

            # TODO : account_journal_period has been removed
#         #create the journal.period object and link it to the old fiscalyear
#         new_period = self.period_id.id
#         ids = obj_acc_journal_period.search([('journal_id', '=', new_journal.id), ('period_id', '=', new_period)])
#         if not ids:
#             ids = [obj_acc_journal_period.create(cr, uid, {
#                    'name': (new_journal.name or '') + ':' + (period.code or ''),
#                    'journal_id': new_journal.id,
#                    'period_id': period.id
#                })]
#         cr.execute('UPDATE account_fiscalyear ' \
#                     'SET end_journal_id = %s ' \
#                     'WHERE id = %s', (ids.ids[0], old_fyear.id))
#         self.env['account.fiscalyear'].invalidate_cache(['end_journal_id'], [old_fyear.id])

        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
