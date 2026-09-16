import logging
from datetime import datetime, time, timedelta

from odoo import SUPERUSER_ID, api, fields
from odoo.db.schema import column_exists, table_exists

_logger = logging.getLogger(__name__)

MAP_TABLE = "fleet_migration_map"
STATE_BY_XMLID = {
    "fleet_vehicle_state_new_request": "draft",
    "fleet_vehicle_state_to_order": "draft",
    "fleet_vehicle_state_ordered": "draft",
    "fleet_vehicle_state_registered": "in_service",
    "fleet_vehicle_state_waiting_list": "in_service",
    "fleet_vehicle_state_reserve": "in_service",
    "fleet_vehicle_state_downgraded": "disposed",
}
MODEL_SPEC_COLUMNS = {
    "seats": "seats",
    "doors": "doors",
    "transmission": "transmission",
    "default_fuel_type": "fuel_type",
    "default_co2": "co2",
    "power": "power",
    "power_unit": "power_unit",
    "horsepower": "horsepower",
    "vehicle_range": "vehicle_range",
    "range_unit": "range_unit",
    "trailer_hook": "trailer_hook",
    "drive_type": "drive_type",
    "color": "vehicle_color",
    "model_year": "vehicle_model_year",
}


def migrate(cr, version):
    if not version or not table_exists(cr, "fleet_vehicle"):
        return
    env = api.Environment(
        cr,
        SUPERUSER_ID,
        {
            "active_test": False,
            "tracking_disable": True,
            "mail_create_nolog": True,
            "skip_asset_identity_check": True,
        },
    )
    cr.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MAP_TABLE} (
            model varchar NOT NULL,
            old_id integer NOT NULL,
            new_model varchar NOT NULL,
            new_id integer NOT NULL,
            PRIMARY KEY (model, old_id)
        )
        """
    )
    brands = _migrate_brands(env)
    categories = _migrate_categories(env)
    products = _migrate_models(env, brands, categories)
    services = _migrate_service_types(env)
    vehicles = _migrate_vehicles(env, products)
    _migrate_tags(cr, vehicles)
    _migrate_odometers(env, vehicles)
    _migrate_drivers(env, vehicles)
    service_logs = _migrate_services(env, vehicles, services)
    _note_contracts(env, vehicles)
    _repoint(cr, "fleet.vehicle.model.brand", "res.partner", brands)
    _repoint(cr, "fleet.vehicle.model", "product.product", products)
    _repoint(cr, "fleet.service.type", "product.product", services)
    _repoint(cr, "fleet.vehicle", "resource.asset", vehicles)
    _repoint(cr, "fleet.vehicle.log.services", "resource.asset.log", service_logs)
    cr.execute(
        """
        UPDATE mail_message_subtype
           SET res_model = 'resource.asset'
         WHERE res_model = 'fleet.vehicle'
        """
    )
    cr.execute(
        "DELETE FROM ir_config_parameter WHERE key = 'hr_fleet.delay_alert_contract'"
    )


def _select(cr, table, wanted):
    present = [column for column in wanted if column_exists(cr, table, column)]
    cr.execute(f"SELECT {', '.join(present)} FROM {table} ORDER BY id")
    return [dict(zip(present, row, strict=True)) for row in cr.fetchall()]


def _record_map(cr, model, new_model, mapping):
    for old_id, new_id in mapping.items():
        cr.execute(
            f"""
            INSERT INTO {MAP_TABLE} (model, old_id, new_model, new_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (model, old_id) DO UPDATE SET new_id = EXCLUDED.new_id
            """,
            [model, old_id, new_model, new_id],
        )


def _translated(value):
    if isinstance(value, dict):
        return value.get("en_US") or next(iter(value.values()), "")
    return value or ""


def _as_datetime(value, default=None):
    if not value:
        return default
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


def _reloaded_record(env, cr, model, old_id, new_model):
    cr.execute(
        """
        SELECT name FROM ir_model_data
         WHERE module = 'fleet' AND model = %s AND res_id = %s AND name LIKE 'legacy\\_%%'
        """,
        [model, old_id],
    )
    row = cr.fetchone()
    if not row:
        return None
    record = env.ref(
        f"fleet.{row[0].removeprefix('legacy_')}", raise_if_not_found=False
    )
    return record if record and record._name == new_model else None


def _migrate_brands(env):
    cr = env.cr
    partners = env["res.partner"]
    mapping = {}
    for brand in _select(cr, "fleet_vehicle_model_brand", ["id", "name"]):
        cr.execute(
            """
            SELECT name FROM ir_model_data
             WHERE module = 'fleet'
               AND model = 'fleet.vehicle.model.brand'
               AND res_id = %s
            """,
            [brand["id"]],
        )
        row = cr.fetchone()
        partner = (
            env.ref(f"fleet.{row[0].removeprefix('legacy_')}", raise_if_not_found=False)
            if row
            else None
        )
        if not partner:
            partner = partners.search(
                [("is_manufacturer", "=", True), ("name", "=ilike", brand["name"])],
                limit=1,
            )
        if not partner:
            image = (
                env["ir.attachment"]
                .search(
                    [
                        ("res_model", "=", "fleet.vehicle.model.brand"),
                        ("res_field", "=", "image_128"),
                        ("res_id", "=", brand["id"]),
                    ],
                    limit=1,
                )
                .datas
            )
            partner = partners.create(
                {
                    "name": brand["name"],
                    "is_company": True,
                    "is_manufacturer": True,
                    "image_1920": image or False,
                }
            )
        mapping[brand["id"]] = partner.id
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'fleet'
           AND model = 'fleet.vehicle.model.brand'
           AND name LIKE 'legacy\\_%'
        """
    )
    _record_map(cr, "fleet.vehicle.model.brand", "res.partner", mapping)
    return mapping


def _migrate_categories(env):
    cr = env.cr
    rows = _select(cr, "fleet_vehicle_model_category", ["id", "name"])
    if not rows:
        return {}
    categories = env["product.category"]
    parent = categories.search(
        [("name", "=", "Vehicles"), ("parent_id", "=", False)], limit=1
    )
    parent = parent or categories.create({"name": "Vehicles"})
    mapping = {}
    for row in rows:
        category = categories.search(
            [("name", "=", row["name"]), ("parent_id", "=", parent.id)], limit=1
        ) or categories.create({"name": row["name"], "parent_id": parent.id})
        mapping[row["id"]] = category.id
    _record_map(cr, "fleet.vehicle.model.category", "product.category", mapping)
    return mapping


def _migrate_models(env, brands, categories):
    cr = env.cr
    kind = env.ref("resource_asset.kind_vehicle")
    years = {
        value
        for value, _label in env["product.template"]._selection_vehicle_model_years()
    }
    specs = env["product.template"]._fields
    mapping = {}
    for row in _select(
        cr,
        "fleet_vehicle_model",
        ["id", "name", "brand_id", "category_id", "active", *MODEL_SPEC_COLUMNS],
    ):
        reloaded = _reloaded_record(
            env, cr, "fleet.vehicle.model", row["id"], "product.product"
        )
        if reloaded:
            mapping[row["id"]] = reloaded.id
            continue
        vals = {
            "name": _translated(row["name"]),
            "type": "consu",
            "sale_ok": False,
            "asset_kind_id": kind.id,
            "manufacturer_id": brands.get(row.get("brand_id")) or False,
            "active": row.get("active", True),
        }
        if categories.get(row.get("category_id")):
            vals["categ_id"] = categories[row["category_id"]]
        for column, field_name in MODEL_SPEC_COLUMNS.items():
            value = row.get(column)
            if value in (None, False, ""):
                continue
            if field_name == "vehicle_model_year" and str(value) not in years:
                continue
            field = specs[field_name]
            if field.type == "selection" and not isinstance(field.selection, str):
                if value not in dict(field.selection):
                    continue
            vals[field_name] = (
                str(value) if field_name == "vehicle_model_year" else value
            )
        mapping[row["id"]] = env["product.product"].create(vals).id
    _record_map(cr, "fleet.vehicle.model", "product.product", mapping)
    return mapping


def _migrate_service_types(env):
    cr = env.cr
    category = env.ref("fleet.product_category_vehicle_services")
    mapping = {}
    for row in _select(cr, "fleet_service_type", ["id", "name", "category"]):
        if row.get("category") != "service":
            continue
        reloaded = _reloaded_record(
            env, cr, "fleet.service.type", row["id"], "product.product"
        )
        if reloaded:
            mapping[row["id"]] = reloaded.id
            continue
        mapping[row["id"]] = (
            env["product.product"]
            .create(
                {
                    "name": _translated(row["name"]),
                    "type": "service",
                    "sale_ok": False,
                    "categ_id": category.id,
                }
            )
            .id
        )
    _record_map(cr, "fleet.service.type", "product.product", mapping)
    return mapping


def _state_by_state_id(cr):
    cr.execute(
        """
        SELECT res_id, name FROM ir_model_data
         WHERE model = 'fleet.vehicle.state'
        """
    )
    return {
        res_id: STATE_BY_XMLID[name]
        for res_id, name in cr.fetchall()
        if name in STATE_BY_XMLID
    }


def _migrate_vehicles(env, products):
    cr = env.cr
    kind = env.ref("resource_asset.kind_vehicle")
    kilometer = env.ref("uom.product_uom_km", raise_if_not_found=False)
    mile = env.ref("uom.product_uom_mile", raise_if_not_found=False)
    states = _state_by_state_id(cr)
    assets = env["resource.asset"]
    mapping = {}
    for row in _select(
        cr,
        "fleet_vehicle",
        [
            "id",
            "name",
            "license_plate",
            "vin_sn",
            "model_id",
            "company_id",
            "active",
            "acquisition_date",
            "write_off_date",
            "state_id",
            "description",
            "manager_id",
            "odometer_unit",
            "location",
        ],
    ):
        reloaded = _reloaded_record(
            env, cr, "fleet.vehicle", row["id"], "resource.asset"
        )
        if reloaded:
            mapping[row["id"]] = reloaded.id
            continue
        state = states.get(row.get("state_id"), "in_service")
        disposal = row.get("write_off_date")
        if state == "disposed" and not disposal:
            disposal = fields.Date.context_today(assets)
        description = row.get("description") or ""
        if row.get("location"):
            description = f"{description}<p>{row['location']}</p>"
        vals = {
            "name": row.get("license_plate")
            or _translated(row.get("name"))
            or "Vehicle",
            "kind_id": kind.id,
            "product_id": products.get(row.get("model_id")) or False,
            "company_id": row.get("company_id") or False,
            "date_acquisition": row.get("acquisition_date"),
            "date_disposal": disposal,
            "state": state,
            "description": description or False,
            "manager_id": row.get("manager_id") or False,
            "odometer_uom_id": (
                mile if row.get("odometer_unit") == "miles" else kilometer
            ).id
            if kilometer
            else False,
        }
        asset = assets.create(vals)
        for field_name in ("license_plate", "vin_sn"):
            if not row.get(field_name):
                continue
            try:
                with cr.savepoint():
                    asset[field_name] = row[field_name]
                    asset.flush_recordset()
            except Exception as error:
                _logger.warning(
                    "Vehicle %s: %s %r not kept on asset %s: %s",
                    row["id"],
                    field_name,
                    row[field_name],
                    asset.id,
                    error,
                )
                asset.invalidate_recordset()
        if not row.get("active", True):
            asset.active = False
        mapping[row["id"]] = asset.id
    _record_map(cr, "fleet.vehicle", "resource.asset", mapping)
    return mapping


def _migrate_tags(cr, vehicles):
    if not table_exists(cr, "fleet_vehicle_vehicle_tag_rel"):
        return
    cr.execute("SELECT vehicle_tag_id, tag_id FROM fleet_vehicle_vehicle_tag_rel")
    for vehicle_id, tag_id in cr.fetchall():
        if vehicle_id in vehicles:
            cr.execute(
                """
                INSERT INTO resource_asset_fleet_vehicle_tag_rel (asset_id, tag_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                [vehicles[vehicle_id], tag_id],
            )


def _migrate_odometers(env, vehicles):
    cr = env.cr
    readings = env["resource.asset.meter.reading"].with_context(
        skip_meter_monotonic=True
    )
    meters = {}
    for row in _select(
        cr, "fleet_vehicle_odometer", ["id", "vehicle_id", "date", "value"]
    ):
        asset_id = vehicles.get(row["vehicle_id"])
        if not asset_id or row.get("value") is None or row["value"] < 0:
            continue
        if asset_id not in meters:
            asset = env["resource.asset"].browse(asset_id)
            meters[asset_id] = asset.odometer_meter_id or env[
                "resource.asset.meter"
            ].create(
                {
                    "asset_id": asset_id,
                    "name": "Odometer",
                    "kind": "odometer",
                    "uom_id": asset.odometer_uom_id.id,
                    "monotonic": True,
                }
            )
        readings.create(
            {
                "meter_id": meters[asset_id].id,
                "value": row["value"],
                "date": _as_datetime(row.get("date"), fields.Datetime.now()),
                "source": "manual",
            }
        )


def _get_driver_resource(env, partner_id, company_id, cache):
    key = (partner_id, company_id)
    if key in cache:
        return cache[key]
    partner = env["res.partner"].browse(partner_id)
    resources = env["resource.resource"]
    if hasattr(partner, "_get_or_create_resources"):
        resource = partner._get_or_create_resources(
            env["res.company"].browse(company_id)
        )
    else:
        resource = resources.search(
            [
                ("partner_id", "=", partner_id),
                ("resource_type", "=", "user"),
                ("company_id", "=", company_id),
            ],
            limit=1,
        ) or resources.create(
            {
                "name": partner.name,
                "partner_id": partner_id,
                "resource_type": "user",
                "company_id": company_id,
            }
        )
    cache[key] = resource
    return resource


def _migrate_drivers(env, vehicles):
    cr = env.cr
    now = fields.Datetime.now()
    cache = {}
    assignments = env["resource.assignment"]
    rows = {
        row["id"]: row
        for row in _select(
            cr,
            "fleet_vehicle",
            [
                "id",
                "company_id",
                "driver_id",
                "future_driver_id",
                "next_assignation_date",
                "acquisition_date",
                "create_date",
            ],
        )
    }
    for log in _select(
        cr,
        "fleet_vehicle_assignation_log",
        ["id", "vehicle_id", "driver_id", "date_start", "date_end"],
    ):
        vehicle = rows.get(log["vehicle_id"])
        if not vehicle or log["vehicle_id"] not in vehicles or not log.get("driver_id"):
            continue
        asset = env["resource.asset"].browse(vehicles[log["vehicle_id"]])
        start = _as_datetime(log.get("date_start")) or _as_datetime(
            vehicle.get("acquisition_date"), vehicle.get("create_date") or now
        )
        end = _as_datetime(log.get("date_end"))
        if end and end < start:
            end = start
        try:
            with cr.savepoint():
                assignments.create(
                    {
                        "resource_id": asset.resource_id.id,
                        "assignee_id": _get_driver_resource(
                            env,
                            log["driver_id"],
                            vehicle.get("company_id") or False,
                            cache,
                        ).id,
                        "role": "driver",
                        "date_start": start,
                        "date_end": end,
                    }
                )
        except Exception as error:
            _logger.warning("Driver log %s not migrated: %s", log["id"], error)
    for vehicle_id, asset_id in vehicles.items():
        vehicle = rows[vehicle_id]
        asset = env["resource.asset"].browse(asset_id)
        asset.invalidate_recordset()
        company_id = vehicle.get("company_id") or False
        if vehicle.get("driver_id"):
            resource = _get_driver_resource(
                env, vehicle["driver_id"], company_id, cache
            )
            if asset.driver_id != resource:
                asset.driver_id = resource
        if vehicle.get("future_driver_id"):
            resource = _get_driver_resource(
                env, vehicle["future_driver_id"], company_id, cache
            )
            start = _as_datetime(vehicle.get("next_assignation_date"))
            asset.write(
                {
                    "future_driver_id": resource.id,
                    "next_assignation_date": start
                    if start and start > now
                    else now + timedelta(days=7),
                }
            )


def _migrate_services(env, vehicles, services):
    cr = env.cr
    fallback = env.ref("fleet.product_product_vehicle_service")
    logs = env["resource.asset.log"]
    mapping = {}
    for row in _select(
        cr,
        "fleet_vehicle_log_services",
        [
            "id",
            "vehicle_id",
            "service_type_id",
            "amount",
            "date",
            "vendor_id",
            "inv_ref",
            "notes",
            "description",
            "state",
            "active",
        ],
    ):
        asset_id = vehicles.get(row.get("vehicle_id"))
        if not asset_id:
            continue
        notes = "\n".join(
            part for part in (row.get("description"), row.get("notes")) if part
        )
        state = row.get("state") or "done"
        log = logs.create(
            {
                "asset_id": asset_id,
                "product_id": services.get(row.get("service_type_id")) or fallback.id,
                "log_type": "service",
                "amount": row.get("amount") or 0.0,
                "date": row.get("date"),
                "vendor_id": row.get("vendor_id") or False,
                "inv_ref": row.get("inv_ref") or False,
                "notes": notes or False,
                "state": "new" if state == "cancelled" else state,
            }
        )
        if state == "cancelled":
            log.state = "cancelled"
        if row.get("active") is False:
            log.active = False
        mapping[row["id"]] = log.id
    _record_map(cr, "fleet.vehicle.log.services", "resource.asset.log", mapping)
    return mapping


def _note_contracts(env, vehicles):
    cr = env.cr
    if not table_exists(cr, "fleet_vehicle_log_contract"):
        return
    for row in _select(
        cr,
        "fleet_vehicle_log_contract",
        [
            "id",
            "vehicle_id",
            "name",
            "start_date",
            "expiration_date",
            "amount",
            "cost_generated",
            "state",
        ],
    ):
        asset_id = vehicles.get(row.get("vehicle_id"))
        if not asset_id:
            continue
        env["resource.asset"].browse(asset_id).message_post(
            body=env._(
                "Contract %(name)s (%(state)s), %(start)s to %(end)s: activation cost %(amount)s, recurring cost %(recurring)s. Fleet no longer tracks contracts; file it as a document of this vehicle.",
                name=_translated(row.get("name")) or row["id"],
                state=row.get("state") or "",
                start=row.get("start_date") or "",
                end=row.get("expiration_date") or "",
                amount=row.get("amount") or 0,
                recurring=row.get("cost_generated") or 0,
            )
        )


def _repoint(cr, model, new_model, mapping):
    if not mapping:
        return
    pairs = list(mapping.items())
    for table, model_column in (
        ("ir_model_data", "model"),
        ("mail_message", "model"),
        ("mail_followers", "res_model"),
        ("mail_activity", "res_model"),
        ("ir_attachment", "res_model"),
    ):
        if not table_exists(cr, table):
            continue
        cr.execute(
            f"""
            UPDATE {table} target
               SET {model_column} = %s, res_id = mapped.new_id
              FROM (SELECT unnest(%s::int[]) AS old_id, unnest(%s::int[]) AS new_id) mapped
             WHERE target.{model_column} = %s
               AND target.res_id = mapped.old_id
            """,
            [
                new_model,
                [old for old, _new in pairs],
                [new for _old, new in pairs],
                model,
            ],
        )
    cr.execute(
        """
        DELETE FROM ir_model_data target
         USING ir_model_data reloaded
         WHERE target.module = 'fleet'
           AND target.name LIKE 'legacy\\_%'
           AND reloaded.module = 'fleet'
           AND reloaded.name = substr(target.name, 8)
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = substr(name, 8)
         WHERE module = 'fleet' AND model = %s AND name LIKE 'legacy\\_%%'
        """,
        [new_model],
    )
    cr.execute("DELETE FROM ir_model_data WHERE model = %s", [model])
