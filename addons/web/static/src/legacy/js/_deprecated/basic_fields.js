////////////////////////////////////////////////////////////////////////////////
// /!\ DEPRECATED
// 
// Legacy Field Widgets are added in this file when they are converted into
// Owl Component.
////////////////////////////////////////////////////////////////////////////////

odoo.define('web.basic_fields.deprecated', function (require) {
"use strict";

/**
 * This module contains most of the basic (meaning: non relational) field
 * widgets. Field widgets are supposed to be used in views inheriting from
 * BasicView, so, they can work with the records obtained from a BasicModel.
 */

var AbstractField = require('web.AbstractField');
var core = require('web.core');

var _lt = core._lt;

var FieldBoolean = AbstractField.extend({
    className: 'o_field_boolean',
    description: _lt("Checkbox"),
    events: _.extend({}, AbstractField.prototype.events, {
        change: '_onChange',
    }),
    supportedFieldTypes: ['boolean'],
    isQuickEditable: true,

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Toggle the checkbox if it is activated due to a click on itself.
     *
     * @override
     */
    activate: function (options) {
        var activated = this._super.apply(this, arguments);
        // The formatValue of boolean fields renders HTML elements similar to
        // the one rendered by the widget itself. Even though the event might
        // have been fired on the non-widget version of this field, we can still
        // test the presence of its custom class.
        if (activated && options && options.event && $(options.event.target).closest('.form-check').length) {
            this._setValue(!this.value);  // Toggle the checkbox
        }
        return activated;
    },

    /**
     * @override
     * @returns {jQuery} the focusable checkbox input
     */
    getFocusableElement: function () {
        return this.mode === 'readonly' ? $() : this.$input;
    },
    /**
     * A boolean field is always set since false is a valid value.
     *
     * @override
     */
    isSet: function () {
        return true;
    },
    /**
     * When the checkbox is rerendered, we need to check if it was the actual
     * origin of the reset. If it is, we need to activate it back so it looks
     * like it was not rerendered but is still the same input.
     *
     * @override
     */
    reset: function (record, event) {
        var rendered = this._super.apply(this, arguments);
        if (event && event.target.name === this.name) {
            this.activate();
        }
        return rendered;
    },
    /**
     * Associates the 'for' attribute of the internal label.
     *
     * @override
     */
    setIDForLabel: function (id) {
        this._super.apply(this, arguments);
        this.$('.form-check-label').attr('for', id);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     * @params {Object} extraInfo
     * @params {boolean} extraInfo.value
     */
    _quickEdit: function (extraInfo) {
        this._super(...arguments);
        // toggle if extraInfo.value === undefined (if clicked on label)
        // otherwise force the new value
        this._setValue(extraInfo.value === undefined ? !this.value : extraInfo.value);
    },
    /**
     * @private
     * @override
     * @returns {Object}
     */
    _getQuickEditExtraInfo() {
        return {
            value: !this.value,
        };
    },
    /**
     * The actual checkbox is designed in css to have full control over its
     * appearance, as opposed to letting the browser and the os decide how
     * a checkbox should look. The actual input is disabled and hidden. In
     * readonly mode, the checkbox is disabled.
     *
     * @override
     * @private
     */
    _render: function () {
        var $checkbox = this._formatValue(this.value);
        this.$input = $checkbox.find('input');
        this.$input.prop('disabled', this.hasReadonlyModifier && this.mode != 'edit');
        this.$el.addClass($checkbox.attr('class'));
        this.$el.empty().append($checkbox.contents());
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Properly update the value when the checkbox is (un)ticked to trigger
     * possible onchanges.
     *
     * @private
     */
    _onChange: function () {
        this._setValue(this.$input[0].checked);
    },
    /**
     * Implement keyboard movements.  Mostly useful for its environment, such
     * as a list view.
     *
     * @override
     * @private
     * @param {KeyEvent} ev
     */
    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.ENTER:
                // prevent subsequent 'click' event (see _onKeydown of AbstractField)
                ev.preventDefault();
                this.$input.prop('checked', !this.value);
                this._setValue(!this.value);
                return;
            case $.ui.keyCode.UP:
            case $.ui.keyCode.RIGHT:
            case $.ui.keyCode.DOWN:
            case $.ui.keyCode.LEFT:
                ev.preventDefault();
        }
        this._super.apply(this, arguments);
    },
});

return {
    FieldBoolean: FieldBoolean,
};

});
