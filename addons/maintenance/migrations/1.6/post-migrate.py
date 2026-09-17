import logging
import re

from odoo import SUPERUSER_ID, api, fields
from odoo.db.schema import column_exists, table_exists

_logger = logging.getLogger(__name__)

EQUIPMENT_MODELS = ("maintenance.equipment", "maintenance.equipment.category")
PARKED = "__retired_equipment__"
RETIRED_SUBTYPES = ("mt_mat_assign", "mt_cat_mat_assign", "mt_cat_order_created")
RELIABILITY = {
    "maintenance_team_id": "maintenance_team_id",
    "technician_user_id": "technician_user_id",
    "expected_mtbf": "expected_mtbf",
    "date_effective": "date_in_service",
}
QUIET = {
    "mail_create_nolog": True,
    "mail_create_nosubscribe": True,
    "mail_notrack": True,
    "tracking_disable": True,
    "active_test": False,
}


def migrate(cr, version):
    if not version or not table_exists(cr, "maintenance_equipment"):
        return
    env = api.Environment(cr, SUPERUSER_ID, QUIET)
    env.invalidate_all()
    for table, column in (
        ("maintenance_equipment", "asset_id"),
        ("maintenance_equipment_category", "kind_id"),
    ):
        if table_exists(cr, table) and not column_exists(cr, table, column):
            cr.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}" int4')
    kinds = _convert_categories(cr, env)
    assets = _convert_equipment(cr, env, kinds)
    _link_orders_and_plans(cr)
    _move_custody(cr, env, assets)
    _move_mail(cr)
    _retire_subtypes(cr)
    cr.execute("DELETE FROM ir_model_data WHERE module = %s", [PARKED])
    env.invalidate_all()
    _logger.info(
        "maintenance: %s equipment categories became kinds, %s equipment became assets",
        len(kinds),
        len(assets),
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


def _adopt_or_restore_xmlid(env, parked, target_model, create):
    if not parked:
        return create()
    full_name, noupdate = parked
    module, name = full_name.split(".", 1)
    existing = env.ref(full_name, raise_if_not_found=False)
    if existing and existing._name == target_model:
        return existing
    record = create()
    env.cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (module, name) DO UPDATE SET model = EXCLUDED.model, res_id = EXCLUDED.res_id
        """,
        [module, name, target_model, record.id, noupdate],
    )
    return record


def _name_serial_like_its_asset(cr, parked, asset):
    full_name, noupdate = parked
    module, name = full_name.split(".", 1)
    serial = asset.identifier_ids.filtered(lambda i: i.type_id.code == "serial")[:1]
    if not serial:
        return
    cr.execute(
        """
        INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
        VALUES (%s, %s, 'resource.asset.identifier', %s, %s)
        ON CONFLICT (module, name) DO NOTHING
        """,
        [module, f"{name}_serial", serial.id, noupdate],
    )


def _convert_categories(cr, env):
    if not table_exists(cr, "maintenance_equipment_category"):
        return {}
    has_definition = column_exists(
        cr, "maintenance_equipment_category", "equipment_properties_definition"
    )
    cr.execute(
        f"""
        SELECT id, name, technician_user_id,
               {"equipment_properties_definition" if has_definition else "NULL"}
                   AS definition
          FROM maintenance_equipment_category
         WHERE kind_id IS NULL
         ORDER BY id
        """
    )
    categories = cr.dictfetchall()
    Kind = env["resource.asset.kind"]
    parked = _parked_xmlids(cr, "maintenance.equipment.category")
    taken = set(Kind.search([]).mapped("code"))

    def create(category):
        label = _name(category["name"]) or f"Category {category['id']}"
        base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "category"
        code, suffix = base, 2
        while code in taken:
            code, suffix = f"{base}_{suffix}", suffix + 1
        taken.add(code)
        return Kind.create(
            {
                "name": label,
                "code": code,
                "technician_user_id": category["technician_user_id"],
                "asset_properties_definition": category["definition"] or [],
            }
        )

    kinds = {}
    for category in categories:
        kind = _adopt_or_restore_xmlid(
            env,
            parked.get(category["id"]),
            "resource.asset.kind",
            lambda category=category: create(category),
        )
        cr.execute(
            "UPDATE maintenance_equipment_category SET kind_id = %s WHERE id = %s",
            (kind.id, category["id"]),
        )
        kinds[category["id"]] = kind.id
    return kinds


def _convert_equipment(cr, env, kinds):
    def optional(column):
        present = column_exists(cr, "maintenance_equipment", column)
        return f"{column if present else 'NULL'} AS {column}"

    cr.execute(
        f"""
        SELECT id, name, active, category_id, partner_id, partner_ref, model,
               serial_no, warranty_date, cost, note, color, scrap_date,
               create_date, create_uid, {optional("company_id")},
               {optional("date_effective")}, {optional("equipment_properties")}
          FROM maintenance_equipment
         WHERE asset_id IS NULL
         ORDER BY id
        """
    )
    rows = cr.dictfetchall()
    fallback_kind = env.ref("resource_asset.kind_equipment")
    serial_type = env.ref("resource_asset.identifier_type_serial")
    Asset = env["resource.asset"]
    parked = _parked_xmlids(cr, "maintenance.equipment")

    def create(equipment):
        vals = {
            "name": _name(equipment["name"]) or f"Equipment {equipment['id']}",
            "kind_id": kinds.get(equipment["category_id"]) or fallback_kind.id,
            "company_id": equipment["company_id"],
            "partner_id": equipment["partner_id"],
            "partner_ref": equipment["partner_ref"],
            "model": equipment["model"],
            "warranty_date": equipment["warranty_date"],
            "value_original": equipment["cost"] or 0.0,
            "description": equipment["note"],
            "color": equipment["color"] or 0,
            "date_acquisition": min(
                filter(None, (equipment["date_effective"], equipment["scrap_date"])),
                default=False,
            ),
            "state": "disposed" if equipment["scrap_date"] else "in_service",
            "date_disposal": equipment["scrap_date"],
            "asset_properties": equipment["equipment_properties"] or {},
        }
        asset = Asset.create(vals)
        if equipment["serial_no"]:
            env["resource.asset.identifier"].create(
                {
                    "asset_id": asset.id,
                    "type_id": serial_type.id,
                    "value": equipment["serial_no"],
                }
            )
        cr.execute(
            "UPDATE resource_asset SET create_date = %s, create_uid = %s WHERE id = %s",
            (equipment["create_date"], equipment["create_uid"], asset.id),
        )
        return asset

    assets = {}
    for equipment in rows:
        asset = _adopt_or_restore_xmlid(
            env,
            parked.get(equipment["id"]),
            "resource.asset",
            lambda equipment=equipment: create(equipment),
        )
        if parked.get(equipment["id"]):
            _name_serial_like_its_asset(cr, parked[equipment["id"]], asset)
        if not equipment["active"] or equipment["scrap_date"]:
            asset.active = False
        cr.execute(
            "UPDATE maintenance_equipment SET asset_id = %s WHERE id = %s",
            (asset.id, equipment["id"]),
        )
        assets[equipment["id"]] = asset
    columns = [c for c in RELIABILITY if column_exists(cr, "maintenance_equipment", c)]
    if columns:
        assignments = ", ".join(
            f"{RELIABILITY[c]} = COALESCE(equipment.{c}, resource.{RELIABILITY[c]})"
            for c in columns
        )
        cr.execute(
            f"""
            UPDATE resource_resource resource
               SET {assignments}
              FROM maintenance_equipment equipment
              JOIN resource_asset asset ON asset.id = equipment.asset_id
             WHERE asset.resource_id = resource.id
            """
        )
    return assets


def _link_orders_and_plans(cr):
    for table, column in (
        ("maintenance_order", "order_id"),
        ("maintenance_plan", "plan_id"),
    ):
        if not column_exists(cr, table, "equipment_id"):
            continue
        cr.execute(
            f"""
            INSERT INTO {table}_resource_rel ({column}, resource_id)
            SELECT record.id, asset.resource_id
              FROM "{table}" record
              JOIN maintenance_equipment equipment ON equipment.id = record.equipment_id
              JOIN resource_asset asset ON asset.id = equipment.asset_id
            ON CONFLICT DO NOTHING
            """
        )


def _move_custody(cr, env, assets):
    if not column_exists(cr, "maintenance_equipment", "owner_user_id"):
        return
    by_hr = column_exists(cr, "maintenance_equipment", "equipment_assign_to")
    cr.execute(
        f"""
        SELECT id, owner_user_id, assign_date, create_date, active, scrap_date
          FROM maintenance_equipment
         WHERE owner_user_id IS NOT NULL
           {"AND equipment_assign_to = 'other'" if by_hr else ""}
        """
    )
    holders = {}
    vals_list = []
    for (
        equipment_id,
        user_id,
        assign_date,
        create_date,
        active,
        scrap_date,
    ) in cr.fetchall():
        asset = assets.get(equipment_id)
        if not asset:
            continue
        date_start = fields.Datetime.to_datetime(assign_date) or create_date
        user = env["res.users"].browse(user_id)
        company = asset.company_id or user.company_id
        key = (user_id, company.id)
        if key not in holders:
            holders[key] = user.partner_id._get_or_create_resources(company)
        vals_list.append(
            {
                "resource_id": asset.resource_id.id,
                "assignee_id": holders[key].id,
                "role": "custodian",
                "date_start": date_start,
                "date_end": _retired_on(active, scrap_date, date_start),
            }
        )
    env["resource.assignment"].create(vals_list)


def _retired_on(active, scrap_date, date_start):
    if active and not scrap_date:
        return False
    return max(fields.Datetime.to_datetime(scrap_date) or date_start, date_start)


def _move_mail(cr):
    cr.execute("SELECT id FROM ir_model WHERE model = 'resource.asset'")
    asset_model_id = cr.fetchone()[0]
    for table, model_column, extra in (
        ("mail_message", "model", ""),
        ("ir_attachment", "res_model", ""),
        ("mail_activity", "res_model", f", res_model_id = {int(asset_model_id)}"),
    ):
        id_column = "res_id"
        cr.execute(
            f"""
            UPDATE {table} target
               SET {model_column} = 'resource.asset', {id_column} = equipment.asset_id{extra}
              FROM maintenance_equipment equipment
             WHERE equipment.asset_id IS NOT NULL
               AND target.{model_column} = 'maintenance.equipment'
               AND target.{id_column} = equipment.id
            """
        )
    cr.execute(
        """
        DELETE FROM mail_followers follower
              USING maintenance_equipment equipment
              WHERE follower.res_model = 'maintenance.equipment'
                AND follower.res_id = equipment.id
                AND EXISTS (
                    SELECT 1 FROM mail_followers kept
                     WHERE kept.res_model = 'resource.asset'
                       AND kept.res_id = equipment.asset_id
                       AND kept.partner_id = follower.partner_id
                )
        """
    )
    cr.execute(
        """
        UPDATE mail_followers follower
           SET res_model = 'resource.asset', res_id = equipment.asset_id
          FROM maintenance_equipment equipment
         WHERE equipment.asset_id IS NOT NULL
           AND follower.res_model = 'maintenance.equipment'
           AND follower.res_id = equipment.id
        """
    )


def _retire_subtypes(cr):
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
         WHERE module = 'maintenance' AND model = 'mail.message.subtype'
           AND name = ANY(%s)
        """,
        [list(RETIRED_SUBTYPES)],
    )
    subtype_ids = [row[0] for row in cr.fetchall()]
    cr.execute(
        "DELETE FROM mail_message_subtype WHERE res_model = ANY(%s) OR id = ANY(%s)",
        [list(EQUIPMENT_MODELS), subtype_ids],
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'maintenance' AND model = 'mail.message.subtype'
           AND name = ANY(%s)
        """,
        [list(RETIRED_SUBTYPES)],
    )
