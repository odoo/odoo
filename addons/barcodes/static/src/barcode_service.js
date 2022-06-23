/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";

const { EventBus, whenReady } = owl;

function isEditable(element) {
    return element.matches('input,textarea,[contenteditable="true"]');
}

function makeBarcodeInput() {
    const inputEl = document.createElement('input');
    inputEl.setAttribute("style", "position:fixed;top:50%;transform:translateY(-50%);z-index:-1;opacity:0");
    inputEl.setAttribute("autocomplete", "off");
    inputEl.setAttribute("inputmode", "none"); // magic! prevent native keyboard from popping
    inputEl.classList.add("o-barcode-input");
    inputEl.setAttribute('name', 'barcode');
    return inputEl;
}

export const barcodeService = {
    // Keys from a barcode scanner are usually processed as quick as possible,
    // but some scanners can use an intercharacter delay (we support <= 50 ms)
    maxTimeBetweenKeysInMs: session.max_time_between_keys_in_ms || 55,

    start() {
        const bus = new EventBus();
        let timeout = null;

        let bufferedBarcode = "";
        let currentTarget = null;
        let barcodeInput = null;

        function handleBarcode(barcode, target) {
            bus.trigger('barcode_scanned', {barcode,target});
            if (target.getAttribute('barcode_events') === "true") {
                $(target).trigger('barcode_scanned', barcode);
            }
        }

        /**
         * check if we have a barcode, and trigger appropriate events
         */
        function checkBarcode() {
            const str = barcodeInput ? barcodeInput.value : bufferedBarcode;
            if (str.length >= 3) {
                handleBarcode(str, currentTarget);
            }
            if (barcodeInput) {
                barcodeInput.value = "";
            }
            bufferedBarcode = "";
            currentTarget = null;
        }

        function keydownHandler(ev) {
            // Ignore 'Shift', 'Escape', 'Backspace', 'Insert', 'Delete', 'Home', 'End', Arrow*, F*, Page*, ...
            // ctrl, meta and alt are often used for UX purpose (like shortcuts)
            // Note: shiftKey is not ignored because it can be used by some barcode scanner for digits.
            const isSpecialKey = ev.key.length > 1 || ev.ctrlKey || ev.metaKey || ev.altKey;
            const isEndCharacter = ev.key.match(/(Enter|Tab)/);
            const isVirtualKeyboard = ev.key === "Unidentified" && ev.keyCode === 229;

            // Don't catch non-printable keys except 'enter' and 'tab'
            if (isSpecialKey && !isEndCharacter && !isVirtualKeyboard) {
                return;
            }

            // Detects keydown triggered  by the Android virtual keyboard (used by some barcode scanners)
            if (isVirtualKeyboard && !barcodeInput) {
                barcodeInput = makeBarcodeInput();
                document.body.appendChild(barcodeInput);
            }

            if (barcodeInput) {
                if ($(document.activeElement).not('input:text, textarea, [contenteditable], ' +
                    '[type="email"], [type="number"], [type="password"], [type="tel"], [type="search"]').length) {
                    barcodeInput.focus();
                }
            }

            currentTarget = ev.target;
            // Don't catch events targeting elements that are editable because we
            // have no way of redispatching 'genuine' key events. Resent events
            // don't trigger native event handlers of elements. So this means that
            // our fake events will not appear in eg. an <input> element.
            if (currentTarget !== barcodeInput && isEditable(currentTarget) &&
                !currentTarget.dataset.enableBarcode &&
                currentTarget.getAttribute("barcode_events") !== "true") {
                return;
            }

            clearTimeout(timeout);
            if (isEndCharacter) {
                checkBarcode();
            } else {
                bufferedBarcode += ev.key;
                timeout = setTimeout(checkBarcode, barcodeService.maxTimeBetweenKeysInMs);
            }
        }

        whenReady(() => {
            document.body.addEventListener('keydown', keydownHandler);
        });

        return {
            bus,
        };
    },
};

registry.category("services").add("barcode", barcodeService);
