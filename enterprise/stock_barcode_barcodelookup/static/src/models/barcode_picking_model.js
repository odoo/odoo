import BarcodePickingModel from "@stock_barcode/models/barcode_picking_model";
import { patch } from "@web/core/utils/patch";

patch(BarcodePickingModel.prototype, {
    _mustScanProductFirst(barcodeData) {
        return super._mustScanProductFirst(barcodeData) && !this.isValidForBarcodeLookup;
    },
});
