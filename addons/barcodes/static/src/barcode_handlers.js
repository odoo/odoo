/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getVisibleElements } from "@web/core/utils/ui";
import { MacroEngine } from "@web/core/macro";

function clickOnButton(selector) {
    const button = document.body.querySelector(selector);
    if (button) {
        button.click();
    }
}
function updatePager(position) {
    const pager = document.body.querySelector("nav.o_pager");
    if (!pager || pager.innerText.includes("-")) {
        // we don't change pages if we are in a multi record view
        return;
    }
    let next;
    if (position === "first") {
        next = 1;
    } else {
        next = parseInt(pager.querySelector(".o_pager_limit").textContent, 10);
    }
    let current = parseInt(pager.innerText.split('/')[0], 10);
    if (current === next) {
        return;
    }
    const engine = new MacroEngine();
    engine.activate({
        name: "updating pager",
        timeout: 1000,
        interval: 0,
        steps: [
            {
                trigger: "span.o_pager_value",
                action: "click"
            },
            {
                trigger: "input.o_pager_value",
                action: "text",
                value: next
            }
        ]
    });
}

export const COMMANDS = {
    "O-CMD.EDIT": () => clickOnButton(".o_form_button_edit"),
    "O-CMD.DISCARD": () => clickOnButton(".o_form_button_cancel"),
    "O-CMD.SAVE": () => clickOnButton(".o_form_button_save"),
    "O-CMD.PREV": () => clickOnButton(".o_pager_previous"),
    "O-CMD.NEXT": () => clickOnButton(".o_pager_next"),
    "O-CMD.PAGER-FIRST": () => updatePager("first"),
    "O-CMD.PAGER-LAST": () => updatePager("last"),
};

export const barcodeGenericHandlers = {
    dependencies: ["ui", "barcode", "notification"],
    start(env, { ui, barcode, notification }) {

        barcode.bus.addEventListener("barcode_scanned", (ev) => {
            const barcode = ev.detail.barcode;
            if (barcode.startsWith("O-BTN.")) {
                let targets = [];
                try {
                    // the scanned barcode could be anything, and could crash the queryselectorall
                    // function
                    targets = getVisibleElements(ui.activeElement, `[barcode_trigger=${barcode.slice(6)}]`);
                } catch (_e) {
                    console.warn(`Barcode '${barcode}' is not valid`);
                }
                for (let elem of targets) {
                    elem.click();
                }
            }
            if (barcode.startsWith("O-CMD.")) {
                const fn = COMMANDS[barcode];
                if (fn) {
                    fn();
                } else {
                    notification.add(env._t("Barcode: ") + `'${barcode}'`, {
                        title: env._t("Unknown barcode command"),
                        type: "danger"
                    });
                }
            }
        });
    }
};

registry.category("services").add("barcode_handlers", barcodeGenericHandlers);
