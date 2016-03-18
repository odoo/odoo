odoo.define('barcodes.FormViewBarcodeHandler', function(require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var common = require('web.form_common');
var BarcodeEvents = require('barcodes.BarcodeEvents');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
var KanbanRecord = require('web_kanban.Record');

var _t = core._t;

// web_kanban.Record and web.list_common.Record do not implement the
// same interface and are thus inherently incompatible with each
// other. Luckily barcodes keeps things pretty simple when it comes to
// the records it wants to use. So if we give the KanbanRecord a get()
// function that behaves like the one of web.list.Record, everything
// is fine.
KanbanRecord.include({
    get: function (key) {
        return this.values[key] && this.values[key].value;
    },
});

var FormViewBarcodeHandler = common.AbstractField.extend(BarcodeHandlerMixin, {
    init: function(parent, context) {
        this.__quantity_listener = _.bind(this._set_quantity_listener, this);
        BarcodeHandlerMixin.init.apply(this, arguments);

        return this._super.apply(this, arguments);
    },

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

    _display_no_edit_mode_warning: function() {
        this.do_warn(_t('Error : Document not editable'), _t('To modify this document, please first start edition.'));
    },

    _display_no_last_scanned_warning: function() {
        this.do_warn(_t('Error : No last scanned barcode'), _t('To set the quantity please scan a barcode first.'));
    },

    _set_quantity_listener: function(event) {
        var self = this;
        var character = String.fromCharCode(event.which);

        // only catch the event if we're not focused in
        // another field and it's a number
        if ($(event.target).is('body') && /[0-9]/.test(character)) {
            if (this.form_view.get('actual_mode') === 'view') {
                this._display_no_edit_mode_warning();
            } else {
                var field = this.form_view.fields[this.m2x_field];
                var view = field.viewmanager.active_view;

                if (this.last_scanned_barcode) {
                    var new_qty = window.prompt(_t('Set quantity'), character) || "0";
                    new_qty = new_qty.replace(',', '.');
                    var record = this._get_records(field).find(function(record) {
                        return record.get('product_barcode') === self.last_scanned_barcode;
                    });
                    if (record) {
                        var values = {};
                        values[this.quantity_field] = parseFloat(new_qty);
                        field.data_update(record.get('id'), values).then(function () {
                            view.controller.reload_record(record);
                        });
                    } else {
                        this._display_no_last_scanned_warning();
                    }
                } else {
                    this._display_no_last_scanned_warning();
                }
            }
        }
    },

    start_listening: function() {
        if (this.quantity_field && ! this.is_listening) {
            core.bus.on('keypress', this, this.__quantity_listener);
        }

        BarcodeHandlerMixin.start_listening.call(this);
    },

    stop_listening: function() {
        if (this.quantity_field && this.is_listening) {
            core.bus.off('keypress', this, this.__quantity_listener);
            delete this.last_scanned_barcode;
        }

        BarcodeHandlerMixin.stop_listening.call(this);
    },

    // Let subclasses add custom behaviour before onchange. Must return a deferred.
    // Resolve the deferred with true proceed with the onchange, false to prevent it.
    pre_onchange_hook: function(barcode) {
        return $.Deferred().resolve(true);
    },

    on_barcode_scanned: function(barcode) {
        var self = this;
        self.last_scanned_barcode = barcode;
        // Execute a harcoded action
        var action = this.map_barcode_method[barcode];
        if (typeof action === "function")
            return $.when(action());
        if (_.any(BarcodeEvents.ReservedBarcodePrefixes, function(prefix) { return barcode.indexOf(prefix) === 0 }))
            return;
        // Warn the user if form view is not editable
        else if (this.form_view.get('actual_mode') === 'view')
            this._display_no_edit_mode_warning();
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

    _get_records: function(field) {
        return field.viewmanager.active_view.controller.records || // tree view
            field.viewmanager.active_view.controller.widgets; // kanban view
    },
});

core.form_widget_registry.add('barcode_handler', FormViewBarcodeHandler);

return FormViewBarcodeHandler;

});
