/** @odoo-module **/

import { isBrowserChrome, isMobileOS } from "@web/core/browser/feature_detection";
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
    maxTimeBetweenKeysInMs: session.max_time_between_keys_in_ms || 100,

    // this is done here to make it easily mockable in mobile tests
    isMobileChrome: isMobileOS() && isBrowserChrome(),

    start() {
        const bus = new EventBus();
        let timeout = null;

        let bufferedBarcode = "";
        let currentTarget = null;
        let barcodeInput = null;

        function handleBarcode(barcode, target) {
            bus.trigger('barcode_scanned', {barcode,target});
            if (target.getAttribute('barcode_events') === "true") {
                const barcodeScannedEvent = new CustomEvent("barcode_scanned", { detail: { barcode, target } });
                target.dispatchEvent(barcodeScannedEvent);
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
            if (!ev.key) {
                // Chrome may trigger incomplete keydown events under certain circumstances.
                // E.g. when using browser built-in autocomplete on an input.
                // See https://stackoverflow.com/questions/59534586/google-chrome-fires-keydown-event-when-form-autocomplete
                return;
            }
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

        function mobileChromeHandler(ev) {
            if (ev.key === "Unidentified") {
                return;
            }
            if ($(document.activeElement).not('input:text, textarea, [contenteditable], ' +
                '[type="email"], [type="number"], [type="password"], [type="tel"], [type="search"]').length) {
                barcodeInput.focus();
            }
            keydownHandler(ev);
        }

        whenReady(() => {
            const isMobileChrome = barcodeService.isMobileChrome;
            if (isMobileChrome) {
                barcodeInput = makeBarcodeInput();
                document.body.appendChild(barcodeInput);
            }
            const handler = isMobileChrome ? mobileChromeHandler : keydownHandler;
            document.body.addEventListener('keydown', handler);
        });

        return {
            bus,
        };
    },
};

registry.category("services").add("barcode", barcodeService);
