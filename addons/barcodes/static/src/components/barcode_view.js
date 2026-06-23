import { Component, signal, props, proxy, t, useListener } from "@odoo/owl";
import { BarcodeVideoScanner, isBarcodeScannerSupported } from "@web/core/barcode/barcode_video_scanner";
import { BarcodeInput } from "./barcode_input";

export class BarcodeView extends Component {
    static template = "barcodes.BarcodeView";
    static components = {
        BarcodeVideoScanner,
        BarcodeInput,
    };

    props = props(
        {
            facingMode: t.selection(["environment", "left", "right", "user"]),
            onResult: t.function(),
            onError: t.function(),
            onInputSubmit: t.function(),
            slots: t.object().optional(),
            inputFocus: t.boolean().optional(),
        },
        {
            inputFocus: false,
        }
    )

    setup() {
        this.state = proxy({
            barcodeScannerSupported: isBarcodeScannerSupported(),
            barcodeScannerOpened: false,
        });

        this.barcodeRef = signal(null);

        useListener(window, "click", (ev) => {
            if (this.barcodeRef() && !this.barcodeRef().contains(ev.target)) {
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

    /**
     * Invoked when input button is pressed
     * We need to close the view in this case
     */
    inputButtonSubmit(barcode) {
        const inputResult = this.props.onInputSubmit(barcode);
        this.toggleView();
        return inputResult;
    }
}
