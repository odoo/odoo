import { Component, useEffect, useState } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { _t } from "@web/core/l10n/translation";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

export class BarcodeScannerPopup extends Component {
    static template = "pos_self_order_loyalty.BarcodeScannerPopup";
    static props = {
        text: String,
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.selfOrder = useSelfOrder();
        this.barcodeReader = useService("barcode_reader");
        this.state = useState({
            code: "",
        });
    }

    confirm() {
        this.props.getPayload(this.state.code);
        this.props.close();
    }

    async openMobileScanner() {
        if (!isBarcodeScannerSupported && this.barcodeReader) {
            return;
        }
        let data;
        try {
            data = await scanBarcode(this.env);
        } catch (error) {
            // Here, we know the structure of the error raised by BarcodeScanner.
            this.dialog.add(AlertDialog, {
                title: _t("Unable to scan"),
                body: error?.message || error?.error?.message || "Unable to find barcode scanner.",
            });
            return;
        }
        if (data) {
            this.barcodeReader.scan(data);
            if ("vibrate" in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.env.services.notification.notify({
                type: "warning",
                message: "Please, Scan again!",
            });
        }
    }
}
