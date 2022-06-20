/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getVisibleElements } from "@web/core/utils/ui";

export const barcodeAutoClick = {
    dependencies: ["ui", "barcode"],
    start(env, { ui, barcode }) {

        barcode.bus.addEventListener("barcode_scanned", (ev) => {
            const barcode = ev.detail.barcode;
            if (!barcode.startsWith("O-BTN.")) {
                return;
            }
            let targets = [];
            try {
                // the scanned barcode could be anything, and could crash the queryselectorall
                // function
                targets = getVisibleElements(ui.activeElement, `[barcode_trigger=${barcode.slice(6)}]`);
            } catch (_e) {
                console.warn(`Barcode '${barcode}' is not valid`)
            }
            for (let elem of targets) {
                elem.click();
            }
        });
    }
};

registry.category("services").add("barcode_autoclick", barcodeAutoClick);
