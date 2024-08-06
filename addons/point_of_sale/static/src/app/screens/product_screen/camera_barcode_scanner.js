import { useService } from "@web/core/utils/hooks";
import { BarcodeVideoScanner } from "@web/webclient/barcode/barcode_video_scanner";

export class CameraBarcodeScanner extends BarcodeVideoScanner {
    static props = [];
    setup() {
        super.setup();
        this.barcodeScanner = useService("barcode_reader");
        this.sound = useService("sound");
        this.props = {
            facingMode: "environment",
            onResult: (result) => this.onResult(result),
            onError: console.error,
            delayBetweenScan: 2000,
        };
    }
    onResult(result) {
        this.barcodeScanner.scan(result);
        this.sound.play("beep");
    }
}
