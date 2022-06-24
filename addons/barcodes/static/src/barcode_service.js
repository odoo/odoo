/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";

const { EventBus, whenReady } = owl;

function isEditable(element) {
    return element.matches('input,textarea,[contenteditable="true"]');
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
            if (bufferedBarcode.length >= 3) {
                handleBarcode(bufferedBarcode, currentTarget);
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

            // Don't catch non-printable keys except 'enter' and 'tab'
            if (isSpecialKey && !isEndCharacter) {
                return;
            }

            currentTarget = ev.target;
            // Don't catch events targeting elements that are editable because we
            // have no way of redispatching 'genuine' key events. Resent events
            // don't trigger native event handlers of elements. So this means that
            // our fake events will not appear in eg. an <input> element.
            if (isEditable(currentTarget) &&
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
