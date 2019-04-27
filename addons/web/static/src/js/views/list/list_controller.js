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
var Dialog = require('web.Dialog');
var Sidebar = require('web.Sidebar');

var _t = core._t;
var qweb = core.qweb;

var ListController = BasicController.extend({
    /**
     * This key contains the name of the buttons template to render on top of
     * the list view. It can be overridden to add buttons in specific child views.
     */
    buttons_template: 'ListView.buttons',
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        activate_next_widget: '_onActivateNextWidget',
        add_record: '_onAddRecord',
        button_clicked: '_onButtonClicked',
        group_edit_button_clicked: '_onEditGroupClicked',
        edit_line: '_onEditLine',
        save_line: '_onSaveLine',
        selection_changed: '_onSelectionChanged',
        toggle_column_order: '_onToggleColumnOrder',
        toggle_group: '_onToggleGroup',
        navigation_move: '_onNavigationMove',
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
     * @returns {Promise<array[]>} a promise that resolve to the active domain
     */
    getActiveDomain: function () {
        // TODO: this method should be synchronous...
        var self = this;
        if (this.$('thead .o_list_record_selector input').prop('checked')) {
            var searchQuery = this._controlPanel ? this._controlPanel.getSearchQuery() : {};
            var record = self.model.get(self.handle, {raw: true});
            return Promise.all(record.getDomain().concat(searchQuery.domain || []));
        } else {
            return Promise.resolve();
        }
    },
    /*
     * @override
     */
    getOwnedQueryParams: function () {
        var state = this._super.apply(this, arguments);
        var orderedBy = this.model.get(this.handle, {raw: true}).orderedBy || [];
        return _.extend({}, state, {orderedBy: orderedBy});
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
            this.$buttons = $(qweb.render(this.buttons_template, {widget: this}));
            this.$buttons.on('click', '.o_list_button_add', this._onCreateRecord.bind(this));

            this._assignCreateKeyboardBehavior(this.$buttons.find('.o_list_button_add'));
            this.$buttons.find('.o_list_button_add').tooltip({
                delay: {show: 200, hide: 0},
                title: function () {
                    return qweb.render('CreateButton.tooltip');
                },
                trigger: 'manual',
            });
            this.$buttons.on('click', '.o_list_button_discard', this._onDiscard.bind(this));
            this.$buttons.appendTo($node);
        }
    },
    /**
     * Render the sidebar (the 'action' menu in the control panel, right of the
     * main buttons)
     *
     * @param {jQuery Node} $node
     * @returns {Promise}
     */
    renderSidebar: function ($node) {
        var self = this;
        if (this.hasSidebar) {
            var other = [{
                label: _t("Export"),
                callback: this._onExportData.bind(this)
            }];
            if (this.archiveEnabled) {
                other.push({
                    label: _t("Archive"),
                    callback: function () {
                        Dialog.confirm(self, _t("Are you sure that you want to archive all the selected records?"), {
                            confirm_callback: self._toggleArchiveState.bind(self, true),
                        });
                    }
                });
                other.push({
                    label: _t("Unarchive"),
                    callback: this._toggleArchiveState.bind(this, false)
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
            return this.sidebar.appendTo($node).then(function() {
                self._toggleSidebar();
            });
        }
        return Promise.resolve();
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
     * Adds a new record to the a dataPoint of type 'list'.
     * Disables the buttons to prevent concurrent record creation or edition.
     *
     * @todo make record creation a basic controller feature
     * @private
     * @param {string} dataPointId a dataPoint of type 'list' (may be grouped)
     * @return {Promise}
     */
    _addRecord: function (dataPointId) {
        var self = this;
        this._disableButtons();
        return this.renderer.unselectRow().then(function () {
            return self.model.addDefaultRecord(dataPointId, {
                position: self.editable,
            });
        }).then(function (recordID) {
            var state = self.model.get(self.handle);
            self.renderer.updateState(state, {})
                .then(function () {
                    self.renderer.editRecord(recordID);
                }).then(self._updatePager.bind(self));
        }).then(this._enableButtons.bind(this)).guardedCatch(this._enableButtons.bind(this));
    },
    /**
     * Archive the current selection
     *
     * @private
     * @param {string[]} ids
     * @param {boolean} archive
     * @returns {Promise}
     */
    _archive: function (ids, archive) {
        if (ids.length === 0) {
            return Promise.resolve();
        }
        return this.model
            .toggleActive(ids, !archive, this.handle)
            .then(this.update.bind(this, {}, {reload: false}));
    },
    /**
     * Assign on the buttons create additionnal behavior to facilitate the work of the users doing input only using the keyboard
     *
     * @param {jQueryElement} $createButton  The create button itself
     */
    _assignCreateKeyboardBehavior: function($createButton) {
        var self = this;
        $createButton.on('keydown', function(e) {
            $createButton.tooltip('hide');
            switch(e.which) {
                case $.ui.keyCode.ENTER:
                    e.preventDefault();
                    self._onCreateRecord.apply(self);
                    break;
                case $.ui.keyCode.DOWN:
                    e.preventDefault();
                    self.renderer.giveFocus();
                    break;
                case $.ui.keyCode.TAB:
                    if (!e.shiftKey && e.target.classList.contains("btn-primary")) {
                        e.preventDefault();
                        $createButton.tooltip('show');
                    }
                    break;
            }
        });
    },
    /**
     * This function is the hook called by the field manager mixin to confirm
     * that a record has been saved.
     *
     * @override
     * @param {string} id a basicmodel valid resource handle.  It is supposed to
     *   be a record from the list view.
     * @returns {Promise}
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
     * @returns {Promise}
     */
    _discardChanges: function (recordID) {
        if ((recordID || this.handle) === this.handle) {
            recordID = this.renderer.getEditableRecordID();
            if (recordID === null) {
                return Promise.resolve();
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
     * @private
     * @returns {boolean}
     */
    _inMultipleRecordEdition: function (recordId) {
        var record = this.model.get(recordId, { raw: true });
        var recordIds = _.union([recordId], this.selectedRecords);
        return recordIds.length > 1 && record.res_id;
    },
    /**
     * Only display the pager when there are data to display.
     *
     * @override
     * @private
     */
    _isPagerVisible: function () {
        var state = this.model.get(this.handle, {raw: true});
        return !!state.count;
    },
    /**
     * @private
     * @param {string} recordId
     * @param {Object} node
     * @param {Object} changes
     */
    _saveMultipleRecords: function (recordId, node, changes) {
        var self = this;
        var value = Object.values(changes)[0];
        var recordIds = _.union([recordId], this.selectedRecords);
        var validRecordIds = recordIds.reduce(function (result, recordId) {
            var record = self.model.get(recordId);
            var modifiers = self.renderer._registerModifiers(node, record);
            if (!modifiers.readonly && (!modifiers.required || value)) {
                result.push(recordId);
            }
            return result;
        }, []);
        var message = _.str.sprintf(
            _t('Do you want to set the value on the %d valid selected records?'),
            validRecordIds.length);
        if (recordIds.length !== validRecordIds.length) {
            var nbInvalid = recordIds.length - validRecordIds.length;
            message += ' ' + _.str.sprintf(_t('(%d invalid)'), nbInvalid);
        }
        Dialog.confirm(this, message, {
            confirm_callback: function () {
                self.model.saveRecords(recordId, validRecordIds)
                    .then(function () {
                        self._updateButtons('readonly');
                        var state = self.model.get(self.handle);
                        self.renderer.updateState(state, {});
                    });
            },
        });
    },
    /**
     * Overridden to deal with edition of multiple line.
     *
     * @override
     * @param {string} recordId
     */
    _saveRecord: function (recordId) {
        var record = this.model.get(recordId, { raw: true });
        if (record.isDirty() && this._inMultipleRecordEdition(recordId)) {
            // do not save the record (see _saveMultipleRecords)
            return Promise.resolve();

        }
        return this._super.apply(this, arguments);
    },
    /**
     * Allows to change the mode of a single row.
     *
     * @override
     * @private
     * @param {string} mode
     * @param {string} [recordID] - default to main recordID
     * @returns {Promise}
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
     * Called when clicking on 'Archive' or 'Unarchive' in the sidebar.
     *
     * @private
     * @param {boolean} archive
     */
    _toggleArchiveState: function (archive) {
        this._archive(this.selectedRecords, archive);
    },
    /**
     * Hide the create button in non-empty grouped editable list views, as an
     * 'Add an item' link is available in each group.
     *
     * @private
     */
    _toggleCreateButton: function () {
        if (this.$buttons) {
            var state = this.model.get(this.handle);
            var createHidden = this.editable && state.groupedBy.length && state.data.length;
            this.$buttons.find('.o_list_button_add').toggleClass('o_hidden', !!createHidden);
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
     * @returns {Promise}
     */
    _update: function () {
        return this._super.apply(this, arguments)
            .then(this._toggleSidebar.bind(this))
            .then(this._toggleCreateButton.bind(this));
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
     * Triggered when navigating with TAB, when the end of the list has been
     * reached. Go back to the first row in that case.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onActivateNextWidget: function (ev) {
        ev.stopPropagation();
        this.renderer.editFirstRecord();
    },
    /**
     * Add a record to the list
     *
     * @private
     * @param {OdooEvent} ev
     * @param {string} [ev.data.groupId=this.handle] the id of a dataPoint of
     *   type list to which the record must be added (default: main list)
     */
    _onAddRecord: function (ev) {
        ev.stopPropagation();
        var dataPointId = ev.data.groupId || this.handle;
        if (this.activeActions.create) {
            this._addRecord(dataPointId);
        } else if (ev.data.onFail) {
            ev.data.onFail();
        }
    },
    /**
     * Handles a click on a button by performing its action.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onButtonClicked: function (ev) {
        ev.stopPropagation();
        this._callButtonAction(ev.data.attrs, ev.data.record);
    },
    /**
     * When the user clicks on the 'create' button, two things can happen. We
     * can switch to the form view with no active res_id, so it is in 'create'
     * mode, or we can edit inline.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onCreateRecord: function (ev) {
        // we prevent the event propagation because we don't want this event to
        // trigger a click on the main bus, which would be then caught by the
        // list editable renderer and would unselect the newly created row
        if (ev) {
            ev.stopPropagation();
        }
        var state = this.model.get(this.handle, {raw: true});
        if (this.editable && !state.groupedBy.length) {
            this._addRecord(this.handle);
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
                self._setMode('edit', ev.data.recordId)
                    .then(ev.data.onSuccess);
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
        var defaultExportFields = _.map(this.renderer.columns, function (field) {
            return field.attrs.name;
        });
        new DataExport(this, record, defaultExportFields).open();
    },
    /**
     * Opens the related form view.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onEditGroupClicked: function (ev) {
        ev.stopPropagation();
        this.do_action({
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            res_model: ev.data.record.model,
            res_id: ev.data.record.res_id,
            flags: {mode: 'edit'},
        });
    },
    /**
     * Overridden to deal with the edition of multiple records.
     *
     * Note that we don't manage saving multiple records on saveLine
     * because we don't want the onchanges to be applied.
     *
     * @private
     * @override
     */
    _onFieldChanged: function (ev) {
        ev.stopPropagation();
        var self = this;

        if (this._inMultipleRecordEdition(ev.data.dataPointID)) {
            // deal with edition of multiple lines
            var _onSuccess = ev.data.onSuccess;
            ev.data.onSuccess = function () {
                Promise.resolve(_onSuccess()).then(function () {
                    self._saveMultipleRecords(ev.data.dataPointID, ev.target.__node, ev.data.changes);
                });
            };
        }
        this._super.apply(this, arguments);
    },
    /**
     * Called when the renderer displays an editable row and the user tries to
     * leave it -> Saves the record associated to that line.
     *
     * @param {OdooEvent} ev
     */
    _onSaveLine: function (ev) {
        this.saveRecord(ev.data.recordID)
            .then(ev.data.onSuccess)
            .guardedCatch(ev.data.onFailure);
    },
    /**
     * When the current selection changes (by clicking on the checkboxes on the
     * left), we need to display (or hide) the 'sidebar'.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSelectionChanged: function (ev) {
        this.selectedRecords = ev.data.selection;
        this._toggleSidebar();
    },
    /**
     * When the user clicks on one of the sortable column headers, we need to
     * tell the model to sort itself properly, to update the pager and to
     * rerender the view.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onToggleColumnOrder: function (ev) {
        ev.stopPropagation();
        var data = this.model.get(this.handle);
        if (!data.groupedBy) {
            this.pager.updateState({current_min: 1});
        }
        var self = this;
        this.model.setSort(data.id, ev.data.name).then(function () {
            self.update({});
        });
    },
    /**
     * In a grouped list view, each group can be clicked on to open/close them.
     * This method just transfer the request to the model, then update the
     * renderer.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onToggleGroup: function (ev) {
        var self = this;
        this.model
            .toggleGroup(ev.data.group.id)
            .then(function () {
                self.update({}, {keepSelection: true, reload: false}).then(function () {
                    if (ev.data.onSuccess) {
                        ev.data.onSuccess();
                    }
                });
            });
    },
});

return ListController;

});
