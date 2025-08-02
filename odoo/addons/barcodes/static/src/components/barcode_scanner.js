/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
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
            barcode = await scanBarcode(this.env, this.facingMode);
        } catch (err) {
            error = err.message;
        }

        if (barcode) {
            this.props.onBarcodeScanned(barcode);
            if ("vibrate" in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.notification.add(error || _t("Please, Scan again!"), {
                type: "warning",
            });
        }
    }
}

BarcodeScanner.template = "barcodes.BarcodeScanner";
BarcodeScanner.props = {
    onBarcodeScanned: { type: Function },
};
