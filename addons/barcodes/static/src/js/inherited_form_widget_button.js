odoo.define('stock_barcode.InheritedFormWidgetButton', function (require) {
"use strict";

var widgets = require('web.form_widgets');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');

// If the button has a barcode_trigger attribute, dynamically inherit
// BarcodeHandlerMixin and redefine on_barcode_scanned
widgets.WidgetButton.include({
    start: function() {
        this._super.apply(this, arguments);
        if (! this.node.attrs.barcode_trigger)
            return;
        this.barcode_trigger = this.node.attrs.barcode_trigger;
        for (var prop_name in BarcodeHandlerMixin)
            this[prop_name] = BarcodeHandlerMixin[prop_name];
        this.on_barcode_scanned = function(barcode) {
            var match = barcode.match(/O-BTN\.(\w+)/);
            if (match && match[1] === this.barcode_trigger && this.$el.is(':visible'))
                this.on_click();
        }.bind(this);
        this.init.call(this);
    },
});

});
