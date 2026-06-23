import { Component, onMounted, proxy, signal, props, t } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";

export class BarcodeInput extends Component {
    static template = "barcodes.BarcodeInput";

    props = props(
        {
            onSubmit: t.function(),
            placeholder: t.string().optional(),
            inputFocus: t.boolean().optional(),
        },
        {
            placeholder: _t("Enter a barcode..."),
            inputFocus: true,
        },
    );

    setup() {
        this.state = proxy({
            barcode: false,
        });
        this.barcodeManual = signal(null);
        // Autofocus processing was blocked because a document already has a focused element.
        onMounted(() => {
            if (this.props.inputFocus) {
                this.barcodeManual().focus();
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
