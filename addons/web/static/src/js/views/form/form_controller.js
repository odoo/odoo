odoo.define('web.FormController', function (require) {
"use strict";

var BasicController = require('web.BasicController');
var dialogs = require('web.view_dialogs');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Sidebar = require('web.Sidebar');
var Context = require('web.Context');

var _t = core._t;
var qweb = core.qweb;

var FormController = BasicController.extend({
    // className: "o_form_view",
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        add_one2many_record: '_onAddOne2ManyRecord',
        bounce_edit: '_onBounceEdit',
        button_clicked: '_onButtonClicked',
        open_record: '_onOpenRecord',
        toggle_column_order: '_onToggleColumnOrder',
    }),
    /**
     * @override
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        this.actionButtons = params.actionButtons;
        this.footerToButtons = params.footerToButtons;
        this.defaultButtons = params.defaultButtons;
        this.hasSidebar = params.hasSidebar;
        this.toolbar = params.toolbar;
        this.mode = params.mode;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This method is supposed to focus the first active control, I think. It
     * is currently only called by the FormViewDialog.
     *
     * @todo To be implemented
     */
    autofocus: function () {
    },
    /**
     * Determines if we can discard the current change.  If the model is not
     * dirty, that is not a problem.  However, if it is dirty, we have to ask
     * the user for confirmation.
     *
     * @override
     * @returns {Deferred} If the deferred is resolved, we assume the changes
     *   can be discarded.  If it is rejected, then we cannot discard.
     */
    canBeDiscarded: function () {
        if (!this.isDirty) {
            return $.when();
        }
        var message = _t("The record has been modified, your changes will be discarded. Are you sure you want to leave this page ?");
        var def = $.Deferred();
        var options = {
            title: _t("Warning"),
            confirm_callback: function () {
                this.on('closed', null, def.resolve.bind(def));
            },
            cancel_callback: def.reject.bind(def)
        };
        var dialog = Dialog.confirm(this, message, options);
        dialog.$modal.on('hidden.bs.modal', def.reject.bind(def));
        return def;
    },
    /**
     * @returns {boolean}
     */
    checkInvalidFields: function () {
        var invalidFields = this.renderer.checkInvalidFields();
        if (invalidFields.length) {
            this._notifyInvalidFields(invalidFields);
        }
        return !!invalidFields.length;
    },
    /**
     * This method switches the form view in edit mode, with a new record.
     *
     * @returns {Deferred}
     */
    createRecord: function () {
        var self = this;
        var record = this.model.get(this.handle, {raw: true});
        return this.model.makeDefaultRecord(this.modelName, {
                context: this.context,
                fieldsInfo: record.fieldsInfo,
                fieldNames: record.fieldNames,
                fields: record.fields,
                res_ids: record.res_ids,
            }).then(function (handle) {
                self.handle = handle;
                self._updateEnv();
                self._toEditMode();
            });
    },
    /**
     * Returns the current res_id, wrapped in a list. This is only used by the
     * sidebar (and the debugmanager)
     *
     * @todo This should be private.  Need to change sidebar code
     *
     * @returns {number[]} either [current res_id] or []
     */
    getSelectedIds: function () {
        var env = this.model.get(this.handle, {env: true});
        // FIX ME : fix sidebar widget
        return env.currentId ? [env.currentId] : [];
    },
    /**
     * @override method from AbstractController
     * @returns {string}
     */
    getTitle: function () {
        var dataPoint = this.model.get(this.handle, {raw: true});
        return dataPoint.data.display_name || _t('New');
    },
    /**
     * Render buttons for the control panel.  The form view can be rendered in
     * a dialog, and in that case, if we have buttons defined in the footer, we
     * have to use them instead of the standard buttons.
     *
     * @override method from AbstractController
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        var $footer = this.$('footer');
        if (!this.defaultButtons && (!this.footerToButtons || !$footer.length)) {
            return;
        }
        this.$buttons = $('<div/>');
        if (this.footerToButtons && $footer.length) {
            this.$buttons.append($footer.detach().contents());
        } else {
            this.$buttons.append(qweb.render("FormView.buttons", {widget: this}));
            this.$buttons.on('click', '.o_form_button_edit', this._toEditMode.bind(this));
            this.$buttons.on('click', '.o_form_button_save', this.saveRecord.bind(this));
            this.$buttons.on('click', '.o_form_button_cancel', this._onDiscardChange.bind(this));
            this.$buttons.on('click', '.o_form_button_create', this.createRecord.bind(this));

            this._updateButtons();
        }
        this.$buttons.appendTo($node);
    },
    /**
     * The form view has to prevent a click on the pager if the form is dirty
     *
     * @override method from BasicController
     * @param {jQueryElement} $node
     * @param {Object} options
     */
    renderPager: function ($node, options) {
        options = _.extend({}, options, {
            validate: this.canBeDiscarded.bind(this),
        });
        this._super($node, options);
    },
    /**
     * Instantiate and render the sidebar if a sidebar is requested
     * Sets this.sidebar
     * @param {jQuery} [$node] a jQuery node where the sidebar should be
     *   inserted
     **/
    renderSidebar: function ($node) {
        if (!this.sidebar && this.hasSidebar) {
            this.sidebar = new Sidebar(this, {
                editable: this.is_action_enabled('edit')
            });
            if (this.toolbar) {
                this.sidebar.add_toolbar(this.toolbar);
            }
            var otherItems = [];
            if (this.is_action_enabled('delete')) {
                otherItems.push({
                    label: _t('Delete'),
                    callback: this._deleteRecords.bind(this, [this.handle]),
                });
            }
            if (this.is_action_enabled('create')) {
                otherItems.push({
                    label: _t('Duplicate'),
                    callback: this._onDuplicateRecord.bind(this),
                });
            }
            this.sidebar.add_items('other', otherItems);
            this.sidebar.appendTo($node);

            // Show or hide the sidebar according to the view mode
            this._updateSidebar();
        }
    },
    /**
     * Save the current record
     *
     * @param {Object} options
     * @param {boolean} [options.stayInEdit=false] if true, don't switch to
     *   readonly mode after saving the record
     * @param {boolean} [options.reload=true] if true, reload the record after
     *   saving
     * @param {boolean} [options.localSave=false] if true, the record will only
     *   be 'locally' saved: its changes will move from the _changes key to the
     *   data key
     * @returns {Deferred}
     */
    saveRecord: function (options) {
        var self = this;
        options = options || {};
        var stayInEdit = 'stayInEdit' in options ? options.stayInEdit : false;
        var shouldReload = 'reload' in options ? options.reload : true;
        if (!this.model.isDirty(this.handle) && !this.model.isNew(this.handle)) {
            if (!stayInEdit) {
                this._toReadOnlyMode();
            }
            return $.Deferred().resolve();
        } else {
            if (this.checkInvalidFields()) {
                return $.Deferred().reject();
            } else {
                return this.model.save(this.handle, {reload: shouldReload, localSave: options.localSave})
                    .then(function () {
                        if (!stayInEdit) {
                            self._toReadOnlyMode();
                        }
                        self.isDirty = false;
                    });
            }
        }
    },
    /**
     * We need to check for all 'mode' change, because the information is not
     * available from the model.
     *
     * @override
     * @param {Object} params
     * @returns {Deferred}
     */
    update: function (params) {
        this.mode = params.mode || this.mode;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * When the user clicks on a form button, this function determines what
     * should happen.
     *
     * @private
     * @param {Object} attrs the attrs of the button clicked
     * @param {Object} [record] the current state of the view
     * @returns {Deferred}
     */
    _callButtonAction: function (attrs, record) {
        var self = this;
        var def = $.Deferred();
        record = record || this.model.get(this.handle);
        var recordID = record.data.id;
        this.trigger_up('execute_action', {
            action_data: _.extend({}, attrs, {
                context: _.extend(record.getContext(), attrs.context),
            }),
            model: record.model,
            record_id: recordID,
            on_closed: function (reason) {
                if (!_.isObject(reason)) {
                    return self.reload();
                }
            },
            on_fail: this.reload.bind(this),
            on_success: def.resolve.bind(def),
        });
        return def;
    },
    /**
     * @override method from FieldManagerMixin
     * @private
     * @param {string} id it is ignored, because we already know it.
     * @param {string[]} fields
     * @param {OdooEvent} event the event that triggered the change
     */
    _confirmChange: function (id, fields, event) {
        var record = this.model.get(this.handle);
        this.renderer.updateWidgets(fields, record, event);
    },
    /**
     * When a save operation has been confirmed from the model, this method is
     * called.
     *
     * @private
     * @override method from field manager mixin
     * @param {string} id
     */
    _confirmSave: function (id) {
        this.isDirty = false;
        if (id === this.handle) {
            this.reload();
        } else {
            // a subrecord changed, so update the corresponding relational field
            // i.e. the one whose value is a record with the given id or a list
            // having a record with the given id in its data
            var record = this.model.get(this.handle);
            var fieldsChanged = _.findKey(record.data, function (d) {
                return _.isObject(d) &&
                    (d.id === id || _.findWhere(d.data, {id: id}));
            });
            this.renderer.updateWidgets([fieldsChanged], record);
        }
    },
    /**
     * Helper function to display a warning that some field have an invalid
     * value.  This is used when a save operation cannot be completed.
     *
     * @private
     * @param {string[]} invalidFields list of field names
     */
    _notifyInvalidFields: function (invalidFields) {
        var record = this.model.get(this.handle, {raw: true});
        var fields = record.fields;
        var warnings = invalidFields.map(function (field_name) {
            var fieldStr = fields[field_name].string;
            return _.str.sprintf('<li>%s</li>', _.escape(fieldStr));
        });
        warnings.unshift('<ul>');
        warnings.push('</ul>');
        this.do_warn(_t("The following fields are invalid:"), warnings.join(''));
    },
    /**
     * We just add the current ID to the state pushed. This allows the web
     * client to add it in the url, for example.
     *
     * @override method from AbstractController
     * @private
     * @param {Object} [state]
     */
    _pushState: function (state) {
        state = state || {};
        var env = this.model.get(this.handle, {env: true});
        state.id = env.currentId;
        this._super(state);
    },
    /**
     * Change the view mode to 'edit'
     *
     * @see _toReadOnlyMode
     * @private
     */
    _toEditMode: function () {
        this.$el.addClass('o_form_editable');
        this.update({mode: "edit"}, {reload: false});
    },
    /**
     * Change the view mode to 'readonly'
     *
     * @see _toEditMode
     * @private
     */
    _toReadOnlyMode: function () {
        this.$el.removeClass('o_form_editable');
        this.update({mode: "readonly"}, {reload: false});
    },
    /**
     * Updates the controller's title according to the new state
     *
     * @override
     * @private
     * @param {Object} state
     * @returns {Deferred}
     */
    _update: function (state) {
        var title = this.getTitle();
        this.set('title', title);
        this._updateButtons();
        this._updateSidebar();
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     */
    _updateButtons: function () {
        if (this.$buttons) {
            var edit_mode = (this.mode === 'edit');
            this.$buttons.find('.o_form_buttons_edit')
                         .toggleClass('o_hidden', !edit_mode);
            this.$buttons.find('.o_form_buttons_view')
                         .toggleClass('o_hidden', edit_mode);
        }
    },
    /**
     * Show or hide the sidebar according to the actual_mode
     * @private
     */
    _updateSidebar: function () {
        if (this.sidebar) {
            this.sidebar.do_toggle(this.mode === 'readonly');
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onAddOne2ManyRecord: function (event) {
        var field = event.data.field;
        var attrs = event.data.attrs;
        new dialogs.FormViewDialog(this, {
            res_model: field.relation,
            shouldSaveLocally: true,
            domain: event.data.domain,
            context: event.data.context,
            on_save: event.data.on_save,
            title: _t('Create: ') + field.string,
            initial_view: 'form',
            fields_view: attrs.views ? attrs.views.form : undefined,
            form_view_options: {'not_interactible_on_create': true},
            model: this.model,
            parentID: this.handle,
        }).open();
    },
    /**
     * Bounce the 'Edit' button.
     *
     * @private
     */
    _onBounceEdit: function () {
        if (this.$buttons) {
            this.$buttons.find('.o_form_button_edit').openerpBounce();
        }
    },
    /**
     * If the user clicks on 'Discard', we have to check if the changes can be
     * discarded, then actually do it.
     *
     * @private
     */
    _onDiscardChange: function () {
        var self = this;
        this.canBeDiscarded().then(function () {
            self.model.discardChanges(self.handle);
            self.isDirty = false;
            if (!self.model.isNew(self.handle)) {
                self._toReadOnlyMode();
            } else {
                self.do_action('history_back');
            }
        });
    },
    /**
     * Called when the user clicks on 'Duplicate Record' in the sidebar
     *
     * @private
     */
    _onDuplicateRecord: function () {
        var self = this;
        this.model.duplicateRecord(this.handle)
            .then(function (handle) {
                self.isDirty = false;
                self.handle = handle;
                self._updateEnv();
                self._toEditMode();
            });
    },
    /**
     * This method comes from the field manager mixin. We force to save directly
     * the changes if the form is in readonly, because in that case the changes
     * come from widgets that are editable even in readonly (e.g. Priority).
     *
     * @override
     * @private
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        if (this.mode === 'readonly') {
            event.data.force_save = true;
        }
        this._super.apply(this, arguments);
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onButtonClicked: function (event) {
        // stop the event's propagation as a form controller might have other
        // form controllers in its descendants (e.g. in a FormViewDialog)
        event.stopPropagation();
        var self = this;
        var def;

        var attrs = event.data.attrs;
        if (attrs.confirm) {
            var d = $.Deferred();
            Dialog.confirm(this, attrs.confirm, { confirm_callback: function () {
                self._callButtonAction(attrs, event.data.record);
            }}).on("closed", null, function () {
                d.resolve();
            });
            def = d.promise();
        } else if (attrs.special) {
            def = this._callButtonAction(attrs, event.data.record);
        } else {
            def = this.saveRecord().then(function () {
                return self._callButtonAction(attrs, event.data.record);
            });
        }
        def.then(function () {
            self.reload();
        });

        if (event.data.show_wow) {
            def.then(function () {
                self.show_wow();
            });
        }
    },
    /**
     * Open a record in a form view dialog
     *
     * @private
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
        var self = this;
        var record = this.model.get(event.data.id);
        var model = record.model;
        var res_id = record.res_id;
        var fieldsViewDef;
        if (event.data.form_view) {
            fieldsViewDef = $.when({form: event.data.form_view});
        } else {
            fieldsViewDef = this.loadViews(model, new Context(event.data.context), [[null, 'form']], {});
        }
        fieldsViewDef.then(function (views) {
            new dialogs.FormViewDialog(self, {
                res_model: model,
                res_id: res_id,
                fields_view: views.form,
                context: record.getContext(),
                readonly: event.data.readonly,
                title: _t("Open: ") + event.data.string,
                on_save: event.data.on_save,
                on_saved: event.data.on_saved,
                model: self.model,
                parentID: self.handle,
                recordID: record.id,
                shouldSaveLocally: event.data.shouldSaveLocally,
            }).open();
        });
    },
    /**
     * This method is called when someone tries to sort a column, most likely
     * in a x2many list view
     *
     * @private
     * @param {OdooEvent} event
     */
    _onToggleColumnOrder: function (event) {
        this.model.setSort(event.data.id, event.data.name);
        var field = event.data.field;
        var state = this.model.get(this.handle);
        this.renderer.updateWidgets([field], state);
    },

});

return FormController;

});

    // load_record: function (id) {
    //     var index = _.indexOf(this.datasetIds, this.currentId);
    //     return this.model.load({
    //         // context: this.options.context,
    //         id: id,
    //         model: this.modelName,
    //         offset: index,
    //         res_ids: this.datasetIds,
    //         count: this.datasetIds.length,
    //     });
    // },
    // do_show: function (view_options) {
    //     var defs = [];
    //     defs.push(this._super.apply(this, arguments));
    //     if (this.has_been_started) {
    //         var dataset = view_options && view_options.dataset;
    //         this.dataset_ids = dataset ? dataset.res_ids : this.dataset.ids;
    //         this.current_id = dataset ? dataset.current_id : this.dataset.ids[this.dataset.index];
    //         defs.push(this.load_record(this.current_id).then(this.update_state.bind(this)));
    //     }
    //     this.has_been_started = true;
    //     return $.when.apply($, defs);
    // },
    // _onDeletedRecords: function (ids) {
    //     var index = this.dataset_ids.indexOf(this.current_id);
    //     this.dataset_ids.splice(index, 1);
    //     this.current_id = this.dataset_ids[index];
    //     if (!this.current_id) {
    //         this.current_id = this.dataset_ids[this.dataset_ids.length - 1];
    //     }
    //     if (!this.current_id) {
    //         this.do_action('history_back');
    //     } else {
    //         this.load_record(this.current_id).then(this.update_state.bind(this));
    //     }
    // },
    // _callButtonAction: function (attrs, record) {
    //     var self = this;
    //     var def = $.Deferred();
    //     record = record || this.model.get(this.db_id);
    //     var record_id = record.data.id;
    //     this.trigger_up('execute_action', {
    //         action_data: _.extend({}, attrs, { context: _.extend(record.getContext(), attrs.context) }),
    //         dataset: this.dataset,
    //         record_id: record_id,
    //         on_close: function (reason) {
    //             if (!_.isObject(reason)) {
    //                 return self.load_record(record_id).then(self.update_state.bind(self));
    //             }
    //         },
    //         on_fail: function () {
    //             self.load_record(record_id).then(function (db_id) {
    //                 self.update_state(db_id);
    //                 def.resolve();
    //             });
    //         },
    //         on_success: def.resolve.bind(def),
    //     });
    //     return def;
    // },
    // show_wow: function () {
    //     var others = ['o_wow_peace', 'o_wow_heart'];
    //     var wow_class = Math.random() <= 0.9 ? 'o_wow_thumbs' : _.sample(others);
    //     var $body = $('body');
    //     $body.addClass(wow_class);
    //     setTimeout(function () {
    //         $body.removeClass(wow_class);
    //     }, 1000);
    // },
    // _onFieldChanged: function (event) {
    //     if (this.mode === 'readonly') {
    //         event.data.force_save = true;
    //     }
    //     this._super.apply(this, arguments);
    // },
    // update_renderer: function () {
    //     var state = this.model.get(this.db_id);
    //     this.renderer.update(state, {mode: this.mode});
    // },
        // do_action: function (event) {
        //     this.do_action(event.data.action, event.data.options || {}).then(function (result) {
        //         if (event.data.on_success) {
        //             event.data.on_success(result);
        //         }
        //     });
        // },

        // this.dataset_ids = this.options.dataset ? this.options.dataset.res_ids : this.dataset.ids;
        // this.current_id = this.options.dataset ? this.options.dataset.current_id : this.dataset.ids[this.dataset.index];
        // this.options.context = _.extend({}, this.options.action.context, this.options.context);
