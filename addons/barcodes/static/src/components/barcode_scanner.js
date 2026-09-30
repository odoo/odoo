import { _t } from "@web/core/l10n/translation";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BarcodeScanner extends Component {
    static template = "barcodes.BarcodeScanner";
    static props = {
        onBarcodeScanned: { type: Function },
    };

    setup() {
        this.notification = useService("notification");
        this.isBarcodeScannerSupported = isBarcodeScannerSupported();
        this.scanBarcode = () => scanBarcode(this.env, this.facingMode);
    }

    get facingMode() {
        return "environment";
    }

    async openMobileScanner() {
        let error = null;
        let barcode = null;
        try {
            barcode = await this.scanBarcode();
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
