/** @odoo-module alias=web.basic_fields **/

/**
 * This module contains most of the basic (meaning: non relational) field
 * widgets. Field widgets are supposed to be used in views inheriting from
 * BasicView, so, they can work with the records obtained from a BasicModel.
 */

import AbstractField from "web.AbstractField";
import core from "web.core";
import datepicker from "web.datepicker";
import dom from "web.dom";
import framework from "web.framework";
import py_utils from "web.py_utils";
import session from "web.session";
import field_utils from "web.field_utils";
import utils from "web.utils";
import { sprintf } from "@web/core/utils/strings";
import { debounce } from "@web/core/utils/timing";
import { uniqueId } from "@web/core/utils/functions";

var _t = core._t;
var _lt = core._lt;

var TranslatableFieldMixin = {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {jQuery}
     */
    _renderTranslateButton: function () {
        if (_t.database.multi_lang && this.field.translate) {
            var lang = _t.database.parameters.code.split('_')[0].toUpperCase();
            return $(`<span class="o_field_translate btn btn-link">${lang}</span>`)
                .on('click', this._onTranslate.bind(this));
        }
        return $();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * open the translation view for the current field
     *
     * @param {MouseEvent} ev
     * @private
     */
    _onTranslate: function (ev) {
        ev.preventDefault();
        this.trigger_up('translate', {
            fieldName: this.name,
            id: this.dataPointID,
            isComingFromTranslationAlert: false,
        });
    },
};

var FieldBoolean = AbstractField.extend({
    className: 'o_field_boolean',
    description: _lt("Checkbox"),
    events: Object.assign({}, AbstractField.prototype.events, {
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

var DebouncedField = AbstractField.extend({
    /**
     * For field widgets that may have a large number of field changes quickly,
     * it could be a good idea to debounce the changes. In that case, this is
     * the suggested value.
     */
    DEBOUNCE: 1000000000,

    /**
     * Override init to debounce the field "_doAction" method (by creating a new
     * one called "_doDebouncedAction"). By default, this method notifies the
     * current value of the field and we do not want that to happen for each
     * keystroke. Note that this is done here and not on the prototype, so that
     * each DebouncedField has its own debounced function to work with. Also, if
     * the debounce value is set to 0, no debouncing is done, which is really
     * useful for the unit tests.
     *
     * @constructor
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        // _isDirty is used to detect that the user interacted at least
        // once with the widget, so that we can prevent it from triggering a
        // field_changed in commitChanges if the user didn't change anything
        this._isDirty = false;
        if (this.mode === 'edit') {
            if (this.DEBOUNCE) {
                this._doDebouncedAction = debounce(this._doAction, this.DEBOUNCE);
            } else {
                this._doDebouncedAction = this._doAction;
            }

            var self = this;
            var debouncedFunction = this._doDebouncedAction;
            this._doDebouncedAction = function () {
                self._isDirty = true;
                debouncedFunction.apply(self, arguments);
            };
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This field main action is debounced and might sets the field's value.
     * When the changes are asked to be commited, the debounced action has to
     * be done immediately.
     *
     * @override
     */
    commitChanges: function () {
        if (this._isDirty && this.mode === 'edit') {
            return this._doAction();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * By default, notifies the outside world of the new value (checked from the
     * DOM). This method has an automatically-created (@see init) associated
     * debounced version called _doDebouncedAction.
     *
     * @private
     */
    _doAction: function () {
        // as _doAction may be debounced, it may happen that it is called after
        // the widget has been destroyed, and in this case, we don't want it to
        // do anything (commitChanges ensures that if it has local changes, they
        // are triggered up before the widget is destroyed, if necessary).
        if (!this.isDestroyed()) {
            return this._setValue(this._getValue());
        }
    },
    /**
     * Should return the current value of the field, in the DOM (for example,
     * the content of the input)
     *
     * @abstract
     * @private
     * @returns {*}
     */
    _getValue: function () {},
    /**
     * Should make an action on lost focus.
     *
     * @abstract
     * @private
     * @returns {*}
     */
    _onBlur: function () {},
});

var InputField = DebouncedField.extend({
    custom_events: Object.assign({}, DebouncedField.prototype.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    events: Object.assign({}, DebouncedField.prototype.events, {
        'input': '_onInput',
        'change': '_onChange',
        'blur' : '_onBlur',
    }),

    /**
     * Prepares the rendering so that it creates an element the user can type
     * text into in edit mode.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.nodeOptions.isPassword = 'password' in this.attrs;
        if (this.mode === 'edit') {
            this.tagName = 'input';
        }
        // We need to know if the widget is dirty (i.e. if the user has changed
        // the value, and those changes haven't been acknowledged yet by the
        // environment), to prevent erasing that new value on a reset (e.g.
        // coming by an onchange on another field)
        this.isDirty = false;
        this.lastChangeEvent = undefined;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the associated <input/> element.
     *
     * @override
     */
    getFocusableElement: function () {
        return this.$input || $();
    },
    /**
     * Re-renders the widget if it isn't dirty. The widget is dirty if the user
     * changed the value, and that change hasn't been acknowledged yet by the
     * environment. For example, another field with an onchange has been updated
     * and this field is updated before the onchange returns. Two '_setValue'
     * are done (this is sequential), the first one returns and this widget is
     * reset. However, it has pending changes, so we don't re-render.
     *
     * @override
     */
    reset: function (record, event) {
        this._reset(record, event);
        if (!event || event === this.lastChangeEvent) {
            this.isDirty = false;
        }
        if (this.isDirty || (event && event.target === this &&
            event.data.changes &&
            event.data.changes[this.name] === this.value)) {
            if (this.attrs.decorations) {
                // if a field is modified, then it could have triggered an onchange
                // which changed some of its decorations. Since we bypass the
                // render function, we need to apply decorations here to make
                // sure they are recomputed.
                this._applyDecorations();
            }
            return Promise.resolve();
        } else {
            return this._render();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {string} the content of the input
     */
    _getValue: function () {
        return this.$input.val();
    },
    /**
     * By default this only calls a debounced method to notify the outside world
     * of the changes if the actual value is not the same than the previous one.
     * @see _doDebouncedAction
     */
    _notifyChanges() {
        this.isDirty = !this._isLastSetValue(this.$input.val());
        this._doDebouncedAction();
    },
    /**
     * Formats an input element for edit mode. This is in a separate function so
     * extending widgets can use it on their input without having input as tagName.
     *
     * @private
     * @param {jQuery|undefined} $input
     *        The <input/> element to prepare and save as the $input attribute.
     *        If no element is given, the <input/> is created.
     * @returns {jQuery} the prepared this.$input element
     */
    _prepareInput: function ($input) {
        this.$input = $input || $("<input/>");
        this.$input.addClass('o_input');

        var inputAttrs = { placeholder: this.attrs.placeholder || "" };
        var inputVal;
        if (this.nodeOptions.isPassword) {
            inputAttrs = Object.assign(inputAttrs, { type: 'password', autocomplete: this.attrs.autocomplete || 'new-password' });
            inputVal = this.value || '';
        } else {
            inputAttrs = Object.assign(inputAttrs, { type: 'text', autocomplete: this.attrs.autocomplete || 'off'});
            inputVal = this._formatValue(this.value);
        }

        this.$input.attr(inputAttrs);
        this.$input.val(inputVal);

        return this.$input;
    },
    /**
     * Formats the HTML input tag for edit mode and stores selection status.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        // Keep a reference to the input so $el can become something else
        // without losing track of the actual input.
        this._prepareInput(this.$el);
    },
    /**
     * Resets the content to the formated value in readonly mode.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(this._formatValue(this.value));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * We immediately notify the outside world when this field confirms its
     * changes.
     *
     * @private
     */
    _onChange: function () {
        this._doAction();
    },
    /**
     * Listens to events 'field_changed' to keep track of the last event that
     * has been trigerred. This allows to detect that all changes have been
     * acknowledged by the environment.
     *
     * @param {OdooEvent} event 'field_changed' event
     */
    _onFieldChanged: function (event) {
        this.lastChangeEvent = event;
    },
    /**
     * Called when the user is typing text
     * @see _notifyChanges
     *
     * @private
     */
    _onInput() {
        this._notifyChanges();
    },
    /**
     * Stops the left/right navigation move event if the cursor is not at the
     * start/end of the input element.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        this._super.apply(this, arguments);

        // the following code only makes sense in edit mode, with an input
        if (this.mode === 'edit' && ev.data.direction !== 'cancel') {
            var input = this.$input[0];
            var selecting = (input.selectionEnd !== input.selectionStart);
            if ((ev.data.direction === "left" && (selecting || input.selectionStart !== 0))
                || (ev.data.direction === "right" && (selecting || input.selectionStart !== input.value.length))) {
                ev.stopPropagation();
            }
            if (ev.data.direction ==='next' &&
                this.attrs.modifiersValue &&
                this.attrs.modifiersValue.required &&
                this.viewType !== 'list') {
                if (!this.$input.val()){
                    this.setInvalidClass();
                    ev.stopPropagation();
                } else {
                    this.removeInvalidClass();
                }
            }
        }
    },
});

var NumericField = InputField.extend({
    tagName: 'span',

    /**
     * @override
     */
    init() {
        this._super.apply(this, arguments);
        this.shouldFormat = Boolean(
            JSON.parse('format' in this.nodeOptions ? this.nodeOptions.format : true)
        );
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * For numeric fields, 0 is a valid value.
     *
     * @override
     */
    isSet: function () {
        return this.value === 0 || this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Evaluate a string representing a simple formula,
     * a formula is composed of numbers and arithmetic operations
     * (ex: 4+3*2)
     *
     * Supported arithmetic operations: + - * / ^ ( )
     * Since each number in the formula can be expressed in user locale,
     * we parse each float value inside the formula using the user context
     * This function uses py_eval to safe eval the formula.
     * We assume that this function is used as a calculator so operand ^ (xor)
     * is replaced by operand ** (power) so that users that are used to
     * excel or libreoffice are not confused
     *
     * @private
     * @param expr
     * @return a float representing the result of the evaluated formula
     * @throws error if formula can't be evaluated
     */
    _evalFormula: function (expr, context) {
        // remove extra space
        var val = expr.replace(new RegExp(/( )/g), '');
        var safeEvalString = '';
        for (let v of val.split(new RegExp(/([-+*/()^])/g))) {
            if (!['+','-','*','/','(',')','^'].includes(v) && v.length) {
                // check if this is a float and take into account user delimiter preference
                v = field_utils.parse.float(v);
            }
            if (v === '^') {
                v = '**';
            }
            safeEvalString += v;
        };
        return py_utils.py_eval(safeEvalString, context);
    },

    /**
     * Format numerical value (integer or float)
     *
     * Note: We have to overwrite this method to skip the format if we are into
     * edit mode on a input type number.
     *
     * @override
     * @private
     */
    _formatValue: function (value) {
        if (!this.shouldFormat || (this.mode === 'edit' && this.nodeOptions.type === 'number')) {
            return value;
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Parse numerical value (integer or float)
     *
     * Note: We have to overwrite this method to skip the format if we are into
     * edit mode on a input type number.
     *
     * @override
     * @private
     */
    _parseValue: function (value) {
        if (this.mode === 'edit' && this.nodeOptions.type === 'number') {
            return Number(value);
        }
        return this._super.apply(this, arguments);
    },

    /**
     * Formats an input element for edit mode. This is in a separate function so
     * extending widgets can use it on their input without having input as tagName.
     *
     * Note: We have to overwrite this method to set the input's type to number if
     * option setted into the field.
     *
     * @override
     * @private
     */
    _prepareInput: function ($input) {
        var result = this._super.apply(this, arguments);
        if (this.nodeOptions.type === 'number') {
            this.$input.attr({type: 'number'});
        }
        if (this.nodeOptions.step) {
            this.$input.attr({step: this.nodeOptions.step});
        }
        return result;
    },

    /**
     * Evaluate value set by user if starts with =
     *
     * @override
     * @private
     * @param {any} value
     * @param {Object} [options]
     */
    _setValue: function (value, options) {
        var originalValue = value;
        value = value.trim();
        if (value.startsWith('=')) {
            try {
                // Evaluate the formula
                value = this._evalFormula(value.substr(1));
                // Format back the value in user locale
                value = this._formatValue(value);
                // Set the computed value in the input
                this.$input.val(value);
            } catch {
                // in case of exception, set value as the original value
                // that way the Webclient will show an error as
                // it is expecting a numeric value.
                value = originalValue;
            }
        }
        return this._super(value, options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Replace the decimal separator of the numpad decimal key
     * by the decimal separator from the user's language setting.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onKeydown(ev) {
        const kbdEvt = ev.originalEvent;
        if (kbdEvt && utils.isNumpadDecimalSeparatorKey(kbdEvt)) {
            const inputField = this.$input[0];
            if (inputField.type === 'number') {
                return this._super(...arguments);
            }
            const curVal = inputField.value;
            const from = inputField.selectionStart;
            const to = inputField.selectionEnd;
            const point = _t.database.parameters.decimal_point;

            // Make sure the correct decimal separator
            // from the user's settings is inserted
            inputField.value = curVal.slice(0, from) + point + curVal.slice(to);

            // Put the user caret at the right place
            inputField.selectionStart = inputField.selectionEnd = from + point.length;

            // Tell the world we made some changes and
            // return preventing event default behaviour.
            this._notifyChanges();
            kbdEvt.preventDefault();
            return;
        }

        return this._super(...arguments);
    },
});

var FieldChar = InputField.extend(TranslatableFieldMixin, {
    description: _lt("Text"),
    className: 'o_field_char',
    tagName: 'span',
    supportedFieldTypes: ['char'],
    isQuickEditable: true,

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add translation button
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        var def = this._super.apply(this, arguments);
        if (this.field.size && this.field.size > 0) {
            this.$el.attr('maxlength', this.field.size);
        }
        if (this.field.translate) {
            this.$el = this.$el.add(this._renderTranslateButton());
            this.$el.addClass('o_field_translate');
        }
        return def;
    },
    /**
     * Trim the value input by the user.
     *
     * @override
     * @private
     * @param {any} value
     * @param {Object} [options]
     */
    _setValue: function (value, options) {
        if (this.field.trim) {
            value = value.trim();
        }
        return this._super(value, options);
    },
});

var FieldDate = InputField.extend({
    description: _lt("Date"),
    className: "o_field_date",
    tagName: "span",
    supportedFieldTypes: ['date', 'datetime'],
    isQuickEditable: true,
    // we don't need to listen on 'input' nor 'change' events because the
    // datepicker widget is already listening, and will correctly notify changes
    events: AbstractField.prototype.events,

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        // use the session timezone when formatting dates
        this.formatOptions.timezone = true;
        this.datepickerOptions = Object.assign(
            { defaultDate: this.value },
            this.nodeOptions.datepicker || {}
        );
    },
    /**
     * In edit mode, instantiates a DateWidget datepicker and listen to changes.
     *
     * @override
     */
    start: function () {
        var self = this;
        var prom;
        if (this.mode === 'edit') {
            this.datewidget = this._makeDatePicker();
            this.datewidget.on('datetime_changed', this, function () {
                var value = this._getValue();
                if ((!value && this.value) || (value && !this._isSameValue(value))) {
                    this._setValue(value);
                }
            });
            prom = this.datewidget.appendTo('<div>').then(function () {
                self.datewidget.$el.addClass(self.$el.attr('class'));
                self._prepareInput(self.datewidget.$input);
                self._replaceElement(self.datewidget.$el);
            });
        }
        return Promise.resolve(prom).then(this._super.bind(this));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Asks the datepicker widget to activate the input, instead of doing it
     * ourself, such that 'input' events triggered by the lib are correctly
     * intercepted, and don't produce unwanted 'field_changed' events.
     *
     * @override
     */
    activate: function () {
        if (this.isFocusable() && this.datewidget) {
            this.datewidget.$input.focus();
            this.datewidget.$input.select();
            return true;
        }
        return false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _doDebouncedAction: function () {
        this.datewidget.changeDatetime();
    },
    /**
     * @private
     * @override
     */
    _quickEdit: function () {
        if (this.datewidget) {
            this.datewidget.$input.click();
        }
    },

    /**
     * return the datepicker value
     *
     * @private
     */
    _getValue: function () {
        return this.datewidget.getValue();
    },
    /**
     * @override
     * @private
     * @param {Moment|false} value
     * @returns {boolean}
     */
    _isSameValue: function (value) {
        if (this.value === false || value === false) {
            return this.value === value;
        }
        return value.isSame(this.value, 'day');
    },
    /**
     * Instantiates a new DateWidget datepicker.
     *
     * @private
     */
    _makeDatePicker: function () {
        return new datepicker.DateWidget(this, this.datepickerOptions);
    },

    /**
     * Set the datepicker to the right value rather than the default one.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        this.datewidget.setValue(this.value);
        this.$input = this.datewidget.$input;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Confirm the value on hit enter and re-render
     * It will also remove the offset to get the UTC value
     *
     * @private
     * @override
     * @param {KeyboardEvent} ev
     */
    async _onKeydown(ev) {
        this._super(...arguments);
        if (ev.which === $.ui.keyCode.ENTER) {
            let value = this.$input.val();
            try {
                value = this._parseValue(value);
                if (this.datewidget.type_of_date === "datetime") {
                    value.add(-this.getSession().getTZOffset(value), "minutes");
                }
            } catch {}
            await this._setValue(value);
            this._render();
        }
    },
});

var FieldDateTime = FieldDate.extend({
    description: _lt("Date & Time"),
    supportedFieldTypes: ['datetime'],
    isQuickEditable: true,

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this.value) {
            var offset = this.getSession().getTZOffset(this.value);
            var displayedValue = this.value.clone().add(offset, 'minutes');
            this.datepickerOptions.defaultDate = displayedValue;
        }
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * return the datepicker value
     *
     * @private
     */
    _getValue: function () {
        var value = this.datewidget.getValue();
        return value && value.add(-this.getSession().getTZOffset(value), 'minutes');
    },
    /**
     * @override
     * @private
     */
    _isSameValue: function (value) {
        if (this.value === false || value === false) {
            return this.value === value;
        }
        return value.isSame(this.value);
    },
    /**
     * Instantiates a new DateTimeWidget datepicker rather than DateWidget.
     *
     * @override
     * @private
     */
    _makeDatePicker: function () {
        return new datepicker.DateTimeWidget(this, this.datepickerOptions);
    },
    /**
     * Set the datepicker to the right value rather than the default one.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        var value = this.value && this.value.clone().add(this.getSession().getTZOffset(this.value), 'minutes');
        this.datewidget.setValue(value);
        this.$input = this.datewidget.$input;
    },
});

var FieldMonetary = NumericField.extend({
    description: _lt("Monetary"),
    className: 'o_field_monetary o_field_number',
    tagName: 'span',
    supportedFieldTypes: ['float', 'monetary'],
    resetOnAnyFieldChange: true, // Have to listen to currency changes
    isQuickEditable: true,

    /**
     * Float fields using a monetary widget have an additional currency_field
     * parameter which defines the name of the field from which the currency
     * should be read.
     *
     * They are also displayed differently than other inputs in
     * edit mode. They are a div containing a span with the currency symbol and
     * the actual input.
     *
     * If no currency field is given or the field does not exist, we fallback
     * to the default input behavior instead.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this._setCurrency();

        if (this.mode === 'edit') {
            this.tagName = 'div';
            this.className += ' o_input';

            // do not display currency symbol in edit
            this.formatOptions.noSymbol = true;
        }

        this.formatOptions.currency = this.currency;
        this.formatOptions.digits = [16, 2];
        this.formatOptions.field_digits = this.nodeOptions.field_digits;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * For monetary fields, 0 is a valid value.
     *
     * @override
     */
    isSet: function () {
        return this.value === 0 || this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * For monetary fields, the input is inside a div, alongside a span
     * containing the currency symbol.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        this.$el.empty();

        // Prepare and add the input
        var def = this._prepareInput(this.$input).appendTo(this.$el);

        if (this.currency && !this.nodeOptions.no_symbol) {
            // Prepare and add the currency symbol
            var $currencySymbol = $('<span>', {text: this.currency.symbol});
            if (this.currency.position === "after") {
                this.$el.append($currencySymbol);
            } else {
                this.$el.prepend($currencySymbol);
            }
        }
        return def;
    },
    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.html(this._formatValue(this.value));
    },
    /**
     * Re-gets the currency as its value may have changed.
     * @see FieldMonetary.resetOnAnyFieldChange
     *
     * @override
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        this._setCurrency();
    },
    /**
     * Deduces the currency description from the field options and view state.
     * The description is then available at this.currency.
     *
     * @private
     */
    _setCurrency: function () {
        var currencyField = this.nodeOptions.currency_field || this.field.currency_field || 'currency_id';
        var currencyID = this.record.data[currencyField] && this.record.data[currencyField].res_id;
        this.currency = session.get_currency(currencyID);
        this.formatOptions.currency = this.currency; // _formatValue() uses formatOptions
    },
});

var FieldInteger = NumericField.extend({
    description: _lt("Integer"),
    className: 'o_field_integer o_field_number',
    supportedFieldTypes: ['integer'],
    isQuickEditable: true,

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Format integer value
     *
     * Note: We have to overwrite this method to allow virtual ids. A virtual id
     * is a character string composed of an integer and has a dash and other
     * information.
     * E.g: in calendar, the recursive event have virtual id linked to a real id
     * virtual event id "23-20170418020000" is linked to the event id 23
     *
     * @override
     * @private
     * @param {integer|string} value
     * @returns {string}
     */
    _formatValue: function (value) {
        if (typeof value === 'string') {
            if (!/^[0-9]+-/.test(value)) {
                throw new Error('"' + value + '" is not an integer or a virtual id');
            }
            return value;
        }
        return this._super.apply(this, arguments);
    },
});

var FieldFloat = NumericField.extend({
    description: _lt("Decimal"),
    className: 'o_field_float o_field_number',
    supportedFieldTypes: ['float'],
    isQuickEditable: true,

    /**
     * Float fields have an additional precision parameter that is read from
     * either the field node in the view or the field python definition itself.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this.attrs.digits) {
            this.nodeOptions.digits = JSON.parse(this.attrs.digits);
        }
    },
});

var FieldFloatTime = FieldFloat.extend({
    description: _lt("Time"),
    // this is not strictly necessary, as for this widget to be used, the 'widget'
    // attrs must be set to 'float_time', so the formatType is automatically
    // 'float_time', but for the sake of clarity, we explicitely define a
    // FieldFloatTime widget with formatType = 'float_time'.
    formatType: 'float_time',
    isQuickEditable: true,

    init: function () {
        this._super.apply(this, arguments);
        this.formatType = 'float_time';
    },
    /**
     * Ensure the widget is re-rendered after being edited s.t. the value is
     * directly formatted (without waiting for the record to be saved, as we do
     * by default).
     *
     * See InputField@reset: we skip the call to _render if this widget initiated
     * the change.
     *
     * Note: the default behavior could be changed s.t. all fields are formatted
     * directly on blur.
     *
     * @override
     */
    async reset() {
        await this._super(...arguments);
        if (!this.isDirty) {
            await this._render();
        }
    },
});

var FieldFloatFactor = FieldFloat.extend({
    supportedFieldTypes: ['float'],
    className: 'o_field_float_factor',
    formatType: 'float_factor',
    isQuickEditable: true,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        // default values
        if (!this.nodeOptions.factor){
            this.nodeOptions.factor = 1;
        }
        // use as format and parse options
        this.parseOptions = this.nodeOptions;
    }
});

/**
 * The goal of this widget is to replace the input field by a button containing a
 * range of possible values (given in the options). Each click allows the user to loop
 * in the range. The purpose here is to restrict the field value to a predefined selection.
 * Also, the widget support the factor conversion as the *float_factor* widget (Range values
 * should be the result of the conversion).
 **/
var FieldFloatToggle = AbstractField.extend({
    supportedFieldTypes: ['float'],
    formatType: 'float_factor',
    className: 'o_field_float_toggle',
    tagName: 'span',
    events: {
        click: '_onClick'
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.formatType = 'float_factor';

        // force the button to work in readonly mode
        if (this.mode === 'edit' || this.nodeOptions.force_button) {
            this.tagName = 'button';
        }

        // we don't inherit Float Field
        if (this.attrs.digits) {
            this.nodeOptions.digits = JSON.parse(this.attrs.digits);
        }
        // default values
        if (!this.nodeOptions.factor){
            this.nodeOptions.factor = 1;
        }
        if (!this.nodeOptions.range){
            this.nodeOptions.range = [0.0, 0.5, 1.0];
        }

        // use as format and parse options
        this.parseOptions = this.nodeOptions;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Get the display value but in real type to use it in calculations
     *
     * @private
     * @returns {float} The current formatted value
     */
    _getDisplayedValue: function () {
        // this.value is a plain float
        // Matches what is in Database
        var usrFormatValue = this._formatValue(this.value);
        // usrFormatValue is string
        // contains a float represented in a user specific format
        // the float is the fraction by [this.factor] of this.value
        return field_utils.parse['float'](usrFormatValue);
    },
    /**
     * Formats the HTML input tag for edit mode and stores selection status.
     *
     * @override
     * @private
     */
    _renderEdit: function () {
        // Keep a reference to the input so $el can become something else
        // without losing track of the actual input.
        this.$el.text(this._formatValue(this.value));
    },
    /**
     * Resets the content to the formated value in readonly mode.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(this._formatValue(this.value));
    },
    /**
     * Get the next value in the range, from the current one. If the current
     * one is not in the range, the next value of the closest one will be chosen.
     *
     * @private
     * @returns {number} The next value in the range
     */
    _nextValue: function () {
        var range = this.nodeOptions.range;
        var val =  utils.closestNumber(this._getDisplayedValue(), range);
        var index = range.indexOf(val);
        if (index !== -1) {
            if (index + 1 < range.length) {
                return range[index + 1];
            }
        }
        return range[0];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Clicking on the button triggers the change of value; the next one of
     * the range will be displayed.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onClick: function(ev) {
        // force the button to work in readonly mode
        if (this.mode === 'edit' || this.nodeOptions.force_button) {
            ev.stopPropagation();
            var next_val = this._nextValue();
            next_val = field_utils.format['float'](next_val);
            this._setValue(next_val); // will be parsed in _setValue
        }
    },
    /**
     * For float toggle fields, 0 is a valid value.
     *
     * @override
     */
    isSet: function () {
        return this.value === 0 || this._super(...arguments);
    },
});

var FieldPercentage = FieldFloat.extend({
    className: 'o_field_float_percentage o_field_number',
    description: _lt("Percentage"),

    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        if (this.mode === 'edit') {
            this.tagName = 'div';
            this.className += ' o_input';

            // do not display % in the input in edit
            this.formatOptions.noSymbol = true;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * For percentage widget, the input is inside a div, alongside a span
     * containing the percentage(%) symbol.
     *
     * @override
     * @private
     */
    _renderEdit() {
        this.$el.empty();
        // Prepare and add the input
        this._prepareInput(this.$input).appendTo(this.$el);
        const $percentageSymbol = $('<span>', { text: '%' });
        this.$el.append($percentageSymbol);
    },
});

var FieldText = InputField.extend(TranslatableFieldMixin, {
    description: _lt("Multiline Text"),
    className: 'o_field_text',
    supportedFieldTypes: ['text', 'html'],
    tagName: 'span',
    isQuickEditable: true,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        if (this.mode === 'edit') {
            this.tagName = 'textarea';
        }
        this.autoResizeOptions = {parent: this};
    },
    /**
     * As it it done in the start function, the autoresize is done only once.
     *
     * @override
     */
    start: function () {
        if (this.mode === 'edit') {
            dom.autoresize(this.$el, this.autoResizeOptions);
            if (this.field.translate) {
                this.$el = this.$el.add(this._renderTranslateButton());
                this.$el.addClass('o_field_translate');
            }
        }
        return this._super();
    },
    /**
     * Override to force a resize of the textarea when its value has changed
     *
     * @override
     */
    reset: function () {
        var self = this;
        return Promise.resolve(this._super.apply(this, arguments)).then(function () {
            if (self.mode === 'edit') {
                self.$input.trigger('change');
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Stops the enter navigation in a text area.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onKeydown: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER) {
            ev.stopPropagation();
            return;
        }
        this._super.apply(this, arguments);
    },
});

var UrlWidget = InputField.extend({
    description: _lt("URL"),
    className: 'o_field_url',
    events: Object.assign({}, InputField.prototype.events, {
        'click': '_onClick',
    }),
    supportedFieldTypes: ['char'],
    isQuickEditable: true,

    /**
     * Urls are links in readonly mode.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = this.mode === 'readonly' ? 'div' : 'input';
        this.websitePath = this.nodeOptions.website_path || false;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the associated link.
     *
     * @override
     */
    getFocusableElement: function () {
        return this.mode === 'readonly' ? this.$el.find('a') : this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * In readonly, the widget needs to be a link with proper href and proper
     * support for the design, which is achieved by the added classes.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        if (!this.value) {
            return;
        }
        let href = this.value;
        if (this.value && !this.websitePath) {
            const regex = /^((ftp|http)s?:\/)?\//i; // http(s)://... ftp(s)://... /...
            href = !regex.test(this.value) ? `http://${href}` : href;
        }
        this.el.classList.add("o_form_uri", "o_text_overflow");
        const anchorEl = Object.assign(document.createElement('a'), {
            text: this.attrs.text || this.value,
            href: href,
            target: '_blank',
        });
        this.el.textContent = '';
        this.el.appendChild(anchorEl);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Prevent the URL click from opening the record (when used on a list).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick: function (ev) {
        ev.stopPropagation();
    },
});

var AbstractFieldBinary = AbstractField.extend({
    events: Object.assign({}, AbstractField.prototype.events, {
        'change .o_input_file': 'on_file_change',
        'click .o_select_file_button': function () {
            this.$('.o_input_file').click();
        },
        'click .o_clear_file_button': '_onClearClick',
    }),
    init: function (parent, name, record) {
        this._super.apply(this, arguments);
        this.fields = record.fields;
        this.useFileAPI = !!window.FileReader;
        this.max_upload_size = session.max_file_upload_size || 128 * 1024 * 1024;
        this.accepted_file_extensions = (this.nodeOptions && this.nodeOptions.accepted_file_extensions) || this.accepted_file_extensions || '*';
        if (!this.useFileAPI) {
            var self = this;
            this.fileupload_id = uniqueId("o_fileupload");
            $(window).on(this.fileupload_id, function () {
                var args = [].slice.call(arguments).slice(1);
                self.on_file_uploaded.apply(self, args);
            });
        }
    },
    destroy: function () {
        if (this.fileupload_id) {
            $(window).off(this.fileupload_id);
        }
        this._super.apply(this, arguments);
    },
    on_file_change: function (e) {
        var self = this;
        var file_node = e.target;
        if ((this.useFileAPI && file_node.files.length) || (!this.useFileAPI && $(file_node).val() !== '')) {
            if (this.useFileAPI) {
                var file = file_node.files[0];
                if (file.size > this.max_upload_size) {
                    var msg = _t("The selected file exceed the maximum file size of %s.");
                    this.displayNotification({ title: _t("File upload"), message: sprintf(msg, utils.human_size(this.max_upload_size)), type: 'danger' });
                    return false;
                }
                utils.getDataURLFromFile(file).then(function (data) {
                    data = data.split(',')[1];
                    self.on_file_uploaded(file.size, file.name, file.type, data);
                });
            } else {
                this.$('form.o_form_binary_form').submit();
            }
            this.$('.o_form_binary_progress').show();
            this.$('button').hide();
        }
    },
    on_file_uploaded: function (size, name) {
        if (size === false) {
            this.displayNotification({ message: _t("There was a problem while uploading your file"), type: 'danger' });
            console.warn("Error while uploading file : ", name);
        } else {
            this.on_file_uploaded_and_valid.apply(this, arguments);
        }
        this.$('.o_form_binary_progress').hide();
        this.$('button').show();
    },
    on_file_uploaded_and_valid: function (size, name, content_type, file_base64) {
        this.set_filename(name);
        this._setValue(file_base64);
        this._render();
    },
    /**
     * We need to update another field.  This method is so deprecated it is not
     * even funny.  We need to replace this with the mechanism of field widgets
     * declaring statically that they need to listen to every changes in other
     * fields
     *
     * @deprecated
     *
     * @param {any} value
     */
    set_filename: function (value) {
        var filename = this.attrs.filename;
        if (filename && filename in this.fields) {
            var changes = {};
            changes[filename] = value;
            this.trigger_up('field_changed', {
                dataPointID: this.dataPointID,
                changes: changes,
                viewType: this.viewType,
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Clear the file input
     *
     * @private
     */
    _clearFile: function (){
        var self = this;
        this.$('.o_input_file').val('');
        this.set_filename('');
        if (!this.isDestroyed()) {
            this._setValue(false).then(function() {
                self._render();
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * On "clear file" button click
     *
     * @param {MouseEvent} ev
     * @private
     */
    _onClearClick: function (ev) {
        this._clearFile();
    },
});

var FieldBinaryFile = AbstractFieldBinary.extend({
    description: _lt("File"),
    template: 'FieldBinaryFile',
    events: Object.assign({}, AbstractFieldBinary.prototype.events, {
        'click': function (event) {
            if (this.mode === 'readonly' && this.value && this.recordData.id) {
                this.on_save_as(event);
            }
        },
        'click .o_input': function () { // eq[0]
            this.$('.o_input_file').click();
        },
    }),
    supportedFieldTypes: ['binary'],
    init: function () {
        this._super.apply(this, arguments);
        this.filename_value = this.recordData[this.attrs.filename];
    },
    _renderReadonly: function () {
        var visible = !!(this.value && this.res_id);
        this.$el.empty().css('cursor', 'not-allowed');
        this.do_toggle(visible);
        if (visible) {
            this.$el.css('cursor', 'pointer')
                    .text(this.filename_value || '')
                    .prepend($('<span class="fa fa-download"/>'), ' ');
        }
    },
    _renderEdit: function () {
        if (this.value) {
            this.$el.children().removeClass('o_hidden');
            this.$('.o_select_file_button').first().addClass('o_hidden');
            this.$('.o_input').eq(0).val(this.filename_value || this.value);
        } else {
            this.$el.children().addClass('o_hidden');
            this.$('.o_select_file_button').first().removeClass('o_hidden');
        }
    },
    set_filename: function (value) {
        this._super.apply(this, arguments);
        this.filename_value = value; // will be used in the re-render
        // the filename being edited but not yet saved, if the user clicks on
        // download, he'll get the file corresponding to the current value
        // stored in db, which isn't the one whose filename is displayed in the
        // input, so we disable the download button
        this.$('.o_save_file_button').prop('disabled', true);
    },
    on_save_as: function (ev) {
        if (!this.value) {
            this.displayNotification({ message: _t("The field is empty, there's nothing to save."), type: 'danger' });
            ev.stopPropagation();
        } else if (this.res_id) {
            framework.blockUI();
            var filename_fieldname = this.attrs.filename;
            this.getSession().get_file({
                complete: framework.unblockUI,
                data: {
                    'model': this.model,
                    'id': this.res_id,
                    'field': this.name,
                    'filename_field': filename_fieldname,
                    'filename': this.recordData[filename_fieldname] || "",
                    'download': true,
                    'data': utils.is_bin_size(this.value) ? null : this.value,
                },
                error: (error) => this.call('crash_manager', 'rpc_error', error),
                url: '/web/content',
            });
            ev.stopPropagation();
        }
    },
});

/**
 * This widget is intended to be used on boolean fields. It toggles a button
 * switching between a green bullet / gray bullet.
*/
var FieldToggleBoolean = AbstractField.extend({
    description: _lt("Button"),
    template: "toggle_button",
    events: {
        'click': '_onToggleButton'
    },
    supportedFieldTypes: ['boolean'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * A boolean field is always set since false is a valid value.
     *
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        this.$('i')
            .toggleClass('o_toggle_button_success', !!this.value)
            .toggleClass('text-muted', !this.value);
        const isReadonly = this.record.evalModifiers(this.attrs.modifiers).readonly;
        if (isReadonly) {
            this.el.setAttribute('disabled', isReadonly);
        }
        var title = this.value ? this.attrs.options.active : this.attrs.options.inactive;
        this.$el.attr('title', title);
        this.$el.attr('aria-pressed', this.value);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle the button
     *
     * @private
     * @param {MouseEvent} event
     */
    _onToggleButton: function (event) {
        event.stopPropagation();
        this._setValue(!this.value);
    },
});

export default {
    TranslatableFieldMixin: TranslatableFieldMixin,
    DebouncedField: DebouncedField,
    FieldBinaryFile: FieldBinaryFile,
    AbstractFieldBinary: AbstractFieldBinary,
    FieldBoolean: FieldBoolean,
    FieldChar: FieldChar,
    FieldDate: FieldDate,
    FieldDateTime: FieldDateTime,
    FieldFloat: FieldFloat,
    FieldFloatTime: FieldFloatTime,
    FieldFloatFactor: FieldFloatFactor,
    FieldFloatToggle: FieldFloatToggle,
    FieldPercentage: FieldPercentage,
    FieldInteger: FieldInteger,
    FieldMonetary: FieldMonetary,
    FieldText: FieldText,
    FieldToggleBoolean: FieldToggleBoolean,
    InputField: InputField,
    NumericField: NumericField,
    UrlWidget: UrlWidget,
};
