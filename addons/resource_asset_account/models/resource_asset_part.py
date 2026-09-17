from odoo import fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.resource_asset_product.models.resource_asset_part import LEDGER_STATES

_debug = DebugLog(__name__)


class ResourceAssetPart(models.Model):
    _inherit = "resource.asset.part"

    # FIELDS
    account_move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Bill Line",
        index="btree_not_null",
        copy=False,
        domain="[('asset_id', '=', asset_id), ('move_id.move_type', '=', 'in_invoice')]",
        ondelete="set null",
        help="The vendor bill line that charges this part. A flagged part holds its bill.",
    )

    # LEDGER METHODS
    def _action_install(self):
        super()._action_install()
        self._bind_bill_lines()
        self._sync_review_holds()

    def _sync_review_holds(self):
        super()._sync_review_holds()
        # sudo: holding a bill follows from the part's review, whoever installed it.
        self.sudo().account_move_line_id.move_id._sync_asset_part_hold()

    def _bind_bill_lines(self):
        parts = self.filtered(
            lambda part: (
                part.state in LEDGER_STATES
                and part.vendor_id
                and not part.account_move_line_id
            )
        )
        if not parts:
            return
        _debug.pipeline("parts_bill_lines_lookup", parts=parts)
        # sudo: the installer may hold no right on the vendor's bills.
        lines = (
            self.env["account.move.line"]
            .sudo()
            .search(
                [
                    ("asset_id", "in", parts.asset_id.ids),
                    ("product_id", "in", parts.product_id.ids),
                    ("display_type", "=", "product"),
                    ("move_id.move_type", "=", "in_invoice"),
                    ("parent_state", "in", ("draft", "posted")),
                ],
                order="id",
            )
        )
        lines._bind_asset_parts(parts)
