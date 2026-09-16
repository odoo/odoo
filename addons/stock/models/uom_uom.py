from odoo import _, fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class UomUom(models.Model):
    _inherit = "uom.uom"

    package_type_id = fields.Many2one(comodel_name="stock.package.type")
    route_ids = fields.Many2many(
        related="package_type_id.route_ids",
        string="Routes",
        help="Routes propagated from the package type",
    )

    def write(self, vals):
        keys_to_protect = {"factor", "relative_factor", "relative_uom_id"}
        if any(key in vals for key in keys_to_protect):
            changed = self.filtered(
                lambda u: (
                    any(
                        f in vals and u[f] != vals[f]
                        for f in ("factor", "relative_factor")
                    )
                    or (
                        "relative_uom_id" in vals
                        and (u.relative_uom_id.id or 0)
                        != int(vals["relative_uom_id"] or 0)
                    )
                ),
            )
            if changed:
                dbg.logic.debug(
                    "uom.write: ratio change on %s, checking stock usage",
                    dbg.rec(changed),
                )
                error_msg = _(
                    "You cannot change the ratio of this unit of measure"
                    " as some products with this UoM have already been moved"
                    " or are currently reserved.",
                )
                if (
                    self.env["stock.move"]
                    .sudo()
                    .search_count(
                        [
                            ("product_uom_id", "in", changed.ids),
                            ("state", "not in", ("cancel", "done")),
                        ],
                        limit=1,
                    )
                ):
                    raise UserError(error_msg)
                if (
                    self.env["stock.move.line"]
                    .sudo()
                    .search_count(
                        [
                            ("product_uom_id", "in", changed.ids),
                            ("state", "not in", ("cancel", "done")),
                        ],
                        limit=1,
                    )
                ):
                    raise UserError(error_msg)
                if (
                    self.env["stock.quant"]
                    .sudo()
                    .search_count(
                        [
                            ("product_id.product_tmpl_id.uom_id", "in", changed.ids),
                            ("quantity", "!=", 0),
                        ],
                        limit=1,
                    )
                ):
                    raise UserError(error_msg)
        return super().write(vals)

    def _get_procurement_qty_and_uom(self, qty, quant_uom):
        get_param = self.env["ir.config_parameter"].sudo().get_param
        if get_param("stock.propagate_uom") == "1":
            dbg.logic.debug(
                "_get_procurement_qty_and_uom: propagate_uom keeps %s", self.id
            )
            return (qty, self)
        computed_qty = self._get_quantity_stored(qty, quant_uom)
        if qty and quant_uom.is_zero(computed_qty):
            dbg.logic.debug(
                "_get_procurement_qty_and_uom: %s %s rounds to zero in %s, kept",
                qty,
                self.id,
                quant_uom.id,
            )
            return (qty, self)
        return (computed_qty, quant_uom)
