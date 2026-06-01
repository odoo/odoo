import { proxy } from "@odoo/owl";
import { BarcodeScanner } from "@barcodes/components/barcode_scanner";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";
import { isDisplayStandalone } from "@web/core/browser/feature_detection";
import { AttendanceVideoStream } from "@hr_attendance/components/attendance_video_stream/attendance_video_stream";

export class KioskBarcodeScanner extends BarcodeScanner {
    static props = {
        ...BarcodeScanner.props,
        barcodeSource: String,
        token: String,
        kioskMode: String,
        fromTrialMode: Boolean,
        captureCheckInImage: Boolean,
        exposeCameraCapture: Function,
    };
    static template = "hr_attendance.KioskBarcodeScanner";
    static components = {
        AttendanceVideoStream,
    };
    setup() {
        super.setup();
        this.isDisplayStandalone = isDisplayStandalone();
        this.scanBarcode = () => scanBarcode(this.env, this.facingMode);
        this.state = proxy({
            streamAvailable: null,
        });
    }

    get facingMode() {
        if (this.props.barcodeSource == "front") {
            return "user";
        }
        return super.facingMode;
    }

    get installURL() {
        const url = `hr_attendance/${this.props.token}`;
        return `/scoped_app?app_id=hr_attendance&path=${encodeURIComponent(url)}`;
    }

    get showVideoStream() {
        return this.props.captureCheckInImage && this.state.streamAvailable !== false;
    }

    setStreamAvailable(isAvailable) {
        this.state.streamAvailable = isAvailable;
    }
}
