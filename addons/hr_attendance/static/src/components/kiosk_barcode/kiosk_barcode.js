/** @odoo-module **/

import { BarcodeScanner } from "@barcodes/components/barcode_scanner";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";

export class KioskBarcodeScanner extends BarcodeScanner {
    static props = {
        ...BarcodeScanner.props,
        barcodeSource: String,
        token: String,
    };
    static template = "hr_attendance.BarcodeScanner";
    setup() {
        super.setup();
        this.isDisplayStandalone = isDisplayStandalone();
        this.scanBarcode = () => scanBarcode(this.env, this.facingMode);
    }

    get facingMode() {
        if (this.props.barcodeSource == "front") {
            return "user";
        }
        return super.facingMode;
    }

    get installURL() {
        const url = `hr_attendance/${this.props.token}`;
        return `/scoped_app?app_id=hr_attendance&path=${encodeURIComponent(url)}`;
    }
}
