odoo.define('barcodes.FieldFloatScannable', function(require) {
"use strict";

var core = require('web.core');
var formats = require('web.formats');
var form_widgets = require('web.form_widgets');

// Field in which the user can both type normally and scan barcodes

var FieldFloatScannable = form_widgets.FieldFloat.extend({
    events: {
        // The barcode_events component intercepts keypresses and releases them when it
        // appears they are not part of a barcode. But since released keypresses don't
        // trigger native behaviour (like characters input), we must simulate it.
        'keypress': 'simulateKeypress',
    },

    // Widget values are parsed according to the widget type. Since this widget is of type
    // "FieldFloatScannable" and there is no parsing planned for this type, it defaults
    // to outputting the value as a string. Hence the need to redefine parse_value
    parse_value: function(val, def) {
        return formats.parse_value(val, {type: "float"}, def);
    },

    simulateKeypress: function (e) {
        /* only simulate a keypress if it has been previously prevented */
        if (e.originalEvent.dispatched_by_barcode_reader !== true) {
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
        this.store_dom_value();
    },
});

core.form_widget_registry.add('field_float_scannable', FieldFloatScannable);

return {
    FieldFloatScannable: FieldFloatScannable,
};

});
