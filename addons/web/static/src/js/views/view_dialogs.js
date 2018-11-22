odoo.define('web.view_dialogs', function (require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var ListController = require('web.ListController');
var ListView = require('web.ListView');
var pyeval = require('web.pyeval');
var SearchView = require('web.SearchView');
var view_registry = require('web.view_registry');

var _t = core._t;

/**
 * Class with everything which is common between FormViewDialog and
 * SelectCreateDialog.
 */
var ViewDialog = Dialog.extend({
    custom_events: _.extend({}, Dialog.prototype.custom_events, {
        push_state: '_onPushState',
        env_updated: function (event) {
            event.stopPropagation();
        },
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
        options.dialogClass = options.dialogClass || '' + ' o_act_window';

        this._super(parent, $.extend(true, {}, options));

        this.res_model = options.res_model || null;
        this.domain = options.domain || [];
        this.context = options.context || {};
        this.options = _.extend(this.options || {}, options || {});

        // FIXME: remove this once a dataset won't be necessary anymore to interact
        // with data_manager and instantiate views
        this.dataset = new data.DataSet(this, this.res_model, this.context);
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
     * @param {function} [options.on_saved] callback executed after saving a
     *   record.  It will be called with the record data, and a boolean which
     *   indicates if something was changed
     * @param {BasicModel} [options.model] if given, it will be used instead of
     *  a new form view model
     * @param {string} [options.recordID] if given, the model has to be given as
     *   well, and in that case, it will be used without loading anything.
     * @param {boolean} [options.shouldSaveLocally] if true, the view dialog
     *   will save locally instead of actually saving (useful for one2manys)
     */
    init: function (parent, options) {
        var self = this;

        this.res_id = options.res_id || null;
        this.on_saved = options.on_saved || (function () {});
        this.context = options.context;
        this.model = options.model;
        this.parentID = options.parentID;
        this.recordID = options.recordID;
        this.shouldSaveLocally = options.shouldSaveLocally;

        var multi_select = !_.isNumber(options.res_id) && !options.disable_multiple_selection;
        var readonly = _.isNumber(options.res_id) && options.readonly;

        if (!options || !options.buttons) {
            options = options || {};
            options.buttons = [{
                text: (readonly ? _t("Close") : _t("Discard")),
                classes: "btn-default o_form_button_cancel",
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
                    text: _t("Save") + ((multi_select)? " " + _t(" & Close") : ""),
                    classes: "btn-primary",
                    click: function () {
                        this._save().then(self.close.bind(self));
                    }
                });

                if (multi_select) {
                    options.buttons.splice(1, 0, {
                        text: _t("Save & New"),
                        classes: "btn-primary",
                        click: function () {
                            this._save().then(self.form_view.createRecord.bind(self.form_view, self.parentID));
                        },
                    });
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
            fields_view_def = $.when(this.options.fields_view);
        } else {
            fields_view_def = this.loadFieldView(this.dataset, this.options.view_id, 'form');
        }

        fields_view_def.then(function (viewInfo) {
            if (self.recordID) {
                self.model.addFieldsInfo(self.recordID, viewInfo);
            }
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
                footer_to_buttons: true,
                default_buttons: false,
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
            self.form_view.appendTo(fragment)
                .then(function () {
                    var $buttons = $('<div>');
                    self.form_view.renderButtons($buttons);
                    self.opened().always(function () {
                        if ($buttons.children().length) {
                            self.$footer.empty().append($buttons.contents());
                        }
                        dom.append(self.$el, fragment, {
                            callbacks: [{widget: self.form_view}],
                            in_DOM: true,
                        });
                    });
                    _super();
                });
        });

        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
            self.on_saved(record, !!changedFields.length);
        });
    },
});

var SelectCreateListController = ListController.extend({
    // Override the ListView to handle the custom events 'open_record' (triggered when clicking on a
    // row of the list) such that it triggers up 'select_record' with its res_id.
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        open_record: function (event) {
            var selectedRecord = this.model.get(event.data.id);
            this.trigger_up('select_record', {
                id: selectedRecord.res_id,
                display_name: selectedRecord.data.display_name,
            });
        },
    }),
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
        search: function (event) {
            event.stopPropagation(); // prevent this event from bubbling up to the view manager
            var d = event.data;
            var searchData = this._process_search_data(d.domains, d.contexts, d.groupbys);
            this.list_controller.reload(searchData);
        },
        get_controller_context: '_onGetControllerContext',
    }),

    /**
     * options:
     * - initial_ids
     * - initial_view: form or search (default search)
     * - list_view_options: dict of options to pass to the List View
     * - on_selected: optional callback to execute when records are selected
     * - disable_multiple_selection: true to allow create/select multiple records
     */
    init: function () {
        this._super.apply(this, arguments);
        _.defaults(this.options, { initial_view: 'search' });
        this.on_selected = this.options.on_selected || (function () {});
        this.initial_ids = this.options.initial_ids;
    },

    open: function () {
        if (this.options.initial_view !== "search") {
            return this.create_edit_record();
        }
        var self = this;
        var user_context = this.getSession().user_context;

        var _super = this._super.bind(this);
        var context = pyeval.eval_domains_and_contexts({
            domains: [],
            contexts: [user_context, this.context]
        }).context;
        var search_defaults = {};
        _.each(context, function (value_, key) {
            var match = /^search_default_(.*)$/.exec(key);
            if (match) {
                search_defaults[match[1]] = value_;
            }
        });
        this.loadViews(this.dataset.model, this.dataset.get_context(), [[false, 'list'], [false, 'search']], {})
            .then(this.setup.bind(this, search_defaults))
            .then(function (fragment) {
                self.opened().then(function () {
                    dom.append(self.$el, fragment, {
                        callbacks: [{widget: self.list_controller}],
                        in_DOM: true,
                    });
                    self.set_buttons(self.__buttons);
                });
                _super();
            });
        return this;
    },

    setup: function (search_defaults, fields_views) {
        var self = this;
        var fragment = document.createDocumentFragment();

        var searchDef = $.Deferred();

        // Set the dialog's header and its search view
        var $header = $('<div/>').addClass('o_modal_header').appendTo(fragment);
        var $pager = $('<div/>').addClass('o_pager').appendTo($header);
        var options = {
            $buttons: $('<div/>').addClass('o_search_options').appendTo($header),
            search_defaults: search_defaults,
        };
        var searchview = new SearchView(this, this.dataset, fields_views.search, options);
        searchview.prependTo($header).done(function () {
            var d = searchview.build_search_data();
            if (self.initial_ids) {
                d.domains.push([["id", "in", self.initial_ids]]);
                self.initial_ids = undefined;
            }
            var searchData = self._process_search_data(d.domains, d.contexts, d.groupbys);
            searchDef.resolve(searchData);
        });

        return $.when(searchDef).then(function (searchResult) {
            // Set the list view
            var listView = new ListView(fields_views.list, _.extend({
                context: searchResult.context,
                domain: searchResult.domain,
                groupBy: searchResult.groupBy,
                modelName: self.dataset.model,
                hasSelectors: !self.options.disable_multiple_selection,
                readonly: true,
            }, self.options.list_view_options));
            listView.setController(SelectCreateListController);
            return listView.getController(self);
        }).then(function (controller) {
            self.list_controller = controller;
            // Set the dialog's buttons
            self.__buttons = [{
                text: _t("Cancel"),
                classes: "btn-default o_form_button_cancel",
                close: true,
            }];
            if (!self.options.no_create) {
                self.__buttons.unshift({
                    text: _t("Create"),
                    classes: "btn-primary",
                    click: self.create_edit_record.bind(self)
                });
            }
            if (!self.options.disable_multiple_selection) {
                self.__buttons.unshift({
                    text: _t("Select"),
                    classes: "btn-primary o_select_button",
                    disabled: true,
                    close: true,
                    click: function () {
                        var records = self.list_controller.getSelectedRecords();
                        var values = _.map(records, function (record) {
                            return {
                                id: record.res_id,
                                display_name: record.data.display_name,
                            };
                        });
                        self.on_selected(values);
                    },
                });
            }
            return self.list_controller.appendTo(fragment);
        }).then(function () {
            searchview.toggle_visibility(true);
            self.list_controller.do_show();
            self.list_controller.renderPager($pager);
            return fragment;
        });
    },
    _process_search_data: function (domains, contexts, groupbys) {
        var results = pyeval.eval_domains_and_contexts({
            domains: [this.domain].concat(domains),
            contexts: [this.context].concat(contexts),
            group_by_seq: groupbys || [],
            eval_context: this.getSession().user_context,
        });
        var context = _.omit(results.context, function (value, key) { return key.indexOf('search_default_') === 0; });
        return {
            context: context,
            domain: results.domain,
            groupBy: results.group_by,
        };
    },
    create_edit_record: function () {
        var self = this;
        var dialog = new FormViewDialog(this, _.extend({}, this.options, {
            on_saved: function (record) {
                var values = [{
                    id: record.res_id,
                    display_name: record.data.display_name,
                }];
                self.on_selected(values);
            },
        })).open();
        dialog.on('closed', this, this.close);
        return dialog;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles a context request: provides to the caller the context of the
     * list controller.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {function} ev.data.callback used to send the requested context
     */
    _onGetControllerContext: function (ev) {
        ev.stopPropagation();
        var context = this.list_controller.getContext();
        ev.data.callback(context);
    },
});

return {
    FormViewDialog: FormViewDialog,
    SelectCreateDialog: SelectCreateDialog,
};

});
