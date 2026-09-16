from collections import defaultdict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..tools import debug_log as dbg


class PosPreset(models.Model):
    _name = "pos.preset"
    _inherit = ["mixin.pos.load"]
    _description = "Easily load a set of configuration options"

    name = fields.Char(
        string="Label",
        translate=True,
        required=True,
    )
    pricelist_id = fields.Many2one(comodel_name="product.pricelist")
    fiscal_position_id = fields.Many2one(comodel_name="account.fiscal.position")
    identification = fields.Selection(
        selection=[("none", "Not required"), ("address", "Address"), ("name", "Name")],
        default="none",
        required=True,
    )
    is_return = fields.Boolean(
        string="Return mode",
        default=False,
        help="All quantity in the cart will be in negative. Ideal for return managment.",
    )
    color = fields.Integer(default=0)
    image_512 = fields.Image(
        string="Image",
        max_width=512,
        max_height=512,
    )
    image_128 = fields.Image(
        related="image_512",
        string="Image 128",
        max_width=128,
        max_height=128,
        store=True,
    )
    has_image = fields.Boolean(compute="_compute_has_image")
    count_linked_orders = fields.Integer(compute="_compute_count_linked_orders")
    count_linked_config = fields.Integer(compute="_compute_count_linked_config")

    use_timing = fields.Boolean(
        string="Manage orders by time",
        default=False,
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Resource",
    )
    attendance_ids = fields.One2many(
        related="resource_calendar_id.attendance_ids",
        string="Attendances",
        readonly=False,
    )
    slots_per_interval = fields.Integer(
        string="Capacity",
        default=5,
    )
    interval_time = fields.Integer(
        string="Interval time (in min)",
        default=20,
    )

    @api.constrains("attendance_ids")
    def _check_slots(self):
        for preset in self:
            for attendance in preset.attendance_ids:
                if attendance.hour_from >= attendance.hour_to:
                    raise ValidationError(
                        _("The start time must be before the end time.")
                    )

    @api.constrains("use_timing", "interval_time", "slots_per_interval")
    def _check_slot_capacity(self):
        for preset in self:
            if preset.use_timing and (
                preset.interval_time <= 0 or preset.slots_per_interval <= 0
            ):
                raise ValidationError(
                    _("Timed presets require a positive interval and capacity.")
                )

    @api.model
    def _load_pos_data_domain(self, data, config):
        preset_ids = config.available_preset_ids.ids + [config.default_preset_id.id]
        return [("id", "in", preset_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "name",
            "pricelist_id",
            "fiscal_position_id",
            "is_return",
            "color",
            "has_image",
            "write_date",
            "identification",
            "use_timing",
            "slots_per_interval",
            "interval_time",
            "attendance_ids",
        ]

    def _compute_count_linked_orders(self):
        counts = dict(
            self.env["pos.order"]._read_group(
                [("preset_id", "in", self.ids)], ["preset_id"], ["__count"]
            )
        )
        for record in self:
            record.count_linked_orders = counts.get(record, 0)

    def _compute_count_linked_config(self):
        configs = self.env["pos.config"].search(
            [
                "|",
                ("default_preset_id", "in", self.ids),
                ("available_preset_ids", "in", self.ids),
            ]
        )
        by_preset = defaultdict(set)
        for config in configs:
            if config.default_preset_id:
                by_preset[config.default_preset_id.id].add(config.id)
            for preset_id in config.available_preset_ids.ids:
                by_preset[preset_id].add(config.id)
        for record in self:
            record.count_linked_config = len(by_preset.get(record.id, ()))

    @api.depends("image_512")
    def _compute_has_image(self):
        for record in self:
            record.has_image = bool(record.image_512)

    def get_available_slots(self):
        self.check_singleton()
        usage = self._get_slots_usage()
        return {
            "usage_utc": usage,
        }

    def _get_slots_usage(self):
        self.check_singleton()
        usage = defaultdict(list)
        now = fields.Datetime.now()
        orders = self.env["pos.order"].search(
            [
                ("preset_id", "=", self.id),
                ("preset_time", ">=", now - timedelta(days=1)),
                ("preset_time", "<", now + timedelta(days=8)),
                ("state", "in", ["draft", "paid", "done"]),
            ]
        )
        for order in orders:
            sql_datetime_str = order.preset_time.strftime("%Y-%m-%d %H:%M:%S")
            usage[sql_datetime_str].append(order.id)

        dbg.logic.debug(
            "[preset:%s] slot usage: %d orders over %d slots",
            self.id,
            len(orders),
            len(usage),
        )
        return usage

    def action_view_linked_orders(self):
        self.check_singleton()
        return {
            "name": _("Linked Orders"),
            "view_mode": "list",
            "res_model": "pos.order",
            "type": "ir.actions.act_window",
            "domain": [("preset_id", "=", self.id)],
        }

    def action_view_linked_config(self):
        self.check_singleton()
        return {
            "name": _("Linked POS Configurations"),
            "view_mode": "list",
            "res_model": "pos.config",
            "type": "ir.actions.act_window",
            "domain": [
                "|",
                ("default_preset_id", "=", self.id),
                ("available_preset_ids", "in", self.ids),
            ],
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_preset(self):
        dbg.lifecycle.debug("pos.preset.unlink: %s", dbg.rec(self))
        for preset in self:
            if preset.count_linked_config:
                raise UserError(
                    _(
                        "You cannot delete a preset that is linked to a POS configuration."
                    )
                )
