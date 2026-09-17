"""The kiosk moved from the booking profile onto the resource.

A room's tablet is reached by a short code and an access token; regenerating
them would silently break every door display and every link already handed out,
so the values the profile held are carried over. Calendar's 2.4 script has
already moved the profile's background image onto the same resource.
"""

import logging

from odoo.db.schema import column_exists, table_exists

_logger = logging.getLogger(__name__)

KIOSK_COLUMNS = (
    "short_code",
    "access_token",
    "bookable_background_color",
    "booked_background_color",
)


def migrate(cr, version):
    if not table_exists(cr, "appointment_resource"):
        return
    columns = [
        column
        for column in KIOSK_COLUMNS
        if column_exists(cr, "appointment_resource", column)
    ]
    if not columns:
        return
    # A resource created since the merge may already hold a freshly minted code,
    # and both columns are unique: free the value before the legacy one lands.
    for column in ("short_code", "access_token"):
        if column not in columns:
            continue
        cr.execute(
            f"""
            UPDATE resource_resource resource
               SET {column} = NULL
             WHERE {column} IN (SELECT {column} FROM appointment_resource
                                 WHERE {column} IS NOT NULL)
               AND resource.id NOT IN (SELECT resource_id FROM appointment_resource
                                        WHERE {column} IS NOT NULL
                                          AND resource_id IS NOT NULL)
            """
        )
    assignments = ", ".join(f"{column} = profile.{column}" for column in columns)
    cr.execute(
        f"""
        UPDATE resource_resource resource
           SET {assignments}
          FROM appointment_resource profile
         WHERE profile.resource_id = resource.id
           AND (profile.short_code IS NOT NULL OR profile.access_token IS NOT NULL)
        """
    )
    _logger.info("room: %s kiosks kept their code and token", cr.rowcount)
