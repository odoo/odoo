import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { EventBus, usePlugin, Plugin, useListener, onWillDestroy } from "@odoo/owl";
import { services } from "@web/core/services";
import { isBrowserChrome, isMobileOS } from "@web/core/browser/feature_detection";

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

const REGEX_END_CHARACTER = /[\n|\t|;]/;

export class BarcodePlugin extends Plugin {
    // Keys from a barcode scanner are usually processed as quick as possible,
    // but some scanners can use an intercharacter delay (we support <= 50 ms)
    static maxTimeBetweenKeysInMs = session.max_time_between_keys_in_ms || 150;

    // this is done here to make it easily mockable in mobile tests
    static isMobileChrome = isMobileOS() && isBrowserChrome();

    setup() {
        this.bus = new EventBus();
        this.timeout = null;

        this.bufferedBarcode = "";
        this.barcodeInput = null;

        if (BarcodePlugin.isMobileChrome) {
            this.barcodeInput = makeBarcodeInput();
            document.body.appendChild(this.barcodeInput);

            useListener(this.barcodeInput, "input", (ev) => this.inputHandler(ev));
            useListener(document.body, "keydown", (ev) => this.mobileChromeHandler(ev));
        } else {
            useListener(document.body, "keydown", (ev) => this.keydownHandler(ev));
        }

        onWillDestroy(() => {
            if (this.barcodeInput) {
                this.barcodeInput.remove();
            }
            if (this.timeout) {
                clearTimeout(this.timeout);
            }
        });
    }

    cleanBarcode(barcode) {
        return barcode.replace(/Alt|Shift|Control/g, '');
    }

    handleBarcode(barcode) {
        this.bus.trigger('barcode_scanned', {barcode});
    }

    /**
     * check if we have a barcode, and trigger appropriate events
     */
    checkBarcode(ev) {
        let str = this.barcodeInput ? this.barcodeInput.value : this.bufferedBarcode;
        str = this.cleanBarcode(str);
        if (str.length >= 3) {
            if (ev) {
                ev.preventDefault();
            }
            for (let scannedCode of str.split(RegExp(REGEX_END_CHARACTER)).filter(Boolean)) {
                this.handleBarcode(scannedCode);
            }
        }
        if (this.barcodeInput) {
            this.barcodeInput.value = "";
        }
        this.bufferedBarcode = "";
    }


    keydownHandler(ev) {
        if (!ev.key) {
            // Chrome may trigger incomplete keydown events under certain circumstances.
            // E.g. when using browser built-in autocomplete on an input.
            // See https://stackoverflow.com/questions/59534586/google-chrome-fires-keydown-event-when-form-autocomplete
            return;
        }
        // Ignore 'Shift', 'Escape', 'Backspace', 'Insert', 'Delete', 'Home', 'End', Arrow*, F*, Page*, ...
        // meta is often used for UX purpose (like shortcuts)
        // Notes:
        // - shiftKey is not ignored because it can be used by some barcode scanner for digits.
        // - altKey/ctrlKey are not ignored because it can be used in some barcodes (e.g. GS1 separator)
        const isSpecialKey = !['Control', 'Alt'].includes(ev.key) && (ev.key.length > 1 || ev.metaKey);
        const isEndCharacter = ev.key.match(/(Enter|Tab)/);

        // Don't catch non-printable keys except 'enter' and 'tab'
        if (isSpecialKey && !isEndCharacter) {
            return;
        }

        // Don't catch events targeting elements that are editable because we
        // have no way of redispatching 'genuine' key events. Resent events
        // don't trigger native event handlers of elements. So this means that
        // our fake events will not appear in eg. an <input> element.
        if (ev.target !== this.barcodeInput && isEditable(ev.target)) {
            return;
        }

        clearTimeout(this.timeout);
        if (isEndCharacter) {
            this.checkBarcode(ev);
        } else {
            this.bufferedBarcode += ev.key;
            this.timeout = setTimeout(() => this.checkBarcode, this.maxTimeBetweenKeysInMs);
        }
    }

    mobileChromeHandler() {
        if (document.activeElement && !document.activeElement.matches(
            'input:not([type]), input[type="text"], textarea, [contenteditable], ' +
            '[type="email"], [type="number"], [type="password"], [type="tel"], [type="search"]'
        )) {
            this.barcodeInput.focus();
            browser.requestAnimationFrame(() => this.barcodeInput.setAttribute("inputmode", "text"));
        }
    }

    inputHandler() {
        this.barcodeInput.setAttribute("inputmode", "none");

        const isEndCharacter = this.barcodeInput.value.slice(-1).match(REGEX_END_CHARACTER);

        clearTimeout(this.timeout);
        if (isEndCharacter) {
            this.checkBarcode();
        } else {
            this.timeout = setTimeout(() => this.checkBarcode, this.maxTimeBetweenKeysInMs);
        }
    }
}

services.add(BarcodePlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the barcode service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("barcode", {
    start() {
        return usePlugin(BarcodePlugin);
    }
});

