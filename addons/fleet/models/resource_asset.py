from odoo import api, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    @api.depends("product_id", "license_plate", "vin_sn", "name", "kind_id")
    def _compute_display_name(self):
        # A root-typed recordset runs the root's compute, so the vehicle's
        # naming lives here, keyed on the kind, until reads dispatch to the
        # concrete model.
        vehicles = self.filtered(lambda asset: asset.kind_code == "vehicle")
        for vehicle in vehicles:
            parts = [
                part
                for part in (
                    vehicle.product_id.manufacturer_id.name,
                    vehicle.product_id.name,
                )
                if part
            ]
            parts.append(vehicle._get_display_identity())
            vehicle.display_name = " / ".join(parts)
        super(ResourceAsset, self - vehicles)._compute_display_name()

    def _get_display_identity(self):
        """What names this unit among others of its model. A plate is how a
        vehicle is spoken about, but one waiting for its paperwork has none --
        and a serial says more about which vehicle this is than "No Plate"
        does."""
        self.check_singleton()
        if self.license_plate or self.vin_sn:
            return self.license_plate or self.vin_sn
        # The asset's own name is composed from its model and its serial, and
        # the model is already the part before this one -- the same reason the
        # plate is not appended to a label that ends in it.
        name = self.name or ""
        model = self.product_id.name or ""
        if model and name.startswith(f"{model} "):
            name = name[len(model) + 1 :]
        return name or self.env._("No Plate")
