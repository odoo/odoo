odoo.define('point_of_sale.BarcodeReader', function (require) {
"use strict";

var core = require('web.core');

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
        this.pos = attributes.pos;
        this.action_callback = {};
        this.proxy = attributes.proxy;
        this.remote_scanning = false;
        this.remote_active = 0;
        this.iotbox = false;

        this.barcode_parser = attributes.barcode_parser;

        this.action_callback_stack = [];

        core.bus.on('barcode_scanned', this, function (barcode) {
            this.scan(barcode);
        });
    },

    set_barcode_parser: function (barcode_parser) {
        this.barcode_parser = barcode_parser;
    },

    save_callbacks: function () {
        var callbacks = {};
        for (var name in this.action_callback) {
            callbacks[name] = this.action_callback[name];
        }
        this.action_callback_stack.push(callbacks);
    },

    restore_callbacks: function () {
        if (this.action_callback_stack.length) {
            var callbacks = this.action_callback_stack.pop();
            this.action_callback = callbacks;
        }
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
    set_action_callback: function (action, callback) {
        if (arguments.length == 2) {
            this.action_callback[action] = callback;
        } else {
            var actions = arguments[0];
            for (var action in actions) {
                this.set_action_callback(action,actions[action]);
            }
        }
    },

    //remove all action callbacks
    reset_action_callbacks: function () {
        for (var action in this.action_callback) {
            this.action_callback[action] = undefined;
        }
    },

    scan: function (code) {
        if (!code) {
            return;
        }
        var parsed_result = this.barcode_parser.parse_barcode(code);
        if (this.action_callback[parsed_result.type]) {
            this.action_callback[parsed_result.type](parsed_result);
        } else if (this.action_callback.error) {
            this.action_callback.error(parsed_result);
        } else {
            console.warn("Ignored Barcode Scan:", parsed_result);
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

        $.ajax({
            url: self.proxy.host + '/hw_drivers/check_certificate',
            type: 'GET',
            success: function() {
                self.iotbox = true;
            },
            error: function() {
                self.iotbox = false;
            },
        });

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
                    if (self.iotbox) {
                        waitforbarcode();
                    } else {
                        setTimeout(waitforbarcode,5000);
                    }
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
