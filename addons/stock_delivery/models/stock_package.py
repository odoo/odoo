from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPackage(models.Model):
    _inherit = "stock.package"

    @api.depends("contained_quant_ids", "package_type_id")
    def _compute_weight(self):
        _debug.perf.count("package_weight_compute", packages=self)
        packages_weight = self.sudo()._get_weight(self.env.context.get("picking_id"))
        for package in self:
            package.weight = packages_weight[package]

    def _default_weight_uom_name(self):
        return self.env[
            "product.template"
        ]._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_name(self):
        for package in self:
            package.weight_uom_name = self.env[
                "product.template"
            ]._get_weight_uom_name_from_ir_config_parameter()

    def _compute_weight_uom_info(self):
        self.weight_is_kg = False
        uom_id = self.env[
            "product.template"
        ]._get_weight_uom_id_from_ir_config_parameter()
        if uom_id == self.env.ref("uom.product_uom_kgm"):
            self.weight_is_kg = True
        self.weight_uom_rounding = uom_id.rounding

    weight = fields.Float(
        digits="Stock Weight",
        compute="_compute_weight",
        help="Total weight of all the products contained in the package.",
    )
    weight_uom_name = fields.Char(
        string="Weight unit of measure label",
        compute="_compute_weight_uom_name",
        default=_default_weight_uom_name,
        readonly=True,
    )
    weight_is_kg = fields.Boolean(
        string="Technical field indicating whether weight uom is kg or not (i.e. lb)",
        compute="_compute_weight_uom_info",
    )
    weight_uom_rounding = fields.Float(
        string="Technical field indicating weight's number of decimal places",
        compute="_compute_weight_uom_info",
    )
    package_carrier_type = fields.Selection(
        related="package_type_id.package_carrier_type"
    )

    def _pre_put_in_pack_hook(
        self,
        package_id=False,
        package_type_id=False,
        package_name=False,
        from_package_wizard=False,
    ):
        _debug.pipeline("package_put_in_pack_pre", packages=self)
        res = super()._pre_put_in_pack_hook(
            package_id, package_type_id, package_name, from_package_wizard
        )
        move_lines = self.move_line_ids
        if res and move_lines.carrier_id:
            if self.env.context.get("picking_id"):
                move_lines = move_lines.filtered(
                    lambda ml: ml.picking_id.id == self.env.context["picking_id"]
                )

            context = res.get("context", {})
            context["default_package_carrier_type"] = (
                move_lines._get_package_carrier_type_for_pack()
            )
            res["context"] = context
        return res

    def _post_put_in_pack_hook(self):
        _debug.pipeline("package_put_in_pack_post", packages=self)
        res = super()._post_put_in_pack_hook()
        weight = self.env.context.get("weight")
        if weight:
            res.shipping_weight = weight
        return res
