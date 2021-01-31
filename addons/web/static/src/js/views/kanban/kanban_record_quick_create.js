odoo.define('web.kanban_record_quick_create', function (require) {
"use strict";

/**
 * This file defines the RecordQuickCreate widget for Kanban. It allows to
 * create kanban records directly from the Kanban view.
 */

var core = require('web.core');
var QuickCreateFormView = require('web.QuickCreateFormView');
const session = require('web.session');
var Widget = require('web.Widget');

var RecordQuickCreate = Widget.extend({
    className: 'o_kanban_quick_create',
    custom_events: {
        add: '_onAdd',
        cancel: '_onCancel',
    },
    events: {
        'click .o_kanban_add': '_onAddClicked',
        'click .o_kanban_edit': '_onEditClicked',
        'click .o_kanban_cancel': '_onCancelClicked',
    },

    /**
     * @override
     * @param {Widget} parent
     * @param {Object} options
     * @param {Object} options.context
     * @param {string|null} options.formViewRef
     * @param {string} options.model
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.context = options.context;
        this.formViewRef = options.formViewRef;
        this.model = options.model;
        this._disabled = false; // to prevent from creating multiple records (e.g. on double-clicks)
    },
    /**
     * Loads the form fieldsView (if not provided), instantiates the form view
     * and starts the form controller.
     *
     * @override
     */
    willStart: function () {
        var self = this;
        var superWillStart = this._super.apply(this, arguments);
        var viewsLoaded;
        if (this.formViewRef) {
            var views = [[false, 'form']];
            var context = _.extend({}, this.context, {
                form_view_ref: this.formViewRef,
            });
            viewsLoaded = this.loadViews(this.model, context, views);
        } else {
            var fieldsView = {};
            fieldsView.arch = '<form>' +
                '<field name="display_name" placeholder="Title" modifiers=\'{"required": true}\'/>' +
            '</form>';
            var fields = {
                display_name: {string: 'Display name', type: 'char'},
            };
            fieldsView.fields = fields;
            fieldsView.viewFields = fields;
            viewsLoaded = Promise.resolve({form: fieldsView});
        }
        viewsLoaded = viewsLoaded.then(function (fieldsViews) {
            var formView = new QuickCreateFormView(fieldsViews.form, {
                context: self.context,
                modelName: self.model,
                userContext: session.user_context,
            });
            return formView.getController(self).then(function (controller) {
                self.controller = controller;
                return self.controller.appendTo(document.createDocumentFragment());
            });
        });
        return Promise.all([superWillStart, viewsLoaded]);
    },
    /**
     * @override
     */
    start: function () {
        this.$el.append(this.controller.$el);
        this.controller.renderButtons(this.$el);

        // focus the first field
        this.controller.autofocus();

        // destroy the quick create when the user clicks outside
        core.bus.on('click', this, this._onWindowClicked);

        return this._super.apply(this, arguments);
    },
    /**
     * Called when the quick create is appended into the DOM.
     */
    on_attach_callback: function () {
        if (this.controller) {
            this.controller.autofocus();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Cancels the quick creation if the record isn't dirty, i.e. if no changes
     * have been made yet
     *
     * @private
     * @returns {Promise}
     */
    cancel: function () {
        var self = this;
        return this.controller.commitChanges().then(function () {
            if (!self.controller.isDirty()) {
                self._cancel();
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} [options]
     * @param {boolean} [options.openRecord] set to true to directly open the
     *   newly created record in a form view (in edit mode)
     */
    _add: function (options) {
        var self = this;
        if (this._disabled) {
            // don't do anything if we are already creating a record
            return;
        }
        // disable the widget to prevent the user from creating multiple records
        // with the current values ; if the create works, the widget will be
        // destroyed and another one will be instantiated, so there is no need
        // to re-enable it in that case
        this._disableQuickCreate();
        this.controller.commitChanges().then(function () {
            var canBeSaved = self.controller.canBeSaved();
            if (canBeSaved) {
                self.trigger_up('quick_create_add_record', {
                    openRecord: options && options.openRecord || false,
                    values: self.controller.getChanges(),
                    onFailure: self._enableQuickCreate.bind(self),
                });
            } else {
                self._enableQuickCreate();
            }
        }).guardedCatch(this._enableQuickCreate.bind(this));
    },
    /**
     * Notifies the environment that the quick creation must be cancelled
     *
     * @private
     * @returns {Promise}
     */
    _cancel: function () {
        this.trigger_up('cancel_quick_create');
    },
    /**
     * Disable the widget to indicate the user that it can't interact with it.
     * This function must be called when a record is being created, to prevent
     * it from being created twice.
     *
     * Note that if the record creation works as expected, there is no need to
     * re-enable the widget as it will be destroyed anyway (and replaced by a
     * new instance).
     *
     * @private
     */
    _disableQuickCreate: function () {
        this._disabled = true; // ensures that the record won't be created twice
        this.$el.addClass('o_disabled');
        this.$('input:not(:disabled)')
            .addClass('o_temporarily_disabled')
            .attr('disabled', 'disabled');
    },
    /**
     * Re-enable the widget to allow the user to create again.
     *
     * @private
     */
    _enableQuickCreate: function () {
        this._disabled = false; // allows to create again
        this.$el.removeClass('o_disabled');
        this.$('input.o_temporarily_disabled')
            .removeClass('o_temporarily_disabled')
            .attr('disabled', false);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onAdd: function (ev) {
        ev.stopPropagation();
        this._add();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onAddClicked: function (ev) {
        ev.stopPropagation();
        this._add();
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onCancel: function (ev) {
        ev.stopPropagation();
        this._cancel();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCancelClicked: function (ev) {
        ev.stopPropagation();
        this._cancel();
    },
    /**
     * Validates the quick creation and directly opens the record in a form
     * view in edit mode.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onEditClicked: function (ev) {
        ev.stopPropagation();
        this._add({openRecord: true});
    },
    /**
     * When a click happens outside the quick create, we want to close the quick
     * create.
     *
     * This is quite tricky, because in some cases a click is performed outside
     * the quick create, but is still related to it (e.g. click in a dialog
     * opened from the quick create).
     *
     * @param {MouseEvent} ev
     */
    _onWindowClicked: function (ev) {
        // ignore clicks if the quick create is not in the dom
        if (!document.contains(this.el)) {
            return;
        }

        // ignore clicks on elements that open the quick create widget, to
        // prevent from closing quick create widget that has just been opened
        if ($(ev.target).closest('.o-kanban-button-new, .o_kanban_quick_add').length) {
            return;
        }

        // ignore clicks in autocomplete dropdowns
        if ($(ev.target).parents('.ui-autocomplete').length) {
            return;
        }

        // ignore clicks in modals
        if ($(ev.target).closest('.modal').length) {
            return;
        }

        // ignore clicks while a modal is just about to open
        if ($(document.body).hasClass('modal-open')) {
            return;
        }

        // ignore clicks if target is no longer in dom (e.g., a click on the
        // 'delete' trash icon of a m2m tag)
        if (!document.contains(ev.target)) {
            return;
        }

        // ignore clicks if target is inside the quick create
        if (this.el.contains(ev.target) || this.el === ev.target) {
            return;
        }

        this.cancel();
    },
});

return RecordQuickCreate;

});
