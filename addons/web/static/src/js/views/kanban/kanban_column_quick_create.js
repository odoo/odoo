odoo.define('web.kanban_column_quick_create', function (require) {
"use strict";

/**
 * This file defines the ColumnQuickCreate widget for Kanban. It allows to
 * create kanban columns directly from the Kanban view.
 */

var Widget = require('web.Widget');

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

return ColumnQuickCreate;

});
