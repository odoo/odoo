def migrate(cr, version):
    # Moves of a journal using documents are not numbered by Odoo, so they can never make a sequence
    # gap. Clear the flags wrongly stored before <account.move>._update_sequence_made_gap was overridden.
    cr.execute("""
        UPDATE account_move move
           SET made_sequence_gap = FALSE
          FROM account_journal journal
         WHERE journal.id = move.journal_id
           AND journal.l10n_latam_use_documents = TRUE
           AND move.move_type != 'in_receipt'
           AND move.made_sequence_gap = TRUE
    """)
