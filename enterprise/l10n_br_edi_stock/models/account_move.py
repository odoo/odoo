# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _, api, Command
from odoo.tools import float_round


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_br_plate_number = fields.Char("Plate Number", help="Brazil: vehicle plate number of the delivery vehicle.")
    l10n_br_picking_count = fields.Integer(compute="_compute_l10n_br_picking_count")
    l10n_br_related_package_ids = fields.Many2many("stock.quant.package", string="Related Packages", compute="_compute_l10n_br_related_package_ids")
    l10n_br_package_ids = fields.One2many(
        "stock.quant.package",
        "l10n_br_move_id",
        string="Packages",
        domain="[('id', 'in', l10n_br_related_package_ids), ('l10n_br_move_id', '=', False)]",
        help="Brazil: packages to include in the NF-e used on the deliveries linked to this sales transaction."
    )

    @api.depends("line_ids")
    def _compute_l10n_br_related_package_ids(self):
        """Consider packages belonging to the last validated pickings. We do this so the invoice can be validated before
        products are fully shipped out."""
        for invoice in self:
            invoice.l10n_br_related_package_ids = self.env["stock.quant.package"]

            # Only consider the last validated pickings in each chain.
            for picking in self._l10n_br_get_pickings():
                if picking.state != "done":
                    continue

                next_transfers = picking._get_next_transfers()

                # Include the packages if it's the last in the chain or has any next transfer not done.
                if not next_transfers or any(transfer.state != "done" for transfer in next_transfers):
                    # Only allow packs with content.
                    invoice.l10n_br_related_package_ids |= picking.move_line_ids.result_package_id.filtered("quant_ids")

    @api.depends("line_ids")
    def _compute_l10n_br_picking_count(self):
        for move in self:
            move.l10n_br_picking_count = len(move._l10n_br_get_pickings())

    def action_l10n_br_view_pickings(self):
        return self.env["sale.order"]._get_action_view_picking(self._l10n_br_get_pickings())

    def _l10n_br_get_pickings(self):
        return self.line_ids.sale_line_ids.move_ids.picking_id

    def _l10n_br_type_specific_header(self, tax_data_header):
        """Override."""
        res = super()._l10n_br_type_specific_header(tax_data_header)
        if self.l10n_br_is_service_transaction or not self.l10n_br_edi_freight_model:
            return res

        # The API specifies no precision, but round to avoid e.g. 2.999999... which would look bad on the PDF.
        stock_weight_dp = self.env.ref("product.decimal_stock_weight")
        uom_kg = self.env.ref("uom.product_uom_kgm")
        weight_uom = self.env["product.template"]._get_weight_uom_id_from_ir_config_parameter()
        volumes = []

        package_type_to_packages = self.l10n_br_package_ids.grouped("package_type_id")
        for index, (package_type, packages) in enumerate(package_type_to_packages.items()):
            weight_kg = 0
            for package in packages:
                for quant in package.quant_ids:
                    product = quant.product_id
                    weight_kg += weight_uom._compute_quantity(product.weight, uom_kg) * quant.quantity

            package_weight_kg = weight_uom._compute_quantity(package_type.base_weight, uom_kg) * len(packages)
            volume = {
                "volumeNumeration": _("%(amount)s of %(total)s", amount=index + 1, total=len(package_type_to_packages)),
                "netWeight": float_round(weight_kg, precision_digits=stock_weight_dp.digits),
                "grossWeight": float_round(weight_kg + package_weight_kg, precision_digits=stock_weight_dp.digits),
                "qVol": len(packages),
                "specie": package_type.name or _("Volume"),
            }

            # Conditionally add to make sure we don't add falsy values. deep_clean in l10n_br_edi won't clean lists.
            if package_type.l10n_br_brand:
                volume["brand"] = package_type.l10n_br_brand

            volumes.append(volume)

        res["goods"]["transport"]["volumes"] = volumes
        res["goods"]["transport"]["vehicle"] = {
            "automobile": {"licensePlate": self.l10n_br_plate_number},
        }

        return res
