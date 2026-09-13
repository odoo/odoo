from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_uom = fields.Boolean(
        string="Units of Measure & Packagings",
        implied_group="uom.group_uom",
    )
    group_product_variant = fields.Boolean(
        string="Variants",
        implied_group="product.group_product_variant",
    )
    group_product_pricelist = fields.Boolean(
        string="Pricelists",
        implied_group="product.group_product_pricelist",
    )
    product_weight_in_lbs = fields.Selection(
        selection=[
            ("0", "Kilograms (kg)"),
            ("1", "Pounds (lb)"),
        ],
        string="Weight unit of measure",
        default="0",
        config_parameter="product.weight_in_lbs",
    )
    product_volume_volume_in_cubic_feet = fields.Selection(
        selection=[
            ("0", "Cubic Meters (m³)"),
            ("1", "Cubic Feet (ft³)"),
        ],
        string="Volume unit of measure",
        default="0",
        config_parameter="product.volume_in_cubic_feet",
    )
    product_odometer_in_mi = fields.Selection(
        selection=[
            ("0", "Kilometers"),
            ("1", "Miles"),
        ],
        string="Odometer unit of measure",
        default="0",
        config_parameter="product.odometer_in_mi",
    )
    product_area_in_square_ft = fields.Selection(
        selection=[
            ("0", "Square Meters"),
            ("1", "Square Feet"),
        ],
        string="Area unit of measure",
        default="0",
        config_parameter="product.area_in_square_ft",
    )
    product_power_in_hp = fields.Selection(
        selection=[
            ("0", "kW"),
            ("1", "HP"),
        ],
        string="Power unit of measure",
        default="0",
        config_parameter="product.power_in_hp",
    )
    product_fuel_efficiency_in_mpg = fields.Selection(
        selection=[
            ("0", "km/L"),
            ("1", "MPG"),
        ],
        string="Fuel efficiency unit of measure",
        default="0",
        config_parameter="product.fuel_efficiency_in_mpg",
    )
    module_loyalty = fields.Boolean(
        string="Promotions, Coupons, Gift Card & Loyalty Program"
    )

    @api.onchange("group_product_pricelist")
    def _onchange_group_sale_pricelist(self):
        if not self.group_product_pricelist:
            active_pricelist = (
                self.env["product.pricelist"]
                .sudo()
                .search_count([("active", "=", True)], limit=1)
            )
            if active_pricelist:
                return {
                    "warning": {
                        "message": _(
                            "You are deactivating the pricelist feature. "
                            "Every active pricelist will be archived."
                        )
                    }
                }
        return None

    def set_values(self):
        had_group_pl = self.default_get(["group_product_pricelist"])[
            "group_product_pricelist"
        ]
        super().set_values()

        if self.group_product_pricelist and not had_group_pl:
            self.env["res.company"]._activate_or_create_pricelists()
        elif had_group_pl and not self.group_product_pricelist:
            self.env["product.pricelist"].sudo().search(
                [("active", "=", True)]
            ).action_archive()
