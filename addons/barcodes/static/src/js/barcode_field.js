odoo.define('barcodes.field', function(require) {
"use strict";

var AbstractField = require('web.AbstractField');
var basicFields = require('web.basic_fields');
var fieldRegistry = require('web.field_registry');

// Field in which the user can both type normally and scan barcodes

var FieldFloatScannable = basicFields.FieldFloat.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _renderEdit: function () {
        var self = this;
        return Promise.resolve(this._super()).then(function () {
            self.$input.data('enableBarcode', true);
        });
    },

});

// Field to use scan barcodes
var FormViewBarcodeHandler = AbstractField.extend({
    /**
     * @override
     */
    init: function() {
        this._super.apply(this, arguments);

        this.trigger_up('activeBarcode', {
            name: this.name,
            commands: {
                barcode: '_barcodeAddX2MQuantity',
            }
        });
    },
});

fieldRegistry.add('field_float_scannable', FieldFloatScannable);
fieldRegistry.add('barcode_handler', FormViewBarcodeHandler);

return {
    FieldFloatScannable: FieldFloatScannable,
    FormViewBarcodeHandler: FormViewBarcodeHandler,
};

});
