odoo.define('web.kanban_quick_create', function (require) {
"use strict";

/**
 * This file defines two Kanban 'quick create' widgets: one to quick create
 * kanban records, and one to quick create kanban columns.
 */

var Widget = require('web.Widget');

var AbstractQuickCreate = Widget.extend({
    events: {
        'click .o_kanban_add': '_onAddClicked',
        'click .o_kanban_cancel': '_onCancelClicked',
        'keydown': '_onKeydown',
        'keypress input': '_onKeypress',
        'mousedown .o_kanban_add': '_onMousedown',
        'mousedown .o_kanban_cancel': '_onMousedown',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Clears the input value and notify the environment that a quick create
     * has been done
     *
     * @private
     */
    _add: function () {
        var value = this.$input.val();
        this.$input.val('');
        if (/^\s*$/.test(value)) {
            return;
        }
        this._notifyAdd(value);
        this.$input.focus();
    },
    /**
     * Should implement what to do when the quick creation has been cancelled
     *
     * @abstract
     * @private
     */
    _cancel: function () {
    },
    /**
     * Should implement what to do to notify the environment that a quick
     * create has been done
     *
     * @abstract
     * @private
     */
    _notifyAdd: function (name) {
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
     * @private
     */
    _onCancelClicked: function () {
        this._cancel();
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
     * The quick create is destroyed on blur of its input but still needs
     * to create the data when the "Add" button is clicked.
     * This problem is adressed by suppressing the 'focus/blur' event from the
     * relevant buttons (Add and Cancel) entirely by preventing the browser's
     * default mousedown handler.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onMousedown: function (event) {
        event.preventDefault();
    },
});

var RecordQuickCreate = AbstractQuickCreate.extend({
    template: "KanbanView.QuickCreate",
    /**
     * @override
     */
    init: function (parent, width) {
        this._super.apply(this, arguments);
        this.width = width;
    },
    /**
     * @override
     */
    start: function () {
        this.$el.css({width: this.width});
        this.$input = this.$('input');
        this.$input.focus();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Triggers up an event to cancel the quick creation
     *
     * @override
     * @private
     */
    _cancel: function () {
        this.trigger_up('cancel_quick_create');
    },
    /**
     * Triggers up an event to quick create a record with the given value
     *
     * @override
     * @private
     * @param {string} value
     */
    _notifyAdd: function (value) {
        this.trigger_up('quick_create_add_record', {value: value});
    },
});

var ColumnQuickCreate = AbstractQuickCreate.extend({
    template: 'KanbanView.ColumnQuickCreate',
    events: _.extend({}, AbstractQuickCreate.prototype.events, {
        'click': '_onClick',
        'click input': '_onInputClicked',
        'focusout': '_onFocusout',
    }),
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
    // Private
    //--------------------------------------------------------------------------

    /**
     * Triggers up an event to quick create a column with the given value
     *
     * @override
     * @private
     * @param {string} value
     */
    _notifyAdd: function (value) {
        this.trigger_up('quick_create_add_column', {value: value});
    },
    /**
     * Updates the rendering according to the current state
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
    _onClick: function () {
        this.folded = !this.folded;
        this._update();
        if (!this.folded) {
            this.$input.focus();
            this.trigger_up('scrollTo', {selector: '.o_column_quick_create'});
        }
    },
    /**
     * @private
     */
    _onFocusout: function () {
        var hasFocus = this.$(':focus').length > 0;
        if (hasFocus) {
            return;
        }
        this.folded = true;
        this.$input.val('');
        this._update();
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
});

return {
    RecordQuickCreate: RecordQuickCreate,
    ColumnQuickCreate: ColumnQuickCreate,
};

});
