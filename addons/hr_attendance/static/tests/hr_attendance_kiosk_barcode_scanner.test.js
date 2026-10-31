import { KioskBarcodeScanner } from "@hr_attendance/components/kiosk_barcode/kiosk_barcode";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { Deferred, expect, mockPermission, test, waitFor } from "@odoo/hoot";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";

defineMailModels();

test.tags("desktop");
test("KioskBarcodeScanner can be opened and closed", async () => {
    mockPermission("camera", "granted");
    const isBarcodeScannerOpened = new Deferred();
    patchWithCleanup(KioskBarcodeScanner.prototype, {
        setup() {
            super.setup();
            isBarcodeScannerOpened.resolve(true);
        },
    });

    await mountWithCleanup(KioskBarcodeScanner, {
        props: {
            token: crypto.randomUUID(),
            barcodeSource: "environment",
            onBarcodeScanned: () => {},
        },
    });
    await contains("button.o_mobile_barcode").click();
    await waitFor(".modal-body video");
    await contains(`.oi-arrow-left`).click();
    expect(await isBarcodeScannerOpened).toBe(true);
});
