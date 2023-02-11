odoo.define('point_of_sale.BarcodeReader', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var core = require('web.core');
var Mutex = concurrency.Mutex;

// this module interfaces with the barcode reader. It assumes the barcode reader
// is set-up to act like  a keyboard. Use connect() and disconnect() to activate
// and deactivate the barcode reader. Use set_action_callbacks to tell it
// what to do when it reads a barcode.
var BarcodeReader = core.Class.extend({
    actions:[
        'product',
        'cashier',
        'client',
    ],

    init: function (attributes) {
        this.mutex = new Mutex();
        this.pos = attributes.pos;
        this.action_callbacks = {};
        this.exclusive_callbacks = {};
        this.proxy = attributes.proxy;
        this.remote_scanning = false;
        this.remote_active = 0;

        this.barcode_parser = attributes.barcode_parser;

        this.action_callback_stack = [];

        core.bus.on('barcode_scanned', this, function (barcode) {
            // use mutex to make sure scans are done one after the other
            this.mutex.exec(async () => {
                await this.scan(barcode);
            });
        });
    },

    set_barcode_parser: function (barcode_parser) {
        this.barcode_parser = barcode_parser;
    },

    // when a barcode is scanned and parsed, the callback corresponding
    // to its type is called with the parsed_barcode as a parameter.
    // (parsed_barcode is the result of parse_barcode(barcode))
    //
    // callbacks is a Map of 'actions' : callback(parsed_barcode)
    // that sets the callback for each action. if a callback for the
    // specified action already exists, it is replaced.
    //
    // possible actions include :
    // 'product' | 'cashier' | 'client' | 'discount'
    set_action_callback: function (name, callback) {
        if (this.action_callbacks[name]) {
            this.action_callbacks[name].add(callback);
        } else {
            this.action_callbacks[name] = new Set([callback]);
        }
    },

    remove_action_callback: function(name, callback) {
        if (!callback) {
            delete this.action_callbacks[name];
            return;
        }
        const callbacks = this.action_callbacks[name];
        if (callbacks) {
            callbacks.delete(callback);
            if (callbacks.size === 0) {
                delete this.action_callbacks[name];
            }
        }
    },

    /**
     * Allow setting of exclusive callbacks. If there are exclusive callbacks,
     * these callbacks are called neglecting the regular callbacks. This is
     * useful for rendered Components that wants to take exclusive access
     * to the barcode reader.
     *
     * @param {String} name
     * @param {Function} callback function that takes parsed barcode
     */
    set_exclusive_callback: function (name, callback) {
        if (this.exclusive_callbacks[name]) {
            this.exclusive_callbacks[name].add(callback);
        } else {
            this.exclusive_callbacks[name] = new Set([callback]);
        }
    },

    remove_exclusive_callback: function (name, callback) {
        if (!callback) {
            delete this.exclusive_callbacks[name];
            return;
        }
        const callbacks = this.exclusive_callbacks[name];
        if (callbacks) {
            callbacks.delete(callback);
            if (callbacks.size === 0) {
                delete this.exclusive_callbacks[name];
            }
        }
    },

    scan: async function (code) {
        if (!code) return;

        const callbacks = Object.keys(this.exclusive_callbacks).length
            ? this.exclusive_callbacks
            : this.action_callbacks;
        let parsed_results = this.barcode_parser.parse_barcode(code);
        if (! Array.isArray(parsed_results)) {
            parsed_results = [parsed_results];
        }
        for (const parsed_result of parsed_results) {
            if (callbacks[parsed_result.type]) {
                for (const cb of callbacks[parsed_result.type]) {
                    await cb(parsed_result);
                }
            } else if (callbacks.error) {
                [...callbacks.error].map(cb => cb(parsed_result));
            } else {
                console.warn('Ignored Barcode Scan:', parsed_result);
            }
        }
    },

    // the barcode scanner will listen on the hw_proxy/scanner interface for
    // scan events until disconnect_from_proxy is called
    connect_to_proxy: function () {
        var self = this;
        this.remote_scanning = true;
        if (this.remote_active >= 1) {
            return;
        }
        this.remote_active = 1;

        function waitforbarcode(){
            return self.proxy.connection.rpc('/hw_proxy/scanner',{},{shadow: true, timeout:7500})
                .then(function (barcode) {
                    if (!self.remote_scanning) {
                        self.remote_active = 0;
                        return;
                    }
                    self.scan(barcode);
                    waitforbarcode();
                },
                function () {
                    if (!self.remote_scanning) {
                        self.remote_active = 0;
                        return;
                    }
                    waitforbarcode();
                });
        }
        waitforbarcode();
    },

    // the barcode scanner will stop listening on the hw_proxy/scanner remote interface
    disconnect_from_proxy: function () {
        this.remote_scanning = false;
    },
});

return BarcodeReader;

});
