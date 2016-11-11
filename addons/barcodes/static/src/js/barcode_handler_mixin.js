odoo.define('barcodes.BarcodeHandlerMixin', function(require) {
"use strict";

var core = require('web.core');
var View = require('web.View');

// Mixin implementing the common basis for barcode handlers.
// The object on which this mixin is applied must also include ParentedMixin. Example :
// Widget.extend(BarcodeHandlerMixin, { ... });
// Class.extend(PropertiesMixin, BarcodeHandlerMixin, { ... });

return {
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.__on_barcode_scanned = function (barcode, target) {
            // Handle the case where there are several barcode widgets on the same page. Since the
            // event is global on the page, all barcode widgets will be triggered. However, we only
            // want to keep the event on the target widget.
            if ($.contains(target, self.el)) {
                self.on_barcode_scanned.call(self, barcode);
            }
        };
        this.start_listening();
        // Handlers inside a View managed by a ViewManager only listen to barcode events while their view is displayed
        var view = this.findAncestor(function(ancestor) { return ancestor instanceof View });
        if (view) {
            view.on('attached', this, this.start_listening);
            view.on('detached', this, this.stop_listening);
        }
    },

    start_listening: function() {
        if (! this.is_listening) {
            core.bus.on('barcode_scanned', this, this.__on_barcode_scanned);
            this.is_listening = true;
        }
    },

    stop_listening: function() {
        if (this.is_listening) {
            core.bus.off('barcode_scanned', this, this.__on_barcode_scanned);
            this.is_listening = false;
        }
    },

    on_barcode_scanned: function(barcode) {
        console.error('A class implementing BarcodeHandlerMixin must redefine method on_barcode_scanned.');
    },
};

});
