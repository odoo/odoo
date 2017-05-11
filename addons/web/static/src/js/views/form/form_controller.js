odoo.define('web.FormController', function (require) {
"use strict";

var BasicController = require('web.BasicController');
var dialogs = require('web.view_dialogs');
var core = require('web.core');
var Dialog = require('web.Dialog');
var Sidebar = require('web.Sidebar');

var _t = core._t;
var qweb = core.qweb;

var FormController = BasicController.extend({
    custom_events: _.extend({}, BasicController.prototype.custom_events, {
        open_one2many_record: '_onOpenOne2ManyRecord',
        bounce_edit: '_onBounceEdit',
        button_clicked: '_onButtonClicked',
        discard_x2m_changes: '_onDiscardX2MChanges',
        open_record: '_onOpenRecord',
        toggle_column_order: '_onToggleColumnOrder',
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
        this.footerToButtons = params.footerToButtons;
        this.defaultButtons = params.defaultButtons;
        this.hasSidebar = params.hasSidebar;
        this.toolbarActions = params.toolbarActions || {};
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
     * This method switches the form view in edit mode, with a new record.
     *
     * @todo make record creation a basic controller feature
     * @returns {Deferred}
     */
    createRecord: function () {
        var self = this;
        var record = this.model.get(this.handle, {raw: true});
        return this.model.load({
            context: record.getContext(),
            fields: record.fields,
            fieldsInfo: record.fieldsInfo,
            modelName: this.modelName,
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
        var $footer = this.footerToButtons ? this.$('footer') : null;
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * When a save operation has been confirmed from the model, this method is
     * called.
     *
     * @private
     * @override method from field manager mixin
     * @param {string} id
     */
    _confirmSave: function (id) {
        if (id === this.handle) {
            if (this.mode === 'readonly') {
                return this.reload();
            } else {
                return this._setMode('readonly');
            }
        } else {
            // a subrecord changed, so update the corresponding relational field
            // i.e. the one whose value is a record with the given id or a list
            // having a record with the given id in its data
            var record = this.model.get(this.handle);
            var fieldsChanged = _.findKey(record.data, function (d) {
                return _.isObject(d) &&
                    (d.id === id || _.findWhere(d.data, {id: id}));
            });
            return this.renderer.confirmChange(record, record.id, [fieldsChanged]);
        }
    },
    /**
     * Hook method, called when record(s) has been deleted.
     *
     * @override
     */
    _onDeletedRecords: function () {
        var state = this.model.get(this.handle, {raw: true});
        if (!state.res_ids.length) {
            this.do_action('history_back');
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
        return this._super.apply(this, arguments);
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
            this.$buttons.find('.o_form_button_edit').openerpBounce();
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
            // save the record but don't switch to readonly mode
            def = this.saveRecord(this.handle, {
                stayInEdit: true,
                reload: false,
            }).then(function () {
                // we need to reget the record to make sure we have changes made
                // by the basic model, such as the new res_id, if the record is
                // new.
                var record = self.model.get(event.data.record.id);
                return self._callButtonAction(attrs, record);
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
     * Called when the user wants to create a new record -> @see createRecord
     *
     * @private
     */
    _onCreate: function () {
        this.createRecord();
    },
    /**
     * Called when the user wants to discard the changes made to the current
     * record -> @see discardChanges
     *
     * @private
     */
    _onDiscard: function () {
        this.discardChanges();
    },
    /**
     * Called when a x2m asks to discard the changes made to one of its row.
     *
     * @todo find a better way to handle this... this could also be used outside
     * of form views
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onDiscardX2MChanges: function (ev) {
        var self = this;
        ev.stopPropagation();
        var recordID = ev.data.recordID;
        this.discardChanges(recordID)
            .done(function () {
                if (self.model.isNew(recordID)) {
                    self._abandonRecord(recordID);
                }
                // TODO this will tell the renderer to rerender the widget that
                // asked for the discard but will unfortunately lose the click
                // made on another row if any
                self._confirmChange(self.handle, [ev.target.name], ev)
                    .always(ev.data.onSuccess);
            })
            .fail(ev.data.onFailure);
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

        new dialogs.FormViewDialog(this, {
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
    },
    /**
     * Open an existing record in a form view dialog
     *
     * @private
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
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
        this.saveRecord();
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
        this.renderer.confirmChange(state, state.id, [field]);
    },
});

return FormController;

});
