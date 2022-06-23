/** @odoo-module **/

import { isBrowserChrome, isMobileOS } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

const { EventBus, whenReady } = owl;

function isSpecialKey(key) {
    return (key === "ArrowLeft" || key === "ArrowRight" ||
        key === "ArrowUp" || key === "ArrowDown" ||
        key === "Escape" || key === "Tab" ||
        key === "Backspace" || key === "Delete" ||
        key === "Home" || key === "End" ||
        key === "PageUp" || key === "PageDown" ||
        key === "Shift" || /F\d\d?/.test(key));
}

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

    // this is done here to make it easily mockable in mobile tests
    isMobileChrome: isMobileOS() && isBrowserChrome(),

    start() {
        const bus = new EventBus();
        const endRegexp = /[\n\r\t]+/;
        const barcodeRegexp = /(.{3,})[\n\r\t]*/;
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
            const match = str.match(barcodeRegexp);
            if (match) {
                const barcode = match[1];
                handleBarcode(barcode, currentTarget);
            }
            if (barcodeInput) {
                barcodeInput.value = "";
            }
            bufferedBarcode = "";
            currentTarget = null;
        }

        function keydownHandler(ev) {
            // Don't catch non-printable keys for which Firefox triggers a keypress
            if (isSpecialKey(ev.key)) {
                return;
            }
            // Don't catch keypresses which could have a UX purpose (like shortcuts)
            if (ev.ctrlKey || ev.metaKey || ev.altKey) {
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

            if (ev.key !== "Enter" && ev.key !== "Unidentified") {
                bufferedBarcode += ev.key;
            }
            clearTimeout(timeout);
            if (String.fromCharCode(ev.which).match(endRegexp)) {
                checkBarcode();
            } else {
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
