odoo.define('barcodes.FormViewBarcodeHandler', function(require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var common = require('web.form_common');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');

var _t = core._t;

var FormViewBarcodeHandler = common.AbstractField.extend(BarcodeHandlerMixin, {
    start: function() {
        this._super();
        this.form_view = this.field_manager;
        // Hardcoded barcode actions
        this.map_barcode_method = {
            'O-CMD.NEW': this.form_view.on_button_new.bind(this.form_view),
            'O-CMD.CANCEL': this.form_view.on_button_cancel.bind(this.form_view),
            // FIXME: on_button_save shouldn't mix view and model concerns (it expects to be used as onclick handler)
            'O-CMD.SAVE': this.form_view.on_button_save.bind(this.form_view, {target: $('.o_cp_buttons .o_form_button_save')}),
        };
    },
    
    // Let subclasses add custom behaviour before onchange while enforcing a
    // common barcode handling process through template method 'on_barcode_scanned'
    pre_onchange_hook: function(barcode) {
        return false;
    },

    on_barcode_scanned: function(barcode) {
        var self = this;
        // Execute a harcoded action
        var action = this.map_barcode_method[barcode];
        if (typeof action === "function")
            return $.when(action());
        // Warn the user if form view is not editable
        else if (this.form_view.get('actual_mode') === 'view')
            this.do_warn(_t('Error : Document not editable'), _t('To modify this document, please first start edition.'));
        else {
            // Call hook method possibly implemented by subclass
            $.when(this.pre_onchange_hook(barcode)).then(function(result) {
                if (result !== false) {
                    return result;
                } else {
                    // Make sure that, if a field is being edited when a barcode scan
                    // triggers an onchange, its method commit_value() is called first.
                    // A real onchange is triggered when a value actually changes (which
                    // can correspond to a widget's blur event per example). To keep a
                    // consistent UX and avoid side effects, a barcode-triggered onchange
                    // should behave as much as possible like a real onchange.

                    // Wait for hypothetical ongoing onchange to finish
                    self.form_view.onchanges_mutex.exec(function() {
                        // Commit the value of fields
                        var mutex_commit_value = new utils.Mutex();
                        _.each(self.form_view.fields, function(field) {
                            mutex_commit_value.exec(field.commit_value.bind(field));
                        });
                        return mutex_commit_value.def.then(function(){
                            // Trigger the barcode onchange
                            self.set_value(barcode);
                        });
                    });
                }
            });
        }
    },
});

core.form_widget_registry.add('barcode_handler', FormViewBarcodeHandler);

return FormViewBarcodeHandler;

});
