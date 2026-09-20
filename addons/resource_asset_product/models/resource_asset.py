import ast
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


def _literal_context(context):
    if isinstance(context, dict):
        return context
    try:
        parsed = ast.literal_eval(context or "{}")
    except SyntaxError, ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Model",
        index="btree_not_null",
        domain="[('asset_kind_id', '!=', False)]",
        help="The model this unit is an instance of. Its template carries the spec sheet.",
    )
    product_tmpl_id = fields.Many2one(
        related="product_id.product_tmpl_id",
    )
    log_ids = fields.One2many(
        comodel_name="resource.asset.log",
        inverse_name="asset_id",
    )
    part_ids = fields.One2many(
        comodel_name="resource.asset.part",
        inverse_name="asset_id",
        string="Parts",
        domain=[("state", "in", ("installed", "removed"))],
    )
    part_flagged_count = fields.Integer(
        string="Flagged Parts",
        compute="_compute_part_flagged_count",
    )
    log_count = fields.Integer(
        string="Ledger Entries",
        compute="_compute_log_count",
        compute_sudo=True,
        help="Logs booked against this asset, whatever their state. An archived log is not counted.",
    )
    kind_id = fields.Many2one(
        compute="_compute_kind_id",
        precompute=True,
        store=True,
        readonly=False,
    )

    @api.depends("product_id.asset_kind_id")
    def _compute_kind_id(self):
        for asset in self:
            if asset.product_id.asset_kind_id:
                asset.kind_id = asset.product_id.asset_kind_id

    def _compute_part_flagged_count(self):
        counts = dict(
            self.env["resource.asset.part"]._read_group(
                [("asset_id", "in", self.ids), ("review_state", "=", "flagged")],
                ["asset_id"],
                ["__count"],
            )
        )
        for asset in self:
            asset.part_flagged_count = counts.get(asset, 0)

    def _get_log_model(self):
        return self.env["resource.asset.log"].with_context(active_test=True)

    def _get_log_counts_by_type(self):
        counts = defaultdict(lambda: defaultdict(int))
        if not self.ids:
            return counts
        for asset, log_type, count in self._get_log_model()._read_group(
            [("asset_id", "in", self.ids)],
            ["asset_id", "log_type"],
            ["__count"],
        ):
            counts[asset.id][log_type] += count
        return counts

    @api.depends("log_ids", "log_ids.log_type", "log_ids.active")
    def _compute_log_count(self):
        counts = self._get_log_counts_by_type()
        for asset in self:
            asset.log_count = sum(counts[asset.id].values())

    def _get_log_action_xml_id(self):
        return "resource_asset_product.action_resource_asset_log"

    def _action_view_logs(self, domain=(), context=None, xml_id=None):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            xml_id or self._get_log_action_xml_id()
        )
        action["domain"] = [("asset_id", "=", self.id), *domain]
        action["context"] = {
            **_literal_context(action.get("context")),
            "default_asset_id": self.id,
            **(context or {}),
        }
        return action

    def action_view_logs(self):
        return self._action_view_logs()

    def _get_latest_ledger_reading(self):
        """{asset id: (odometer, date)} of the newest positive reading in the
        ledger. NULLS FIRST: an undated reading must not outrank a dated one,
        and Postgres sorts NULL last on a plain ASC."""
        if not self.ids:
            return {}
        timeline = self._get_log_model().search_fetch(
            [("asset_id", "in", self.ids), ("odometer", ">", 0)],
            ["asset_id", "date", "odometer"],
            order="asset_id, date ASC NULLS FIRST, id",
        )
        return {log.asset_id.id: (log.odometer, log.date) for log in timeline}

    def _sync_odometer_meter(self):
        """Record the ledger's newest reading on the odometer meter when the two
        disagree, and keep the meter's unit the asset's. A downward move is
        recorded as a correction; no reading at all leaves the meter alone,
        since 0 is not a measurement."""
        latest = self._get_latest_ledger_reading()
        for asset in self.sudo():
            value, when = latest.get(asset.id, (0.0, False))
            meter = asset.odometer_meter_id
            if not value and not meter:
                continue
            if not meter:
                meter = asset._create_odometer_meter()
            elif meter.uom_id != asset.odometer_uom_id:
                meter.uom_id = asset.odometer_uom_id
            if value and meter.value != value:
                date = fields.Datetime.to_datetime(
                    when or fields.Date.context_today(self)
                )
                if meter.date and date <= meter.date:
                    date = meter.date + relativedelta(seconds=1)
                meter.with_context(skip_meter_monotonic=value < meter.value).record(
                    value, date=date, source="service"
                )

    def action_view_parts(self):
        return self._get_parts_action({"search_default_current": 1})

    def action_view_flagged_parts(self):
        return self._get_parts_action({"search_default_flagged": 1})

    def _get_parts_action(self, context):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "resource_asset_product.action_resource_asset_part"
        )
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {"default_asset_id": self.id, **context}
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("product_id") and not vals.get("kind_id"):
                product = self.env["product.product"].browse(vals["product_id"])
                if product.asset_kind_id:
                    vals["kind_id"] = product.asset_kind_id.id
        return super().create(vals_list)
