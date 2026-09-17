"""`appointment.resource` was a booking profile in front of a resource; the
resource holds the booking itself now.

Everything here runs before the data files load, because that phase already
reads what this changes: a stored arch naming `appointment_resource_ids` fails
view validation, and an xml id still pointing at `appointment.resource` asks the
registry for a model that no longer exists. The links are renamed in place
rather than copied, so no column the ORM creates arrives empty.
"""

import logging
import os

from odoo.db.schema import (
    column_exists,
    drop_constraint,
    get_fk_constraints_batch,
    table_exists,
)
from odoo.exceptions import UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

MERGE_FLAG = "ODOO_APPOINTMENT_RESOURCE_MERGE"

FIELD_RENAMES = (
    ("appointment_resource_ids", "resource_ids"),
    ("appointment_resource_id", "resource_id"),
)

SOURCES = (
    ("ir_ui_view", "arch_db", True),
    ("ir_ui_view", "arch_prev", False),
    ("ir_act_server", "code", False),
    ("ir_rule", "domain_force", False),
    ("ir_filters", "domain", False),
    ("ir_filters", "context", False),
    ("ir_act_window", "domain", False),
    ("ir_act_window", "context", False),
    # A mail template is noupdate data: the data file cannot correct one that a
    # database already carries, so its body is rewritten here too.
    ("mail_template", "body_html", True),
    ("mail_template", "subject", True),
)

RELATIONS = (
    # old table, new table, old profile column, new resource column
    (
        "appointment_type_appointment_resource_rel",
        "appointment_type_resource_rel",
        "appointment_resource_id",
        "resource_id",
    ),
    (
        "appointment_resource_appointment_slot_rel",
        "appointment_slot_resource_resource_rel",
        "appointment_resource_id",
        "resource_resource_id",
    ),
    (
        "appointment_invite_appointment_resource_rel",
        "appointment_invite_resource_resource_rel",
        "appointment_resource_id",
        "resource_resource_id",
    ),
)


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_expressions(cr)
    if not table_exists(cr, "appointment_resource"):
        return
    _refuse_alternative_profiles(cr)
    _repoint_booking_lines(cr)
    for old_table, new_table, old_column, new_column in RELATIONS:
        _repoint_relation(cr, old_table, new_table, old_column, new_column)
    _repoint_combinations(cr)
    _drop_wizard_relation(cr)
    _repoint_attachments(cr)
    _repoint_xmlids(cr)
    cr.execute("SELECT count(*) FROM appointment_resource")
    _logger.info(
        "calendar: %s appointment resources became resources", cr.fetchone()[0]
    )


def _rewrite_stored_expressions(cr):
    rewritten = 0
    for table, column, is_jsonb in SOURCES:
        if not column_exists(cr, table, column):
            continue
        cast = "::text" if is_jsonb else ""
        back = "::jsonb" if is_jsonb else ""
        for old, new in FIELD_RENAMES:
            cr.execute(
                f"UPDATE {table} SET {column} = replace({column}{cast}, %s, %s){back}"
                f" WHERE {column}{cast} LIKE %s",
                (old, new, f"%{old}%"),
            )
            rewritten += cr.rowcount
    _logger.info("calendar: %s stored expressions renamed to the resource", rewritten)


def _refuse_alternative_profiles(cr):
    cr.execute(
        """
        SELECT resource_id, array_agg(id ORDER BY sequence, id)
          FROM appointment_resource
         WHERE resource_id IS NOT NULL
      GROUP BY resource_id
        HAVING count(*) > 1
        """
    )
    clashing = cr.fetchall()
    if not clashing:
        return
    if not os.environ.get(MERGE_FLAG):
        raise UserError(
            "These resources carry more than one appointment resource, and a resource now "
            "holds one booking policy:\n"
            + "\n".join(
                f"  resource {resource_id}: appointment resources {profile_ids}"
                for resource_id, profile_ids in clashing
            )
            + f"\n\nSet {MERGE_FLAG}=1 to keep the first of each by sequence and move its "
            "bookings onto the resource, or separate them onto their own resources first."
        )
    for resource_id, profile_ids in clashing:
        _logger.warning(
            "calendar: resource %s kept appointment resource %s, merged %s into it",
            resource_id,
            profile_ids[0],
            profile_ids[1:],
        )


def _drop_profile_foreign_keys(cr, table, column):
    """The link points at `appointment_resource` until the registry rebuilds it,
    and that constraint refuses the resource ids this script writes."""
    for name, _table, attname, target, _target_column, _ondelete in (
        get_fk_constraints_batch(cr, [table])
    ):
        if attname == column and target == "appointment_resource":
            drop_constraint(cr, table, name)


def _repoint_booking_lines(cr):
    if not column_exists(cr, "appointment_booking_line", "appointment_resource_id"):
        return
    cr.execute(
        "ALTER TABLE appointment_booking_line "
        "RENAME COLUMN appointment_resource_id TO resource_id"
    )
    _drop_profile_foreign_keys(cr, "appointment_booking_line", "resource_id")
    cr.execute(
        """
        UPDATE appointment_booking_line line
           SET resource_id = profile.resource_id
          FROM appointment_resource profile
         WHERE line.resource_id = profile.id
        """
    )
    cr.execute(
        """
        DELETE FROM appointment_booking_line
              WHERE resource_id IS NOT NULL
                AND resource_id NOT IN (SELECT id FROM resource_resource)
        """
    )


def _repoint_relation(cr, old_table, new_table, old_column, new_column):
    if not table_exists(cr, old_table) or table_exists(cr, new_table):
        return
    cr.execute(
        SQL(
            "ALTER TABLE %s RENAME TO %s",
            SQL.identifier(old_table),
            SQL.identifier(new_table),
        )
    )
    cr.execute(
        SQL(
            "ALTER TABLE %s RENAME COLUMN %s TO %s",
            SQL.identifier(new_table),
            SQL.identifier(old_column),
            SQL.identifier(new_column),
        )
    )
    _drop_profile_foreign_keys(cr, new_table, new_column)
    cr.execute(
        SQL(
            """
            DELETE FROM %(table)s link
                  USING appointment_resource profile
                  WHERE link.%(column)s = profile.id
                    AND profile.resource_id IS NULL
            """,
            table=SQL.identifier(new_table),
            column=SQL.identifier(new_column),
        )
    )
    # A profile id and the resource id replacing it share one column, so a row
    # can land on a pair another row still holds. Park the new ids out of the
    # positive range first: the primary key is checked per row, not at commit.
    cr.execute(
        SQL(
            """
            UPDATE %(table)s link
               SET %(column)s = -profile.resource_id
              FROM appointment_resource profile
             WHERE link.%(column)s = profile.id
            """,
            table=SQL.identifier(new_table),
            column=SQL.identifier(new_column),
        )
    )
    cr.execute(
        SQL(
            "UPDATE %(table)s SET %(column)s = -%(column)s WHERE %(column)s < 0",
            table=SQL.identifier(new_table),
            column=SQL.identifier(new_column),
        )
    )


def _repoint_combinations(cr):
    old_table = "appointment_resource_linked_appointment_resource"
    new_table = "resource_combinable_resource_rel"
    if not table_exists(cr, old_table) or table_exists(cr, new_table):
        return
    cr.execute(
        SQL(
            """
            CREATE TABLE %(new_table)s (
                resource_id INTEGER NOT NULL,
                combinable_resource_id INTEGER NOT NULL,
                PRIMARY KEY(resource_id, combinable_resource_id)
            )
            """,
            new_table=SQL.identifier(new_table),
        )
    )
    cr.execute(
        SQL(
            """
            INSERT INTO %(new_table)s (resource_id, combinable_resource_id)
                 SELECT DISTINCT source.resource_id, destination.resource_id
                   FROM %(old_table)s old
                   JOIN appointment_resource source ON source.id = old.resource_id
                   JOIN appointment_resource destination
                     ON destination.id = old.linked_resource_id
                  WHERE source.resource_id IS NOT NULL
                    AND destination.resource_id IS NOT NULL
                    AND source.resource_id != destination.resource_id
            """,
            new_table=SQL.identifier(new_table),
            old_table=SQL.identifier(old_table),
        )
    )
    cr.execute(SQL("DROP TABLE %s", SQL.identifier(old_table)))


def _drop_wizard_relation(cr):
    """The leaves wizard is transient: its rows name profiles that are gone, and
    the registry builds the resource-side table itself."""
    cr.execute("DROP TABLE IF EXISTS appointment_manage_leaves_appointment_resource_rel")


def _repoint_attachments(cr):
    """A profile's files belong to the resource it became: `room` keeps its kiosk
    background there, and an attachment left behind would name a dead model."""
    cr.execute(
        """
        UPDATE ir_attachment attachment
           SET res_model = 'resource.resource', res_id = profile.resource_id
          FROM appointment_resource profile
         WHERE attachment.res_model = 'appointment.resource'
           AND attachment.res_id = profile.id
           AND profile.resource_id IS NOT NULL
        """
    )
    cr.execute(
        "DELETE FROM ir_attachment WHERE res_model = 'appointment.resource' RETURNING id"
    )
    if dropped := cr.rowcount:
        _logger.info("calendar: %s files of profiles without a resource dropped", dropped)


def _repoint_xmlids(cr):
    cr.execute(
        """
        UPDATE ir_model_data data
           SET model = 'resource.resource', res_id = profile.resource_id
          FROM appointment_resource profile
         WHERE data.model = 'appointment.resource'
           AND data.res_id = profile.id
           AND profile.resource_id IS NOT NULL
        """
    )
    cr.execute("DELETE FROM ir_model_data WHERE model = 'appointment.resource'")
