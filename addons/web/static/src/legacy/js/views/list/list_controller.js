/** @odoo-module alias=web.ListController **/

/**
 * The List Controller controls the list renderer and the list model.  Its role
 * is to allow these two components to communicate properly, and also, to render
 * and bind all extra buttons/pager in the control panel.
 */

import config from 'web.config';
import core from 'web.core';
import BasicController from 'web.BasicController';
import DataExport from 'web.DataExport';
import Dialog from 'web.Dialog';
import ListConfirmDialog from 'web.ListConfirmDialog';
import session from 'web.session';
import viewUtils from 'web.viewUtils';

var _t = core._t;
var qweb = core.qweb;

var ListController = BasicController.extend({
    /**
     * This key contains the name of the buttons template to render on top of
     * the list view. It can be overridden to add buttons in specific child views.
     */
    buttons_template: 'ListView.buttons',
    events: _.extend({}, BasicController.prototype.events, {
        'click .o_list_export_xlsx': '_onDirectExportData',
        'click .o_list_select_domain': '_onSelectDomain',
    }),
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
    }),
    /**
     * @constructor
     * @override
     * @param {Object} params
     * @param {boolean} params.editable
     * @param {boolean} params.hasActionMenus
     * @param {Object[]} [params.headerButtons=[]]: a list of node descriptors
     *    for controlPanel's action buttons
     * @param {Object} params.toolbarActions
     * @param {boolean} params.noLeaf
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.hasActionMenus = params.hasActionMenus;
        this.headerButtons = params.headerButtons || [];
        this.toolbarActions = params.toolbarActions || {};
        this.editable = params.editable;
        this.noLeaf = params.noLeaf;
        this.selectedRecords = params.selectedRecords || [];
        this.multipleRecordsSavingPromise = null;
        this.fieldChangedPrevented = false;
        this.isPageSelected = false; // true iff all records of the page are selected
        this.isDomainSelected = false; // true iff the user selected all records matching the domain
        this.isExportEnable = false;
    },

    willStart() {
        const sup = this._super(...arguments);
        const acl = session.user_has_group('base.group_allow_export').then(hasGroup => {
            this.isExportEnable = hasGroup;
        });
        return Promise.all([sup, acl]);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Promise}
     */
    canBeRemoved: async function () {
        const _super = this._super.bind(this);
        await this.renderer.unselectRow({ canDiscard: true });
        return _super(...arguments);
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
     * Returns the list of currently selected res_ids (with the check boxes on
     * the left) or the whole domain res_ids if it is selected
     *
     * This method should be the implementation of getSelectedIds but it is kept for compatibility reasons
     *
     * @returns {Promise<integer[]>}
     */
    getSelectedIdsWithDomain: async function () {
        if (this.isDomainSelected) {
            const state = this.model.get(this.handle, {raw: true});
            return await this._domainToResIds(state.getDomain(), session.active_ids_limit);
        } else {
            return Promise.resolve(this.model.localIdsToResIds(this.selectedRecords));
        }
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
     */
    renderButtons: function ($node) {
        if (this.noLeaf || !this.hasButtons) {
            this.hasButtons = false;
            this.$buttons = $('<div>');
        } else {
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
            this.$buttons.on('mousedown', '.o_list_button_discard', this._onDiscardMousedown.bind(this));
            this.$buttons.on('click', '.o_list_button_discard', this._onDiscard.bind(this));
        }
        if ($node) {
            this.$buttons.appendTo($node);
        }
    },
    /**
     * Renders (and updates) the buttons that are described inside the `header`
     * node of the list view arch. Those buttons are visible when selecting some
     * records. They will be appended to the controlPanel's buttons.
     *
     * @private
     */
    _renderHeaderButtons() {
        if (this.$headerButtons) {
            this.$headerButtons.remove();
            this.$headerButtons = null;
        }
        if (!this.headerButtons.length || !this.selectedRecords.length) {
            return;
        }
        const btnClasses = 'btn-primary btn-secondary btn-link btn-success btn-info btn-warning btn-danger'.split(' ');
        let $elms = $();
        this.headerButtons.forEach(node => {
            const $btn = viewUtils.renderButtonFromNode(node);
            $btn.addClass('btn');
            if (!btnClasses.some(cls => $btn.hasClass(cls))) {
                $btn.addClass('btn-secondary');
            }
            $btn.on("click", this._onHeaderButtonClicked.bind(this, node));
            $elms = $elms.add($btn);
        });
        this.$headerButtons = $elms;
        this.$headerButtons.appendTo(this.$buttons);
    },
    /**
     * Overrides to update the list of selected records
     *
     * @override
     */
    update: function (params, options) {
        var self = this;
        let res_ids;
        if (options && options.keepSelection) {
            // filter out removed records from selection
            res_ids = this.model.get(this.handle).res_ids;
            this.selectedRecords = _.filter(this.selectedRecords, function (id) {
                return _.contains(res_ids, self.model.get(id).res_id);
            });
        } else {
            this.selectedRecords = [];
        }
        if (this.selectedRecords.length === 0 || this.selectedRecords.length < res_ids.length) {
            this.isDomainSelected = false;
            this.isPageSelected = false;
        }

        params.selectedRecords = this.selectedRecords;
        return this._super.apply(this, arguments);
    },
    /**
     * This helper simply makes sure that the control panel buttons matches the
     * current mode.
     *
     * @override
     * @param {string} mode either 'readonly' or 'edit'
     */
    updateButtons: function (mode) {
        if (this.hasButtons) {
            this.$buttons.toggleClass('o-editing', mode === 'edit');
            const state = this.model.get(this.handle, {raw: true});
            if (state.count) {
                this.$buttons.find('.o_list_export_xlsx').show();
            } else {
                this.$buttons.find('.o_list_export_xlsx').hide();
            }
        }
        this._updateSelectionBox();
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
            this._updatePaging(state);
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
        return this._removeSampleData(() => {
            return this.renderer.unselectRow().then(function () {
                return self.model.addDefaultRecord(dataPointId, {
                    position: self.editable,
                });
            }).then(function (recordID) {
                var state = self.model.get(self.handle);
                self._updateRendererState(state, { keepWidths: true })
                    .then(function () {
                        self.renderer.editRecord(recordID);
                    })
                    .then(() => {
                        self._updatePaging(state);
                    });
            }).then(this._enableButtons.bind(this)).guardedCatch(this._enableButtons.bind(this));
        });
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
                    self._giveFocus();
                    break;
                case $.ui.keyCode.TAB:
                    if (
                        !e.shiftKey &&
                        e.target.classList.contains("btn-primary") &&
                        !self.model.isInSampleMode()
                    ) {
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
     * @param {Object} [options] render options
     * @returns {Promise}
     */
    _confirmSave(id, options = {}) {
        const state = this.model.get(this.handle);
        return this._updateRendererState(state, { noRender: !state.isM2MGrouped, ...options }).then(
            this._setMode.bind(this, "readonly", id)
        );
    },
    /**
     * Deletes records matching the current domain. We limit the number of
     * deleted records to the 'active_ids_limit' config parameter.
     *
     * @private
     */
    _deleteRecordsInCurrentDomain: function () {
        const doIt = async () => {
            const state = this.model.get(this.handle, {raw: true});
            const resIds = await this._domainToResIds(state.getDomain(), session.active_ids_limit);
            await this._rpc({
                model: this.modelName,
                method: 'unlink',
                args: [resIds],
                context: state.getContext(),
            });
            if (resIds.length === session.active_ids_limit) {
                const msg = _.str.sprintf(
                    _t("Only the first %d records have been deleted (out of %d selected)"),
                    resIds.length, state.count
                );
                this.displayNotification({ message: msg });
            }
            this.reload();
        };
        if (this.confirmOnDelete) {
            Dialog.confirm(this, _t("Are you sure you want to delete these records ?"), {
                confirm_callback: doIt,
            });
        } else {
            doIt();
        }
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
            self.updateButtons('readonly');
        });
    },
    /**
     * Returns the ids of records matching the given domain.
     *
     * @private
     * @param {Array[]} domain
     * @param {integer} [limit]
     * @returns {integer[]}
     */
    _domainToResIds: function (domain, limit) {
        return this._rpc({
            model: this.modelName,
            method: 'search',
            args: [domain],
            kwargs: {
                limit: limit,
            },
        });
    },
    /**
     * @returns {DataExport} the export dialog widget
     * @private
     */
    _getExportDialogWidget() {
        let state = this.model.get(this.handle);
        let defaultExportFields = this.renderer.columns.filter(field => field.tag === 'field' && state.fields[field.attrs.name].exportable !== false).map(field => field.attrs.name);
        let groupedBy = this.renderer.state.groupedBy;
        const domain = this.isDomainSelected && state.getDomain();
        return new DataExport(this, state, defaultExportFields, groupedBy,
            domain, this.getSelectedIds());
    },
    /**
     * Only display the pager when there are data to display.
     *
     * @override
     * @private
     */
    _getPagingInfo: function (state) {
        if (!state.count) {
            return null;
        }
        return Object.assign(this._super(...arguments), {
            validate: () => this.renderer.unselectRow({ canDiscard: true }),
        });
    },
    /**
     * @override
     * @private
     */
    _getActionMenuItems: function (state) {
        const { isM2MGrouped } = state;
        if (!this.hasActionMenus || !this.selectedRecords.length) {
            return null;
        }
        const props = this._super(...arguments);
        const otherActionItems = [];
        if (this.isExportEnable) {
            otherActionItems.push({
                description: _t("Export"),
                callback: () => this._onExportData()
            });
        }
        if (this.archiveEnabled && !isM2MGrouped) {
            otherActionItems.push({
                description: _t("Archive"),
                callback: () => {
                    const dialog = Dialog.confirm(this, _t("Are you sure that you want to archive all the selected records?"), {
                        confirm_callback: () => {
                            this._toggleArchiveState(true);
                            dialog.close();
                        },
                    });
                }
            }, {
                description: _t("Unarchive"),
                callback: () => this._toggleArchiveState(false)
            });
        }
        if (this.activeActions.delete && !isM2MGrouped) {
            otherActionItems.push({
                description: _t("Delete"),
                callback: () => this._onDeleteSelectedRecords()
            });
        }
        return Object.assign(props, {
            items: Object.assign({}, this.toolbarActions, { other: otherActionItems }),
            context: state.getContext(),
            domain: state.getDomain(),
            isDomainSelected: this.isDomainSelected,
        });
    },
    /**
     * Saves multiple records at once. This method is called by the _onFieldChanged method
     * since the record must be confirmed as soon as the focus leaves a dirty cell.
     * Pseudo-validation is performed with registered modifiers.
     * Returns a promise that is resolved when confirming and rejected in any other case.
     *
     * @private
     * @param {string} recordId
     * @param {Object} node
     * @param {Object} changes
     * @returns {Promise}
     */
    _saveMultipleRecords: function (recordId, node, changes) {
        var recordIds = _.union([recordId], this.selectedRecords);
        var fieldName = node.attrs.name;
        var value = changes[fieldName];
        var validRecordIds = recordIds.reduce((result, nextRecordId) => {
            var record = this.model.get(nextRecordId);
            var modifiers = this.renderer._registerModifiers(node, record);
            if (!modifiers.readonly && (!modifiers.required || value)) {
                result.push(nextRecordId);
            }
            return result;
        }, []);
        return new Promise((resolve, reject) => {
            const saveRecords = () => {
                this.model.saveRecords(this.handle, recordId, validRecordIds, Object.keys(changes))
                    .then(async () => {
                        this.updateButtons('readonly');
                        // If there are changes and the list was multi-editable,
                        // we do not want to select the next row.
                        this.selectedRecords = [];
                        await this._confirmSave(this.handle, {
                            keepWidths: true,
                            selectedRecords: [],
                        });
                        this._updateSelectionBox();
                        this.renderer.focusCell(recordId, node);
                        resolve(!Object.keys(changes).length);
                    })
                    .guardedCatch(discardAndReject);
            };
            const discardAndReject = () => {
                this.model.discardChanges(recordId);
                this._confirmSave(recordId).then(() => {
                    this.renderer.focusCell(recordId, node);
                    reject();
                });
            };
            if (validRecordIds.length > 0) {
                if (recordIds.length === 1) {
                    // Save without prompt
                    return saveRecords();
                }
                const dialogOptions = {
                    confirm_callback: saveRecords,
                    cancel_callback: discardAndReject,
                };
                const record = this.model.get(recordId);
                const params = {
                    isDomainSelected: this.isDomainSelected,
                    fields: Object.keys(changes).map((fieldName) => {
                        let fieldLabel = record.fields[fieldName].string;
                        if (node.attrs.name === fieldName && node.attrs.string) {
                            fieldLabel = node.attrs.string;
                        }
                        return { name: fieldName, label: fieldLabel };
                    }),
                    nbRecords: recordIds.length,
                    nbValidRecords: validRecordIds.length,
                };
                new ListConfirmDialog(this, record, params, dialogOptions)
                    .open({ shouldFocusButtons: true });
            } else {
                Dialog.alert(this, _t("No valid record to save"), {
                    confirm_callback: discardAndReject,
                });
            }
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
        if (record.isDirty() && this.renderer.isInMultipleRecordEdition(recordId)) {
            // do not save the record (see _saveMultipleRecords)
            const prom = this.multipleRecordsSavingPromise || Promise.reject();
            this.multipleRecordsSavingPromise = null;
            return prom;
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
            this.mode = mode;
            this.updateButtons(mode);
            return this.renderer.setRowMode(recordID, mode);
        } else {
            return this._super.apply(this, arguments);
        }
    },
    /**
     * @override
     */
    _shouldBounceOnClick() {
        const state = this.model.get(this.handle, {raw: true});
        return !state.count || state.isSample;
    },
    /**
     * Called when clicking on 'Archive' or 'Unarchive' in the sidebar.
     *
     * @private
     * @param {boolean} archive
     * @returns {Promise}
     */
    _toggleArchiveState: async function (archive) {
        const resIds = await this.getSelectedIdsWithDomain()
        const notif = this.isDomainSelected;
        await this._archive(resIds, archive);
        const total = this.model.get(this.handle, {raw: true}).count;
        if (notif && resIds.length === session.active_ids_limit && resIds.length < total) {
            const msg = _.str.sprintf(
                _t("Of the %d records selected, only the first %d have been archived/unarchived."),
                total, resIds.length
            );
            this.displayNotification({ title: _t('Warning'), message: msg });
        }
    },
    /**
     * Hide the create button in non-empty grouped editable list views, as an
     * 'Add an item' link is available in each group.
     *
     * @private
     */
    _toggleCreateButton: function () {
        if (this.hasButtons) {
            var state = this.model.get(this.handle);
            var createHidden = this.editable && state.groupedBy.length && state.data.length;
            this.$buttons.find('.o_list_button_add').toggleClass('o_hidden', !!createHidden);
        }
    },
    /**
     * @override
     * @returns {Promise}
     */
    _update: async function () {
        await this._super(...arguments);
        this._toggleCreateButton();
        this.updateButtons('readonly');
    },
    /**
     * When records are selected, a box is displayed in the control panel (next
     * to the buttons). It indicates the number of selected records, and allows
     * the user to select the whole domain instead of the current page (when the
     * page is selected). This function renders and displays this box when at
     * least one record is selected.
     * Since header action buttons' display is dependent on the selection, we
     * refresh them each time the selection is updated.
     *
     * @private
     */
    _updateSelectionBox() {
        this._renderHeaderButtons();
        if (this.$selectionBox) {
            this.$selectionBox.remove();
            this.$selectionBox = null;
        }
        if (this.selectedRecords.length) {
            const state = this.model.get(this.handle, {raw: true});
            this.$selectionBox = $(qweb.render('ListView.selection', {
                isDomainSelected: this.isDomainSelected,
                isMobile: config.device.isMobile,
                isPageSelected: this.isPageSelected,
                nbSelected: this.selectedRecords.length,
                nbTotal: state.count,
            }));
            this.$selectionBox.appendTo(this.$buttons);
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
        this.renderer.editFirstRecord(ev);
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
     * Save the row in edition, if any, when we are about to leave Odoo.
     *
     * @override
     */
    _onBeforeUnload: function () {
        const recordId = this.renderer.getEditableRecordID();
        if (recordId) {
            this._urgentSave(recordId);
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
    _onDeleteSelectedRecords: async function () {
        if (this.isDomainSelected) {
            this._deleteRecordsInCurrentDomain();
        } else {
            this._deleteRecords(this.selectedRecords);
        }
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
     * Used to detect if the discard button is about to be clicked.
     * Some focusout events might occur and trigger a save which
     * is not always wanted when clicking "Discard".
     *
     * @param {MouseEvent} ev
     * @private
     */
    _onDiscardMousedown: function (ev) {
        var self = this;
        this.fieldChangedPrevented = true;
        window.addEventListener('mouseup', function (mouseupEvent) {
            var preventedEvent = self.fieldChangedPrevented;
            self.fieldChangedPrevented = false;
            // If the user starts clicking (mousedown) on the button and stops clicking
            // (mouseup) outside of the button, we want to trigger the original onFieldChanged
            // Event that was prevented in the meantime.
            if (ev.target !== mouseupEvent.target && preventedEvent.constructor.name === 'OdooEvent') {
                self._onFieldChanged(preventedEvent);
            }
        }, { capture: true, once: true });
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
        this._getExportDialogWidget().open();
    },
    /**
     * Export Records in a xls file
     *
     * @private
     */
    _onDirectExportData() {
        // access rights check before exporting data
        return this._rpc({
            model: 'ir.exports',
            method: 'search_read',
            args: [[], ['id']],
            limit: 1,
        }).then(() => this._getExportDialogWidget().export())
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
            context: {create: false},
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
        const recordId = ev.data.dataPointID;

        if (this.fieldChangedPrevented) {
            this.fieldChangedPrevented = ev;
        } else if (this.renderer.isInMultipleRecordEdition(recordId)) {
            const saveMulti = () => {
                // if ev.data.__originalComponent is set, it is the field Component
                // that triggered the event, otherwise ev.target is the legacy field
                // Widget that triggered the event
                const target = ev.data.__originalComponent || ev.target;
                this.multipleRecordsSavingPromise =
                    this._saveMultipleRecords(ev.data.dataPointID, target.__node, ev.data.changes);
            };
            // deal with edition of multiple lines
            ev.data.onSuccess = saveMulti; // will ask confirmation, and save
            ev.data.onFailure = saveMulti; // will show the appropriate dialog
            // disable onchanges as we'll save directly
            ev.data.notifyChange = false;
            // In multi edit mode, we will be asked if we want to write on the selected
            // records, so the force_save for readonly is not necessary.
            ev.data.force_save = false;
        }
        this._super.apply(this, arguments);
    },
    /**
     * @private
     * @param {Object} node the button's node in the xml
     * @returns {Promise}
     */
    async _onHeaderButtonClicked(node) {
        this._disableButtons();
        const state = this.model.get(this.handle);
        try {
            const resIds = await this.getSelectedIdsWithDomain();
            // add the context of the button node (in the xml) and our custom one
            // (active_ids and domain) to the action's execution context
            const actionData = Object.assign({}, node.attrs, {
                context: state.getContext({ additionalContext: node.attrs.context }),
            });
            Object.assign(actionData.context, {
                active_domain: state.getDomain(),
                active_id: resIds[0],
                active_ids: resIds,
                active_model: state.model,
            });
            // load the action with the correct context and record parameters (resIDs, model etc...)
            const recordData = {
                context: state.getContext(),
                model: state.model,
                resIDs: resIds,
            };
            await this._executeButtonAction(actionData, recordData);
        } finally {
            this._enableButtons();
        }
    },
    /**
     * Overridden to always reload the main record when grouped by M2M.
     *
     * @override
     */
    _onReload(ev) {
        const { isM2MGrouped } = this.model.get(this.handle);
        if (isM2MGrouped) {
            // Ask for the main record to be reloaded.
            ev.data.db_id = this.handle;
        }
        this._super(...arguments);
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
     * @private
     */
    _onSelectDomain: function (ev) {
        ev.preventDefault();
        this.isDomainSelected = true;
        this._updateSelectionBox();
        this._updateControlPanel();
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
        this.isPageSelected = ev.data.allChecked;
        this.isDomainSelected = false;
        this.$('.o_list_export_xlsx').toggle(!this.selectedRecords.length);
        this._updateSelectionBox();
        this._updateControlPanel();
    },
    /**
     * If the record is set as dirty while in multiple record edition,
     * we want to immediatly discard the change.
     *
     * @private
     * @override
     * @param {OdooEvent} ev
     */
    _onSetDirty: function (ev) {
        var recordId = ev.data.dataPointID;
        if (this.renderer.isInMultipleRecordEdition(recordId)) {
            ev.stopPropagation();
            Dialog.alert(this, _t("No valid record to save"), {
                confirm_callback: async () => {
                    this.model.discardChanges(recordId);
                    await this._confirmSave(recordId);
                    this.renderer.focusCell(recordId, ev.target.__node);
                },
            });
        } else {
            this._super.apply(this, arguments);
        }
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
        var state = this.model.get(this.handle);
        if (!state.groupedBy) {
            this._updatePaging(state, { currentMinimum: 1 });
        }
        var self = this;
        this.model.setSort(state.id, ev.data.name).then(function () {
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
        ev.stopPropagation();
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

export default ListController;
