/** @odoo-module **/

import { BarcodeScanner } from "@barcodes/components/barcode_scanner";

export class KioskBarcodeScanner extends BarcodeScanner {
    get facingMode() {
        if (this.props.barcodeSource == "front") {
            return "user";
        }
        return super.facingMode;
    }
}
KioskBarcodeScanner.props = {
    ...BarcodeScanner.props,
    barcodeSource: String,
};
