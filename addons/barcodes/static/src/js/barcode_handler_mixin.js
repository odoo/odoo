odoo.define('barcodes.BarcodeHandlerMixin', function(require) {
"use strict";

var core = require('web.core');

return {
    init: function() {
        this._super.apply(this, arguments);
        this.__on_barcode_scanned = this.on_barcode_scanned.bind(this);
        this.start_listening();
    },

    start_listening: function() {
        core.bus.on('barcode_scanned', this, this.__on_barcode_scanned);
    },

    stop_listening: function() {
        core.bus.off('barcode_scanned', this, this.__on_barcode_scanned);
    },

    on_barcode_scanned: function(barcode) {
        console.error('A class implementing BarcodeHandlerMixin must redefine method on_barcode_scanned.');
    },
};

});
