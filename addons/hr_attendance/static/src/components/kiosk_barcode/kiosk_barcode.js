/** @odoo-module **/

import { BarcodeScanner } from "@barcodes/components/barcode_scanner";
import { AttendanceBarcodeDialog } from "../barcode_dialog/kiosk_barcode_dialog";

export class KioskBarcodeScanner extends BarcodeScanner {
    static props = {
        ...BarcodeScanner.props,
        barcodeSource: String,
        token: String,
    };
    setup() {
        super.setup();
        this.scanBarcode = () => scanBarcode(this.env, this.facingMode, this.props.token);
    }

    get facingMode() {
        if (this.props.barcodeSource == "front") {
            return "user";
        }
        return super.facingMode;
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
    env.services.dialog.add(AttendanceBarcodeDialog, {
        facingMode,
        token: token,
        onResult: (result) => res(result),
        onError: (error) => rej(error),
    });
    return promise;
}
