odoo.define('web.BarcodeEvents', function(require) {
"use strict";

var core = require('web.core');
var mixins = core.mixins;

var BarcodeEvents = core.Class.extend(mixins.PropertiesMixin, {
    timeout: null,
    key_pressed: {},
    buffered_key_events: [],
    min_barcode_keys: 3, // minimum barcode length
    max_time_between_keys_in_ms: 50, // max time between keys to be detected as a barcode

    init: function(parent) {
        mixins.PropertiesMixin.init.call(this);
        this.setParent(parent);
        // Bind event handler once the DOM is loaded
        // TODO: find a way to be active only when there are listeners on the bus
        $(this.start.bind(this));
    },

    handle_buffered_keys: function() {
        var code = "";

        if (this.buffered_key_events.length >= this.min_barcode_keys) {
            for (var i = 0; i < this.buffered_key_events.length; i++) {
                code += String.fromCharCode(this.buffered_key_events[i].which);
            }

            core.bus.trigger('barcode_scanned', code);

            // Dispatch a barcode_scanned DOM event to elements that have
            // barcode_events="true" set.
            if (this.element_is_editable(this.buffered_key_events[0].target)) {
                $(this.buffered_key_events[0].target).trigger('barcode_scanned', code);
            }
        } else {
            this.resend_buffered_keys();
        }

        this.buffered_key_events = [];
    },

    resend_buffered_keys: function() {
        for(var i = 0; i < this.buffered_key_events.length; i++) {
            var old_event = this.buffered_key_events[i];

            if(old_event.which !== 13) { // ignore returns
                // We do not create a 'real' keypress event through
                // eg. KeyboardEvent because there are several issues
                // with them that make them very different from
                // genuine keypresses. Chrome per example has had a
                // bug for the longest time that causes keyCode and
                // charCode to not be set for events created this way:
                // https://bugs.webkit.org/show_bug.cgi?id=16735
                var new_event = new Event("keypress", {
                    'bubbles': old_event.bubbles,
                    'cancelable': old_event.cancelable,
                });

                new_event.viewArg = old_event.viewArg;
                new_event.ctrl = old_event.ctrl;
                new_event.alt = old_event.alt;
                new_event.shift = old_event.shift;
                new_event.meta = old_event.meta;
                new_event.char = old_event.char;
                new_event.key = old_event.key;
                new_event.charCode = old_event.charCode;
                new_event.keyCode = old_event.keyCode || old_event.which; // Firefox doesn't set keyCode for keypresses, only keyup/down
                new_event.which = old_event.which;
                new_event.dispatched_by_barcode_reader = true;

                old_event.target.dispatchEvent(new_event);
            }
        }
    },

    element_is_editable: function(element) {
        return $(element).is('input,textarea,[contenteditable="true"]');
    },

    // This checks that a keypress event is either ESC, TAB or an
    // arrow key. This is Firefox specific, in Chrom{e,ium}
    // keypress events are not fired for these types of keys, only
    // keyup/keydown.
    is_special_key: function(e) {
        if (e.key === "ArrowLeft" || e.key === "ArrowRight" ||
            e.key === "ArrowUp" || e.key === "ArrowDown" ||
            e.key === "Escape" || e.key === "Tab") {
            return true;
        } else {
            return false;
        }
    },

    // The keydown and keyup handlers are here to disallow key
    // repeat. When preventDefault() is called on a keydown event
    // the keypress that normally follows is cancelled.
    keydown_handler: function(e){
        if (this.key_pressed[e.which]) {
            e.preventDefault();
        } else {
            this.key_pressed[e.which] = true;
        }
    },

    keyup_handler: function(e){
        this.key_pressed[e.which] = false;
    },

    handler: function(e){
        if (! e.dispatched_by_barcode_reader && ! this.is_special_key(e)) {
            // We only stop events targeting elements that are editable. We
            // do not stop events targeting other elements because we have
            // no way of redispatching 'genuine' key events that trigger
            // native event handlers of elements. So this means that our
            // fake events will not appear in eg. an <input> element.
            if (! this.element_is_editable(e.target) || e.target.getAttribute("barcode_events") === "true") {
                this.buffered_key_events.push(e);
                e.preventDefault();
                e.stopImmediatePropagation();

                clearTimeout(this.timeout);
                this.timeout = setTimeout(this.handle_buffered_keys.bind(this), this.max_time_between_keys_in_ms);
            }
        }
    },

    start: function(){
        document.body.addEventListener('keydown', this.keydown_handler.bind(this), true);
        document.body.addEventListener('keyup', this.keyup_handler.bind(this), true);
        document.body.addEventListener('keypress', this.handler.bind(this), true);
    },

    stop: function(){
        document.body.removeEventListener('keydown', this.keydown_handler.bind(this), true);
        document.body.removeEventListener('keyup', this.keyup_handler.bind(this), true);
        document.body.removeEventListener('keypress', this.handler.bind(this), true);
    },
});

return {
    BarcodeEvents: new BarcodeEvents(),
};

});
