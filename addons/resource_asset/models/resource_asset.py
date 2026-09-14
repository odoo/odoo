from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


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
    model_year = fields.Char()
    description = fields.Html()

    identifier_ids = fields.One2many(
        comodel_name="resource.asset.identifier",
        inverse_name="asset_id",
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
    address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Location",
        help="Where the asset normally is, when no inventory location tracks it.",
    )
    assignment_ids = fields.One2many(related="resource_id.assignment_ids")
    holder_id = fields.Many2one(related="resource_id.holder_id")
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

    @api.depends("identifier_ids.type_id", "kind_id.identifier_type_ids")
    def _compute_missing_identifier_type_ids(self):
        for asset in self:
            asset.missing_identifier_type_ids = (
                asset.kind_id.identifier_type_ids - asset.identifier_ids.type_id
            )

    def _search_missing_identifier_type_ids(self, operator, value):
        if operator not in ("in", "not in", "=", "!="):
            return NotImplemented
        missing = self.search([]).filtered(
            lambda a: a.missing_identifier_type_ids.filtered_domain(
                [("id", operator, value)]
            )
        )
        return [("id", "in", missing.ids)]

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
        for vals in vals_list:
            if vals.get("kind_id") and self._around_the_clock(vals):
                vals["resource_calendar_id"] = False
        return super().create(vals_list)

    def write(self, vals):
        if "active" in vals and not vals["active"]:
            self._end_custody()
        return super().write(vals)

    def _end_custody(self):
        now = fields.Datetime.now()
        open_assignments = self.resource_id.assignment_ids.filtered(
            lambda a: not a.date_end or a.date_end > now
        )
        started = open_assignments.filtered(lambda a: a.date_start <= now)
        started.write({"date_end": now})
        for planned in open_assignments - started:
            planned.date_end = planned.date_start

    def action_set_in_service(self):
        self.write({"state": "in_service"})

    def action_dispose(self):
        self.write(
            {
                "state": "disposed",
                "date_disposal": fields.Date.context_today(self),
                "active": False,
            }
        )

    def get_identifier(self, code):
        self.check_singleton()
        return self.identifier_ids.filtered(lambda i: i.type_id.code == code)[:1].value

    def get_meter(self, kind):
        self.check_singleton()
        return self.meter_ids.filtered(lambda m: m.kind == kind)[:1]

    def _get_holder(self, role=None, at=None):
        self.check_singleton()
        return self.env["resource.assignment"]._get_holder(
            self.resource_id, role=role, at=at
        )

    def _search_domain_of_kind(self, code):
        return Domain("kind_id.code", "=", code)
