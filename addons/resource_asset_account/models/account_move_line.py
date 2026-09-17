import math
from typing import Any

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index="btree_not_null",
        help="Asset to which this expense or revenue is allocated. "
        "Used for tracking costs per vehicle, equipment, or property",
    )
    need_asset = fields.Boolean(compute="_compute_need_asset")
    asset_log_ids = fields.One2many(
        comodel_name="resource.asset.log",
        inverse_name="account_move_line_id",
        string="Asset Logs",
        export_string_translation=False,
        help="Service log entries automatically created from this accounting line",
    )

    asset_part_ids = fields.One2many(
        comodel_name="resource.asset.part",
        inverse_name="account_move_line_id",
        string="Asset Parts",
        help="The installed parts this bill line charges.",
    )

    @api.depends("account_id", "move_id.move_type")
    def _compute_need_asset(self) -> None:
        self.need_asset = False

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]) -> models.Model:
        lines = super().create(vals_list)
        lines._sync_asset_logs()
        return lines

    def write(self, vals: dict[str, Any]) -> bool:
        if "asset_id" in vals and not vals["asset_id"]:
            self.sudo().asset_log_ids.with_context(
                ignore_linked_bill_constraint=True,
            ).unlink()
        res = super().write(vals)
        if vals.get("asset_id"):
            self._sync_asset_logs()
        return res

    def unlink(self) -> bool:
        self.sudo().asset_log_ids.with_context(
            ignore_linked_bill_constraint=True,
        ).unlink()
        return super().unlink()

    def _get_analytic_distribution_arguments(self, root_plans):
        arguments = super()._get_analytic_distribution_arguments(root_plans)
        arguments["asset_id"] = self.asset_id.id
        return arguments

    def _sync_asset_logs(self) -> None:
        # Vendor bills and their credit notes both write to the asset ledger:
        # the log carries the signed balance, so a refund offsets what the bill
        # booked instead of leaving its gross cost on the asset forever.
        purchase_types = self.env["account.move"].get_purchase_types()
        to_create = self.filtered(
            lambda line: (
                line.asset_id
                and line.display_type == "product"
                and line.move_id.move_type in purchase_types
                and not line.asset_log_ids
            ),
        )
        if not to_create:
            return
        # sudo: the biller may hold no right on the serial behind the line, and
        # the log needs the asset that serial carries.
        self.env["resource.asset.log"].sudo().create(
            [line.sudo()._prepare_asset_log() for line in to_create],
        )

    def _prepare_asset_log(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id.id,
            "company_id": self.company_id.id,
            "vendor_id": self.partner_id.id,
            "product_id": self.product_id.id,
            "account_move_line_id": self.id,
            "log_type": self._get_asset_log_type(),
            "source": "bill",
        }

    def _get_asset_log_type(self) -> str | bool:
        # sudo: asset_log_type is gated on group_asset_manager, and typing a log
        # is a side effect of booking a bill — the accountant posting it need not
        # be an asset manager to have the type derived for them.
        return (
            self.product_id.categ_id.log_type or self.account_id.sudo().asset_log_type
        )

    def _bind_asset_parts(self, parts) -> None:
        for line in self.filtered(
            lambda line: (
                line.asset_id
                and line.product_id
                and line.display_type == "product"
                and line.move_id.move_type == "in_invoice"
            )
        ):
            vendor = line.move_id.commercial_partner_id
            free = max(math.ceil(line.quantity), 1) - len(line.asset_part_ids)
            if free <= 0:
                continue
            candidates = parts.filtered(
                lambda part, line=line, vendor=vendor: (
                    part.asset_id == line.asset_id
                    and part.product_id == line.product_id
                    and part.vendor_id.commercial_partner_id == vendor
                    and not part.account_move_line_id
                )
            )[:free]
            _debug.logic(
                "bill_line_parts_bound",
                line=line,
                vendor=vendor,
                free=free,
                parts=candidates,
            )
            if candidates:
                candidates.with_context(asset_part_ledger_write=True).write(
                    {"account_move_line_id": line.id}
                )
