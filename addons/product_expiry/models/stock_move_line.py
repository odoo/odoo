import datetime

from odoo import api, fields, models
from odoo.db.schema import column_exists, create_column
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    expiration_date = fields.Datetime(
        compute="_compute_expiration_date",
        store=True,
        readonly=False,
        help="This is the date on which the goods with this Serial Number may"
        " become dangerous and must not be consumed.",
    )
    removal_date = fields.Datetime(
        compute="_compute_removal_date",
        store=True,
        readonly=False,
    )
    is_expired = fields.Boolean(related="lot_id.product_expiry_alert")
    use_expiration_date = fields.Boolean(
        related="product_id.use_expiration_date",
        string="Use Expiration Date",
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_move_line", "expiration_date"):
            create_column(
                self.env.cr, "stock_move_line", "expiration_date", "timestamp"
            )
        if not column_exists(self.env.cr, "stock_move_line", "removal_date"):
            create_column(self.env.cr, "stock_move_line", "removal_date", "timestamp")
        return super()._auto_init()

    @api.depends(
        "product_id",
        "product_id.use_expiration_date",
        "lot_id.expiration_date",
        "picking_id.date_planned",
        "quant_id",
    )
    def _compute_expiration_date(self):
        for move_line in self:
            if lot_id := move_line.quant_id.lot_id or move_line.lot_id:
                move_line.expiration_date = lot_id.expiration_date
            elif (
                not move_line.picking_type_use_create_lots
                or not move_line.product_id.use_expiration_date
            ):
                move_line.expiration_date = False
            elif not move_line.expiration_date:
                move_line.expiration_date = (
                    move_line.product_id._get_expiration_date_from(
                        move_line.picking_id.date_planned
                    )
                )

    @api.depends(
        "product_id",
        "product_id.use_expiration_date",
        "expiration_date",
        "lot_id.removal_date",
    )
    def _compute_removal_date(self):
        for move_line in self:
            if move_line.lot_id.removal_date:
                move_line.removal_date = move_line.lot_id.removal_date
            elif (
                move_line.picking_type_use_create_lots
                and move_line.product_id.use_expiration_date
                and move_line.expiration_date
            ):
                move_line.removal_date = move_line.expiration_date - datetime.timedelta(
                    days=move_line.product_id.removal_time
                )
            else:
                move_line.removal_date = False

    def _filtered_expired(self, at=None):
        _debug.logic("move_lines_expired_filter", lines=self, at=at)
        at = at or fields.Datetime.now()
        return self.filtered(
            lambda ml: (
                ml.use_expiration_date
                and (
                    (ml.removal_date and ml.removal_date <= at)
                    or (ml.lot_id.expiration_date and ml.lot_id.expiration_date <= at)
                )
            )
        )

    def _prepare_new_lot_vals(self):
        vals = super()._prepare_new_lot_vals()
        if self.expiration_date:
            vals["expiration_date"] = self.expiration_date
        if self.removal_date:
            vals["removal_date"] = self.removal_date
        return vals
