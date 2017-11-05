odoo.define('barcodes.field', function(require) {
"use strict";

var AbstractField = require('web.AbstractField');
var basicFields = require('web.basic_fields');
var fieldRegistry = require('web.field_registry');

// Field in which the user can both type normally and scan barcodes

var FieldFloatScannable = basicFields.FieldFloat.extend({
    events: _.extend({}, basicFields.FieldFloat.prototype.events, {
        // The barcode_events component intercepts keypresses and releases them when it
        // appears they are not part of a barcode. But since released keypresses don't
        // trigger native behaviour (like characters input), we must simulate it.
        'keypress': '_onKeypress',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _renderEdit: function() {
        var self = this;
        $.when(this._super()).then(function () {
            self.$input.data('enableBarcode', true);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {KeyboardEvent} e
     */
    _onKeypress: function (e) {
        /* only simulate a keypress if it has been previously prevented */
        if (e.dispatched_by_barcode_reader !== true) {
            e.preventDefault();
            return;
        }
        var character = String.fromCharCode(e.which);
        var current_str = e.target.value;
        var str_before_carret = current_str.substring(0, e.target.selectionStart);
        var str_after_carret = current_str.substring(e.target.selectionEnd);
        e.target.value = str_before_carret + character + str_after_carret;
        var new_carret_index = str_before_carret.length + character.length;
        e.target.setSelectionRange(new_carret_index, new_carret_index);
        // trigger an 'input' event to notify the widget that it's value changed
        $(e.target).trigger('input');
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
