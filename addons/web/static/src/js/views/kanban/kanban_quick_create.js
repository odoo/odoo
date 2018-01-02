odoo.define('web.kanban_quick_create', function (require) {
"use strict";

/**
 * This file defines two Kanban 'quick create' widgets: one to quick create
 * kanban records, and one to quick create kanban columns.
 */

var core = require('web.core');
var QuickCreateFormView = require('web.QuickCreateFormView');
var Widget = require('web.Widget');

var qweb = core.qweb;

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
    },
    /**
     * Loads the form fieldsView (if not provided), instantiates the form view
     * and starts the form controller.
     *
     * @override
     */
    willStart: function () {
        var self = this;
        var def1 = this._super.apply(this, arguments);
        var def2;
        if (this.formViewRef) {
            var views = [[false, 'form']];
            var context = _.extend({}, this.context, {
                form_view_ref: this.formViewRef,
            });
            def2 = this.loadViews(this.model, context, views);
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
            def2 = $.when({form: fieldsView});
        }
        def2 = def2.then(function (fieldsViews) {
            var formView = new QuickCreateFormView(fieldsViews.form, {
                context: self.context,
                modelName: self.model,
                userContext: self.getSession().user_context,
            });
            return formView.getController(self).then(function (controller) {
                self.controller = controller;
                return self.controller.appendTo(document.createDocumentFragment());
            });
        });
        return $.when(def1, def2);
    },
    /**
     * @override
     */
    start: function () {
        this.$el.append(this.controller.$el);
        this.$el.append(qweb.render('KanbanView.RecordQuickCreate.buttons'));

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
     * @returns {Deferred}
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
     * @override
     * @private
     * @param {Object} [options]
     * @param {boolean} [options.openRecord] set to true to directly open the
     *   newly created record in a form view (in edit mode)
     * @returns {Deferred}
     */
    _add: function (options) {
        var self = this;
        return this.controller.commitChanges().then(function () {
            var canBeSaved = self.controller.canBeSaved();
            if (canBeSaved) {
                self.trigger_up('quick_create_add_record', {
                    openRecord: options && options.openRecord || false,
                    values: self.controller.getChanges(),
                });
            }
        });
    },
    /**
     * Notifies the environment that the quick creation must be cancelled
     *
     * @private
     * @returns {Deferred}
     */
    _cancel: function () {
        this.trigger_up('cancel_quick_create');
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

        // ignore clicks if target is no longer in dom (e.g., a click on the
        // 'delete' trash icon of a m2m tag)
        if (!document.contains(ev.target)) {
            return;
        }

        // ignore clicks if target is inside the quick create
        if (this.el.contains(ev.target) && this.el !== ev.target) {
            return;
        }

        this.cancel();
    },
});

var ColumnQuickCreate = Widget.extend({
    template: 'KanbanView.ColumnQuickCreate',
    events: {
        'click': 'toggleFold',
        'click input': '_onInputClicked',
        'click .o_kanban_add': '_onAddClicked',
        'focusout': '_onFocusout',
        'keydown': '_onKeydown',
        'keypress input': '_onKeypress',
        'mousedown .o_kanban_add': '_onMousedown',
    },

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.folded = true;
    },
    /**
     * @override
     */
    start: function () {
        this.$header = this.$('.o_column_header');
        this.$quick_create = this.$('.o_kanban_quick_create');
        this.$input = this.$('input');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Folds/unfolds the Column quick create widget
     */
    toggleFold: function () {
        this.folded = !this.folded;
        this._update();
        if (!this.folded) {
            this.$input.focus();
            this.trigger_up('scrollTo', {selector: '.o_column_quick_create'});
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Clears the input value and notify the environment to create a column
     *
     * @private
     */
    _add: function () {
        var value = this.$input.val().trim();
        if (!value.length) {
            return;
        }
        this.$input.val('');
        this.trigger_up('quick_create_add_column', {value: value});
        this.$input.focus();
    },
    /**
     * Cancels the quick creation
     *
     * @private
     */
    _cancel: function () {
        this.folded = true;
        this.$input.val('');
        this._update();
    },
    /**
     * Updates the rendering according to the current state (folded/unfolded)
     *
     * @private
     */
    _update: function () {
        this.$header.toggle(this.folded);
        this.$quick_create.toggle(!this.folded);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onAddClicked: function (event) {
        event.stopPropagation();
        this._add();
    },
    /**
     * Cancels the quick creation when the input loses the focus
     *
     * @private
     */
    _onFocusout: function () {
        var hasFocus = this.$(':focus').length > 0;
        if (hasFocus) {
            return;
        }
        this._cancel();
    },
    /**
     * Stops the propagation of the event to prevent the quick create from
     * toggling when the user clicks in the input
     *
     * @private
     * @param {MouseEvent} event
     */
    _onInputClicked: function (event) {
        event.stopPropagation();
    },
    /**
     * Cancels quick creation on escape keydown event
     *
     * @private
     * @param {KeyEvent} event
     */
    _onKeydown: function (event) {
        if (event.keyCode === 27) { // escape
            this._cancel();
        }
    },
    /**
     * Validates quick creation on enter keypress event
     *
     * @private
     * @param {KeyEvent} event
     */
    _onKeypress: function (event) {
        if (event.keyCode === 13) { // enter
            this._add();
        }
    },
    /**
     * In all browsers the 'focus/blur' event is triggered before a button's
     * 'click' (it's actually triggered by mousedown).
     * The quick create is hidden on blur of its input but still needs to create
     * the data when the "Add" button is clicked.
     * This problem is adressed by suppressing the 'focus/blur' event from the
     * Add button entirely by preventing the browser's default mousedown handler.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onMousedown: function (event) {
        event.preventDefault();
    },
});

return {
    RecordQuickCreate: RecordQuickCreate,
    ColumnQuickCreate: ColumnQuickCreate,
};

});
