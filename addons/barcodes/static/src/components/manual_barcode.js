import { useRef } from "@web/owl2/utils";
import { BarcodeDialog } from "@web/core/barcode/barcode_dialog";
import { Component, onMounted, props, proxy, t } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";

export class BarcodeInput extends Component {
    static template = "barcodes.BarcodeInput";
    props = props({
        onSubmit: t.function(),
        placeholder: t.string().optional(_t("Enter a barcode...")),
    });
    setup() {
        this.state = proxy({
            barcode: false,
        });
        this.barcodeManual = useRef("manualBarcode");
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
