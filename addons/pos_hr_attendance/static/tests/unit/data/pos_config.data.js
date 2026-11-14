import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

export const KIOSK_INFO = {
    token: "kiosk-token",
    companyId: 1,
    companyName: "Test Company",
    departments: [],
    kioskMode: "barcode_manual",
    barcodeSource: "scanner",
    fromTrialMode: false,
    deviceTrackingEnabled: false,
    captureCheckInImage: false,
    lang: "en-US",
};

patch(PosConfig.prototype, {
    get_attendance_kiosk_info() {
        return KIOSK_INFO;
    },
});
