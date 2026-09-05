import { Component, onMounted, proxy, signal, t, useProps } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { _t } from "@web/core/l10n/translation";

export class BarcodeInput extends Component {
    static template = "barcodes.BarcodeInput";
    props = useProps({
        onSubmit: t.function(),
        placeholder: t.string().optional(_t("Enter a barcode")),
        inputFocus: t.boolean().optional(true),
    });
    barcodeManual = signal.ref();

    setup() {
        this.state = proxy({
            barcode: false,
        });
        // Autofocus processing was blocked because a document already has a focused element.
        onMounted(() => {
            if (this.props.inputFocus) {
                this.barcodeManual()?.focus();
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
