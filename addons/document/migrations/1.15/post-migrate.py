"""Give every document already in the trash the date the old rule implied.

`_get_domain_gc_clear_bin` used to compute the purge date as
`write_date + document.deletion_delay`. It now reads a stored `deletion_date`,
stamped by `action_archive`. Documents archived before this upgrade carry no
such date, and the GC deliberately skips rows without one -- so without this
they would sit in the trash forever.

The value written here is exactly what the old rule would have computed for
them, so nothing is purged earlier or later than it would have been.
"""

DEFAULT_DELETION_DELAY = 30


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        "SELECT value FROM ir_config_parameter WHERE key = 'document.deletion_delay'"
    )
    row = cr.fetchone()
    try:
        delay = int(row[0]) if row and row[0] else DEFAULT_DELETION_DELAY
    except ValueError:
        delay = DEFAULT_DELETION_DELAY

    cr.execute(
        """
        UPDATE document_document
           SET deletion_date = (write_date + make_interval(days => %s))::date
         WHERE active = false
           AND deletion_date IS NULL
        """,
        (delay,),
    )
