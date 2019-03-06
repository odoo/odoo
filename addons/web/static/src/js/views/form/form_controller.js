odoo.define('web.FormController', function (require) {
"use strict";

var BasicController = require('web.BasicController');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dialogs = require('web.view_dialogs');
var Sidebar = require('web.Sidebar');

var _t = core._t;
var qweb = core.qweb;

var FormController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        bounce_edit: '_onBounceEdit',
        button_clicked: '_onButtonClicked',
        do_action: '_onDoAction',
        edited_list: '_onEditedList',
        open_one2many_record: '_onOpenOne2ManyRecord',
        open_record: '_onOpenRecord',
        toggle_column_order: '_onToggleColumnOrder',
        focus_control_button: '_onFocusControlButton',
        form_dialog_discarded: '_onFormDialogDiscarded',
        swipe_left: '_onSwipeLeft',
        swipe_right: '_onSwipeRight',
    }),
    /**
     * @override
     *
     * @param {boolean} params.hasSidebar
     * @param {Object} params.toolbarActions
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        this.actionButtons = params.actionButtons;
        this.disableAutofocus = params.disableAutofocus;
        this.footerToButtons = params.footerToButtons;
        this.defaultButtons = params.defaultButtons;
        this.hasSidebar = params.hasSidebar;
        this.toolbarActions = params.toolbarActions || {};
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
     * Force mode back to readonly. Whenever we leave a form view, it is saved,
     * and should no longer be in edit mode.
     *
     * @override
     */
    willRestore: function () {
        this.mode = 'readonly';
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
     * This method switches the form view in edit mode, with a new record.
     *
     * @todo make record creation a basic controller feature
     * @param {string} [parentID] if given, the parentID will be used as parent
     *                            for the new record.
     * @returns {Promise}
     */
    createRecord: function (parentID) {
        var self = this;
        var record = this.model.get(this.handle, {raw: true});
        return this.model.load({
            context: record.getContext(),
            fields: record.fields,
            fieldsInfo: record.fieldsInfo,
            modelName: this.modelName,
            parentID: parentID,
            res_ids: record.res_ids,
            type: 'record',
            viewType: 'form',
        }).then(function (handle) {
            self.handle = handle;
            self._updateEnv();
            return self._setMode('edit');
        });
    },
    /**
     * Returns the current res_id, wrapped in a list. This is only used by the
     * sidebar (and the debugmanager)
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
     * Render buttons for the control panel.  The form view can be rendered in
     * a dialog, and in that case, if we have buttons defined in the footer, we
     * have to use them instead of the standard buttons.
     *
     * @override method from AbstractController
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        var $footer = this.footerToButtons ? this.renderer.$('footer') : null;
        var mustRenderFooterButtons = $footer && $footer.length;
        if (!this.defaultButtons && !mustRenderFooterButtons) {
            return;
        }
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
     * @returns {Promise}
     */
    renderPager: function ($node, options) {
        options = _.extend({}, options, {
            validate: this.canBeDiscarded.bind(this),
        });
        return this._super($node, options);
    },
    /**
     * Instantiate and render the sidebar if a sidebar is requested
     * Sets this.sidebar
     * @param {jQuery} [$node] a jQuery node where the sidebar should be
     *   inserted
     * @return {Promise}
     **/
    renderSidebar: function ($node) {
        var self = this;
        if (this.hasSidebar) {
            var otherItems = [];
            if (this.is_action_enabled('delete')) {
                otherItems.push({
                    label: _t('Delete'),
                    callback: this._onDeleteRecord.bind(this),
                });
            }
            if (this.is_action_enabled('create') && this.is_action_enabled('duplicate')) {
                otherItems.push({
                    label: _t('Duplicate'),
                    callback: this._onDuplicateRecord.bind(this),
                });
            }
            this.sidebar = new Sidebar(this, {
                editable: this.is_action_enabled('edit'),
                viewType: 'form',
                env: {
                    context: this.model.get(this.handle).getContext(),
                    activeIds: this.getSelectedIds(),
                    model: this.modelName,
                },
                actions: _.extend(this.toolbarActions, {other: otherItems}),
            });
            return this.sidebar.appendTo($node).then(function() {
                 // Show or hide the sidebar according to the view mode
                self._updateSidebar();
            });
        }
        return Promise.resolve();
    },
    /**
     * Show a warning message if the user modified a translated field.  For each
     * field, the notification provides a link to edit the field's translations.
     *
     * @override
     */
    saveRecord: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function (changedFields) {
            // the title could have been changed
            self._setTitle(self.getTitle());
            self._updateEnv();

            if (_t.database.multi_lang && changedFields.length) {
                // need to make sure changed fields that should be translated
                // are displayed with an alert
                var fields = self.renderer.state.fields;
                var data = self.renderer.state.data;
                var alertFields = {};
                for (var k = 0; k < changedFields.length; k++) {
                    var field = fields[changedFields[k]];
                    var fieldData = data[changedFields[k]];
                    if (field.translate && fieldData) {
                        alertFields[changedFields[k]] = field;
                    }
                }
                if (!_.isEmpty(alertFields)) {
                    self.renderer.updateAlertFields(alertFields);
                }
            }
            return changedFields;
        });
    },
    /**
     * Overrides to force the viewType to 'form', so that we ensure that the
     * correct fields are reloaded (this is only useful for one2many form views).
     *
     * @override
     */
    update: function (params, options) {
        if ('currentId' in params && !params.currentId) {
            this.mode = 'edit'; // if there is no record, we are in 'edit' mode
        }
        params = _.extend({viewType: 'form', mode: this.mode}, params);
        return this._super(params, options);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
     * Updates the controller's title according to the new state
     *
     * @override
     * @private
     * @param {Object} state
     * @returns {Promise}
     */
    _update: function () {
        var self = this;

        return this._super.apply(this, arguments).then(function() {
            var title = self.getTitle();
            self._setTitle(title);
            self._updateButtons();
            self._updateSidebar();

            self.autofocus();
        });
    },
    /**
     * @private
     */
    _updateButtons: function () {
        if (this.$buttons) {
            if (this.footerToButtons) {
                var $footer = this.renderer.$('footer');
                if ($footer.length) {
                    this.$buttons.empty().append($footer);
                }
            }
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
     * Bounce the 'Edit' button.
     *
     * @private
     */
    _onBounceEdit: function () {
        if (this.$buttons) {
            this.$buttons.find('.o_form_button_edit').odooBounce();
        }
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
                Dialog.confirm(this, attrs.confirm, {
                    confirm_callback: saveAndExecuteAction,
                }).on("closed", null, resolve);
            });
        } else if (attrs.special === 'cancel') {
            def = this._callButtonAction(attrs, ev.data.record);
        } else if (!attrs.special || attrs.special === 'save') {
            // save the record but don't switch to readonly mode
            def = saveAndExecuteAction();
        }

        def.then(this._enableButtons.bind(this)).guardedCatch(this._enableButtons.bind(this));
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
        this._discardChanges();
    },
    /**
     * Destroy subdialog widgets after an action is finished.
     *
     * @param {OdooEvent} ev
     * @private
     */
    _onDoAction: function (ev) {
        var self = this;
        // A priori, different widgets could write on the "on_success" key.
        // Below we ensure that all the actions required by those widgets
        // are executed in a suitable order before every cycle of destruction.
        var callback = ev.data.on_success || function () {};
        ev.data.on_success = function () {
            callback();
            function isDialog (widget) {
                return (widget instanceof Dialog);
            }
            _.invoke(self.getChildren().filter(isDialog), 'destroy');
        };
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
                self.handle = handle;
                self._updateEnv();
                self._setMode('edit');
            });
    },
    /**
     * Called when the user wants to edit the current record -> @see _setMode
     *
     * @private
     */
    _onEdit: function () {
        this._setMode('edit');
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
    _onFormDialogDiscarded: function(e) {
        e.stopPropagation();
        this.renderer.focusLastActivatedWidget();
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
    _onOpenOne2ManyRecord: function (ev) {
        ev.stopPropagation();
        var data = ev.data;
        var record;
        if (data.id) {
            record = this.model.get(data.id, {raw: true});
        }

        new dialogs.FormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: data.on_saved,
            on_remove: data.on_remove,
            parentID: data.parentID,
            readonly: data.readonly,
            deletable: record ? data.deletable : false,
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
            res_id: record.res_id,
            res_model: record.model,
            title: _t("Open: ") + ev.data.string,
        }).open();
    },
    /**
     * Called when the user wants to save the current record -> @see saveRecord
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onSave: function (ev) {
        ev.stopPropagation(); // Prevent x2m lines to be auto-saved
        var self = this;
        this._disableButtons();
        this.saveRecord().then(this._enableButtons.bind(this)).guardedCatch(this._enableButtons.bind(this));
    },
    /**
     * Called when user swipes left. Move to next record.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSwipeLeft: function (ev) {
        ev.stopPropagation();
        if (this.pager) {
            this.pager.next();
        }
    },
    /**
     * Called when user swipes right. Move to previous record.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSwipeRight: function (ev) {
        ev.stopPropagation();
        if (this.pager) {
            this.pager.previous();
        }
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
});

return FormController;

});
