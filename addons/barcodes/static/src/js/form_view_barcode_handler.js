odoo.define('barcodes.FormViewBarcodeHandler', function(require) {
"use strict";

var core = require('web.core');
var utils = require('web.utils');
var common = require('web.form_common');
var BarcodeEvents = require('barcodes.BarcodeEvents');
var BarcodeHandlerMixin = require('barcodes.BarcodeHandlerMixin');
var KanbanRecord = require('web_kanban.Record');
var Dialog = require('web.Dialog');

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

        this.process_barcode_mutex = new utils.Mutex();

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

    destroy: function () {
        this.stop_listening();
        this._super.apply(this, arguments);
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
                var $content = $('<div>').append($('<input>', {type: 'text', class: 'o_set_qty_input'}));

                if (this.last_scanned_barcode) {
                    this.dialog = new Dialog(this, {
                        title: _t('Set quantity'),
                        buttons: [{text: _t('Select'), classes: 'btn-primary', close: true, click: function () {
                            var new_qty = this.$content.find('.o_set_qty_input').val();
                            var record = _.find(self._get_records(field), function (record) {
                                return record.get('product_barcode') === self.last_scanned_barcode;
                            });
                            if (record) {
                                var values = {};
                                values[self.quantity_field] = parseFloat(new_qty);
                                field.data_update(record.get('id'), values).then(function () {
                                    view.controller.reload_record(record);
                                });
                            } else {
                                self._display_no_last_scanned_warning();
                            }
                        }}, {text: _t('Discard'), close: true}],
                        $content: $content,
                    }).open();
                    // This line set the value of the key which triggered the _set_quantity in the input
                    this.dialog.$content.find('.o_set_qty_input').focus().val(character);

                    var $selectBtn = this.dialog.$footer.find('.btn-primary');
                    core.bus.on('keypress', this.dialog, function(event){
                        if (event.which === 13) {
                            event.preventDefault();
                            $selectBtn.click();
                        }
                    });
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
            var process_barcode = function () {
                // this function can be passed to `Mutex.exec` in order to make sure
                // that every ongoing onchanges in the form view are done
                var form_onchanges_mutex = function () {
                    return self.form_view.onchanges_mutex.def;
                }

                // before setting the barcode field with the received barcode, we commit
                // every fields of the form view and we wait for their hypothetical ongoing
                // onchanges to finish
                var commit_mutex = new utils.Mutex();
                _.each(self.form_view.fields, function (field) {
                    commit_mutex.exec(function () {
                        return field.commit_value();
                    });
                    commit_mutex.exec(form_onchanges_mutex);
                });

                return commit_mutex.def.then(function () {
                    return self.pre_onchange_hook(barcode).then(function (proceed) {
                        if (proceed) {
                            self.set_value(barcode);       // set the barcode field with the received one
                            return form_onchanges_mutex(); // wait for its onchange to finish
                        }
                    });
                });
            };

            this.process_barcode_mutex.exec(process_barcode);
        }
    },

    _get_records: function(field) {
        var active_view = field.viewmanager.active_view;
        if (active_view.type === "kanban") {
            return active_view.controller.widgets;
        } else {
             // tree view case
            return active_view.controller.records.records;
        }
    },
});

core.form_widget_registry.add('barcode_handler', FormViewBarcodeHandler);

return FormViewBarcodeHandler;

});
