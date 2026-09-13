from odoo import api, fields, models


class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    shipper_package_code = fields.Char(string="Carrier Code")
    package_carrier_type = fields.Selection(
        selection=[("none", "No carrier integration")],
        string="Carrier",
        default="none",
    )

    @api.onchange("package_carrier_type")
    def _onchange_carrier_type(self):
        carrier_id = self.env["delivery.carrier"].search(
            [("delivery_type", "=", self.package_carrier_type)], limit=1
        )
        if carrier_id:
            self.shipper_package_code = carrier_id._get_default_custom_package_code()
        else:
            self.shipper_package_code = False

    @api.depends("package_carrier_type")
    def _compute_length_uom_name(self):
        package_without_carrier = self.env["stock.package.type"]
        for package in self:
            if package.package_carrier_type and package.package_carrier_type != "none":
                package.length_uom_name = ""
            else:
                package_without_carrier |= package
        super(StockPackageType, package_without_carrier)._compute_length_uom_name()
