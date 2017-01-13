odoo.define('barcode.InheritedFormWidgetButton', function (require) {
"use strict";

var widgets = require('web.form_widgets');
var BarcodeEvents = require('barcodes.BarcodeEvents');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');

// If the button has a barcode_trigger attribute, dynamically inherit
// BarcodeHandlerMixin and redefine on_barcode_scanned

var ButtonBarcodeHandlerMixin = _.extend({}, BarcodeHandlerMixin, {
    init: function(field_manager, node) {
        if (node.attrs.barcode_trigger) {
            BarcodeHandlerMixin.init.call(this, field_manager, node);
            var self = this;
            this.on_barcode_scanned = function(barcode) {
                var match = barcode.match(/O-BTN\.(.+)/);
                if (match && match[1] === self.node.attrs.barcode_trigger &&
                    (self.$el.is(':visible') || self.$el.parent('.dropdown-menu').length)) {
                    self.on_click();
                }
            };
        } else {
            this._super(field_manager, node);
        }
    },
});

BarcodeEvents.ReservedBarcodePrefixes.push('O-BTN');

widgets.WidgetButton.include(ButtonBarcodeHandlerMixin);

});
