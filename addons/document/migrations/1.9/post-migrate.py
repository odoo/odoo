def migrate(cr, version):
    # document.redirect was read by three share-link lookups and written by
    # nothing in this fork (its producer lived in upstream's upgrade repo).
    cr.execute("DROP TABLE IF EXISTS document_redirect")
    cr.execute("DELETE FROM ir_model WHERE model = 'document.redirect'")
