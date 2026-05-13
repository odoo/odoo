import { useState, useExternalListener } from "@web/owl2/utils";
import { Component, useRef } from "@odoo/owl";
import { BarcodeVideoScanner, isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { BarcodeInput } from "./barcode_input";

export class BarcodeView extends Component {
    static template = "barcodes.BarcodeView";
    static components = {
        BarcodeVideoScanner,
        BarcodeInput,
    };

    static props = {
        ...BarcodeVideoScanner.props,
        onInputSubmit: { type: Function },
        slots: { type: Object, optional: true },
        inputFocus: { type: Boolean, optional: true },
    }

    setup() {
        this.state = useState({
            barcodeScannerSupported: isBarcodeScannerSupported(),
            barcodeScannerOpened: false,
        });

        const barcodeRef = useRef("barcode_container");

        useExternalListener(window, "click", (ev) => {
            if (barcodeRef.el && !barcodeRef.el.contains(ev.target)) {
                this.state.barcodeScannerOpened = false;
            }
        });
    }

    /**
     * Detection success handler
     *
     * @param {string} result found code
     */
    onResult(result) {
        this.props.onResult(result);
    }

    /**
     * Opens or closes the view
     */
    toggleView() {
        this.state.barcodeScannerOpened = !this.state.barcodeScannerOpened;
    }

    /**
     * Detection error handler
     *
     * @param {Error} error
     */
    onError(error) {
        this.state.barcodeScannerSupported = false;
    }
}
