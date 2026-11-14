def migrate(cr, version):
    """Rename the legacy 'permission' attendance status to 'excused'."""
    if not version:
        return
    cr.execute(
        "UPDATE university_attendance SET status = 'excused' WHERE status = 'permission'"
    )