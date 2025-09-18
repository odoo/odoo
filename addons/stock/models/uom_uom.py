from odoo import _, fields, models
from odoo.exceptions import UserError


class UomUom(models.Model):
    _inherit = "uom.uom"

    package_type_id = fields.Many2one(
        comodel_name="stock.package.type",
        string="Package Type",
    )
    route_ids = fields.Many2many(
        related="package_type_id.route_ids",
        string="Routes",
        help="Routes propagated from the package type",
    )

    def write(self, vals):
        # Users can not update the factor if open stock moves are based on it
        keys_to_protect = {"factor", "relative_factor", "relative_uom_id"}
        if any(key in vals for key in keys_to_protect):
            changed = self.filtered(
                lambda u: any(
                    f in vals and u[f] != vals[f] for f in ("factor", "relative_factor")
                )
                or (
                    "relative_uom_id" in vals
                    and u.relative_uom_id.id != int(vals["relative_uom_id"])
                ),
            )
            if changed:
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
                            ("product_uom", "in", changed.ids),
                            ("state", "not in", ("cancel", "done")),
                        ],
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
                    )
                ):
                    raise UserError(error_msg)
        return super().write(vals)

    def _adjust_uom_quantities(self, qty, quant_uom):
        """This method adjust the quantities of a procurement if its UoM isn't the same
        as the one of the quant and the parameter 'propagate_uom' is not set.
        """
        procurement_uom = self
        computed_qty = qty
        get_param = self.env["ir.config_parameter"].sudo().get_param
        if get_param("stock.propagate_uom") != "1":
            computed_qty = self._compute_quantity(
                qty,
                quant_uom,
                rounding_method="HALF-UP",
            )
            procurement_uom = quant_uom
        else:
            computed_qty = self._compute_quantity(
                qty,
                procurement_uom,
                rounding_method="HALF-UP",
            )
        return (computed_qty, procurement_uom)
