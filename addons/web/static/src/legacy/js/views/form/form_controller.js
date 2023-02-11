odoo.define('web.FormController', function (require) {
"use strict";

var BasicController = require('web.BasicController');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dialogs = require('web.view_dialogs');

var _t = core._t;
var qweb = core.qweb;

var FormController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        button_clicked: '_onButtonClicked',
        edited_list: '_onEditedList',
        open_one2many_record: '_onOpenOne2ManyRecord',
        open_record: '_onOpenRecord',
        toggle_column_order: '_onToggleColumnOrder',
        focus_control_button: '_onFocusControlButton',
        form_dialog_discarded: '_onFormDialogDiscarded',
        quick_edit: '_onQuickEdit',
    }),
    /**
     * Time between multiple clicks (used to detect double click text selection)
     */
    multiClickTime: 350,
    /**
     * @override
     *
     * @param {boolean} params.hasActionMenus
     * @param {Object} params.toolbarActions
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        this.actionButtons = params.actionButtons;
        this.disableAutofocus = params.disableAutofocus;
        this.footerToButtons = params.footerToButtons;
        this.defaultButtons = params.defaultButtons;
        this.hasActionMenus = params.hasActionMenus;
        this.toolbarActions = params.toolbarActions || {};
        // Quick edit is delayed by `multiClickTime` time. If a subsequent click
        // happens within this time, the quick edit is aborted.
        this.quickEditTimeout = undefined;
    },
    /**
     * Called each time the form view is attached into the DOM
     *
     * @todo convert to new style
     */
    on_attach_callback: function () {
        this._super.apply(this, arguments);
        this.autofocus();
    },
    /**
     * This hook is called when a form view is restored (by clicking on the
     * breadcrumbs). In general, we force mode back to readonly, because
     * whenever we leave a form view by stacking another action on the top of
     * it, it is saved, and should no longer be in edit mode. However, there is
     * a special case for new records for which we still want to be in 'edit'
     * as no record has been created (changes have been discarded before
     * leaving).
     *
     * @override
     * @param {boolean} [shouldReload]
     */
    willRestore: function (shouldReload) {
        this.mode = this.model.isNew(this.handle) ? 'edit' : 'readonly';
        if (shouldReload) {
            return this._setMode(this.mode);
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Calls autofocus on the renderer
     */
    autofocus: function () {
        if (!this.disableAutofocus) {
            var isControlActivted = this.renderer.autofocus();
            if (!isControlActivted) {
                // this can happen in read mode if there are no buttons with
                // btn-primary class
                if (this.$buttons && this.mode === 'readonly') {
                    return this.$buttons.find('.o_form_button_edit').focus();
                }
            }
        }
    },
    /**
     * @override
     * @param {string} [recordID] - default to main recordID
     * @returns {Promise<boolean>}
     *          resolved if can be discarded, a boolean value is given to tells
     *          if there is something to discard or not
     *          rejected otherwise
     */
    canBeDiscarded: function (recordId) {
        if (recordId !== this.handle && this.isDirty(recordId)) {
            // Embedded list views can ask to discard their changes when we
            // click in the webclient. If a field in the list is invalid, it
            // stay dirty.
            // When these conditions are met we don't want to discard.
            return Promise.reject();
        } else {
            return Promise.resolve(true);
        }
    },
    /**
     * This method switches the form view in edit mode, with a new record.
     *
     * @todo make record creation a basic controller feature
     * @param {string} [parentID] if given, the parentID will be used as parent
     *                            for the new record.
     * @param {Object} [additionalContext]
     * @returns {Promise}
     */
    createRecord: async function (parentID, additionalContext) {
        const record = this.model.get(this.handle, { raw: true });
        const handle = await this.model.load({
            context: record.getContext({ additionalContext: additionalContext}),
            fields: record.fields,
            fieldsInfo: record.fieldsInfo,
            modelName: this.modelName,
            parentID: parentID,
            res_ids: record.res_ids,
            type: 'record',
            viewType: 'form',
        });
        this.handle = handle;
        this._updateControlPanel();
        return this._setMode('edit');
    },
    /**
     * Returns the current res_id, wrapped in a list. This is only used by the
     * action menus (and the debugmanager)
     *
     * @override
     *
     * @returns {number[]} either [current res_id] or []
     */
    getSelectedIds: function () {
        var env = this.model.get(this.handle, {env: true});
        return env.currentId ? [env.currentId] : [];
    },
    /**
     * @override method from AbstractController
     * @returns {string}
     */
    getTitle: function () {
        return this.model.getName(this.handle);
    },
    /**
     * Add the current ID to the state pushed in the url.
     *
     * @override
     */
    getState: function () {
        const state = this._super.apply(this, arguments);
        const env = this.model.get(this.handle, {env: true});
        state.id = env.currentId;
        return state;
    },
    /**
     * Render buttons for the control panel.  The form view can be rendered in
     * a dialog, and in that case, if we have buttons defined in the footer, we
     * have to use them instead of the standard buttons.
     *
     * @override method from AbstractController
     * @param {jQuery} [$node]
     */
    renderButtons: function ($node) {
        var $footer = this.footerToButtons ? this.renderer.$el && this.renderer.$('footer') : null;
        var mustRenderFooterButtons = $footer && $footer.length;
        if ((this.defaultButtons && !this.$buttons) || mustRenderFooterButtons) {
            this.$buttons = $('<div/>');
            if (mustRenderFooterButtons) {
                this.$buttons.append($footer);
            } else {
                this.$buttons.append(qweb.render("FormView.buttons", {widget: this}));
                this.$buttons.on('click', '.o_form_button_edit', this._onEdit.bind(this));
                this.$buttons.on('click', '.o_form_button_create', this._onCreate.bind(this));
                this.$buttons.on('click', '.o_form_button_save', this._onSave.bind(this));
                this.$buttons.on('click', '.o_form_button_cancel', this._onDiscard.bind(this));
                this._assignSaveCancelKeyboardBehavior(this.$buttons.find('.o_form_buttons_edit'));
                this.$buttons.find('.o_form_buttons_edit').tooltip({
                    delay: {show: 200, hide:0},
                    title: function(){
                        return qweb.render('SaveCancelButton.tooltip');
                    },
                    trigger: 'manual',
                });
            }
        }
        if (this.$buttons && $node) {
            this.$buttons.appendTo($node);
        }
    },
    /**
     * The form view has to prevent a click on the pager if the form is dirty
     *
     * @override method from BasicController
     * @param {jQueryElement} $node
     * @param {Object} options
     * @returns {Promise}
     */
    _getPagingInfo: function () {
        // Only display the pager if we are not on a new record.
        if (this.model.isNew(this.handle)) {
            return null;
        }
        return Object.assign(this._super(...arguments), {
            validate: this.saveChanges.bind(this),
        });
    },
    /**
     * @override
     * @private
     **/
    _getActionMenuItems: function (state) {
        if (!this.hasActionMenus || this.mode === 'edit') {
            return null;
        }
        const props = this._super(...arguments);
        const activeField = this.model.getActiveField(state);
        const otherActionItems = [];
        if (this.archiveEnabled && activeField in state.data) {
            if (state.data[activeField]) {
                otherActionItems.push({
                    description: _t("Archive"),
                    callback: () => {
                        Dialog.confirm(this, _t("Are you sure that you want to archive this record?"), {
                            confirm_callback: () => this._toggleArchiveState(true),
                        });
                    },
                });
            } else {
                otherActionItems.push({
                    description: _t("Unarchive"),
                    callback: () => this._toggleArchiveState(false),
                });
            }
        }
        if (this.activeActions.create && this.activeActions.duplicate) {
            otherActionItems.push({
                description: _t("Duplicate"),
                callback: () => this._onDuplicateRecord(this),
            });
        }
        if (this.activeActions.delete) {
            otherActionItems.push({
                description: _t("Delete"),
                callback: () => this._onDeleteRecord(this),
            });
        }
        return Object.assign(props, {
            items: Object.assign(this.toolbarActions, { other: otherActionItems }),
        });
    },
    /**
     * Show a warning message if the user modified a translated field.  For each
     * field, the notification provides a link to edit the field's translations.
     *
     * @override
     */
    saveRecord: async function () {
        const changedFields = await this._super(...arguments);
        // the title could have been changed
        this._updateControlPanel();

        if (_t.database.multi_lang && changedFields.length) {
            // need to make sure changed fields that should be translated
            // are displayed with an alert
            var fields = this.renderer.state.fields;
            var data = this.renderer.state.data;
            var alertFields = {};
            for (var k = 0; k < changedFields.length; k++) {
                var field = fields[changedFields[k]];
                var fieldData = data[changedFields[k]];
                if (field.translate && fieldData && fieldData !== '<p><br></p>') {
                    alertFields[changedFields[k]] = field;
                }
            }
            if (!_.isEmpty(alertFields)) {
                this.renderer.updateAlertFields(alertFields);
            }
        }
        return changedFields;
    },
    /**
     * Overrides to force the viewType to 'form', so that we ensure that the
     * correct fields are reloaded (this is only useful for one2many form views).
     *
     * @override
     */
    update: async function (params, options) {
        if ('currentId' in params && !params.currentId) {
            this.mode = 'edit'; // if there is no record, we are in 'edit' mode
        }
        params = _.extend({viewType: 'form', mode: this.mode}, params);
        await this._super(params, options);
        this.autofocus();
    },
    /**
     * @override
     */
    updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        if (this.footerToButtons) {
            var $footer = this.renderer.$el && this.renderer.$('footer');
            if ($footer && $footer.length) {
                this.$buttons.empty().append($footer);
            }
        }
        var edit_mode = (this.mode === 'edit');
        this.$buttons.find('.o_form_buttons_edit')
            .toggleClass('o_hidden', !edit_mode);
        this.$buttons.find('.o_form_buttons_view')
            .toggleClass('o_hidden', edit_mode);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _applyChanges: async function () {
        const result = await this._super.apply(this, arguments);
        core.bus.trigger('DOM_updated');
        return result;
    },
    /**
     * Assign on the buttons save and discard additionnal behavior to facilitate
     * the work of the users doing input only using the keyboard
     *
     * @param {jQueryElement} $saveCancelButtonContainer  The div containing the
     * save and cancel buttons
     * @private
     */
    _assignSaveCancelKeyboardBehavior: function ($saveCancelButtonContainer) {
        var self = this;
        $saveCancelButtonContainer.children().on('keydown', function (e) {
            switch(e.which) {
                case $.ui.keyCode.ENTER:
                    e.preventDefault();
                    self.saveRecord();
                    break;
                case $.ui.keyCode.ESCAPE:
                    e.preventDefault();
                    self._discardChanges();
                    break;
                case $.ui.keyCode.TAB:
                    if (!e.shiftKey && e.target.classList.contains('btn-primary')) {
                        $saveCancelButtonContainer.tooltip('show');
                        e.preventDefault();
                    }
                    break;
            }
        });
    },
    /**
     * When a save operation has been confirmed from the model, this method is
     * called.
     *
     * @private
     * @override method from field manager mixin
     * @param {string} id - id of the previously changed record
     * @returns {Promise}
     */
    _confirmSave: function (id) {
        if (id === this.handle) {
            if (this.mode === 'readonly') {
                return this.reload();
            } else {
                return this._setMode('readonly');
            }
        } else {
            // A subrecord has changed, so update the corresponding relational field
            // i.e. the one whose value is a record with the given id or a list
            // having a record with the given id in its data
            var record = this.model.get(this.handle);

            // Callback function which returns true
            // if a value recursively contains a record with the given id.
            // This will be used to determine the list of fields to reload.
            var containsChangedRecord = function (value) {
                return _.isObject(value) &&
                    (value.id === id || _.find(value.data, containsChangedRecord));
            };

            var changedFields = _.findKey(record.data, containsChangedRecord);
            return this.renderer.confirmChange(record, record.id, [changedFields]);
        }
    },
    /**
     * Override to disable buttons in the renderer.
     *
     * @override
     * @private
     */
    _disableButtons: function () {
        this._super.apply(this, arguments);
        this.renderer.disableButtons();
    },
    /**
     * Override to enable buttons in the renderer.
     *
     * @override
     * @private
     */
    _enableButtons: function () {
        this._super.apply(this, arguments);
        this.renderer.enableButtons();
    },
    /**
     * Hook method, called when record(s) has been deleted.
     *
     * @override
     */
    _onDeletedRecords: function () {
        var state = this.model.get(this.handle, {raw: true});
        if (!state.res_ids.length) {
            this.trigger_up('history_back');
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to reload the form when saving failed in readonly (e.g. after
     * a change on a widget like priority or statusbar).
     *
     * @override
     * @private
     */
    _rejectSave: function () {
        if (this.mode === 'readonly') {
            return this.reload();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     * @returns {Promise}
     */
    _setEditMode: function () {
        this._disableButtons();
        // wait for potential pending changes to be saved (done with widgets
        // allowing to edit in readonly)
        return this.mutex.getUnlockedDef()
            .then(this._setMode.bind(this, 'edit'))
            .then(this._enableButtons.bind(this))
            .guardedCatch(this._enableButtons.bind(this));
    },
    /**
     * Calls unfreezeOrder when changing the mode.
     * Also, when there is a change of mode, the tracking of last activated
     * field is reset, so that the following field activation process starts
     * with the 1st field.
     *
     * @override
     */
    _setMode: function (mode, recordID) {
        if ((recordID || this.handle) === this.handle) {
            this.model.unfreezeOrder(this.handle);
        }
        if (this.mode !== mode) {
            this.renderer.resetLastActivatedField();
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    _shouldBounceOnClick(element) {
        return this.mode === 'readonly' &&
            !!element.closest('.oe_title, .o_inner_group') &&
            this.quickEditTimeout === undefined;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Save the record when we are about to leave Odoo.
     *
     * @override
     */
    _onBeforeUnload: function () {
        this._urgentSave(this.handle);
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onButtonClicked: function (ev) {
        // stop the event's propagation as a form controller might have other
        // form controllers in its descendants (e.g. in a FormViewDialog)
        ev.stopPropagation();
        var self = this;
        var def;

        this._disableButtons();

        function saveAndExecuteAction () {
            return self.saveRecord(self.handle, {
                stayInEdit: true,
            }).then(function () {
                // we need to reget the record to make sure we have changes made
                // by the basic model, such as the new res_id, if the record is
                // new.
                var record = self.model.get(ev.data.record.id);
                return self._callButtonAction(attrs, record);
            });
        }
        var attrs = ev.data.attrs;
        if (attrs.confirm) {
            def = new Promise(function (resolve, reject) {
                Dialog.confirm(self, attrs.confirm, {
                    confirm_callback: saveAndExecuteAction,
                }).on("closed", null, resolve);
            });
        } else if (attrs.special === 'cancel') {
            def = this._callButtonAction(attrs, ev.data.record);
        } else if (!attrs.special || attrs.special === 'save') {
            // save the record but don't switch to readonly mode
            def = saveAndExecuteAction();
        } else {
            console.warn('Unhandled button event', ev);
            return;
        }

        // Kind of hack for FormViewDialog: button on footer should trigger the dialog closing
        // if the `close` attribute is set
        def.then(function () {
            self._enableButtons();
            if (attrs.close) {
                self.trigger_up('close_dialog');
            }
        }).guardedCatch(this._enableButtons.bind(this));
    },
    /**
     * Called when the user wants to create a new record -> @see createRecord
     *
     * @private
     */
    _onCreate: function () {
        this.createRecord();
    },
    /**
     * Deletes the current record
     *
     * @private
     */
    _onDeleteRecord: function () {
        this._deleteRecords([this.handle]);
    },
    /**
     * Called when the user wants to discard the changes made to the current
     * record -> @see discardChanges
     *
     * @private
     */
    _onDiscard: function () {
        this._disableButtons();
        this._discardChanges()
            .then(this._enableButtons.bind(this))
            .guardedCatch(this._enableButtons.bind(this));
    },
    /**
     * Called when the user clicks on 'Duplicate Record' in the action menus
     *
     * @private
     */
    _onDuplicateRecord: async function () {
        const handle = await this.model.duplicateRecord(this.handle);
        this.handle = handle;
        this._updateControlPanel();
        this._setMode('edit');
    },
    /**
     * Called when the user wants to edit the current record -> @see _setMode
     *
     */
    _onEdit: function () {
        this._setEditMode();
    },
    /**
     * This method is called when someone tries to freeze the order, most likely
     * in a x2many list view
     *
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.id of the list to freeze while editing a line
     */
    _onEditedList: function (ev) {
        ev.stopPropagation();
        if (ev.data.id) {
            this.model.save(ev.data.id, {savePoint: true});
        }
        this.model.freezeOrder(ev.data.id);
    },
    /**
     * Set the focus on the first primary button of the controller (likely Edit)
     *
     * @private
     * @param {OdooEvent} event
     */
    _onFocusControlButton:function(e) {
        if (this.$buttons) {
            e.stopPropagation();
            this.$buttons.find('.btn-primary:visible:first()').focus();
        }
    },
    /**
     * Reset the focus on the control that openned a Dialog after it was closed
     *
     * @private
     * @param {OdooEvent} event
     */
    _onFormDialogDiscarded: function(ev) {
        ev.stopPropagation();
        var isFocused = this.renderer.focusLastActivatedWidget();
        if (ev.data.callback) {
            ev.data.callback(_.str.toBool(isFocused));
        }
    },
    /**
     * Opens a one2many record (potentially new) in a dialog. This handler is
     * o2m specific as in this case, the changes done on the related record
     * shouldn't be saved in DB when the user clicks on 'Save' in the dialog,
     * but later on when he clicks on 'Save' in the main form view. For this to
     * work correctly, the main model and the local id of the opened record must
     * be given to the dialog, which will complete the viewInfo of the record
     * with the one of the form view.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onOpenOne2ManyRecord: async function (ev) {
        ev.stopPropagation();
        var data = ev.data;
        var record;
        if (data.id) {
            record = this.model.get(data.id, {raw: true});
        }

        // Sync with the mutex to wait for potential onchanges
        await this.model.mutex.getUnlockedDef();

        new dialogs.FormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: data.on_saved,
            on_remove: data.on_remove,
            parentID: data.parentID,
            readonly: data.readonly,
            editable: data.editable,
            deletable: record ? data.deletable : false,
            disable_multiple_selection: data.disable_multiple_selection,
            recordID: record && record.id,
            res_id: record && record.res_id,
            res_model: data.field.relation,
            shouldSaveLocally: true,
            title: (record ? _t("Open: ") : _t("Create ")) + (ev.target.string || data.field.string),
        }).open();
    },
    /**
     * Open an existing record in a form view dialog
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onOpenRecord: function (ev) {
        ev.stopPropagation();
        var self = this;
        var record = this.model.get(ev.data.id, {raw: true});
        new dialogs.FormViewDialog(self, {
            context: ev.data.context,
            fields_view: ev.data.fields_view,
            on_saved: ev.data.on_saved,
            on_remove: ev.data.on_remove,
            readonly: ev.data.readonly,
            deletable: ev.data.deletable,
            editable: ev.data.editable,
            res_id: record.res_id,
            res_model: record.model,
            title: _t("Open: ") + ev.data.string,
        }).open();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onQuickEdit: function (ev) {
        ev.stopPropagation();
        clearTimeout(this.quickEditTimeout);
        if (this.activeActions.edit && !window.getSelection().toString()) {
            const quickEdit = async () => {
                if (!this.isDestroyed()) {
                    await this._setEditMode();
                    this.renderer.quickEdit(ev.data);
                }
                this.quickEditTimeout = undefined;
            };
            if (this.multiClickTime > 0) {
                this.quickEditTimeout = setTimeout(quickEdit, this.multiClickTime);
            } else {
                quickEdit();
            }
        }
    },
    /**
     * Called when the user wants to save the current record -> @see saveRecord
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onSave: function (ev) {
        ev.stopPropagation(); // Prevent x2m lines to be auto-saved
        this._disableButtons();
        this.saveRecord().then(this._enableButtons.bind(this)).guardedCatch(this._enableButtons.bind(this));
    },
    /**
     * This method is called when someone tries to sort a column, most likely
     * in a x2many list view
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onToggleColumnOrder: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.model.setSort(ev.data.id, ev.data.name).then(function () {
            var field = ev.data.field;
            var state = self.model.get(self.handle);
            self.renderer.confirmChange(state, state.id, [field]);
        });
    },
    /**
     * Called when clicking on 'Archive' or 'Unarchive' in the action menus.
     *
     * @private
     * @param {boolean} archive
     */
    _toggleArchiveState: function (archive) {
        const resIds = this.model.localIdsToResIds([this.handle]);
        this._archive(resIds, archive);
    },
});

return FormController;

});
