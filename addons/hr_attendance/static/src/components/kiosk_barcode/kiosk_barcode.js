/** @odoo-module **/

import { BarcodeScanner } from "@barcodes/components/barcode_scanner";
import { BarcodeDialog } from '@web/core/barcode/barcode_dialog';
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
        this.scanBarcode = () => scanBarcode(this.env, this.facingMode, this.props.token);
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

/**
 * Opens the BarcodeScanning dialog and begins code detection using the device's camera.
 *
 * @returns {Promise<string>} resolves when a {qr,bar}code has been detected
 */
export async function scanBarcode(env, facingMode = "environment", token) {
    let res;
    let rej;
    const promise = new Promise((resolve, reject) => {
        res = resolve;
        rej = reject;
    });
    env.services.dialog.add(BarcodeDialog, {
        facingMode,
        token: token,
        onResult: (result) => res(result),
        onError: (error) => rej(error),
    });
    return promise;
}
