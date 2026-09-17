import json
import logging

from odoo import SUPERUSER_ID, Command, api
from odoo.db.schema import get_table_columns, table_exists
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

PARKED = "__retired_room__"
QUIET = {
    "mail_create_nolog": True,
    "mail_create_nosubscribe": True,
    "mail_notrack": True,
    "tracking_disable": True,
    "no_mail_to_attendees": True,
    "active_test": False,
}


def migrate(cr, version):
    if not version or not table_exists(cr, "room_room"):
        return
    env = api.Environment(cr, SUPERUSER_ID, QUIET)
    env.invalidate_all()
    partners, renames = _convert_offices(cr, env)
    rooms = _convert_rooms(cr, env, partners, renames)
    bookings = _convert_bookings(cr, env, rooms)
    _move_mail(
        cr, "room.room", "resource.asset", {r: a.id for r, (a, _p) in rooms.items()}
    )
    _move_mail(
        cr, "room.booking", "calendar.event", {b: e.id for b, e in bookings.items()}
    )
    _move_background_images(cr, rooms)
    cr.execute("DELETE FROM ir_model_data WHERE module = %s", [PARKED])
    env.invalidate_all()
    _logger.info(
        "room: %s offices became addresses, %s rooms became assets, %s bookings became calendar events",
        len(partners),
        len(rooms),
        len(bookings),
    )


def _name(value):
    if isinstance(value, dict):
        return value.get("en_US") or next(iter(value.values()), "")
    return value or ""


def _parked_xmlids(cr, model):
    cr.execute(
        "SELECT res_id, name, noupdate FROM ir_model_data WHERE module = %s AND model = %s",
        [PARKED, model],
    )
    return {res_id: (name, noupdate) for res_id, name, noupdate in cr.fetchall()}


def _restore_xmlid(cr, parked, target_model, res_id):
    if not parked:
        return
    full_name, noupdate = parked
    module, name = full_name.split(".", 1)
    cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (module, name) DO UPDATE SET model = EXCLUDED.model, res_id = EXCLUDED.res_id
        """,
        [module, name, target_model, res_id, noupdate],
    )


def _adopt_or_create(env, parked, target_model, create):
    """The module's own data and demo files reload before this script runs, so a
    record this migration is about to convert may already exist under the xml id
    parked in pre-migrate. Adopt that one instead of creating a second. With no
    `create`, an unadopted record answers None and the caller creates it in batch."""
    if parked:
        existing = env.ref(parked[0], raise_if_not_found=False)
        if existing and existing._name == target_model and existing.exists():
            return existing
    if create is None:
        return None
    record = create()
    _restore_xmlid(env.cr, parked, target_model, record.id)
    return record


def _free_kiosk_code(env, field, value, keep):
    if not value:
        return
    holder = (
        env["resource.resource"]
        .with_context(active_test=False)
        .search([(field, "=", value), ("id", "!=", keep.id)])
    )
    if holder:
        holder.write({field: False})


def _convert_offices(cr, env):
    cr.execute(
        """
        SELECT office.id, office.name, office.company_id, company.partner_id,
               office.room_properties_definition
          FROM room_office office
          JOIN res_company company ON company.id = office.company_id
         ORDER BY office.id
        """
    )
    rows = cr.fetchall()
    parked = _parked_xmlids(cr, "room.office")
    kind = env.ref("room.kind_room")
    definitions = list(kind.asset_properties_definition or [])
    renames = {}
    partners = {}
    for office_id, name, company_id, company_partner_id, definition in rows:
        partner = _adopt_or_create(
            env,
            parked.get(office_id),
            "res.partner",
            lambda name=name, company_id=company_id, parent=company_partner_id: env[
                "res.partner"
            ].create(
                {
                    "name": _name(name),
                    "type": "other",
                    "parent_id": parent,
                    "company_id": company_id,
                }
            ),
        )
        partners[office_id] = partner
        for prop in definition or []:
            known = next((d for d in definitions if d["name"] == prop["name"]), None)
            if known is None:
                definitions.append(prop)
            elif known.get("type") != prop.get("type"):
                renamed = {**prop, "name": f"{prop['name']}_{office_id}"}
                definitions.append(renamed)
                renames[office_id, prop["name"]] = renamed["name"]
    if definitions != list(kind.asset_properties_definition or []):
        kind.asset_properties_definition = definitions
    return partners, renames


def _convert_rooms(cr, env, partners, renames):
    description = (
        SQL("room.description")
        if get_table_columns(cr, "resource_asset")["description"]["udt_name"] == "jsonb"
        else SQL("room.description ->> 'en_US'")
    )
    cr.execute(
        """
        SELECT id, name, active, office_id, company_id, short_code, access_token,
               bookable_background_color, booked_background_color, room_properties
          FROM room_room
         ORDER BY id
        """
    )
    rows = cr.fetchall()
    parked = _parked_xmlids(cr, "room.room")
    kind = env.ref("room.kind_room")
    rooms = {}
    for (
        room_id,
        name,
        active,
        office_id,
        company_id,
        short_code,
        access_token,
        bookable_color,
        booked_color,
        properties,
    ) in rows:
        office_partner = partners.get(office_id)
        asset = _adopt_or_create(
            env,
            parked.get(room_id),
            "resource.asset",
            lambda name=name, company_id=company_id, address=office_partner: env[
                "resource.asset"
            ].create(
                {
                    "name": name,
                    "kind_id": kind.id,
                    "state": "in_service",
                    "company_id": company_id,
                    "address_id": address.id if address else False,
                }
            ),
        )
        values = {
            renames.get((office_id, key), key): value
            for key, value in (properties or {}).items()
        }
        cr.execute(
            SQL(
                """
                UPDATE resource_asset asset
                   SET description = %s,
                       asset_properties = %s::jsonb
                  FROM room_room room
                 WHERE asset.id = %s AND room.id = %s
                """,
                description,
                json.dumps(values) if values else None,
                asset.id,
                room_id,
            )
        )
        resource = asset.resource_id
        _free_kiosk_code(env, "short_code", short_code, resource)
        _free_kiosk_code(env, "access_token", access_token, resource)
        resource.write(
            {
                "short_code": short_code,
                "access_token": access_token,
                "bookable_background_color": bookable_color,
                "booked_background_color": booked_color,
            }
        )
        if not active:
            asset.active = False
        rooms[room_id] = (asset, resource)
    env.invalidate_all()
    return rooms


def _convert_bookings(cr, env, rooms):
    cr.execute(
        """
        SELECT booking.id, booking.name, booking.room_id, booking.start_datetime,
               booking.stop_datetime, booking.organizer_id, users.partner_id
          FROM room_booking booking
     LEFT JOIN res_users users ON users.id = booking.organizer_id
         ORDER BY booking.start_datetime, booking.id
        """
    )
    rows = cr.fetchall()
    parked = _parked_xmlids(cr, "room.booking")
    room_type = env.ref("room.appointment_type_room")
    vals_list = []
    booking_ids = []
    bookings = {}
    for booking_id, name, room_id, start, stop, organizer_id, partner_id in rows:
        _asset, resource = rooms[room_id]
        adopted = _adopt_or_create(env, parked.get(booking_id), "calendar.event", None)
        if adopted is not None:
            bookings[booking_id] = adopted
            continue
        vals_list.append(
            {
                "name": name,
                "start": start,
                "stop": stop,
                "user_id": organizer_id or False,
                "partner_ids": [Command.set([partner_id] if partner_id else [])],
                "appointment_type_id": room_type.id,
                "booking_line_ids": [
                    Command.create(
                        {"resource_id": resource.id, "capacity_reserved": 1}
                    )
                ],
            }
        )
        booking_ids.append(booking_id)
    events = env["calendar.event"].create(vals_list) if vals_list else []
    for booking_id, event in zip(booking_ids, events, strict=True):
        _restore_xmlid(cr, parked.get(booking_id), "calendar.event", event.id)
        bookings[booking_id] = event
    return bookings


def _move_mail(cr, source_model, target_model, targets):
    if not targets:
        return
    cr.execute("SELECT id FROM ir_model WHERE model = %s", [target_model])
    target_model_id = cr.fetchone()[0]
    mapping = json.dumps({str(source): target for source, target in targets.items()})
    new_res_id = SQL("(%s::jsonb ->> res_id::text)::int", mapping)
    moved = SQL("%s::jsonb ? res_id::text", mapping)
    for table, model_column, extra_set, extra_where in (
        ("mail_message", "model", SQL(), SQL()),
        ("ir_attachment", "res_model", SQL(), SQL("AND res_field IS NULL")),
        (
            "mail_activity",
            "res_model",
            SQL(", res_model_id = %s", target_model_id),
            SQL(),
        ),
    ):
        cr.execute(
            SQL(
                """
                UPDATE %(table)s
                   SET %(column)s = %(target)s, res_id = %(res_id)s %(extra_set)s
                 WHERE %(column)s = %(source)s AND %(moved)s %(extra_where)s
                """,
                table=SQL.identifier(table),
                column=SQL.identifier(model_column),
                target=target_model,
                source=source_model,
                res_id=new_res_id,
                moved=moved,
                extra_set=extra_set,
                extra_where=extra_where,
            )
        )
    cr.execute(
        SQL(
            """
            DELETE FROM mail_followers follower
             WHERE follower.res_model = %(source)s
               AND EXISTS (
                   SELECT 1 FROM mail_followers kept
                    WHERE kept.res_model = %(target)s
                      AND kept.res_id = (%(mapping)s::jsonb ->> follower.res_id::text)::int
                      AND kept.partner_id = follower.partner_id
               )
            """,
            source=source_model,
            target=target_model,
            mapping=mapping,
        )
    )
    cr.execute(
        SQL(
            """
            UPDATE mail_followers
               SET res_model = %(target)s, res_id = %(res_id)s
             WHERE res_model = %(source)s AND %(moved)s
            """,
            target=target_model,
            source=source_model,
            res_id=new_res_id,
            moved=moved,
        )
    )


def _move_background_images(cr, rooms):
    if not rooms:
        return
    mapping = json.dumps(
        {str(room_id): resource.id for room_id, (_asset, resource) in rooms.items()}
    )
    cr.execute(
        SQL(
            """
            UPDATE ir_attachment
               SET res_model = 'resource.resource',
                   res_id = (%(mapping)s::jsonb ->> res_id::text)::int
             WHERE res_model = 'room.room'
               AND res_field = 'room_background_image'
               AND %(mapping)s::jsonb ? res_id::text
            """,
            mapping=mapping,
        )
    )
