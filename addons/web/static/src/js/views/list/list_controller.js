odoo.define('web.ListController', function (require) {
"use strict";

/**
 * The List Controller controls the list renderer and the list model.  Its role
 * is to allow these two components to communicate properly, and also, to render
 * and bind all extra buttons/pager in the control panel.
 */

var core = require('web.core');
var BasicController = require('web.BasicController');
var DataExport = require('web.DataExport');
var pyeval = require('web.pyeval');
var Sidebar = require('web.Sidebar');

var _t = core._t;
var qweb = core.qweb;

var ListController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        add_record: '_onAddRecord',
        button_clicked: '_onButtonClicked',
        edit_line: '_onEditLine',
        save_line: '_onSaveLine',
        resequence: '_onResequence',
        selection_changed: '_onSelectionChanged',
        toggle_column_order: '_onToggleColumnOrder',
        toggle_group: '_onToggleGroup',
    }),
    /**
     * @constructor
     * @override
     * @param {Object} params
     * @param {boolean} params.editable
     * @param {boolean} params.hasSidebar
     * @param {Object} params.toolbarActions
     * @param {boolean} params.noLeaf
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.hasSidebar = params.hasSidebar;
        this.toolbarActions = params.toolbarActions || {};
        this.editable = params.editable;
        this.noLeaf = params.noLeaf;
        this.selectedRecords = params.selectedRecords || [];
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Calculate the active domain of the list view. This should be done only
     * if the header checkbox has been checked. This is done by evaluating the
     * search results, and then adding the dataset domain (i.e. action domain).
     *
     * @todo This is done only for the data export.  The full mechanism is wrong,
     * this method should be private, most of the code in the sidebar should be
     * moved to the controller, and we should not use the getParent method...
     *
     * @returns {Deferred<array[]>} a deferred that resolve to the active domain
     */
    getActiveDomain: function () {
        // TODO: this method should be synchronous...
        var self = this;
        if (this.$('thead .o_list_record_selector input').prop('checked')) {
            var searchView = this.getParent().searchview; // fixme
            var searchData = searchView.build_search_data();
            var userContext = this.getSession().user_context;
            var results = pyeval.eval_domains_and_contexts({
                domains: searchData.domains,
                contexts: [userContext].concat(searchData.contexts),
                group_by_seq: searchData.groupbys || []
            });
            var record = self.model.get(self.handle, {raw: true});
            return $.when(record.getDomain().concat(results.domain || []));
        } else {
            return $.Deferred().resolve();
        }
    },
    /**
     * Returns the list of currently selected res_ids (with the check boxes on
     * the left)
     *
     * @override
     *
     * @returns {number[]} list of res_ids
     */
    getSelectedIds: function () {
        return _.map(this.getSelectedRecords(), function (record) {
            return record.res_id;
        });
    },
    /**
     * Returns the list of currently selected records (with the check boxes on
     * the left)
     *
     * @returns {Object[]} list of records
     */
    getSelectedRecords: function () {
        var self = this;
        return _.map(this.selectedRecords, function (db_id) {
            return self.model.get(db_id, {raw: true});
        });
    },
    /**
     * Display and bind all buttons in the control panel
     *
     * Note: clicking on the "Save" button does nothing special. Indeed, all
     * editable rows are saved once left and clicking on the "Save" button does
     * induce the leaving of the current row.
     *
     * @override
     * @param {jQuery} $node
     */
    renderButtons: function ($node) {
        if (!this.noLeaf && this.hasButtons) {
            this.$buttons = $(qweb.render('ListView.buttons', {widget: this}));
            this.$buttons.on('click', '.o_list_button_add', this._onCreateRecord.bind(this));
            this.$buttons.on('click', '.o_list_button_discard', this._onDiscard.bind(this));
            this.$buttons.appendTo($node);
        }
    },
    /**
     * Render the sidebar (the 'action' menu in the control panel, right of the
     * main buttons)
     *
     * @param {jQuery Node} $node
     */
    renderSidebar: function ($node) {
        if (this.hasSidebar && !this.sidebar) {
            var other = [{
                label: _t("Export"),
                callback: this._onExportData.bind(this)
            }];
            if (this.archiveEnabled) {
                other.push({
                    label: _t("Archive"),
                    callback: this._onToggleArchiveState.bind(this, true)
                });
                other.push({
                    label: _t("Unarchive"),
                    callback: this._onToggleArchiveState.bind(this, false)
                });
            }
            if (this.is_action_enabled('delete')) {
                other.push({
                    label: _t('Delete'),
                    callback: this._onDeleteSelectedRecords.bind(this)
                });
            }
            this.sidebar = new Sidebar(this, {
                editable: this.is_action_enabled('edit'),
                env: {
                    context: this.model.get(this.handle, {raw: true}).getContext(),
                    activeIds: this.getSelectedIds(),
                    model: this.modelName,
                },
                actions: _.extend(this.toolbarActions, {other: other}),
            });
            this.sidebar.appendTo($node);

            this._toggleSidebar();
        }
    },
    /**
     * Overrides to update the list of selected records
     *
     * @override
     */
    update: function (params, options) {
        var self = this;
        if (options && options.keepSelection) {
            // filter out removed records from selection
            var res_ids = this.model.get(this.handle).res_ids;
            this.selectedRecords = _.filter(this.selectedRecords, function (id) {
                return _.contains(res_ids, self.model.get(id).res_id);
            });
        } else {
            this.selectedRecords = [];
        }
        params.selectedRecords = this.selectedRecords;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @see BasicController._abandonRecord
     * If the given abandoned record is not the main one, notifies the renderer
     * to remove the appropriate subrecord (line).
     *
     * @override
     * @private
     * @param {string} [recordID] - default to the main recordID
     */
    _abandonRecord: function (recordID) {
        this._super.apply(this, arguments);
        if ((recordID || this.handle) !== this.handle) {
            var state = this.model.get(this.handle);
            this.renderer.removeLine(state, recordID);
            this._updatePager();
        }
    },
    /**
     * Adds a record to the list.
     * Disables the buttons to prevent concurrent record creation or edition.
     *
     * @todo make record creation a basic controller feature
     * @private
     */
    _addRecord: function () {
        var self = this;
        this._disableButtons();
        return this.renderer.unselectRow().then(function () {
            return self.model.addDefaultRecord(self.handle, {
                position: self.editable,
            });
        }).then(function (recordID) {
            var state = self.model.get(self.handle);
            self.renderer.updateState(state, {});
            self.renderer.editRecord(recordID);
            self._updatePager();
        }).always(this._enableButtons.bind(this));
    },
    /**
     * Archive the current selection
     *
     * @private
     * @param {string[]} ids
     * @param {boolean} archive
     * @returns {Deferred}
     */
    _archive: function (ids, archive) {
        if (ids.length === 0) {
            return $.when();
        }
        return this.model
            .toggleActive(ids, !archive, this.handle)
            .then(this.update.bind(this, {}, {reload: false}));
    },
    /**
     * This function is the hook called by the field manager mixin to confirm
     * that a record has been saved.
     *
     * @override
     * @param {string} id a basicmodel valid resource handle.  It is supposed to
     *   be a record from the list view.
     * @returns {Deferred}
     */
    _confirmSave: function (id) {
        var state = this.model.get(this.handle);
        return this.renderer.updateState(state, {noRender: true})
            .then(this._setMode.bind(this, 'readonly', id));
    },
    /**
     * To improve performance, list view must not be rerendered if it is asked
     * to discard all its changes. Indeed, only the in-edition row needs to be
     * discarded in that case.
     *
     * @override
     * @private
     * @param {string} [recordID] - default to main recordID
     * @returns {Deferred}
     */
    _discardChanges: function (recordID) {
        if ((recordID || this.handle) === this.handle) {
            recordID = this.renderer.getEditableRecordID();
            if (recordID === null) {
                return $.when();
            }
        }
        var self = this;
        return this._super(recordID).then(function () {
            self._updateButtons('readonly');
        });
    },
    /**
     * @override
     * @private
     */
    _getSidebarEnv: function () {
        var env = this._super.apply(this, arguments);
        var record = this.model.get(this.handle);
        return _.extend(env, {domain: record.getDomain()});
    },
    /**
     * Allows to change the mode of a single row.
     *
     * @override
     * @private
     * @param {string} mode
     * @param {string} [recordID] - default to main recordID
     * @returns {Deferred}
     */
    _setMode: function (mode, recordID) {
        if ((recordID || this.handle) !== this.handle) {
            this._updateButtons(mode);
            return this.renderer.setRowMode(recordID, mode);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * Display the sidebar (the 'action' menu in the control panel) if we have
     * some selected records.
     */
    _toggleSidebar: function () {
        if (this.sidebar) {
            this.sidebar.do_toggle(this.selectedRecords.length > 0);
        }
    },
    /**
     * @override
     * @returns {Deferred}
     */
    _update: function () {
        this._toggleSidebar();
        return this._super.apply(this, arguments);
    },
    /**
     * This helper simply makes sure that the control panel buttons matches the
     * current mode.
     *
     * @param {string} mode either 'readonly' or 'edit'
     */
    _updateButtons: function (mode) {
        if (this.$buttons) {
            this.$buttons.toggleClass('o-editing', mode === 'edit');
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add a record to the list
     *
     * @private
     * @param {OdooEvent} event
     */
    _onAddRecord: function (event) {
        event.stopPropagation();
        if (this.activeActions.create) {
            this._addRecord();
        } else if (event.data.onFail) {
            event.data.onFail();
        }
    },
    /**
     * Handles a click on a button by performing its action.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onButtonClicked: function (event) {
        event.stopPropagation();
        this._callButtonAction(event.data.attrs, event.data.record);
    },
    /**
     * When the user clicks on the 'create' button, two things can happen. We
     * can switch to the form view with no active res_id, so it is in 'create'
     * mode, or we can edit inline.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onCreateRecord: function (event) {
        // we prevent the event propagation because we don't want this event to
        // trigger a click on the main bus, which would be then caught by the
        // list editable renderer and would unselect the newly created row
        event.stopPropagation();
        var state = this.model.get(this.handle, {raw: true});
        if (this.editable && !state.groupedBy.length) {
            this._addRecord();
        } else {
            this.trigger_up('switch_view', {view_type: 'form', res_id: undefined});
        }
    },
    /**
     * Called when the 'delete' action is clicked on in the side bar.
     *
     * @private
     */
    _onDeleteSelectedRecords: function () {
        this._deleteRecords(this.selectedRecords);
    },
    /**
     * Handler called when the user clicked on the 'Discard' button.
     *
     * @param {Event} ev
     */
    _onDiscard: function (ev) {
        ev.stopPropagation(); // So that it is not considered as a row leaving
        this._discardChanges();
    },
    /**
     * Called when the user asks to edit a row -> Updates the controller buttons
     *
     * @param {OdooEvent} ev
     */
    _onEditLine: function (ev) {
        var self = this;
        ev.stopPropagation();
        this.trigger_up('mutexify', {
            action: function () {
                var record = self.model.get(self.handle);
                var editedRecord = record.data[ev.data.index];
                self._setMode('edit', editedRecord.id)
                    .done(ev.data.onSuccess);
            },
        });
    },
    /**
     * Opens the Export Dialog
     *
     * @private
     */
    _onExportData: function () {
        var record = this.model.get(this.handle);
        new DataExport(this, record).open();
    },
    /**
     * Called when the renderer displays an editable row and the user tries to
     * leave it -> Saves the record associated to that line.
     *
     * @param {OdooEvent} ev
     */
    _onSaveLine: function (ev) {
        var recordID = ev.data.recordID;
        this.saveRecord(recordID)
            .done(ev.data.onSuccess)
            .fail(ev.data.onFailure);
    },
    /**
     * Force a resequence of the records curently on this page.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onResequence: function (event) {
        var self = this;

        this.trigger_up('mutexify', {
            action: function () {
                var state = self.model.get(self.handle);
                var resIDs = _.map(event.data.rowIDs, function(rowID) {
                    return _.findWhere(state.data, {id: rowID}).res_id;
                });
                var options = {
                    offset: event.data.offset,
                    field: event.data.handleField,
                };
                return self.model.resequence(self.modelName, resIDs, self.handle, options).then(function () {
                    self._updateEnv();
                    state = self.model.get(self.handle);
                    return self.renderer.updateState(state, {noRender: true});
                });
            },
        });
    },
    /**
     * When the current selection changes (by clicking on the checkboxes on the
     * left), we need to display (or hide) the 'sidebar'.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onSelectionChanged: function (event) {
        this.selectedRecords = event.data.selection;
        this._toggleSidebar();
    },
    /**
     * @override
     */
    _onSidebarDataAsked: function (event) {
        var env = this._getSidebarEnv();
        event.data.callback(env);
    },
    /**
     * Called when clicking on 'Archive' or 'Unarchive' in the sidebar.
     *
     * @private
     * @param {boolean} archive
     */
    _onToggleArchiveState: function (archive) {
        this._archive(this.selectedRecords, archive);
    },
    /**
     * When the user clicks on one of the sortable column headers, we need to
     * tell the model to sort itself properly, to update the pager and to
     * rerender the view.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onToggleColumnOrder: function (event) {
        event.stopPropagation();
        var data = this.model.get(this.handle);
        if (!data.groupedBy) {
            this.pager.updateState({current_min: 1});
        }
        var self = this;
        this.model.setSort(data.id, event.data.name).then(function () {
            self.update({});
        });
    },
    /**
     * In a grouped list view, each group can be clicked on to open/close them.
     * This method just transfer the request to the model, then update the
     * renderer.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onToggleGroup: function (event) {
        this.model
            .toggleGroup(event.data.group.id)
            .then(this.update.bind(this, {}, {keepSelection: true, reload: false}));
    },
});

return ListController;

});
