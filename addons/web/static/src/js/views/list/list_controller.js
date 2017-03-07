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
        button_clicked: '_onButtonClicked',
        change_mode: '_onChangeMode',
        selection_changed: '_onSelectionChanged',
        toggle_column_order: '_onToggleColumnOrder',
        toggle_group: '_onToggleGroup',
    }),
    /**
     * @constructor
     * @override
     * @param {Object} params
     * @param {Object} params
     * @param {boolean} params.editable
     * @param {boolean} params.hasSidebar
     * @param {boolean} params.hasToolbar
     * @param {boolean} params.noLeaf
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.hasSidebar = params.hasSidebar;
        this.hasToolbar = params.hasToolbar;
        this.editable = params.editable;
        this.noLeaf = params.noLeaf;
        this.selectedRecords = []; // there is no selected record by default
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Calculate the active domain of the list view. This should be done only
     * if the header checkbox has been checked. This is done by evaluating the
     * search results, and then adding the dataset domain (i.e. action domain).
     *
     * @todo This is done only for the sidebar.  The full mechanism is wrong,
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
            return $.when(self.dataset.domain.concat(results.domain || []));
        } else {
            return $.Deferred().resolve();
        }
    },
    /**
     * Returns the list of currently selected res_ids (with the check boxes on
     * the left)
     *
     * @todo This should be private.  Need to change sidebar code
     *
     * @returns {number[]} list of res_ids
     */
    getSelectedIds: function () {
        var self = this;
        return _.map(this.selectedRecords, function (db_id) {
            return self.model.get(db_id, {raw: true}).res_id;
        });
    },
    /**
     * Display and bind all buttons in the control panel
     *
     * @override
     * @param {jQuery Node} $node
     */
    renderButtons: function ($node) {
        if (!this.noLeaf && this.hasButtons) {
            this.$buttons = $(qweb.render('ListView.buttons', {widget: this}));
            this.$buttons.find('.o_list_button_add')
                         .click(this._onCreateRecord.bind(this));
            this.$buttons.find('.o_list_button_save')
                         .click(this._onSave.bind(this));
            this.$buttons.find('.o_list_button_discard')
                         .click(this._onDiscard.bind(this));
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
            this.sidebar = new Sidebar(this, {
                editable: this.is_action_enabled('edit')
            });
            if (this.hasToolbar) {
                this.sidebar.add_toolbar(this.fields_view.toolbar);
            }
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
            this.sidebar.add_items('other', other);
            this.sidebar.appendTo($node);

            this._toggleSidebar();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _archive: function (ids, archive) {
        if (ids.length === 0) {
            return $.when();
        }
        return this.model
            .toggleActive(ids, !archive, this.handle)
            .then(this.update_state.bind(this));
    },
    /**
     * This function is the hook called by the field manager mixin to confirm
     * that a change just occured (after the eventual onchange have been
     * applied).
     *
     * @param {string} id a basicmodel id, which is a record in the list view
     * @param {string[]} fields the changed fields
     * @param {OdooEvent} event the event that triggered the change
     */
    _confirmChange: function (id, fields, event) {
        var state = this.model.get(this.handle);
        this.renderer.confirmChange(state, id, fields, event);
    },
    /**
     * This function is the hook called by the field manager mixin to confirm
     * that a record has been saved.
     *
     * @override
     * @param {string} id a basicmodel valid resource handle.  It is supposed to
     *   be a record from the list view.
     */
    _confirmSave: function (id) {
        var state = this.model.get(this.handle);
        this.renderer.confirmSave(state, id);
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
     * @param {Object} state
     * @returns {Deferred}
     */
    _update: function (state) {
        this._toggleNoContentHelper(state.count === 0);
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
     * Handles a click on a button by performing its action.
     *
     * @param {OdooEvent} event
     */
    _onButtonClicked: function (event) {
        this.trigger_up('execute_action', {
            action_data: event.data.attrs,
            model: this.modelName,
            record_id: event.data.record.res_id,
        });
    },
    /**
     * This event is triggered when a list renderer goes from mode = readonly to
     * edit, and vice versa. In that case, we need to make sure that the buttons
     * displayed in the control panel are correct.
     *
     * @param {OdooEvent} event
     */
    _onChangeMode: function (event) {
        this._updateButtons(event.data.mode);
    },
    /**
     * When the user clicks on the 'create' button, two things can happen. We
     * can switch to the form view with no active res_id, so it is in 'create'
     * mode, or we can edit inline.
     *
     * @param {MouseEvent} event
     */
    _onCreateRecord: function (event) {
        // we prevent the event propagation because we don't want this event to
        // trigger a click on the main bus, which would be then caught by the
        // list editable renderer and would unselect the newly created row
        event.stopPropagation();

        var self = this;
        if (this.editable) {
            this.model.addDefaultRecord(this.handle).then(function (recordID) {
                self._toggleNoContentHelper(false);
                var state = self.model.get(self.handle);
                self.renderer.updateState(state);
                self.renderer.editRecord(recordID);
            });
        } else {
            this.trigger_up('switch_view', {view_type: 'form', res_id: undefined});
        }
    },
    /**
     * Called when the 'delete' action is clicked on in the side bar.
     */
    _onDeleteSelectedRecords: function () {
        this._deleteRecords(this.selectedRecords);
    },
    /**
     * Handler called when the user clicked on the 'Discard' button.
     */
    _onDiscard: function () {
        this.model.discardChanges(this.handle);
        this.update(this.handle, {reload: false});
    },
    /**
     * Opens the Export Dialog
     */
    _onExportData: function () {
        new DataExport(this, this.dataset).open();
    },
    /**
     * changes of the list editable are automatically saved when unselecting the
     * row, which is done when clicking on 'Save' (anywhere outside the row
     * actually), so this function should only switch back to readonly mode
     *
     * @param {MouseEvent} event
     */
    _onSave: function (event) {
        // we prevent the event propagation because we don't want this event to
        // trigger a click on the main bus, which would be then caught by the
        // list editable renderer and would unselect the newly created row
        // event.stopPropagation();
        this._updateButtons('readonly');
    },
    /**
     * When the current selection changes (by clicking on the checkboxes on the
     * left), we need to display (or hide) the 'sidebar'.
     *
     * @param {OdooEvent} event
     */
    _onSelectionChanged: function (event) {
        this.selectedRecords = event.data.selection;
        this._toggleSidebar();
    },
    /**
     * Called when clicking on 'Archive' or 'Unarchive' in the sidebar.
     *
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
     * @param {OdooEvent} event
     */
    _onToggleColumnOrder: function (event) {
        var data = this.model.get(this.handle);
        if (!data.groupedBy) {
            this.pager.updateState({current_min: 1});
        }
        this.model.setSort(data.id, event.data.name);
        this.update();
    },
    /**
     * In a grouped list view, each group can be clicked on to open/close them.
     * This method just transfer the request to the model, then update the
     * renderer.
     *
     * @param {OdooEvent} event
     */
    _onToggleGroup: function (event) {
        this.model
            .toggleGroup(event.data.group.id)
            .then(this.update.bind(this, {}, {reload: false}));
    },
});

return ListController;

});
