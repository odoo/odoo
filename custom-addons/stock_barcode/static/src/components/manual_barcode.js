/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, onMounted, useRef, useState } from "@odoo/owl";

export class ManualBarcodeScanner extends Component {
    setup() {
        this.title = _t("Barcode Manual Entry");
        this.state = useState({
            'barcode': false,
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
            const barcode = this.props.onApply(this.state.barcode);
            if (barcode) {
                this.props.close();
            }
        }
    }

    /**
     * Mobile barcode scanner open and process the barcode.
     *
     * @private
     */
    _onBarcodeScan() {
        this.props.openMobileScanner();
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

ManualBarcodeScanner.components = { Dialog };
ManualBarcodeScanner.props = {
    onApply: { type: Function },
    openMobileScanner: { type: Function },
    close: Function
};
ManualBarcodeScanner.template = "stock_barcode.ManualBarcodeScanner";
