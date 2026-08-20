def migrate(cr, version):
    """
    Move the closing journal back to the field that means it.

    Up to 19.0 the two PoS journals lived in two fields: 'journal_id' held the journal of
    the session closing entries, and 'invoice_journal_id' the one of the customer
    invoices. The accounting refactor dropped 'invoice_journal_id' and made 'journal_id'
    carry both, which inverted the meaning of that column: it holds a closing journal,
    while the new code reads it as an invoice journal.
    """
    cr.execute("""
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'pos_config'
           AND column_name = 'invoice_journal_id'
    """)
    if not cr.rowcount:
        return

    cr.execute("""
        UPDATE pos_config
           SET journal_id = invoice_journal_id,
               closing_journal_id = NULLIF(journal_id, invoice_journal_id)
         WHERE closing_journal_id IS NULL
           AND invoice_journal_id IS NOT NULL
    """)
