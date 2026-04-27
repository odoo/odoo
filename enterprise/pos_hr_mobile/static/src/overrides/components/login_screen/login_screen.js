import { _t } from "@web/core/l10n/translation";
import { LoginScreen } from "@point_of_sale/app/screens/login_screen/login_screen";
import { patch } from "@web/core/utils/patch";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";

patch(LoginScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.barcodeReader = useService("barcode_reader");
        this.hasMobileScanner = isBarcodeScannerSupported() && this.barcodeReader;
    },
    async open_mobile_scanner() {
        if (!this.hasMobileScanner) {
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
    },
});
