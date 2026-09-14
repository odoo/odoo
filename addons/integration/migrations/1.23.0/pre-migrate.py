def migrate(cr, version):
    if not version:
        return
    # log_retention_days was never read and defaulted to 90 on every endpoint. It
    # now overrides the global retention when positive, so the untouched default
    # must become 0 (use the global value) rather than start pinning 90 days.
    cr.execute(
        "UPDATE integration_service SET log_retention_days = 0 "
        "WHERE log_retention_days = 90"
    )
