import { useRef, useState } from "@web/owl2/utils";
import { Component, onMounted } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";

export class BarcodeInput extends Component {
    static template = "barcodes.BarcodeInput";
    static props = {
        onSubmit: Function,
        placeholder: { type: String, optional: true },
        inputFocus: { type: Boolean, optional: true },
    };
    static defaultProps = {
        placeholder: _t("Enter a barcode..."),
        inputFocus: true,
    };

    setup() {
        this.state = useState({
            barcode: false,
        });
        this.barcodeManual = useRef("manualBarcode");
        // Autofocus processing was blocked because a document already has a focused element.
        onMounted(() => {
            if (this.props.inputFocus) this.barcodeManual.el.focus();
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
