# -*- coding: utf-8 -*-

from openerp import models, fields, api

class BarcodeEventsMixin(models.AbstractModel):
    """ Mixin class for objects reacting when a barcode is scanned in their form views
        which contains `<field name="_barcode_scanned" widget="barcode_handler"/>`.
        Models using this mixin must implement the method on_barcode_scanned. It works
        like an onchange and receives the scanned barcode in parameter.
    """

    _name = 'barcodes.barcode_events_mixin'

    _barcode_scanned = fields.Char("Barcode Scanned", help="Value of the last barcode scanned.", store=False)

    @api.onchange('_barcode_scanned')
    def _on_barcode_scanned(self):
        barcode = self._barcode_scanned
        if barcode:
            self._barcode_scanned = ""
            return self.on_barcode_scanned(barcode)

    def on_barcode_scanned(self, barcode):
        raise NotImplementedError("In order to use barcodes.barcode_events_mixin, method on_barcode_scanned must be implemented")
