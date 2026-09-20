import logging

_logger = logging.getLogger(__name__)

PATTERNS = {"vin": "[A-HJ-NPR-Z0-9]{17}", "imei": "[0-9]{15}"}


def migrate(cr, version):
    """A VIN and an IMEI have a shape; the type carries it (noupdate data, so an
    existing database takes it here). Rows that do not match are not touched:
    the check runs on the next write of each, and the log names them now."""
    if not version:
        return
    for code, pattern in PATTERNS.items():
        cr.execute(
            """
            UPDATE resource_asset_identifier_type
               SET pattern = %s
             WHERE code = %s AND COALESCE(pattern, '') = ''
            """,
            (pattern, code),
        )
        cr.execute(
            """
            SELECT i.id, i.value
              FROM resource_asset_identifier i
              JOIN resource_asset_identifier_type t ON t.id = i.type_id
             WHERE t.code = %s AND i.normalized_value !~ ('^' || %s || '$')
            """,
            (code, pattern),
        )
        rows = cr.fetchall()
        if rows:
            _logger.warning(
                "%d %s identifier(s) do not match %s and will be refused on their next "
                "write until corrected: %s",
                len(rows),
                code,
                pattern,
                ", ".join(f"#{row_id} {value}" for row_id, value in rows),
            )
