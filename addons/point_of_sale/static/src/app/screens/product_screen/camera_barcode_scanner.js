import { xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { BarcodeDialog } from "@web/webclient/barcode/barcode_scanner";

export class CameraBarcodeScanner extends BarcodeDialog {
    static template = xml`
        <CropOverlay onResize.bind="this.onResize" isReady="state.isReady">
            <video t-ref="videoPreview" muted="true" autoplay="true" playsinline="true" class="w-100 h-100"/>
        </CropOverlay>
    `;
    static props = [];
    setup() {
        super.setup();
        this.barcodeScanner = useService("barcode_reader");
        this.props = {
            facingMode: "environment",
            onResult: (result) => this.barcodeScanner.scan(result),
            onError: console.error,
            close: () => {},
        };
    }
    onResult(result) {
        super.onResult(result);
        clearInterval(this.interval);
        setTimeout(() => {
            this.interval = setInterval(this.detectCode.bind(this), 100);
        }, 2000);
    }
}
