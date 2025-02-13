import { BarcodeDialog } from "@web/core/barcode/barcode_dialog";
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";

export class BarcodeInput extends Component {
    static template = "barcodes.BarcodeInput";
    static props = {
        onSubmit: Function,
        placeholder: { type: String, optional: true },
        autofocus: { type: Boolean, optional: true },
    };
    static defaultProps = {
        placeholder: _t("Enter a barcode..."),
        autofocus: true,
    };
    setup() {
        this.state = useState({
            barcode: false,
        });
        this.barcodeManual = useRef("manualBarcode");
        // Autofocus processing was blocked because a document already has a focused element.
        onMounted(() => {
            if (this.props.autofocus) {
                this.barcodeManual.el.focus();
            }
        });
    }

    /**
     * Called when press Enter after filling barcode input manually.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter" && this.state.barcode) {
            this.props.onSubmit(this.state.barcode);
        }
    }
}

export class ManualBarcodeScanner extends BarcodeDialog {
    static template = "barcodes.ManualBarcodeScanner";
    static components = {
        ...BarcodeDialog.components,
        BarcodeInput,
    };
    static props = [...BarcodeDialog.props, "placeholder?"];
}
