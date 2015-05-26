odoo.define('web.BarcodeEvents', function(require) {
    "use strict";

    var core = require('web.core');
    var mixins = core.mixins;

    return core.Class.extend(mixins.PropertiesMixin, {
        timeout: null,
        key_released: true,
        buffered_key_events: [],

        init: function(parent) {
            mixins.PropertiesMixin.init.call(this);
        },

        handle_buffered_keys: function() {
            var code = "";

            if (this.buffered_key_events.length >= 3) {
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

        keyup_handler: function(e){
            this.key_released = true;
        },

        handler: function(e){
            if (! e.dispatched_by_barcode_reader) {
                if (! this.key_released) { // don't allow key repeat
                    e.preventDefault();
                    e.stopImmediatePropagation();
                    return;
                }

                this.key_released = false;

                // We only stop events targeting body (meaning nothing is
                // focused). We do not stop events targeting other elements
                // because we have no way of redispatching 'genuine' key events
                // that trigger native event handlers of elements. So this means
                // that our fake events will not appear in eg. an <input>
                // element. The addition of the contentEditable attribute in HTML5
                // means that this is not only limited to <input>, <textarea>,...
                if (! this.element_is_editable(e.target) || e.target.getAttribute("barcode_events") === "true") {
                    this.buffered_key_events.push(e);
                    e.preventDefault();
                    e.stopImmediatePropagation();

                    clearTimeout(this.timeout);
                    this.timeout = setTimeout(this.handle_buffered_keys.bind(this), 100);
                }
            }
        },

        start: function(){
            document.body.addEventListener('keypress', this.handler.bind(this), true);
            document.body.addEventListener('keyup', this.keyup_handler.bind(this), true);
        },

        stop: function(){
            document.body.removeEventListener('keypress', this.handler.bind(this), true);
            document.body.removeEventListener('keyup', this.keyup_handler.bind(this), true);
        },
    });
});
