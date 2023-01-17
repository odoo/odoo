/** @odoo-module **/

import { isBarcodeScannerSupported, scanBarcode } from "@web/webclient/barcode/barcode_scanner";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BarcodeScanner extends Component {
    setup() {
        this.notification = useService("notification");
        this.isBarcodeScannerSupported = isBarcodeScannerSupported();
    }

    get facingMode() {
        return "environment";
    }

    async openMobileScanner() {
        let error = null;
        let barcode = null;
        try {
            barcode = await scanBarcode(this.facingMode);
        } catch (err) {
            error = err.error.message;
        }

        if (barcode) {
            this.props.onBarcodeScanned(barcode);
            if ("vibrate" in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.notification.add(error || this.env._t("Please, Scan again !"), {
                type: "warning",
            });
        }
    }
}

BarcodeScanner.template = "barcodes.BarcodeScanner";
BarcodeScanner.props = {
    onBarcodeScanned: { type: Function },
};
