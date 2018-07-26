# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import models

from openerp import SUPERUSER_ID
from collections import OrderedDict
from openerp.tools import float_compare

def _migrate_full_reconcile(cr, registry):
    #avoid doing anything if the table has already something in it (already migrated)
    cr.execute("""SELECT count(id) FROM account_full_reconcile""")
    res = cr.fetchone()[0]
    if res:
        return
    #check column reconcile_id exists on account.move.line
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'account_move_line'
          AND column_name = 'reconcile_id'
        """)
    if cr.fetchone():
        #if yes, use the table account_move_reconcile if it exists (not dropped by migration)
        cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'account_move_reconcile'")
        if cr.fetchone():
            #account_move_reconcile exists
            #copy old table
            cr.execute("""
                INSERT INTO account_full_reconcile (id, name, create_date)
                    SELECT id, name, create_date
                    FROM account_move_reconcile
                    WHERE id IN (
                        SELECT DISTINCT reconcile_id FROM account_move_line WHERE reconcile_id IS NOT NULL)
                """)
        else:
            #account_move_reconcile was dropped during migration, rebuild that table
            cr.execute("""
                INSERT INTO account_full_reconcile (id, name)
                    SELECT DISTINCT reconcile_id, reconcile_ref FROM account_move_line WHERE reconcile_id IS NOT NULL
                """)
        #update the index of account_full_reconcile
        cr.execute("SELECT setval('account_full_reconcile_id_seq', (SELECT MAX(id) FROM account_full_reconcile))")

        #copy the full_reconcile_id existing of account.move.line to their account.partial.reconcile
        cr.execute("""
            WITH tmp_table AS (
              SELECT partial_id, MAX(full_id) AS full_id FROM (
                SELECT rec.id AS partial_id, aml.reconcile_id AS full_id
                FROM account_move_line aml
                RIGHT JOIN account_partial_reconcile rec
                    ON aml.id = rec.debit_move_id
                WHERE aml.reconcile_id IS NOT NULL
                UNION
                SELECT rec.id AS partial_id, aml.reconcile_id AS full_id
                FROM account_move_line aml
                RIGHT JOIN account_partial_reconcile rec
                    ON aml.id = rec.credit_move_id
                WHERE aml.reconcile_id IS NOT NULL) tmp_table_with_duplicated_recs
             GROUP BY partial_id HAVING COUNT(partial_id) = 1)
            UPDATE account_partial_reconcile p
            SET full_reconcile_id = tmp.full_id FROM tmp_table tmp WHERE p.id = tmp.partial_id
            """)
    #if it's a fresh v9 database, or it has been used after the migration, we need to fill the table based on partial
    all_partial_rec_ids = registry['account.partial.reconcile'].search(cr, SUPERUSER_ID, [('full_reconcile_id', '=', False)])
    already_processed = {}
    for partial in registry['account.partial.reconcile'].browse(cr, SUPERUSER_ID, all_partial_rec_ids):
        partial_rec_set = OrderedDict.fromkeys([partial])
        aml_set = set()
        total_debit = 0
        total_credit = 0
        for partial_rec in partial_rec_set:
            if partial_rec in already_processed:
                continue
            for aml in [partial_rec.debit_move_id, partial_rec.credit_move_id]:
                if aml not in aml_set:
                    total_debit += aml.debit
                    total_credit += aml.credit
                    aml_set |= set([aml])
                for x in aml.matched_debit_ids | aml.matched_credit_ids:
                    partial_rec_set[x] = None
        partial_rec_ids = []
        for x in partial_rec_set.keys():
            partial_rec_ids.append(x.id)
            already_processed[x] = None
        aml_ids = [x.id for x in aml_set]
        if aml_ids and partial_rec_ids:
            #then, if the total debit and credit are equal, the reconciliation is full
            digits_rounding_precision = aml.company_id.currency_id.rounding
            if float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0:
                #in that case, mark the reference on the partial reconciliations and the entries
                registry['account.full.reconcile'].create(cr, SUPERUSER_ID, {
                    'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                    }, context={'check_move_validity': False})
    #copy values on account.move.line: rely on partial reconciliations only, as the reconcile_id column may not be
    #up-to-date, as unreconciliations/new reconciliations may have been done after migration
    cr.execute("""
        WITH tmp_table AS (
            SELECT debit_move_id AS aml_id, full_reconcile_id
            FROM account_partial_reconcile rec
            WHERE rec.full_reconcile_id IS NOT NULL
            UNION ALL
            SELECT credit_move_id AS aml_id, full_reconcile_id
            FROM account_partial_reconcile rec
            WHERE rec.full_reconcile_id IS NOT NULL)
        UPDATE account_move_line aml
        SET full_reconcile_id = tmp.full_reconcile_id FROM tmp_table tmp WHERE aml.id = tmp.aml_id
        """)
    return
