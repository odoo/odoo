import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { BarcodeVideoScanner, isBarcodeScannerSupported } from "./barcode_video_scanner";

export class BarcodeDialog extends Component {
    static template = "web.BarcodeDialog";
    static components = {
        BarcodeVideoScanner,
        Dialog,
    };
    static props = ["facingMode", "close", "onResult", "onError"];

    setup() {
        this.state = useState({
            barcodeScannerSupported: isBarcodeScannerSupported(),
            errorMessage: _t("Check your browser permissions"),
        });
    }

    /**
     * Detection success handler
     *
     * @param {string} result found code
     */
    onResult(result) {
        this.props.close();
        this.props.onResult(result);
    }

    /**
     * Detection error handler
     *
     * @param {Error} error
     */
    onError(error) {
        this.state.barcodeScannerSupported = false;
        this.state.errorMessage = error.message;
    }
}

/**
 * Opens the BarcodeScanning dialog and begins code detection using the device's camera.
 *
 * @returns {Promise<string>} resolves when a {qr,bar}code has been detected
 */
export async function scanBarcode(env, facingMode = "environment") {
    let res;
    let rej;
    const promise = new Promise((resolve, reject) => {
        res = resolve;
        rej = reject;
    });
    env.services.dialog.add(BarcodeDialog, {
        facingMode,
        onResult: (result) => res(result),
        onError: (error) => rej(error),
    });
    return promise;
}
