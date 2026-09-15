def migrate(cr, version):
    cr.execute("SELECT state FROM ir_module_module WHERE name = 'hr'")
    row = cr.fetchone()
    if not row or row[0] not in ("installed", "to upgrade", "to install"):
        return
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'to install'
         WHERE name = 'document_compliance_hr'
           AND state = 'uninstalled'
        """
    )
