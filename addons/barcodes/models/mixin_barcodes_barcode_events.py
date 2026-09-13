from odoo import api, fields, models


class MixinBarcodesBarcode_Events_(models.AbstractModel):
    """Mixin for models that react to a barcode scanned in their form view."""

    # The form view must contain
    # `<field name="_barcode_scanned" widget="barcode_handler"/>`. Models using
    # this mixin must implement `on_barcode_scanned`: it works like an onchange
    # and receives the scanned barcode as parameter.
    _name = "mixin.barcodes.barcode_events"
    _description = "Barcode Event Mixin"

    _barcode_scanned = fields.Char(
        string="Barcode Scanned",
        store=False,
        help="Value of the last barcode scanned.",
    )

    @api.onchange("_barcode_scanned")
    def _on_barcode_scanned(self):
        barcode = self._barcode_scanned
        if barcode:
            self._barcode_scanned = ""
            return self.on_barcode_scanned(barcode)
        return None

    def on_barcode_scanned(self, barcode):
        # Not translated: this fires only when a developer inherits the mixin
        # without implementing the hook, so it is addressed to them and never
        # reaches an end user in a language of their own.
        raise NotImplementedError(
            f"{self._name} inherits mixin.barcodes.barcode_events but does not "
            f"implement on_barcode_scanned()."
        )
