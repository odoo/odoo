odoo.define('web.view_dialogs', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var view_registry = require('web.view_registry');
var select_create_controllers_registry = require('web.select_create_controllers_registry');

var _t = core._t;

/**
 * Class with everything which is common between FormViewDialog and
 * SelectCreateDialog.
 */
var ViewDialog = Dialog.extend({
    custom_events: _.extend({}, Dialog.prototype.custom_events, {
        push_state: '_onPushState',
    }),
    /**
     * @constructor
     * @param {Widget} parent
     * @param {options} [options]
     * @param {string} [options.dialogClass=o_act_window]
     * @param {string} [options.res_model] the model of the record(s) to open
     * @param {any[]} [options.domain]
     * @param {Object} [options.context]
     */
    init: function (parent, options) {
        options = options || {};
        options.fullscreen = config.device.isMobile;
        options.dialogClass = options.dialogClass || '' + ' o_act_window';

        this._super(parent, $.extend(true, {}, options));

        this.res_model = options.res_model || null;
        this.domain = options.domain || [];
        this.context = options.context || {};
        this.options = _.extend(this.options || {}, options || {});
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * We stop all push_state events from bubbling up.  It would be weird to
     * change the url because a dialog opened.
     *
     * @param {OdooEvent} event
     */
    _onPushState: function (event) {
        event.stopPropagation();
    },
});

/**
 * Create and edit dialog (displays a form view record and leave once saved)
 */
var FormViewDialog = ViewDialog.extend({
    /**
     * @param {Widget} parent
     * @param {Object} [options]
     * @param {string} [options.parentID] the id of the parent record. It is
     *   useful for situations such as a one2many opened in a form view dialog.
     *   In that case, we want to be able to properly evaluate domains with the
     *   'parent' key.
     * @param {integer} [options.res_id] the id of the record to open
     * @param {Object} [options.form_view_options] dict of options to pass to
     *   the Form View @todo: make it work
     * @param {Object} [options.fields_view] optional form fields_view
     * @param {boolean} [options.readonly=false] only applicable when not in
     *   creation mode
     * @param {boolean} [options.deletable=false] whether or not the record can
     *   be deleted
     * @param {boolean} [options.disable_multiple_selection=false] set to true
     *   to remove the possibility to create several records in a row
     * @param {function} [options.on_saved] callback executed after saving a
     *   record.  It will be called with the record data, and a boolean which
     *   indicates if something was changed
     * @param {function} [options.on_remove] callback executed when the user
     *   clicks on the 'Remove' button
     * @param {BasicModel} [options.model] if given, it will be used instead of
     *  a new form view model
     * @param {string} [options.recordID] if given, the model has to be given as
     *   well, and in that case, it will be used without loading anything.
     * @param {boolean} [options.shouldSaveLocally] if true, the view dialog
     *   will save locally instead of actually saving (useful for one2manys)
     */
    init: function (parent, options) {
        var self = this;
        options = options || {};

        this.res_id = options.res_id || null;
        this.on_saved = options.on_saved || (function () {});
        this.on_remove = options.on_remove || (function () {});
        this.context = options.context;
        this.model = options.model;
        this.parentID = options.parentID;
        this.recordID = options.recordID;
        this.shouldSaveLocally = options.shouldSaveLocally;
        this.readonly = options.readonly;
        this.deletable = options.deletable;
        this.disable_multiple_selection = options.disable_multiple_selection;
        var oBtnRemove = 'o_btn_remove';

        var multi_select = !_.isNumber(options.res_id) && !options.disable_multiple_selection;
        var readonly = _.isNumber(options.res_id) && options.readonly;

        if (!options.buttons) {
            options.buttons = [{
                text: (readonly ? _t("Close") : _t("Discard")),
                classes: "btn-secondary o_form_button_cancel",
                close: true,
                click: function () {
                    if (!readonly) {
                        self.form_view.model.discardChanges(self.form_view.handle, {
                            rollback: self.shouldSaveLocally,
                        });
                    }
                },
            }];

            if (!readonly) {
                options.buttons.unshift({
                    text: (multi_select ? _t("Save & Close") : _t("Save")),
                    classes: "btn-primary",
                    click: function () {
                        self._save().then(self.close.bind(self));
                    }
                });

                if (multi_select) {
                    options.buttons.splice(1, 0, {
                        text: _t("Save & New"),
                        classes: "btn-primary",
                        click: function () {
                            self._save()
                                .then(self.form_view.createRecord.bind(self.form_view, self.parentID))
                                .then(function () {
                                    if (!self.deletable) {
                                        return;
                                    }
                                    self.deletable = false;
                                    self.buttons = self.buttons.filter(function (button) {
                                        return button.classes.split(' ').indexOf(oBtnRemove) < 0;
                                    });
                                    self.set_buttons(self.buttons);
                                    self.set_title(_t("Create ") + _.str.strRight(self.title, _t("Open: ")));
                                });
                        },
                    });
                }

                var multi = options.disable_multiple_selection;
                if (!multi && this.deletable) {
                    this._setRemoveButtonOption(options, oBtnRemove);
                }
            }
        }
        this._super(parent, options);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Open the form view dialog.  It is necessarily asynchronous, but this
     * method returns immediately.
     *
     * @returns {FormViewDialog} this instance
     */
    open: function () {
        var self = this;
        var _super = this._super.bind(this);
        var FormView = view_registry.get('form');
        var fields_view_def;
        if (this.options.fields_view) {
            fields_view_def = Promise.resolve(this.options.fields_view);
        } else {
            fields_view_def = this.loadFieldView(this.res_model, this.context, this.options.view_id, 'form');
        }

        fields_view_def.then(function (viewInfo) {
            var refinedContext = _.pick(self.context, function (value, key) {
                return key.indexOf('_view_ref') === -1;
            });
            var formview = new FormView(viewInfo, {
                modelName: self.res_model,
                context: refinedContext,
                ids: self.res_id ? [self.res_id] : [],
                currentId: self.res_id || undefined,
                index: 0,
                mode: self.res_id && self.options.readonly ? 'readonly' : 'edit',
                footerToButtons: true,
                default_buttons: false,
                withControlPanel: false,
                model: self.model,
                parentID: self.parentID,
                recordID: self.recordID,
            });
            return formview.getController(self);
        }).then(function (formView) {
            self.form_view = formView;
            var fragment = document.createDocumentFragment();
            if (self.recordID && self.shouldSaveLocally) {
                self.model.save(self.recordID, {savePoint: true});
            }
            return self.form_view.appendTo(fragment)
                .then(function () {
                    self.opened().then(function () {
                        var $buttons = $('<div>');
                        self.form_view.renderButtons($buttons);
                        if ($buttons.children().length) {
                            self.$footer.empty().append($buttons.contents());
                        }
                        dom.append(self.$el, fragment, {
                            callbacks: [{widget: self.form_view}],
                            in_DOM: true,
                        });
                    });
                    return _super();
                });
        });

        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _focusOnClose: function() {
        var isFocusSet = false;
        this.trigger_up('form_dialog_discarded', {
            callback: function (isFocused) {
                isFocusSet = isFocused;
            },
        });
        return isFocusSet;
    },

    /**
     * @private
     */
    _remove: function () {
        return Promise.resolve(this.on_remove());
    },

    /**
     * @private
     * @returns {Promise}
     */
    _save: function () {
        var self = this;
        return this.form_view.saveRecord(this.form_view.handle, {
            stayInEdit: true,
            reload: false,
            savePoint: this.shouldSaveLocally,
            viewType: 'form',
        }).then(function (changedFields) {
            // record might have been changed by the save (e.g. if this was a new record, it has an
            // id now), so don't re-use the copy obtained before the save
            var record = self.form_view.model.get(self.form_view.handle);
            return self.on_saved(record, !!changedFields.length);
        });
    },

    /**
     * Set the "remove" button into the options' buttons list
     *
     * @private
     * @param {Object} options The options object to modify
     * @param {string} btnClasses The classes for the remove button
     */
    _setRemoveButtonOption(options, btnClasses) {
        const self = this;
        options.buttons.push({
            text: _t("Remove"),
            classes: 'btn-secondary ' + btnClasses,
            click: function() {
                self._remove().then(self.close.bind(self));
            }
        });
    },
});

/**
 * Search dialog (displays a list of records and permits to create a new one by switching to a form view)
 */
var SelectCreateDialog = ViewDialog.extend({
    custom_events: _.extend({}, ViewDialog.prototype.custom_events, {
        select_record: function (event) {
            if (!this.options.readonly) {
                this.on_selected([event.data]);
                this.close();
            }
        },
        selection_changed: function (event) {
            event.stopPropagation();
            this.$footer.find(".o_select_button").prop('disabled', !event.data.selection.length);
        },
    }),

    /**
     * options:
     * - initial_ids
     * - initial_view: form or search (default search)
     * - list_view_options: dict of options to pass to the List View
     * - on_selected: optional callback to execute when records are selected
     * - disable_multiple_selection: true to allow create/select multiple records
     * - dynamicFilters: filters to add to the searchview
     */
    init: function () {
        this._super.apply(this, arguments);
        _.defaults(this.options, { initial_view: 'search' });
        this.on_selected = this.options.on_selected || (function () {});
        this.on_closed = this.options.on_closed || (function () {});
        this.initialIDs = this.options.initial_ids;
        this.viewType = 'list';
    },

    open: function () {
        if (this.options.initial_view !== "search") {
            return this.create_edit_record();
        }
        var self = this;
        var _super = this._super.bind(this);
        var viewRefID = this.viewType === 'kanban' ?
            (this.options.kanban_view_ref && JSON.parse(this.options.kanban_view_ref) || false) : false;
        return this.loadViews(this.res_model, this.context, [[viewRefID, this.viewType], [false, 'search']], {})
            .then(this.setup.bind(this))
            .then(function (fragment) {
                self.opened().then(function () {
                    dom.append(self.$el, fragment, {
                        callbacks: [{widget: self.viewController}],
                        in_DOM: true,
                    });
                    self.set_buttons(self.__buttons);
                });
                return _super();
            });
    },

    setup: function (fieldsViews) {
        var self = this;
        var fragment = document.createDocumentFragment();

        var domain = this.domain;
        if (this.initialIDs) {
            domain = domain.concat([['id', 'in', this.initialIDs]]);
        }
        var ViewClass = view_registry.get(this.viewType);
        var viewOptions = {};
        var selectCreateController;
        if (this.viewType === 'list') { // add listview specific options
            _.extend(viewOptions, {
                hasSelectors: !this.options.disable_multiple_selection,
                readonly: true,

            }, this.options.list_view_options);
            selectCreateController = select_create_controllers_registry.SelectCreateListController;
        }
        if (this.viewType === 'kanban') {
            _.extend(viewOptions, {
                noDefaultGroupby: true,
                selectionMode: this.options.selectionMode || false,
            });
            selectCreateController = select_create_controllers_registry.SelectCreateKanbanController;
        }
        var view = new ViewClass(fieldsViews[this.viewType], _.extend(viewOptions, {
            action: {
                controlPanelFieldsView: fieldsViews.search,
                help: _.str.sprintf("<p>%s</p>", _t("No records found!")),
            },
            action_buttons: false,
            dynamicFilters: this.options.dynamicFilters,
            context: this.context,
            domain: domain,
            modelName: this.res_model,
            withBreadcrumbs: false,
            withSearchPanel: false,
        }));
        view.setController(selectCreateController);
        return view.getController(this).then(function (controller) {
            self.viewController = controller;
            // render the footer buttons
            self._prepareButtons();
            return self.viewController.appendTo(fragment);
        }).then(function () {
            return fragment;
        });
    },
    close: function () {
        this._super.apply(this, arguments);
        this.on_closed();
    },
    create_edit_record: function () {
        var self = this;
        var dialog = new FormViewDialog(this, _.extend({}, this.options, {
            on_saved: function (record) {
                var values = [{
                    id: record.res_id,
                    display_name: record.data.display_name || record.data.name,
                }];
                self.on_selected(values);
            },
        })).open();
        dialog.on('closed', this, this.close);
        return dialog;
    },
    /**
     * @override
     */
    _focusOnClose: function() {
        var isFocusSet = false;
        this.trigger_up('form_dialog_discarded', {
            callback: function (isFocused) {
                isFocusSet = isFocused;
            },
        });
        return isFocusSet;
    },
    /**
     * prepare buttons for dialog footer based on options
     *
     * @private
     */
    _prepareButtons: function () {
        this.__buttons = [{
            text: _t("Cancel"),
            classes: 'btn-secondary o_form_button_cancel',
            close: true,
        }];
        if (!this.options.no_create) {
            this.__buttons.unshift({
                text: _t("Create"),
                classes: 'btn-primary',
                click: this.create_edit_record.bind(this)
            });
        }
        if (!this.options.disable_multiple_selection) {
            this.__buttons.unshift({
                text: _t("Select"),
                classes: 'btn-primary o_select_button',
                disabled: true,
                close: true,
                click: function () {
                    var records = this.viewController.getSelectedRecords();
                    var values = _.map(records, function (record) {
                        return {
                            id: record.res_id,
                            display_name: record.data.display_name,
                        };
                    });
                    this.on_selected(values);
                },
            });
        }
    },
});

return {
    FormViewDialog: FormViewDialog,
    SelectCreateDialog: SelectCreateDialog,
};

});
