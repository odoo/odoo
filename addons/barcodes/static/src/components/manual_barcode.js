/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { BarcodeScanner } from '@barcodes/components/barcode_scanner';
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class StockBarcodeScanner extends BarcodeScanner {
    static template = "stock_barcode.StockBarcodeScanner";
}

export class ManualBarcodeScanner extends Component {
    static components = { Dialog, StockBarcodeScanner };
    static props = {
        onApply: { type: Function },
        close: Function,
    };
    static template = "barcodes.ManualBarcodeScanner";

    setup() {
        this.title = _t("Barcode Manual Entry");
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
     * Called when clicking on Apply button after entering barcode manually.
     *
     * @private
     */
    _onApply() {
        if (this.state.barcode) {
            this.scanBarcode(this.state.barcode);
        }
    }

    /**
     * Called when a barcode is scanned or manually entered.
     * It will call the parent's method (if a barcode is given) and close the dialog.
     * @param {string} barcode
     */
    scanBarcode(barcode) {
        if (barcode) {
            this.props.onApply(barcode);
        }
        this.props.close();
    }

    /**
     * Called when press Enter after filling barcode input manually.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === 'Enter') {
            this._onApply(ev);
        }
    }
}
