odoo.define('barcodes.FormViewBarcodeHandler', function(require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var common = require('web.form_common');
var BarcodeEvents = require('barcodes.BarcodeEvents');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');

var _t = core._t;

var FormViewBarcodeHandler = common.AbstractField.extend(BarcodeHandlerMixin, {
    start: function() {
        this._super();
        this.form_view = this.field_manager;
        // Hardcoded barcode actions
        this.map_barcode_method = {
            'O-CMD.NEW': _.bind(this.form_view.on_button_new, this.form_view),
            'O-CMD.EDIT': _.bind(this.form_view.on_button_edit, this.form_view),
            'O-CMD.CANCEL': _.bind(this.form_view.on_button_cancel, this.form_view),
            // FIXME: on_button_save shouldn't mix view and model concerns (it expects to be used as onclick handler)
            'O-CMD.SAVE': _.bind(this.form_view.on_button_save, this.form_view, {target: $('.o_cp_buttons .o_form_button_save')}),
        };
        // Old design pager actions
        if (this.form_view.execute_pager_action) {
            this.map_barcode_method['O-CMD.PAGER-PREV'] = _.bind(this.form_view.execute_pager_action, this.form_view, 'previous');
            this.map_barcode_method['O-CMD.PAGER-NEXT'] = _.bind(this.form_view.execute_pager_action, this.form_view, 'next');
        // New design pager actions
        } else if (this.form_view.pager) {
            this.map_barcode_method['O-CMD.PAGER-PREV'] = _.bind(this.form_view.pager.previous, this.form_view.pager);
            this.map_barcode_method['O-CMD.PAGER-NEXT'] = _.bind(this.form_view.pager.next, this.form_view.pager);
        }
    },
    
    // Let subclasses add custom behaviour before onchange. Must return a deferred.
    // Resolve the deferred with true proceed with the onchange, false to prevent it.
    pre_onchange_hook: function(barcode) {
        return $.Deferred().resolve(true);
    },

    on_barcode_scanned: function(barcode) {
        var self = this;
        // Execute a harcoded action
        var action = this.map_barcode_method[barcode];
        if (typeof action === "function")
            return $.when(action());
        if (_.any(BarcodeEvents.ReservedBarcodePrefixes, function(prefix) { return barcode.indexOf(prefix) === 0 }))
            return;
        // Warn the user if form view is not editable
        else if (this.form_view.get('actual_mode') === 'view')
            this.do_warn(_t('Error : Document not editable'), _t('To modify this document, please first start edition.'));
        else {
            // Call hook method possibly implemented by subclass
            this.pre_onchange_hook(barcode).then(function(proceed) {
                if (proceed === true) {
                    // Wait for hypothetical ongoing onchange to finish
                    self.form_view.onchanges_mutex.exec(function() {
                        // A real onchange is triggered when a value actually changes (which can correspond
                        // to a widget's blur event per example). Commit the value of fields before
                        // programmatically triggering an onchange to be consistent with this.
                        var mutex_commit_value = new utils.Mutex();
                        _.each(self.form_view.fields, function(field) {
                            mutex_commit_value.exec(_.bind(field.commit_value, field));
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
