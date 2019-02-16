import models

from openerp import SUPERUSER_ID

def _migration_script(cr, registry):
    #1. set the tax_exigible at True on all account.move lines not related to a tax in cash basis
    cr.execute('''UPDATE account_move_line SET tax_exigible='t' ''')

    cr.execute('''SELECT id FROM account_tax WHERE use_cash_basis = 't' ''')
    tax_ids = tuple([x[0] for x in cr.fetchall()])
    if tax_ids:
        cr.execute('''UPDATE account_move_line SET tax_exigible='f' WHERE id IN (SELECT id FROM account_move_line WHERE tax_line_id IN %s OR id IN (SELECT account_move_line_id FROM account_move_line_account_tax_rel WHERE account_tax_id IN %s))''', (tax_ids, tax_ids))

    #2. Fix the moves already created by the tax case based feature
    #  create account.move.lines for tax_line_id and tax_ids that weren't correctly set/created at the time of reconciliation
    existing_move = registry['account.move'].search(cr, SUPERUSER_ID, [('tax_cash_basis_rec_id', '!=', False)])
    for m in registry['account.move'].browse(cr, SUPERUSER_ID, existing_move):
        partial_rec = m.tax_cash_basis_rec_id
        for move in (partial_rec.debit_move_id.move_id, partial_rec.credit_move_id.move_id):
            matched_percentage = partial_rec.amount and (partial_rec.amount / move.amount) or 0.0
            for l in move.line_ids:
                if l.tax_exigible:
                    continue

                move_to_fix = registry['account.move'].search(cr, SUPERUSER_ID, [('tax_cash_basis_rec_id', '=', partial_rec.id)])[0]
                amount = (l.debit - l.credit) * matched_percentage

                registry['account.move.line'].create(cr, SUPERUSER_ID, {
                    'name': '/',
                    'debit': amount > 0 and amount or 0.0,
                    'credit': amount < 0 and -amount or 0.0,
                    'account_id': l.account_id.id,
                    'tax_line_id': l.tax_line_id and l.tax_line_id.id or False,
                    'tax_ids': l.tax_ids and [(6, 0, l.tax_ids.ids)] or [],
                    'tax_exigible': True,
                    'move_id': move_to_fix,
                }, apply_taxes=False, context={'check_move_validity': False})
                registry['account.move.line'].create(cr, SUPERUSER_ID, {
                    'name': '/',
                    'debit': -amount > 0 and -amount or 0.0,
                    'credit': -amount < 0 and amount or 0.0,
                    'account_id': l.account_id.id,
                    'move_id': move_to_fix,
                    'tax_exigible': True,
                }, context={'check_move_validity': False})
    return
