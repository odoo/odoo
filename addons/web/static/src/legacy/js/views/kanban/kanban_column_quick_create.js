odoo.define('web.kanban_column_quick_create', function (require) {
"use strict";

/**
 * This file defines the ColumnQuickCreate widget for Kanban. It allows to
 * create kanban columns directly from the Kanban view.
 */

var core = require('web.core');
var config = require('web.config');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');

var _t = core._t;
var QWeb = core.qweb;

var ColumnQuickCreate = Widget.extend({
    template: 'KanbanView.ColumnQuickCreate',
    events: {
        'click .o_quick_create_folded': '_onUnfold',
        'click .o_kanban_add': '_onAddClicked',
        'click .o_kanban_examples': '_onShowExamples',
        'keydown': '_onKeydown',
        'keypress input': '_onKeypress',
        'blur input': '_onInputBlur',
        'focus input': '_onInputFocus',
    },

    /**
     * @override
     * @param {Object} [options]
     * @param {Object} [options.examples]
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.applyExamplesText = options.applyExamplesText || _t("Use This For My Kanban");
        this.examples = options.examples;
        this.folded = true;
        this.isMobile = config.device.isMobile;
        this.isFirstColumn = options.isFirstColumn;
        this.groupByFieldString = options.groupByFieldString;
    },
    /**
     * @override
     */
    start: function () {
        this.$quickCreateFolded = this.$('.o_quick_create_folded');
        this.$quickCreateUnfolded = this.$('.o_quick_create_unfolded');
        this.$input = this.$('input');

        if (!this.isFirstColumn) {
            // destroy the quick create when the user clicks outside
            core.bus.on('click', this, this._onWindowClicked);
        }

        this._update();

        return this._super.apply(this, arguments);
    },
    /**
     * Called each time the quick create is attached into the DOM
     */
    on_attach_callback: function () {
        if (!this.folded) {
            this.$input.focus();
        }
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
            this._cancel();
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
        if (!this.folded) {
            this.$input.val('');
            this.folded = true;
            this._update();
        }
    },
    /**
     * Updates the rendering according to the current state (folded/unfolded)
     *
     * @private
     */
    _update: function () {
        this.$quickCreateFolded.toggle(this.folded);
        this.$quickCreateUnfolded.toggle(!this.folded);
        this.trigger_up('quick_create_column_updated');
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
     * When the input is not focused, no key event may occur in the column, so
     * the discard feature will not work by pressing ESC. We simply hide the
     * help message in that case, so we do not mislead our users.
     *
     * @private
     * @param {KeyboardEvent} event
     */
    _onInputBlur: function () {
        this.$('.o_discard_msg').hide();
    },
    /**
     * When the input is focused, we need to show the discard help message (it
     * might have been hidden, @see _onInputBlur)
     *
     * @private
     * @param {KeyboardEvent} event
     */
    _onInputFocus: function () {
        this.$('.o_discard_msg').show();
    },
    /**
     * Cancels quick creation on escape keydown event
     *
     * @private
     * @param {KeyEvent} event
     */
    _onKeydown: function (event) {
        if (event.keyCode === $.ui.keyCode.ESCAPE) {
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
        if (event.keyCode === $.ui.keyCode.ENTER) {
            this._add();
        }
    },
    /**
     * Opens a dialog containing examples of Kanban processes
     *
     * @private
     */
    _onShowExamples: function () {
        var self = this;
        var dialog = new Dialog(this, {
            $content: $(QWeb.render('KanbanView.ExamplesDialog', {
                examples: this.examples,
            })),
            buttons: [{
                classes: 'btn-primary float-end',
                text: this.applyExamplesText,
                close: true,
                click: function () {
                    const activeExample = self.examples[this.$('.nav-link.active').data("exampleIndex")];
                    activeExample.columns.forEach(column => {
                        self.trigger_up('quick_create_add_column', { value: column.toString(), foldQuickCreate: true });
                    });
                }
            }, {
                classes: 'btn-secondary float-end',
                close: true,
                text: _t('Close'),
            }],
            size: "large",
            fullscreen: config.device.isMobile,
            title: _t("Kanban Examples"),
        }).open();
        dialog.on('closed', this, function () {
            self.$input.focus();
        });
    },
    /**
     * @private
     */
    _onUnfold: function () {
        if (this.folded) {
            this.toggleFold();
        }
    },
    /**
     * When a click happens outside the quick create, we want to close it.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onWindowClicked: function (event) {
        // ignore clicks if the quick create is not in the dom
        if (!document.contains(this.el)) {
            return;
        }

        // ignore clicks in modals
        if ($(event.target).closest('.modal').length) {
            return;
        }

        // ignore clicks if target is inside the quick create
        if (this.el.contains(event.target)) {
            return;
        }

        this._cancel();
    },
});

return ColumnQuickCreate;

});
