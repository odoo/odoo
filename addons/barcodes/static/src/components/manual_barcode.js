import { BarcodeDialog } from '@web/core/barcode/barcode_dialog';
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class BarcodeInput extends Component {
    static template = "stock_barcode.BarcodeInput";
    static props = {
        onSubmit: Function,
    };

    setup() {
        this.state = useState({
            barcode: false,
        });
        this.barcodeManual = useRef('manualBarcode');
        // Autofocus processing was blocked because a document already has a focused element.
        onMounted(() => {
            this.barcodeManual.el.focus();
        });
    }

    /**
     * Called when press Enter after filling barcode input manually.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === "Enter" && this.state.barcode) {
            this.props.onSubmit(this.state.barcode);
        }
    }
}

export class ManualBarcodeScanner extends BarcodeDialog {
    static template = "stock_barcode.ManualBarcodeScanner";
    static components = {
        ...BarcodeDialog.components,
        BarcodeInput,
    };
}