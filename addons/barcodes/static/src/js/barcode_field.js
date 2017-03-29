odoo.define('barcodes.field', function(require) {
"use strict";

var AbstractField = require('web.AbstractField');
var basicFields = require('web.basic_fields');
var fieldRegistry = require('web.field_registry');

// Field in which the user can both type normally and scan barcodes

var FieldFloatScannable = basicFields.FieldFloat.extend({
    events: {
        // The barcode_events component intercepts keypresses and releases them when it
        // appears they are not part of a barcode. But since released keypresses don't
        // trigger native behaviour (like characters input), we must simulate it.
        'keypress': '_onKeypress',
    },

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
        if (e.originalEvent.dispatched_by_barcode_reader !== true) {
            e.preventDefault();
            this.$input.blur();
            return;
        }
        var character = String.fromCharCode(e.which);
        var current_str = e.target.value;
        var str_before_carret = current_str.substring(0, e.target.selectionStart);
        var str_after_carret = current_str.substring(e.target.selectionEnd);
        e.target.value = str_before_carret + character + str_after_carret;
        var new_carret_index = str_before_carret.length + character.length;
        e.target.setSelectionRange(new_carret_index, new_carret_index);
        // Note: FieldChar (that FieldFloat extends) calls store_dom_value upon change
        // event, which is triggered when the input loses focus and its internal dirty
        // flag is set. But here, we directly modify the value property of the input,
        // which doesn't set the dirty flag. So we could call store_dom_value upon blur.
        // But we also want the DOM value to be stored when a barcode_event occurs and
        // triggers an onchange. We could listen to barcode_event in order to call
        // store_dom_value, but that would have to happen before the onchange is triggered.
        // So the safest method is still to store the value each time it changes.
        // This long explanation is here to avoid having to do the thinking all over agan
        // in case this strategy doesn't work / breaks.
        // TL;DR Safest way not to lose the value when a barcode scan triggers an onchange.
        this._setValue(e.target.value);
    },
});

// Field to use scan barcodes

var FormViewBarcodeHandler = AbstractField.extend({
    /**
     * Trigger_up 'activeBarcode' to activate features and send options
     * - @params {string} name: the current field name
     * - @params {string} [fieldName] optional for x2many sub field
     * - @params {string} [quantity] optional field to increase quantity
     * - @params {Object} [commands] optional added methods
     *     can use comand with specific barcode (with ReservedBarcodePrefixes)
     *     or change 'barcode' for all other received barcodes
     *     (e.g.: 'O-CMD.MAIN-MENU': function ..., barcode: function () {...})
     *
     * @override
     */
    init: function() {
        this._super.apply(this, arguments);

        this.trigger_up('activeBarcode', {
            name: this.name,
            fieldName: 'pack_operation_product_ids',
            quantity: 'qty_done',
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
