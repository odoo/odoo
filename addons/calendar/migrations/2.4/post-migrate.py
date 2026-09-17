"""What the resource could only receive once its own columns existed.

The links moved in `pre-migrate`; the booking policy the profile carried lands
here, because `booking_exclusive`, `booking_sequence` and `description` are
created by the registry between the two phases.
"""

import logging

from odoo.db.schema import table_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or not table_exists(cr, "appointment_resource"):
        return
    _carry_booking_policy(cr)


def _carry_booking_policy(cr):
    cr.execute(
        """
        UPDATE resource_resource resource
           SET booking_sequence = profile.sequence,
               booking_exclusive = NOT profile.shareable,
               description = profile.description
          FROM (
              SELECT DISTINCT ON (resource_id) resource_id, sequence, shareable, description
                FROM appointment_resource
               WHERE resource_id IS NOT NULL
            ORDER BY resource_id, sequence, id
          ) profile
         WHERE resource.id = profile.resource_id
        """
    )
    _logger.info("calendar: %s resources took their booking policy", cr.rowcount)
