def migrate(cr, version):
    cr.execute("""
        UPDATE account_journal
           SET restrict_mode_hash_table = FALSE
         WHERE type = 'purchase'
           AND l10n_latam_use_documents = TRUE
           AND restrict_mode_hash_table = TRUE
    """)
