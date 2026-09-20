from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

LEDGER_STATES = ("installed", "removed")
FLAG_REASONS = [
    ("same_work", "Same Position Twice in One Job"),
    ("within_life", "Replaced Within Expected Life"),
    ("within_warranty", "Replaced Under Warranty"),
    ("serial_mismatch", "Removed Serial Mismatch"),
    ("not_returned", "Removed Part Not Returned"),
]
INSTALLATION_FIELDS = frozenset(
    {
        "asset_id",
        "position_id",
        "product_id",
        "serial",
        "date_installed",
        "vendor_id",
        "user_id",
        "previous_part_id",
        "meter_id",
        "meter_installed",
        "date_removed",
        "meter_removed",
        "warranty_date",
        "warranty_meter",
        "amount",
        "currency_id",
    }
)


class ResourceAssetPart(models.Model):
    _name = "resource.asset.part"
    _description = "Asset Part Installation"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _order = "date_installed desc, id desc"
    _check_company_auto = True

    # FIELDS
    company_id = fields.Many2one(
        related="asset_id.company_id",
    )
    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index=True,
        required=True,
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    kind_id = fields.Many2one(related="asset_id.kind_id")
    position_id = fields.Many2one(
        comodel_name="resource.asset.kind.position",
        index=True,
        required=True,
        domain="[('kind_id', '=', kind_id)]",
        ondelete="restrict",
        tracking=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Part",
        required=True,
        ondelete="restrict",
        check_company=True,
        tracking=True,
    )
    serial = fields.Char(
        tracking=True,
        help="The serial number of the part that went in.",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Planned"),
            ("installed", "Installed"),
            ("removed", "Removed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        index=True,
        copy=False,
        readonly=True,
        required=True,
        tracking=True,
    )
    source = fields.Selection(
        selection=[("manual", "Manual")],
        default="manual",
        readonly=True,
        required=True,
        help="Which document installed this part.",
    )
    date_installed = fields.Datetime(
        string="Installed On",
        copy=False,
        tracking=True,
    )
    meter_id = fields.Many2one(
        comodel_name="resource.asset.meter",
        copy=False,
        readonly=True,
        help="The meter the position's expected life is read on, when it had a reading at installation.",
    )
    meter_installed = fields.Float(
        string="Meter at Installation",
        copy=False,
        readonly=True,
    )
    date_removed = fields.Datetime(
        string="Removed On",
        copy=False,
        readonly=True,
    )
    meter_removed = fields.Float(
        string="Meter at Removal",
        copy=False,
        readonly=True,
    )
    previous_part_id = fields.Many2one(
        comodel_name="resource.asset.part",
        string="Replaced Part",
        copy=False,
        readonly=True,
        ondelete="set null",
        help="The installation this one replaced at the same position.",
    )
    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor",
        check_company=True,
        tracking=True,
        help="The supplier who installed the part, when it was not done in house.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Installed By",
        tracking=True,
    )
    removed_serial = fields.Char(
        copy=False,
        tracking=True,
        help="The serial number read off the part that came out.",
    )
    removed_returned = fields.Boolean(
        string="Removed Part Returned",
        copy=False,
        tracking=True,
    )
    warranty_date = fields.Date(
        string="Warranty Until",
        tracking=True,
    )
    warranty_meter = fields.Float(
        string="Warranty Distance",
        help="How far on the position's meter the installer's warranty covers this part.",
    )
    amount = fields.Monetary(
        string="Cost",
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    notes = fields.Text()
    flag_ids = fields.One2many(
        comodel_name="resource.asset.part.flag",
        inverse_name="part_id",
        string="Flags",
        readonly=True,
    )
    review_state = fields.Selection(
        selection=[
            ("none", "Not Flagged"),
            ("flagged", "Flagged"),
            ("cleared", "Cleared"),
        ],
        compute="_compute_review_state",
        store=True,
        index=True,
        tracking=True,
    )

    # CONSTRAINT METHODS
    @api.constrains("asset_id", "position_id")
    def _check_position_belongs_to_kind(self):
        for part in self:
            if part.position_id.kind_id != part.asset_id.kind_id:
                raise ValidationError(
                    self.env._(
                        "%(position)s is a position of %(position_kind)s, and %(asset)s is %(asset_kind)s.",
                        position=part.position_id.display_name,
                        position_kind=part.position_id.kind_id.display_name,
                        asset=part.asset_id.display_name,
                        asset_kind=part.asset_id.kind_id.display_name or "-",
                    )
                )

    @api.constrains("position_id", "product_id")
    def _check_product_fits_position(self):
        for part in self:
            category = part.position_id.product_category_id
            if category and not (part.product_id.categ_id.parent_path or "").startswith(
                category.parent_path
            ):
                raise ValidationError(
                    self.env._(
                        "%(product)s cannot be installed at %(position)s: it takes parts of %(category)s.",
                        product=part.product_id.display_name,
                        position=part.position_id.display_name,
                        category=category.display_name,
                    )
                )

    # CRUD METHODS
    @api.model_create_multi
    def create(self, vals_list):
        born_installed = []
        for vals in vals_list:
            state = vals.get("state", "draft")
            if state not in ("draft", "installed"):
                raise UserError(
                    self.env._("A part is recorded as planned or installed.")
                )
            born_installed.append(state == "installed")
            vals["state"] = "draft"
        parts = super().create(vals_list)
        parts.browse(
            [
                part.id
                for part, installed in zip(parts, born_installed, strict=True)
                if installed
            ]
        )._action_install()
        return parts

    def write(self, vals):
        if not self.env.context.get("asset_part_ledger_write"):
            self._check_installation_unchanged(vals)
        res = super().write(vals)
        if self.env.context.get("asset_part_ledger_write"):
            return res
        installed = self.filtered(lambda part: part.state in LEDGER_STATES)
        if vals.get("removed_returned"):
            installed._resolve_flags("not_returned")
        if "removed_serial" in vals:
            installed._flag_serial_mismatch()
            installed._sync_review_holds()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_installed(self):
        if self.filtered(lambda part: part.state in LEDGER_STATES):
            raise UserError(
                self.env._(
                    "An installed part is part of the asset's history and cannot be deleted."
                )
            )

    # COMPUTE METHODS
    @api.depends("flag_ids.state")
    def _compute_review_state(self):
        for part in self:
            if not part.flag_ids:
                part.review_state = "none"
            elif "open" in part.flag_ids.mapped("state"):
                part.review_state = "flagged"
            else:
                part.review_state = "cleared"

    @api.depends("asset_id", "position_id", "product_id")
    def _compute_display_name(self):
        for part in self:
            part.display_name = " / ".join(
                name
                for name in (
                    part.asset_id.display_name,
                    part.position_id.name,
                    part.product_id.display_name,
                )
                if name
            ) or self.env._("New Part")

    # ACTION METHODS
    def action_install(self):
        self._action_install()
        return True

    def action_cancel(self):
        if self.filtered(lambda part: part.state != "draft"):
            raise UserError(self.env._("Only a planned part can be cancelled."))
        self.with_context(asset_part_ledger_write=True).write({"state": "cancelled"})
        return True

    def action_draft(self):
        if self.filtered(lambda part: part.state != "cancelled"):
            raise UserError(self.env._("Only a cancelled part goes back to planned."))
        self.with_context(asset_part_ledger_write=True).write({"state": "draft"})
        return True

    def action_open_clear_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Clear Flags"),
            "res_model": "resource.asset.part.clear",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_part_ids": self.filtered(
                    lambda part: part.review_state == "flagged"
                ).ids
            },
        }

    def action_view_position_history(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Position History"),
            "res_model": "resource.asset.part",
            "view_mode": "list,form",
            "domain": [
                ("asset_id", "=", self.asset_id.id),
                ("position_id", "=", self.position_id.id),
                ("state", "in", LEDGER_STATES),
            ],
            "context": {"create": False},
        }

    # LEDGER METHODS
    def _action_install(self):
        _debug.lifecycle("part_install", parts=self)
        if self.filtered(lambda part: part.state != "draft"):
            raise UserError(self.env._("Only a planned part can be installed."))
        now = fields.Datetime.now()
        Part = self.with_context(asset_part_ledger_write=True)
        for part in self.sorted(lambda part: (part.date_installed or now, part.id)):
            moment = part.date_installed or now
            previous = self.search(  # noqa: E8507 - one query per installation, in date order: the part installed just before may be the previous one of the next
                [
                    ("asset_id", "=", part.asset_id.id),
                    ("position_id", "=", part.position_id.id),
                    ("state", "in", LEDGER_STATES),
                    ("date_installed", "<=", moment),
                    ("id", "!=", part.id),
                ],
                order="date_installed desc, id desc",
                limit=1,
            )
            meter, value = part._get_meter_reading(moment)
            _debug.logic(
                "part_install_position",
                part=part,
                asset=part.asset_id,
                position=part.position_id,
                previous=previous,
                meter=meter,
                meter_value=value,
            )
            Part.browse(part.id).write(
                {
                    "state": "installed",
                    "date_installed": moment,
                    "previous_part_id": previous.id,
                    "meter_id": meter.id,
                    "meter_installed": value,
                }
            )
            if previous.state == "installed":
                _debug.lifecycle("part_removed_by_replacement", part=previous, by=part)
                Part.browse(previous.id).write(
                    {
                        "state": "removed",
                        "date_removed": moment,
                        "meter_removed": value if previous.meter_id == meter else 0.0,
                    }
                )
        self._flag_repeats()
        self._sync_review_holds()

    def _flag_repeats(self):
        for part in self.filtered(lambda part: part.state in LEDGER_STATES):
            same_work = part._get_same_work_parts().filtered(
                lambda other, p=part: (
                    (other.date_installed, other.id) < (p.date_installed, p.id)
                )
            )
            if same_work:
                part._flag(
                    "same_work",
                    self.env._(
                        "%(position)s was replaced more than once in the same job.",
                        position=part.position_id.name,
                    ),
                )
            previous = part.previous_part_id
            if not previous:
                _debug.logic("part_repeat_check_skipped", part=part, reason="baseline")
                continue
            position = part.position_id
            days = (
                part.date_installed - previous.date_installed
            ).total_seconds() / 86400
            distance = (
                part.meter_installed - previous.meter_installed
                if part.meter_id and part.meter_id == previous.meter_id
                else None
            )
            if (position.expected_life_days and days < position.expected_life_days) or (
                position.expected_life_meter
                and distance is not None
                and distance < position.expected_life_meter
            ):
                part._flag(
                    "within_life",
                    self.env._(
                        "%(position)s was replaced %(days)s days after its previous part, installed on %(date)s by %(installer)s.",
                        position=position.name,
                        days=int(days),
                        date=fields.Date.to_string(previous.date_installed.date()),
                        installer=previous._get_installer_name(),
                    ),
                )
            _debug.logic(
                "part_repeat_measured",
                part=part,
                previous=previous,
                days=days,
                distance=distance,
                life_days=position.expected_life_days,
                life_meter=position.expected_life_meter,
                warranty_date=previous.warranty_date,
                warranty_meter=previous.warranty_meter,
                same_work=len(same_work),
            )
            installed_on = fields.Datetime.context_timestamp(
                part, part.date_installed
            ).date()
            if (previous.warranty_date and installed_on <= previous.warranty_date) or (
                previous.warranty_meter
                and distance is not None
                and distance < previous.warranty_meter
            ):
                note = self.env._(
                    "%(position)s was replaced while the previous part was under %(installer)s's warranty: claim it.",
                    position=position.name,
                    installer=previous._get_installer_name(),
                )
                part._flag("within_warranty", note)
                part.activity_schedule(
                    "mail.mail_activity_data_todo",
                    note=note,
                    user_id=(part.asset_id.manager_id.user_id or self.env.user).id,
                )
            part._flag_serial_mismatch()

    def _flag_serial_mismatch(self):
        for part in self:
            previous_serial = (part.previous_part_id.serial or "").strip().casefold()
            removed_serial = (part.removed_serial or "").strip().casefold()
            _debug.logic(
                "part_serial_compared",
                part=part,
                installed=previous_serial,
                removed=removed_serial,
            )
            if previous_serial and removed_serial and previous_serial != removed_serial:
                part._flag(
                    "serial_mismatch",
                    self.env._(
                        "The part removed from %(position)s reads serial %(removed)s, and the part installed there was %(installed)s.",
                        position=part.position_id.name,
                        removed=part.removed_serial,
                        installed=part.previous_part_id.serial,
                    ),
                )
            elif removed_serial and previous_serial == removed_serial:
                part._resolve_flags("serial_mismatch", sync=False)

    def _flag_not_returned(self):
        for part in self.filtered(
            lambda part: (
                part.state in LEDGER_STATES
                and part.vendor_id
                and not part.removed_returned
            )
        ):
            part._flag(
                "not_returned",
                self.env._(
                    "%(vendor)s has not returned the part removed from %(position)s.",
                    vendor=part.vendor_id.display_name,
                    position=part.position_id.name,
                ),
            )
        self._sync_review_holds()

    def _flag(self, reason, note):
        self.check_singleton()
        if self.flag_ids.filtered(
            lambda flag: flag.reason == reason and flag.state == "open"
        ):
            _debug.logic("part_flag_already_open", part=self, reason=reason)
            return
        _debug.lifecycle("part_flagged", part=self, asset=self.asset_id, reason=reason)
        # sudo: a flag is raised by the ledger on whoever installs the part, and
        # nobody holds a right to write one by hand.
        self.env["resource.asset.part.flag"].sudo().create(
            {"part_id": self.id, "reason": reason, "note": note}
        )
        body = Markup("<b>%s</b><br/>%s") % (
            dict(FLAG_REASONS)[reason],
            note,
        )
        # sudo: the flag is the ledger's statement, posted whatever the installer may write.
        self.sudo().message_post(body=body)
        self.asset_id.sudo().message_post(body=body)

    def _resolve_flags(self, reason, sync=True):
        flags = self.flag_ids.filtered(
            lambda flag: flag.reason == reason and flag.state == "open"
        )
        if flags:
            _debug.lifecycle(
                "part_flags_resolved", parts=self, reason=reason, flags=flags
            )
            # sudo: the condition behind the flag no longer holds, whoever made it so.
            flags.sudo().write(
                {"state": "resolved", "date_closed": fields.Datetime.now()}
            )
        if sync:
            self._sync_review_holds()

    def _clear_flags(self, note):
        if not self.env.user.has_group("resource_asset.group_asset_manager"):
            _debug.logic("part_clear_refused", parts=self, uid=self.env.uid)
            raise UserError(self.env._("Only an asset manager clears a flagged part."))
        flags = self.flag_ids.filtered(lambda flag: flag.state == "open")
        _debug.lifecycle(
            "part_flags_cleared", parts=self, flags=flags, uid=self.env.uid
        )
        # sudo: flags are written by the ledger alone; the group check above is the gate.
        flags.sudo().write(
            {
                "state": "cleared",
                "date_closed": fields.Datetime.now(),
                "cleared_user_id": self.env.uid,
                "clear_note": note,
            }
        )
        body = Markup("<b>%s</b><br/>%s") % (self.env._("Flags cleared"), note)
        for part in flags.part_id:
            part.message_post(body=body)
        self._sync_review_holds()

    def _sync_review_holds(self):
        return

    # HELPER METHODS
    def _get_domain_same_work(self):
        return None

    def _get_same_work_parts(self):
        self.check_singleton()
        domain = self._get_domain_same_work()
        if domain is None:
            return self.browse()
        return self.search(
            Domain.AND(
                [
                    domain,
                    [
                        ("asset_id", "=", self.asset_id.id),
                        ("position_id", "=", self.position_id.id),
                        ("state", "in", LEDGER_STATES),
                        ("id", "!=", self.id),
                    ],
                ]
            )
        )

    def _get_meter_reading(self, moment):
        self.check_singleton()
        kind = self.position_id.meter_kind
        Meter = self.env["resource.asset.meter"]
        if not kind:
            return Meter, 0.0
        meter = self.asset_id.meter_ids.filtered(lambda meter: meter.kind == kind)[:1]
        reading = meter.reading_ids.filtered(lambda r: r.date <= moment).sorted(
            key=lambda r: (r.date, r.id), reverse=True
        )[:1]
        if not reading:
            return Meter, 0.0
        return meter, reading.value

    def _get_installer_name(self):
        self.check_singleton()
        return (
            self.vendor_id.display_name
            or self.user_id.display_name
            or self.env._("an unknown installer")
        )

    def _check_installation_unchanged(self, vals):
        if "state" in vals:
            raise UserError(
                self.env._("A part changes state through its actions, not by hand.")
            )
        if vals.get("removed_returned") is False and self.filtered("removed_returned"):
            raise UserError(
                self.env._("A removed part recorded as returned stays returned.")
            )
        changed = INSTALLATION_FIELDS & vals.keys()
        if changed and self.filtered(lambda part: part.state in LEDGER_STATES):
            raise UserError(
                self.env._(
                    "An installed part is evidence: %(fields)s no longer change.",
                    fields=", ".join(
                        self._fields[fname].get_description(self.env)["string"]
                        for fname in sorted(changed)
                    ),
                )
            )


class ResourceAssetPartFlag(models.Model):
    _name = "resource.asset.part.flag"
    _description = "Asset Part Flag"
    _order = "create_date desc, id desc"

    # FIELDS
    part_id = fields.Many2one(
        comodel_name="resource.asset.part",
        index=True,
        required=True,
        ondelete="cascade",
    )
    asset_id = fields.Many2one(
        related="part_id.asset_id",
    )
    company_id = fields.Many2one(
        related="part_id.company_id",
    )
    reason = fields.Selection(
        selection=FLAG_REASONS,
        required=True,
    )
    note = fields.Text()
    state = fields.Selection(
        selection=[
            ("open", "Open"),
            ("resolved", "Resolved"),
            ("cleared", "Cleared"),
        ],
        default="open",
        index=True,
        required=True,
        help="Resolved: the condition went away, such as the removed part arriving. Cleared: a manager accepted it.",
    )
    date_closed = fields.Datetime(string="Closed On")
    cleared_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Cleared By",
    )
    clear_note = fields.Text()
