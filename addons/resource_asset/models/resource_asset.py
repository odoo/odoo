from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.tools.translate import html_translate

CUSTODY_SILENT = "custody_silent"
OPERATOR_ROLE = "operator"
MANAGER_ROLE = "manager"
CUSTODY_ROLE_BY_FIELD = {"operator_id": OPERATOR_ROLE, "manager_id": MANAGER_ROLE}
DEFAULT_HANDOVER_DELAY = timedelta(days=7)

IDENTIFIER_CODE_BY_FIELD = {
    "license_plate": "plate",
    "vin_sn": "vin",
    "engine_sn": "engine",
    "cadastral_id": "cadastral",
    "imei": "imei",
}


class ResourceAsset(models.Model):
    _name = "resource.asset"
    _description = "Asset"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.avatar",
        "mixin.resource",
    ]
    _order = "name, id"
    _check_company_auto = True

    name = fields.Char(
        related="resource_id.name",
        store=True,
        readonly=False,
    )
    active = fields.Boolean(
        related="resource_id.active",
        default=True,
        store=True,
        readonly=False,
    )
    color = fields.Integer(
        related="resource_id.color",
        readonly=False,
    )
    kind_id = fields.Many2one(
        comodel_name="resource.asset.kind",
        index=True,
        required=True,
        ondelete="restrict",
    )
    kind_code = fields.Char(related="kind_id.code")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_service", "In Service"),
            ("maintenance", "Under Maintenance"),
            ("out_of_service", "Out of Service"),
            ("disposed", "Disposed"),
        ],
        default="draft",
        index=True,
        required=True,
        tracking=True,
    )
    date_acquisition = fields.Date(tracking=True)
    date_disposal = fields.Date(tracking=True)
    brand_new = fields.Boolean(default=True)
    model = fields.Char(string="Model Name")
    model_year = fields.Char()
    description = fields.Html(translate=html_translate)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        index="btree_not_null",
        check_company=True,
        tracking=True,
    )
    partner_ref = fields.Char(string="Vendor Reference")
    warranty_date = fields.Date(string="Warranty Expiration Date")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
    )
    value_original = fields.Monetary(
        string="Original Value",
        copy=False,
        tracking=True,
    )
    asset_properties = fields.Properties(
        definition="kind_id.asset_properties_definition",
        copy=True,
    )

    identifier_ids = fields.One2many(
        comodel_name="resource.asset.identifier",
        inverse_name="asset_id",
    )
    license_plate = fields.Char(
        compute="_compute_identifier_columns",
        inverse="_inverse_identifier_columns",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
        help="License plate number of the asset (eg plate number for a car)",
    )
    vin_sn = fields.Char(
        string="Serial Number / VIN",
        compute="_compute_identifier_columns",
        inverse="_inverse_identifier_columns",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
        help="Unique number written on an asset's chassis (VIN/SN number).",
    )
    engine_sn = fields.Char(
        string="Engine Serial Number",
        compute="_compute_identifier_columns",
        inverse="_inverse_identifier_columns",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
        help="Unique number written on the asset's engine.",
    )
    cadastral_id = fields.Char(
        string="Cadastral ID",
        compute="_compute_identifier_columns",
        inverse="_inverse_identifier_columns",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
        help="Government-assigned parcel identifier for real estate assets.",
    )
    imei = fields.Char(
        string="IMEI",
        compute="_compute_identifier_columns",
        inverse="_inverse_identifier_columns",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
        help="International Mobile Equipment Identity of a cellular-capable asset.",
    )
    missing_identifier_type_ids = fields.Many2many(
        comodel_name="resource.asset.identifier.type",
        compute="_compute_missing_identifier_type_ids",
        search="_search_missing_identifier_type_ids",
    )
    meter_ids = fields.One2many(
        comodel_name="resource.asset.meter",
        inverse_name="asset_id",
    )
    odometer_meter_id = fields.Many2one(
        comodel_name="resource.asset.meter",
        compute="_compute_odometer_meter_id",
        store=True,
    )
    odometer = fields.Float(
        compute="_compute_odometer",
        inverse="_inverse_odometer",
        store=True,
        readonly=False,
    )
    odometer_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        tracking=True,
        help="Unit of measurement for the odometer readings",
    )
    odometer_uom_name = fields.Char(
        related="odometer_uom_id.display_name",
        string="Odometer Unit",
    )
    address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Location",
        help="Where the asset normally is, when no inventory location tracks it.",
    )
    assignment_ids = fields.One2many(related="resource_id.assignment_ids")
    holder_id = fields.Many2one(related="resource_id.holder_id")
    operator_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Operator",
        compute="_compute_custody",
        inverse="_inverse_operator_id",
        search="_search_operator_id",
        domain="[('resource_type', '=', 'user'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Who operates the asset now: the live operator assignment.",
    )
    manager_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Manager",
        compute="_compute_custody",
        inverse="_inverse_manager_id",
        search="_search_manager_id",
        domain="[('resource_type', '=', 'user'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Who answers for the asset: the live manager assignment.",
    )
    future_operator_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Future Operator",
        compute="_compute_future_operator",
        inverse="_inverse_future_operator",
        search="_search_future_operator_id",
        domain="[('resource_type', '=', 'user'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Who takes the asset over next: the planned operator assignment.",
    )
    date_future_operator = fields.Datetime(
        string="Hand-over Date",
        compute="_compute_future_operator",
        inverse="_inverse_future_operator",
        help="When the next operator takes over. A hand-over without a date takes effect in a week unless accepted before.",
    )
    operator_history_count = fields.Integer(compute="_compute_operator_history_count")
    parent_id = fields.Many2one(
        comodel_name="resource.asset",
        string="Part Of",
        index=True,
        ondelete="restrict",
    )
    child_ids = fields.One2many(
        comodel_name="resource.asset",
        inverse_name="parent_id",
        string="Components",
    )

    _resource_uniq = models.Constraint(
        "UNIQUE(resource_id)", "A resource is one asset at most."
    )
    _check_dates = models.Constraint(
        "CHECK(date_disposal IS NULL OR date_acquisition IS NULL OR date_disposal >= date_acquisition)",
        "An asset cannot be disposed of before it was acquired.",
    )

    @api.depends("company_id")
    def _compute_currency_id(self):
        fallback = self.env.company.currency_id
        for asset in self:
            asset.currency_id = asset.company_id.currency_id or fallback

    @api.depends("meter_ids.kind")
    def _compute_odometer_meter_id(self):
        for asset in self:
            asset.odometer_meter_id = asset.meter_ids.filtered(
                lambda m: m.kind == "odometer"
            )[:1]

    @api.depends("odometer_meter_id.last_reading_id.value")
    def _compute_odometer(self):
        for asset in self:
            asset.odometer = asset.odometer_meter_id.value

    def _inverse_odometer(self):
        for asset in self:
            meter = asset.odometer_meter_id
            if not asset.odometer and not meter:
                continue
            if not meter:
                meter = asset._create_odometer_meter()
            if meter.value > asset.odometer:
                raise ValidationError(
                    self.env._(
                        "%(asset)s: the odometer cannot go below its last reading of %(value)s.",
                        asset=asset.display_name,
                        value=meter.value,
                    )
                )
            if meter.value != asset.odometer:
                meter.record(asset.odometer)

    def _create_odometer_meter(self):
        self.check_singleton()
        meter = self.env["resource.asset.meter"].create(
            {
                "asset_id": self.id,
                "name": self.env._("Odometer"),
                "kind": "odometer",
                "uom_id": self.odometer_uom_id.id,
            }
        )
        self.invalidate_recordset(["odometer_meter_id"])
        return meter

    def _check_odometer_uom_is_not_reinterpreted(self, new_uom_id):
        """Every reading the meter holds is a number in the asset's unit, and
        nothing stores which unit it was taken in. Changing the unit therefore
        restates the whole history rather than converting it."""
        changing = self.filtered(lambda asset: asset.odometer_uom_id.id != new_uom_id)
        with_readings = changing.sudo().filtered(
            lambda asset: asset.odometer_meter_id.reading_ids
        )
        if with_readings:
            raise ValidationError(
                self.env._(
                    "%(assets)s already carry odometer readings in their current "
                    "unit. Changing it now would restate every one of them; "
                    "convert the readings deliberately instead.",
                    assets=", ".join(with_readings.mapped("display_name")),
                )
            )

    @api.depends("identifier_ids.value", "identifier_ids.type_id")
    def _compute_identifier_columns(self):
        for asset in self:
            by_code = {i.type_id.code: i.value for i in asset.identifier_ids}
            for field_name, code in IDENTIFIER_CODE_BY_FIELD.items():
                asset[field_name] = by_code.get(code, False)

    def _inverse_identifier_columns(self):
        types = {
            identifier_type.code: identifier_type
            for identifier_type in self.env["resource.asset.identifier.type"]
            .sudo()
            .search([("code", "in", list(IDENTIFIER_CODE_BY_FIELD.values()))])
        }
        identifier_model = self.env["resource.asset.identifier"].sudo()
        for asset in self:
            by_type = {i.type_id: i for i in asset.sudo().identifier_ids}
            for field_name, code in IDENTIFIER_CODE_BY_FIELD.items():
                identifier_type = types.get(code)
                if not identifier_type:
                    continue
                value = asset[field_name]
                current = by_type.get(identifier_type)
                if value and current and current.value != value:
                    current.value = value
                elif value and not current:
                    identifier_model.create(
                        {
                            "asset_id": asset.id,
                            "type_id": identifier_type.id,
                            "value": value,
                        }
                    )
                elif not value and current:
                    current.unlink()

    @api.depends("identifier_ids.type_id", "kind_id.identifier_type_ids")
    def _compute_missing_identifier_type_ids(self):
        for asset in self:
            asset.missing_identifier_type_ids = (
                asset.kind_id.identifier_type_ids - asset.identifier_ids.type_id
            )

    def _search_missing_identifier_type_ids(self, operator, value):
        if operator in ("any", "not any"):
            type_query = self.env["resource.asset.identifier.type"]._search(value)
            domain = self._get_missing_identifier_domain(
                SQL("rel.type_id IN %s", type_query.subselect())
            )
        elif operator in ("in", "not in"):
            type_ids = [type_id for type_id in value if type_id]
            domain = Domain.FALSE
            if type_ids:
                domain |= self._get_missing_identifier_domain(
                    SQL("rel.type_id = ANY(%s)", type_ids)
                )
            if len(type_ids) < len(value):
                domain |= ~self._get_missing_identifier_domain()
        else:
            return NotImplemented
        return ~domain if operator.startswith("not") else domain

    @api.model
    def _get_missing_identifier_domain(self, type_condition=None):
        def to_sql(model, alias, query):
            return SQL(
                """
                EXISTS (
                    SELECT 1
                      FROM resource_asset_kind_identifier_type_rel rel
                     WHERE rel.kind_id = %(kind)s
                       AND %(types)s
                       AND NOT EXISTS (
                           SELECT 1
                             FROM resource_asset_identifier identifier
                            WHERE identifier.asset_id = %(asset)s
                              AND identifier.type_id = rel.type_id
                       )
                )
                """,
                kind=SQL.identifier(alias, "kind_id"),
                asset=SQL.identifier(alias, "id"),
                types=type_condition or SQL("TRUE"),
            )

        return Domain.custom(to_sql=to_sql)

    @api.constrains("parent_id")
    def _check_parent(self):
        if self._has_cycle():
            raise ValidationError(self.env._("An asset cannot be a part of itself."))

    @api.constrains("state", "date_disposal")
    def _check_disposal(self):
        for asset in self:
            if asset.state == "disposed" and not asset.date_disposal:
                raise ValidationError(
                    self.env._(
                        "%(name)s: a disposed asset needs its disposal date.",
                        name=asset.name,
                    )
                )

    def _around_the_clock(self, vals):
        """No calendar: an unscheduled kind is available around the clock, and a
        shared (company-less) asset of a scheduled kind cannot take one
        company's hours -- every reader would then see a company crossover."""
        if "resource_calendar_id" in vals:
            return False
        kind = self.env["resource.asset.kind"].browse(vals.get("kind_id"))
        shared = "company_id" in vals and not vals["company_id"]
        return not kind.scheduled or shared

    def _prepare_resource_values(self, vals, tz):
        resource_vals = super()._prepare_resource_values(vals, tz)
        resource_vals["resource_type"] = "material"
        if self._around_the_clock(vals):
            resource_vals["calendar_id"] = False
        return resource_vals

    @api.model_create_multi
    def create(self, vals_list):
        Resource = self.env["resource.resource"].sudo()
        resource_vals_list = []
        for vals in vals_list:
            if vals.get("kind_id") and self._around_the_clock(vals):
                vals["resource_calendar_id"] = False
            if not vals.get("resource_id"):
                vals["resource_id"] = Resource.create(
                    self._prepare_resource_values(vals, vals.pop("tz", False))
                ).id
            resource_vals_list.append(self._pop_resource_vals(vals))
        assets = super().create(vals_list)
        for asset, resource_vals in zip(assets, resource_vals_list, strict=True):
            if resource_vals:
                asset.resource_id.sudo().write(resource_vals)
        return assets

    def _pop_resource_vals(self, vals):
        resource_vals = {}
        for name in list(vals):
            field = self._fields.get(name)
            path = field.related.split(".") if field and field.related else ()
            if len(path) == 2 and path[0] == "resource_id":
                resource_vals[path[1]] = vals.pop(name)
        return resource_vals

    def write(self, vals):
        if "odometer_uom_id" in vals:
            self._check_odometer_uom_is_not_reinterpreted(vals["odometer_uom_id"])
        if "active" in vals and not vals["active"]:
            now = fields.Datetime.now()
            self._end_custody(
                self.resource_id.assignment_ids.filtered(
                    lambda a: not a.date_end or a.date_end > now
                ),
                now,
            )
        if vals.get("active") and "state" not in vals:
            disposed = self.filtered(lambda asset: asset.state == "disposed")
            if disposed:
                disposed._write_through_resource(
                    {**vals, "state": "out_of_service", "date_disposal": False}
                )
                return (self - disposed)._write_through_resource(vals)
        return self._write_through_resource(vals)

    def _write_through_resource(self, vals):
        vals = dict(vals)
        resource_vals = self._pop_resource_vals(vals)
        if resource_vals and self:
            self.check_access("write")
            self.resource_id.sudo().write(resource_vals)
        if not vals:
            return True
        return super().write(vals)

    def _get_custody_assignments(self, role, planned=False, archived=False):
        if not self.ids:
            return self.env["resource.assignment"]
        now = fields.Datetime.now()
        domain = Domain("resource_id", "in", self.sudo().resource_id.ids) & Domain(
            "custody_role", "=", role
        )
        if planned:
            domain &= Domain("date_start", ">", now) & Domain("date_end", "=", False)
        else:
            domain &= Domain("date_start", "<=", now) & (
                Domain("date_end", "=", False) | Domain("date_end", ">", now)
            )
        assignments = self.env["resource.assignment"].sudo()
        if archived:
            # An archived row is invisible to a search and still holds the
            # asset: unarchiving it would bring back a second holder.
            assignments = assignments.with_context(active_test=False)
        return assignments.search(domain)

    def _first_by_asset(self, assignments, reverse):
        asset_by_resource = {asset.sudo().resource_id.id: asset for asset in self}
        first = {}
        for assignment in assignments.sorted("date_start", reverse=reverse):
            asset = asset_by_resource.get(assignment.resource_id.id)
            if asset:
                first.setdefault(asset.id, assignment)
        return first

    @api.depends(
        "resource_id.assignment_ids.assignee_id",
        "resource_id.assignment_ids.custody_role",
        "resource_id.assignment_ids.date_start",
        "resource_id.assignment_ids.date_end",
        "resource_id.assignment_ids.active",
    )
    def _compute_custody(self):
        for field_name, role in CUSTODY_ROLE_BY_FIELD.items():
            live = self._first_by_asset(
                self._get_custody_assignments(role), reverse=True
            )
            for asset in self:
                assignment = live.get(asset.id)
                asset[field_name] = assignment.assignee_id if assignment else False

    @api.depends(
        "resource_id.assignment_ids.assignee_id",
        "resource_id.assignment_ids.custody_role",
        "resource_id.assignment_ids.date_start",
        "resource_id.assignment_ids.date_end",
        "resource_id.assignment_ids.active",
    )
    def _compute_future_operator(self):
        planned = self._first_by_asset(
            self._get_custody_assignments(OPERATOR_ROLE, planned=True), reverse=False
        )
        for asset in self:
            assignment = planned.get(asset.id)
            asset.future_operator_id = assignment.assignee_id if assignment else False
            asset.date_future_operator = assignment.date_start if assignment else False

    def _compute_operator_history_count(self):
        counts = dict(
            self.env["resource.assignment"]._read_group(
                [
                    ("resource_id", "in", self.resource_id.ids),
                    ("custody_role", "=", OPERATOR_ROLE),
                ],
                ["resource_id"],
                ["__count"],
            )
        )
        for asset in self:
            asset.operator_history_count = counts.get(asset.resource_id, 0)

    def _search_custody(self, role, operator, value, planned=False):
        now = fields.Datetime.now()
        if planned:
            window = Domain("date_start", ">", now) & Domain("date_end", "=", False)
        else:
            window = Domain("date_start", "<=", now) & (
                Domain("date_end", "=", False) | Domain("date_end", ">", now)
            )
        live = Domain("custody_role", "=", role) & window
        if operator in ("in", "not in"):
            ids = [value] if isinstance(value, (int, bool)) else list(value)
            resource_ids = [i for i in ids if i]
            wants_empty = len(resource_ids) < len(ids)
        elif operator in ("ilike", "not ilike", "=ilike", "like", "=like"):
            resource_ids = (
                self.env["resource.resource"]
                .with_context(active_test=False)
                ._search([("name", operator.removeprefix("not "), value)])
            )
            wants_empty = False
        else:
            return NotImplemented
        domain = Domain(
            "resource_id.assignment_ids",
            "any",
            live & Domain("assignee_id", "in", resource_ids),
        )
        if wants_empty:
            domain |= ~Domain("resource_id.assignment_ids", "any", live)
        return ~domain if operator.startswith("not") else domain

    def _search_operator_id(self, operator, value):
        return self._search_custody(OPERATOR_ROLE, operator, value)

    def _search_manager_id(self, operator, value):
        return self._search_custody(MANAGER_ROLE, operator, value)

    def _search_future_operator_id(self, operator, value):
        return self._search_custody(OPERATOR_ROLE, operator, value, planned=True)

    def _inverse_operator_id(self):
        self._sync_custody("operator_id")

    def _inverse_manager_id(self):
        self._sync_custody("manager_id")

    def _sync_custody(self, field_name):
        """Write the holder of one role into resource.assignment, and answer
        the assets whose holder actually changed, for whoever records it."""
        role = CUSTODY_ROLE_BY_FIELD[field_name]
        now = fields.Datetime.now()
        live = self._get_custody_assignments(role, archived=True)
        live_by_resource = defaultdict(live.browse)
        for assignment in live:
            live_by_resource[assignment.resource_id.id] |= assignment
        new_vals_list = []
        changed = self.browse()
        for asset in self:
            resource = asset.sudo().resource_id
            current = live_by_resource[resource.id]
            holder = asset[field_name]
            if holder and current.assignee_id == holder:
                continue
            if not holder and not current:
                continue
            previous = current.assignee_id[:1]
            self._end_custody(current, now)
            if holder:
                new_vals_list.append(
                    {
                        "resource_id": resource.id,
                        "assignee_id": holder.id,
                        "custody_role": role,
                        "date_start": now,
                    }
                )
            changed |= asset
            asset._post_custody_message(role, previous, holder)
        if new_vals_list:
            # The rivals are ended above; the create hook has nothing to supersede.
            self.env["resource.assignment"].sudo().with_context(
                custody_sync=True
            ).create(new_vals_list)
        return changed

    def _inverse_future_operator(self):
        now = fields.Datetime.now()
        planned = self._get_custody_assignments(OPERATOR_ROLE, planned=True)
        planned_by_resource = defaultdict(planned.browse)
        for assignment in planned:
            planned_by_resource[assignment.resource_id.id] |= assignment
        new_vals_list = []
        for asset in self:
            resource = asset.sudo().resource_id
            rows = planned_by_resource[resource.id]
            date_start = asset.date_future_operator or now + DEFAULT_HANDOVER_DELAY
            current = rows.sorted("date_start")[:1]
            if (
                asset.future_operator_id
                and current.assignee_id == asset.future_operator_id
                and current.date_start == date_start
            ):
                continue
            self._end_custody(rows, now)
            if asset.future_operator_id:
                if date_start <= now:
                    raise UserError(
                        self.env._("A scheduled hand-over must start in the future.")
                    )
                new_vals_list.append(
                    {
                        "resource_id": resource.id,
                        "assignee_id": asset.future_operator_id.id,
                        "custody_role": OPERATOR_ROLE,
                        "date_start": date_start,
                    }
                )
                if self.env.context.get(CUSTODY_SILENT):
                    continue
                subtype = self.env.ref(
                    "resource_asset.mt_asset_future_operator_scheduled",
                    raise_if_not_found=False,
                )
                asset.sudo().message_post(
                    body=self.env._(
                        "Scheduled operator: %(before)s → %(after)s",
                        before=current.assignee_id.sudo().name or "—",
                        after=asset.future_operator_id.sudo().name,
                    ),
                    subtype_id=subtype.id if subtype else None,
                )
        if new_vals_list:
            self.env["resource.assignment"].sudo().create(new_vals_list)

    def _get_custody_message(self, role, before, after):
        names = {
            "before": before.sudo().name or "—",
            "after": after.sudo().name or "—",
        }
        if role == MANAGER_ROLE:
            return self.env._("Manager: %(before)s → %(after)s", **names)
        return self.env._("Operator: %(before)s → %(after)s", **names)

    def _post_custody_message(self, role, before, after):
        self.check_singleton()
        if before == after or self.env.context.get(CUSTODY_SILENT):
            return
        subtype = self.env.ref(
            "resource_asset.mt_asset_operator_updated", raise_if_not_found=False
        )
        self.sudo().message_post(
            body=self._get_custody_message(role, before, after),
            subtype_id=subtype.id if subtype else None,
        )

    def _get_assets_released_by_operator_change(self):
        return self.search(
            [
                ("kind_id", "in", self.kind_id.ids),
                ("operator_id", "in", self.future_operator_id.ids),
                ("id", "not in", self.ids),
            ]
        )

    def action_accept_operator_change(self):
        assets = self.filtered("future_operator_id")
        assets._get_assets_released_by_operator_change().operator_id = False
        now = fields.Datetime.now()
        for asset in assets:
            planned = asset._get_custody_assignments(
                OPERATOR_ROLE, planned=True
            ).sorted("date_start")[:1]
            previous = asset.operator_id
            self._end_custody(asset._get_custody_assignments(OPERATOR_ROLE), now)
            planned.date_start = now
            asset.invalidate_recordset(
                ["operator_id", "future_operator_id", "date_future_operator"]
            )
            asset._post_custody_message(OPERATOR_ROLE, previous, asset.operator_id)

    def action_view_operator_history(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Operators"),
            "view_mode": "list,form",
            "res_model": "resource.assignment",
            "domain": [
                ("resource_id", "=", self.resource_id.id),
                ("custody_role", "=", OPERATOR_ROLE),
            ],
            "context": {
                "default_resource_id": self.resource_id.id,
                "default_role": OPERATOR_ROLE,
                "active_test": False,
            },
        }

    @api.model
    def _search_live_custody(self, resources):
        """Every custody assignment on those resources that has not ended.

        Wider than `date_end = False`: a row ending in the future is still live,
        and an archived one still holds its resource, so both are superseded
        like an open one rather than left as rivals.
        """
        if not resources:
            return self.env["resource.assignment"]
        now = fields.Datetime.now()
        return (
            self.env["resource.assignment"]
            .sudo()
            .with_context(active_test=False)
            .search(
                Domain("resource_id", "in", resources.ids)
                & Domain("custody_role", "in", list(CUSTODY_ROLE_BY_FIELD.values()))
                & Domain("date_start", "<=", now)
                & (Domain("date_end", "=", False) | Domain("date_end", ">", now))
            )
        )

    @api.model
    def _close_custody(self, resources):
        """End every custody assignment on those resources: what they held is
        no longer theirs to hold."""
        self._end_custody(self._search_live_custody(resources))

    @api.model
    def _end_custody(self, assignments, now=None):
        now = now or fields.Datetime.now()
        started = assignments.filtered(lambda a: a.date_start <= now)
        started.write({"date_end": now})
        for planned in assignments - started:
            planned.date_end = planned.date_start

    def action_set_in_service(self):
        self.write({"state": "in_service"})

    def action_set_maintenance(self):
        self.write({"state": "maintenance"})

    def action_set_out_of_service(self):
        self.write({"state": "out_of_service"})

    def action_dispose(self):
        return self._dispose()

    def _dispose(self, date=None):
        self.write(
            {
                "state": "disposed",
                "date_disposal": date or fields.Date.context_today(self),
                "active": False,
            }
        )

    def get_identifier(self, code):
        self.check_singleton()
        return self.identifier_ids.filtered(lambda i: i.type_id.code == code)[:1].value

    def get_meter(self, kind):
        self.check_singleton()
        return self.meter_ids.filtered(lambda m: m.kind == kind)[:1]

    def _get_holder(self, custody_role=None, at=None):
        self.check_singleton()
        return self.env["resource.assignment"]._get_holder(
            self.resource_id, custody_role=custody_role, at=at
        )

    def _search_domain_of_kind(self, code):
        return Domain("kind_id.code", "=", code)
