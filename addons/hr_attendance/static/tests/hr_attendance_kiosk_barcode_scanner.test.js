import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { KioskBarcodeScanner } from "@hr_attendance/components/kiosk_barcode/kiosk_barcode";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineMailModels, mockGetMedia } from "@mail/../tests/mail_test_helpers";
import { uuid } from "@web/core/utils/strings";

defineMailModels();

test.tags("desktop");
test("KioskBarcodeScanner can be opened and closed", async () => {

    mockGetMedia();
    const isBarcodeScannerOpened = Promise.withResolvers();
    patchWithCleanup(KioskBarcodeScanner.prototype, {
        setup() {
            super.setup();
            isBarcodeScannerOpened.resolve(true);
        },
    });

    await mountWithCleanup(KioskBarcodeScanner, {
        props: {
            token: uuid(),
            barcodeSource: "environment",
            kioskMode: "manual",
            fromTrialMode: false,
            onBarcodeScanned: () => {},
            captureCheckInImage: false,
            exposeCameraCapture: () => {},
        },
    });
    await contains("button.o_mobile_barcode").click();
    await waitFor(".modal-body video");
    await contains(`.oi-arrow-left`).click();
    expect(await isBarcodeScannerOpened.promise).toBe(true);
});
