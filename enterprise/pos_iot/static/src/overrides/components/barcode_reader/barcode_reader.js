import { patch } from "@web/core/utils/patch";
import { BarcodeReader } from "@point_of_sale/app/barcode/barcode_reader_service";

patch(BarcodeReader.prototype, {
    connectToProxy() {
        this.scanners = this.hardwareProxy.deviceControllers.scanners;
        for (const scanner of Object.values(this.scanners)) {
            scanner.addListener((barcode) => this.scan(barcode.value));
        }
    },

    // the barcode scanner will stop listening on the hw_proxy/scanner remote interface
    disconnectFromProxy() {
        if (this.scanners) {
            for (const scanner of Object.values(this.scanners)) {
                scanner.removeListener();
            }
        }
    },
});
