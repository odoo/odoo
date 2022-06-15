odoo.define('barcodes.BarcodeEvents', function(require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var session = require('web.session');

var BarcodeEvents = core.Class.extend({
    timeout: null,
    key_pressed: {},
    buffered_key_events: [],
    // Regexp to match a barcode input and extract its payload
    // Note: to build in init() if prefix/suffix can be configured
    regexp: /(.{3,})[\n\r\t]*/,
    // By knowing the terminal character we can interpret buffered keys
    // as a barcode as soon as it's encountered (instead of waiting x ms)
    suffix: /[\n\r\t]+/,
    // Keys from a barcode scanner are usually processed as quick as possible,
    // but some scanners can use an intercharacter delay (we support <= 50 ms)
    max_time_between_keys_in_ms: session.max_time_between_keys_in_ms || 55,
    // To be able to receive the barcode value, an input must be focused.
    // On mobile devices, this causes the virtual keyboard to open.
    // Unfortunately it is not possible to avoid this behavior...
    // To avoid keyboard flickering at each detection of a barcode value,
    // we want to keep it open for a while (800 ms).
    inputTimeOut: 800,

    init: function() {
        this.__handler = _.bind(this.handler, this);
        // Bind event handler once the DOM is loaded
        // TODO: find a way to be active only when there are listeners on the bus
        $(() => this.start());

        // Mobile device detection
        this.isChromeMobile = config.device.isMobileDevice && navigator.userAgent.match(/Chrome/i);
    },

    getCurrentString() {
        if (this.$barcodeInput) {
            return this.$barcodeInput.val();
        }
        return this.buffered_key_events.reduce(function(memo, e) { return memo + e.key }, '');
    },

    handle_buffered_keys: function() {
        let str = this.getCurrentString();
        var match = str.match(this.regexp);

        if (match) {
            var barcode = match[1];

            // Send the target in case there are several barcode widgets on the same page (e.g.
            // registering the lot numbers in a stock picking)
            core.bus.trigger('barcode_scanned', barcode, this.buffered_key_events[0].target);

            // Dispatch a barcode_scanned DOM event to elements that have barcode_events="true" set.
            if (this.buffered_key_events[0].target.getAttribute("barcode_events") === "true")
                $(this.buffered_key_events[0].target).trigger('barcode_scanned', barcode);
        }

        this.buffered_key_events = [];
    },

    element_is_editable: function(element) {
        return $(element).is('input,textarea,[contenteditable="true"]');
    },

    // This checks that a keypress event is either ESC, TAB, an arrow
    // key or a function key. This is Firefox specific, in Chrom{e,ium}
    // keypress events are not fired for these types of keys, only
    // keyup/keydown.
    is_special_key: function(e) {
        if (e.key === "ArrowLeft" || e.key === "ArrowRight" ||
            e.key === "ArrowUp" || e.key === "ArrowDown" ||
            e.key === "Escape" || e.key === "Tab" ||
            e.key === "Backspace" || e.key === "Delete" ||
            e.key === "Home" || e.key === "End" ||
            e.key === "PageUp" || e.key === "PageDown" ||
            e.key === "Shift" ||
            e.key === "Unidentified" || /F\d\d?/.test(e.key)) {
            return true;
        } else {
            return false;
        }
    },

    handler: function(e){
        // Don't catch non-printable keys for which Firefox triggers a keypress
        if (this.is_special_key(e)) {
            return;
        }
        // Don't catch keypresses which could have a UX purpose (like shortcuts)
        if (e.ctrlKey || e.metaKey || e.altKey) {
            return;
        }
        // Don't catch events targeting elements that are editable because we
        // have no way of redispatching 'genuine' key events. Resent events
        // don't trigger native event handlers of elements. So this means that
        // our fake events will not appear in eg. an <input> element.
        if ((this.element_is_editable(e.target) && !$(e.target).data('enableBarcode')) && e.target.getAttribute("barcode_events") !== "true") {
            return;
        }

        // Catch and buffer the event
        if (e.key !== "Enter") {
            this.buffered_key_events.push(e);
        }

        // Handle buffered keys immediately if the keypress marks the end
        // of a barcode or after x milliseconds without a new keypress
        clearTimeout(this.timeout);
        if (String.fromCharCode(e.which).match(this.suffix)) {
            this.handle_buffered_keys();
        } else {
            this.timeout = setTimeout(_.bind(this.handle_buffered_keys, this), this.max_time_between_keys_in_ms);
        }
    },

    /**
     * Try to detect the barcode value by listening all keydown events:
     * Checks if a dom element who may contains text value has the focus.
     * If not, it's probably because these events are triggered by a barcode scanner.
     * To be able to handle this value, a focused input will be created.
     *
     * This function also has the responsibility to detect the end of the barcode value.
     * (1) In most of cases, an optional key (tab or enter) is sent to mark the end of the value.
     * So, we direclty handle the value.
     * (2) If no end key is configured, we have to calculate the delay between each keydowns.
     * 'max_time_between_keys_in_ms' depends of the device and may be configured.
     * Exceeded this timeout, we consider that the barcode value is entirely sent.
     *
     * @private
     * @param  {jQuery.Event} e keydown event
     */
    _listenBarcodeScanner: function (e) {
        if ($(document.activeElement).not('input:text, textarea, [contenteditable], ' +
            '[type="email"], [type="number"], [type="password"], [type="tel"], [type="search"]').length) {
            this.$barcodeInput.focus();
        }
        if (this.$barcodeInput.is(":focus")) {
            this.handler(e);
            // if the barcode input doesn't receive keydown for a while, remove it.
            this.__blurBarcodeInput();
        }
    },

    /**
     * Removes the value and focus from the barcode input.
     * If nothing happens, the focus will be lost and
     * the virtual keyboard on mobile devices will be closed.
     *
     * @private
     */
    _blurBarcodeInput: function () {
        // Close the virtual keyboard on mobile browsers
        // FIXME: actually we can't prevent keyboard from opening
        this.$barcodeInput.val('').blur();
    },

    start: function(){
        // Chrome Mobile isn't triggering keypress event.
        // This is marked as Legacy in the DOM-Level-3 Standard.
        // See: https://www.w3.org/TR/uievents/#legacy-keyboardevent-event-types
        // This fix is only applied for Google Chrome Mobile but it should work for
        // all other cases.
        // In master, we could remove the behavior with keypress and only use keydown.
        if (this.isChromeMobile) {
            // Creates an input who will receive the barcode scanner value.
            this.$barcodeInput = $('<input/>', {
                name: 'barcode',
                type: 'text',
                css: {
                    'position': 'fixed',
                    'top': '50%',
                    'transform': 'translateY(-50%)',
                    'z-index': '-1',
                    'opacity': '0',
                },
            });
            // Avoid to show autocomplete for a non appearing input
            this.$barcodeInput.attr('autocomplete', 'off');

            this.__blurBarcodeInput = _.debounce(this._blurBarcodeInput, this.inputTimeOut);


            $('body').append(this.$barcodeInput);
            core.bus.on('barcode_scanned', null, () => this._blurBarcodeInput());

            $('body').on("keydown", this._listenBarcodeScanner.bind(this));
        } else {
            $('body').bind("keydown", this.__handler);
        }
    },

    stop: function(){
        $('body').off("keydown", this.__handler);
    },
});

return {
    /** Singleton that emits barcode_scanned events on core.bus */
    BarcodeEvents: new BarcodeEvents(),
    /**
     * List of barcode prefixes that are reserved for internal purposes
     * @type Array
     */
    ReservedBarcodePrefixes: ['O-CMD'],
};

});
