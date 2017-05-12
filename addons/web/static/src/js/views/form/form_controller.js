odoo.define('web.FormController', function (require) {
"use strict";

var Framework = require('web.framework');
var BasicController = require('web.BasicController');
var dialogs = require('web.view_dialogs');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Sidebar = require('web.Sidebar');

var _t = core._t;
var qweb = core.qweb;

var FormController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        bounce_edit: '_onBounceEdit',
        button_clicked: '_onButtonClicked',
        freeze_order: '_onFreezeOrder',
        open_one2many_record: '_onOpenOne2ManyRecord',
        open_record: '_onOpenRecord',
        toggle_column_order: '_onToggleColumnOrder',
        focus_control_button: '_onFocusControlButton',
        shift_enter_pressed: '_onShiftEnterPress',
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

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Calls autofocus on the renderer
     */
    autofocus: function () {
        if (!this.disableAutofocus) {
            if (this.$buttons && this.mode === 'readonly') {
                return this.$buttons.find('.o_form_button_edit').focus();
            }
            this.renderer.autofocus();
        }
    },
    /**
     * This method switches the form view in edit mode, with a new record.
     *
     * @todo make record creation a basic controller feature
     * @param {string} [parentID] if given, the parentID will be used as parent
     *                            for the new record.
     * @returns {Deferred}
     */
    createRecord: function (parentID) {
        var self = this;
        this.lastTabindex = 0;
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
     * Called each time the form view is attached into the DOM
     *
     * @todo convert to new style
     */
    on_attach_callback: function () {
        this.renderer.setTabindexWidgets();
        this.autofocus();
    },
    /**
     * Render buttons for the control panel.  The form view can be rendered in
     * a dialog, and in that case, if we have buttons defined in the footer, we
     * have to use them instead of the standard buttons, when focus comes to button
     * show tip, also support keyboard keys TAB, ENTER and ESCAPE.
     *
     * @override method from AbstractController
     * @param {jQueryElement} $node
     */
    renderButtons: function ($node) {
        var self = this;
        var $footer = this.footerToButtons ? this.$('footer') : null;
        var mustRenderFooterButtons = $footer && $footer.length;
        if (!this.defaultButtons && !mustRenderFooterButtons) {
            return;
        }
        this.$buttons = $('<div/>');
        if (mustRenderFooterButtons) {
            this.$buttons.append($footer);
        } else {
            var mouseClicked = false;
            var on_button_focus = function (bindElement, message) {
                if (mouseClicked) {
                    $(bindElement).tooltip('hide');
                    mouseClicked = false;
                    return;
                }
                Framework.showFocusTip({attachTo: bindElement, message: message, trigger: 'focus'});
            };

            this.$buttons.append(qweb.render("FormView.buttons", {widget: this}));
            this.$buttons.on('mousedown', 'button', function () {
                mouseClicked = true;
            });
            this.$buttons.find('.o_form_button_edit')
                .on('click', this._onEdit.bind(this))
                .on('focus', function () {
                    on_button_focus(this, _t('Press ENTER to Edit or ESC to go back'));
                })
                .on('keydown', function (e) {
                    if (e.which === $.ui.keyCode.ESCAPE) {
                        $(this).tooltip('hide'); //forcefully hide tooltip as firefox doesn't hide it when element get hidden
                        self.trigger_up('history_back');
                    }
                });

            this.$buttons.find('.o_form_button_create')
                .on('click', this._onCreate.bind(this))
                .on('focus', function () {
                    on_button_focus(this, _t('Press ENTER to <b>Create</b> or ESC to go back'));
                })
                .on('keydown', function (e) {
                    if (e.which === $.ui.keyCode.TAB) {
                        e.preventDefault();
                        self.renderer.focusFirstButton();
                    } else if (e.which === $.ui.keyCode.ESCAPE) {
                        $(this).tooltip('hide'); //forcefully hide tooltip as firefox doesn't hide it when element get hidden
                        self.trigger_up('history_back');
                    }
                });

            this.$buttons.find('.o_form_button_save')
                .on('click', this._onSave.bind(this))
                .on('focus', function () {
                    on_button_focus(this, _t('Press ENTER to Save or ESC to Discard'));
                })
                .on('keydown', function (event) {
                    event.preventDefault();
                    if (event.which === $.ui.keyCode.TAB) {
                        if (event.shiftKey && self.renderer.getLastFieldWidget()) {
                            self.renderer.getLastFieldWidget().activate();
                        } else {
                            self.renderer.focusFirstButton();
                        }
                    } else if (event.which === $.ui.keyCode.ENTER) {
                        self._onSave(event).then(function () {
                            self.renderer.focusFirstButton();
                        });
                    } else if (event.which === $.ui.keyCode.ESCAPE) {
                        self._onDiscard();
                    }
                });

            this.$buttons.on('click', '.o_form_button_cancel', this._onDiscard.bind(this));

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
            this.sidebar.appendTo($node);

            // Show or hide the sidebar according to the view mode
            this._updateSidebar();
        }
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
            self.set('title', self.getTitle());
            self._updateEnv();

            if (_t.database.multi_lang && changedFields.length) {
                // need to make sure changed fields that should be translated
                // are displayed with an alert
                var fields = self.renderer.state.fields;
                var data = self.renderer.state.data;
                var alertFields = [];
                for (var k = 0; k < changedFields.length; k++) {
                    var field = fields[changedFields[k]];
                    var fieldData = data[changedFields[k]];
                    if (field.translate && fieldData) {
                        alertFields.push(field);
                    }
                }
                if (alertFields.length) {
                    self.renderer.alertFields = alertFields;
                    self.renderer.displayTranslationAlert();
                }
            }
            return changedFields;
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * When a save operation has been confirmed from the model, this method is
     * called.
     *
     * @private
     * @override method from field manager mixin
     * @param {string} id - id of the previously changed record
     * @returns {Deferred}
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
     *
     * @override
     */
    _setMode: function (mode, recordID) {
        if ((recordID || this.handle) === this.handle) {
            this.model.unfreezeOrder(this.handle);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Updates the controller's title according to the new state
     *
     * @override
     * @private
     * @param {Object} state
     * @returns {Deferred}
     */
    _update: function () {
        var title = this.getTitle();
        this.set('title', title);
        this._updateButtons();
        this._updateSidebar();
        return this._super.apply(this, arguments).then(this.autofocus.bind(this));
    },
    /**
     * @private
     */
    _updateButtons: function () {
        if (this.$buttons) {
            if (this.footerToButtons) {
                var $footer = this.$('footer');
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
     * @param {OdooEvent} event
     */
    _onButtonClicked: function (event) {
        // stop the event's propagation as a form controller might have other
        // form controllers in its descendants (e.g. in a FormViewDialog)
        event.stopPropagation();
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
                var record = self.model.get(event.data.record.id);
                return self._callButtonAction(attrs, record, event.data.callback);
            });
        }
        var attrs = event.data.attrs;
        if (attrs.confirm) {
            var d = $.Deferred();
            Dialog.confirm(this, attrs.confirm, {
                confirm_callback: saveAndExecuteAction,
            }).on("closed", null, function () {
                d.resolve();
            });
            def = d.promise();
        } else if (attrs.special === 'cancel') {
            def = this._callButtonAction(attrs, event.data.record, event.data.callback);
        } else if (!attrs.special || attrs.special === 'save') {
            // save the record but don't switch to readonly mode
            def = saveAndExecuteAction();
        }

        def.always(this._enableButtons.bind(this));
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
     * When user press Escape this method will be called and if there is any dialog
     * then we will first close top most dialog and set focus to previous dialog,
     * if there is not dialog then we will call super method to discard whole record.
     *
     * @override
     */
    _onDiscardChanges: function () {
        // If popups are open and by chance if popup does not have focus instead focus is on some other form maybe on main form
        // then first close the top popup otherwise main form's cancel will move us to history_back(maybe on listview) but popup still remains open
        // this should never happen so to avoid this worst case scenario we check if popup is available then close top popup
        var modals = $('body > .modal').filter(':visible');
        // Need to use document.activeElement because issue is something like: http://blog.mattheworiordan.com/post/9308775285/testing-focus-with-jquery-and-selenium-or
        var hasFocus = $(document.activeElement).closest(".modal").length;
        if (modals.length && !hasFocus) {
            var lastModal = modals && modals.last();
            lastModal.modal('hide');
            lastModal.remove();
            return;
        }
        return this._super.apply(this, arguments);
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
     * @param {OdooEvent} event
     */
    _onFreezeOrder: function (event) {
        event.stopPropagation();
        this.model.freezeOrder(event.data.id);
    },
    /**
     * When someone wants to set focus on Create/Edit/Save buttons then will trigger event focus_control_button,
     * ususally called using keyboard navigation, when user reach to last field widget and if press TAB
     * then user will be first navigated to Save button, if all widgets are traversed and user press TAB
     * then user will be navigated to Create/edit buttons, so this method will set focus to respective button according to mode.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onFocusControlButton: function (event) {
        event.stopPropagation();
        if (this.mode !== 'readonly' && this.$buttons && this.$buttons.find('.o_form_button_save').length) {
            return this.$buttons.find('.o_form_button_save').focus();
        } else if (this.mode === 'readonly' && this.$buttons && this.$buttons.find('.o_form_button_edit')) {
            return this.$buttons.find('.o_form_button_edit').focus();
        } else {
            return this.renderer.focusFirstButton();
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
     * @param {OdooEvent} event
     */
    _onOpenOne2ManyRecord: function (event) {
        event.stopPropagation();
        var data = event.data;
        var record;
        if (data.id) {
            record = this.model.get(data.id, {raw: true});
        }

        var FormViewDialog = new dialogs.FormViewDialog(this, {
            context: data.context,
            domain: data.domain,
            fields_view: data.fields_view,
            model: this.model,
            on_saved: data.on_saved,
            parentID: data.parentID,
            readonly: data.readonly,
            recordID: record && record.id,
            res_id: record && record.res_id,
            res_model: data.field.relation,
            shouldSaveLocally: true,
            title: (record ? _t("Open: ") : _t("Create ")) + (event.target.string || data.field.string),
        }).open();
        FormViewDialog.on('closed', this, function () {
            _.delay(function () {
                data.widget.$el.focus();
            }, 100);
        });
    },
    /**
     * Open an existing record in a form view dialog
     *
     * @private
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
        event.stopPropagation();
        var self = this;
        var record = this.model.get(event.data.id, {raw: true});
        new dialogs.FormViewDialog(self, {
            context: event.data.context,
            fields_view: event.data.fields_view,
            on_saved: event.data.on_saved,
            readonly: event.data.readonly,
            res_id: record.res_id,
            res_model: record.model,
            title: _t("Open: ") + event.data.string,
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
        return this.saveRecord();
    },
    /**
     * Save the record on SHIFT+ENTER and set focus to first header button,
     * if there is no header button then set focus to Edit button,
     * if there are not Save/Edit buttons(i.e. form in wizard) then trigger click of first action button.
     *
     * @private
     * @param {OdooEvent} event
     */
    _onShiftEnterPress: function (ev) {
        var self = this;
        if (this.$buttons && this.$buttons.find('.o_form_button_save').length) {
            this._onSave(ev).then(function () {
                var firstButton = self.renderer.getFirstButtonWidget(); // Need to get firstButton in if..else both because reload will re-render buttons
                if (firstButton) {
                    _.delay(function () {
                        firstButton.activate();
                    }, 0);
                } else {
                    _.delay(function () {
                        if (self.$buttons) {
                            self.$buttons.find('.o_form_button_edit').focus();
                        }
                    }, 0);
                }
            });
        } else {
            // Wizard will not have o_form_button_save, so in that case trigger click event for first button of wizard
            var firstButton = this.renderer.getFirstButtonWidget();
            if (firstButton) {
                firstButton.$el.trigger('click');
            }
        }
    },
    /**
     * This method is called when someone tries to sort a column, most likely
     * in a x2many list view
     *
     * @private
     * @param {OdooEvent} event
     */
    _onToggleColumnOrder: function (event) {
        event.stopPropagation();
        var self = this;
        this.model.setSort(event.data.id, event.data.name).then(function () {
            var field = event.data.field;
            var state = self.model.get(self.handle);
            self.renderer.confirmChange(state, state.id, [field]);
        });
    },
});

return FormController;

});
