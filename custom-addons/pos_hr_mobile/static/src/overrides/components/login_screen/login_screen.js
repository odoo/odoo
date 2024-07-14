/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { LoginScreen } from "@pos_hr/app/login_screen/login_screen";
import { patch } from "@web/core/utils/patch";
import { isBarcodeScannerSupported, scanBarcode } from "@web/webclient/barcode/barcode_scanner";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { useService } from "@web/core/utils/hooks";

patch(LoginScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.barcodeReader = useService("barcode_reader");
        this.hasMobileScanner = isBarcodeScannerSupported() && this.barcodeReader;
        this.popup = useService("popup");
    },
    async open_mobile_scanner() {
        let data;
        try {
            data = await scanBarcode(this.env);
        } catch (error) {
            if (error.error && error.error.message) {
                // Here, we know the structure of the error raised by BarcodeScanner.
                this.popup.add(ErrorPopup, {
                    title: _t("Unable to scan"),
                    body: error.error.message,
                });
                return;
            }
            // Just raise the other errors.
            throw error;
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
    },
});
