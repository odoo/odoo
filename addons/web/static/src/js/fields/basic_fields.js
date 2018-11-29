odoo.define('web.basic_fields', function (require) {
"use strict";

/**
 * This module contains most of the basic (meaning: non relational) field
 * widgets. Field widgets are supposed to be used in views inheriting from
 * BasicView, so, they can work with the records obtained from a BasicModel.
 */

var AbstractField = require('web.AbstractField');
var config = require('web.config');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var datepicker = require('web.datepicker');
var dom = require('web.dom');
var Domain = require('web.Domain');
var DomainSelector = require('web.DomainSelector');
var DomainSelectorDialog = require('web.DomainSelectorDialog');
var framework = require('web.framework');
var session = require('web.session');
var utils = require('web.utils');
var view_dialogs = require('web.view_dialogs');
var field_utils = require('web.field_utils');

var qweb = core.qweb;
var _t = core._t;

var TranslatableFieldMixin = {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {jQuery}
     */
    _renderTranslateButton: function () {
        if (_t.database.multi_lang && this.field.translate && this.res_id) {
            return $('<button>', {
                    type: 'button',
                    'class': 'o_field_translate fa fa-globe btn btn-link',
                })
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
     * @private
     */
    _onTranslate: function () {
        this.trigger_up('translate', {fieldName: this.name, id: this.dataPointID});
    },
};

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
                this._doDebouncedAction = _.debounce(this._doAction, this.DEBOUNCE);
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
            this._doAction();
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
            this._setValue(this._getValue());
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
});

var InputField = DebouncedField.extend({
    custom_events: _.extend({}, DebouncedField.prototype.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    events: _.extend({}, DebouncedField.prototype.events, {
        'input': '_onInput',
        'change': '_onChange',
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
        if (this.isDirty || (event && event.target === this && event.data.changes[this.name] === this.value)) {
            return $.when();
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
        this.$input.attr({
            type: this.nodeOptions.isPassword ? 'password' : 'text',
            placeholder: this.attrs.placeholder || "",
            autocomplete: this.nodeOptions.isPassword ?
                'new-password' :
                this.attrs.autocomplete,
        });
        this.$input.val(this._formatValue(this.value));
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
     * Called when the user is typing text -> By default this only calls a
     * debounced method to notify the outside world of the changes.
     * @see _doDebouncedAction
     *
     * @private
     */
    _onInput: function () {
        this.isDirty = true;
        this._doDebouncedAction();
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
        if (this.mode === 'edit') {
            var input = this.$input[0];
            var selecting = (input.selectionEnd !== input.selectionStart);
            if ((ev.data.direction === "left" && (selecting || input.selectionStart !== 0))
             || (ev.data.direction === "right" && (selecting || input.selectionStart !== input.value.length))) {
                ev.stopPropagation();
            }
        }
    },
});

var FieldChar = InputField.extend(TranslatableFieldMixin, {
    className: 'o_field_char',
    tagName: 'span',
    supportedFieldTypes: ['char'],

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
        this.$el = this.$el.add(this._renderTranslateButton());
        return def;
    },
});


var LinkButton = AbstractField.extend({
    events: _.extend({}, AbstractField.prototype.events, {
        'click': '_onClick'
    }),
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Display button
     * @override
     * @private
     */
    _render: function () {
        if (this.value) {
            var className = this.attrs.icon || 'fa-globe';

            this.$el.html("<span />");
            this.$el.addClass("fa "+ className);
            this.$el.attr('title', this.value);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open link button
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClick: function (event) {
        event.stopPropagation();
        window.open(this.value, '_blank');
    },

});



var FieldDate = InputField.extend({
    className: "o_field_date",
    tagName: "span",
    supportedFieldTypes: ['date', 'datetime'],

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        // use the session timezone when formatting dates
        this.formatOptions.timezone = true;
        this.datepickerOptions = _.defaults(
            this.nodeOptions.datepicker || {},
            {defaultDate: this.value}
        );
    },
    /**
     * In edit mode, instantiates a DateWidget datepicker and listen to changes.
     *
     * @override
     */
    start: function () {
        var self = this;
        var def;
        if (this.mode === 'edit') {
            this.datewidget = this._makeDatePicker();
            this.datewidget.on('datetime_changed', this, function () {
                var value = this._getValue();
                if ((!value && this.value) || (value && !this._isSameValue(value))) {
                    this._setValue(value);
                }
            });
            def = this.datewidget.appendTo('<div>').done(function () {
                self.datewidget.$el.addClass(self.$el.attr('class'));
                self._prepareInput(self.datewidget.$input);
                self.replaceElement(self.datewidget.$el);
            });
        }
        return $.when(def, this._super.apply(this, arguments));
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
        if (value === false) {
            return this.value === false;
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
});

var FieldDateTime = FieldDate.extend({
    supportedFieldTypes: ['datetime'],

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
        if (value === false) {
            return this.value === false;
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

var FieldMonetary = InputField.extend({
    className: 'o_field_monetary o_field_number',
    tagName: 'span',
    supportedFieldTypes: ['float', 'monetary'],
    resetOnAnyFieldChange: true, // Have to listen to currency changes

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
        this._prepareInput().appendTo(this.$el);

        if (this.currency) {
            // Prepare and add the currency symbol
            var $currencySymbol = $('<span>', {text: this.currency.symbol});
            if (this.currency.position === "after") {
                this.$el.append($currencySymbol);
            } else {
                this.$el.prepend($currencySymbol);
            }
        }
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

var FieldBoolean = AbstractField.extend({
    className: 'o_field_boolean',
    events: _.extend({}, AbstractField.prototype.events, {
        change: '_onChange',
    }),
    supportedFieldTypes: ['boolean'],

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
        // test the presence of its o_checkbox class.
        if (activated && options && options.event && $(options.event.target).parents('.o_checkbox').length) {
            this._setValue(!this.value);  // Toggle the checkbox
        }
        return activated;
    },

    /**
     * @override
     * @returns {jQuery} the focusable checkbox input
     */
    getFocusableElement: function () {
        return this.$input || $();
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
        this.$input.prop('disabled', this.mode === 'readonly');
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

var FieldInteger = InputField.extend({
    className: 'o_field_integer o_field_number',
    tagName: 'span',
    supportedFieldTypes: ['integer'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * For integer fields, 0 is a valid value.
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

var FieldFloat = InputField.extend({
    className: 'o_field_float o_field_number',
    tagName: 'span',
    supportedFieldTypes: ['float'],

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

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * For float fields, 0 is a valid value.
     *
     * @override
     */
    isSet: function () {
        return this.value === 0 || this._super.apply(this, arguments);
    },
});

var FieldFloatTime = FieldFloat.extend({
    // this is not strictly necessary, as for this widget to be used, the 'widget'
    // attrs must be set to 'float_time', so the formatType is automatically
    // 'float_time', but for the sake of clarity, we explicitely define a
    // FieldFloatTime widget with formatType = 'float_time'.
    formatType: 'float_time',
});

var FieldText = InputField.extend(TranslatableFieldMixin, {
    className: 'o_field_text',
    supportedFieldTypes: ['text'],
    tagName: 'span',

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        if (this.mode === 'edit') {
            this.tagName = 'textarea';
        }
    },
    /**
     * As it it done in the start function, the autoresize is done only once.
     *
     * @override
     */
    start: function () {
        if (this.mode === 'edit') {
            dom.autoresize(this.$el, {parent: this});

            this.$el = this.$el.add(this._renderTranslateButton());
        }
        return this._super();
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
            return;
        }
        this._super.apply(this, arguments);
    },
});

/**
 * Displays a handle to modify the sequence.
 */
var HandleWidget = AbstractField.extend({
    className: 'o_row_handle fa fa-arrows ui-sortable-handle',
    tagName: 'span',
    description: "",
    supportedFieldTypes: ['integer'],

    /*
     * @override
     */
    isSet: function () {
        return true;
    },
});

var FieldEmail = InputField.extend({
    className: 'o_field_email',
    events: _.extend({}, InputField.prototype.events, {
        'click': '_onClick',
    }),
    prefix: 'mailto',
    supportedFieldTypes: ['char'],

    /**
     * In readonly, emails should be a link, not a span.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = this.mode === 'readonly' ? 'a' : 'input';
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
        return this.mode === 'readonly' ? this.$el : this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * In readonly, emails should be a mailto: link with proper formatting.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this.$el.text(this.value)
            .addClass('o_form_uri o_text_overflow')
            .attr('href', this.prefix + ':' + this.value);
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

var FieldPhone = FieldEmail.extend({
    className: 'o_field_phone',
    prefix: 'tel',

    /**
     * The phone widget is an extension of email, with the distinction that, in
     * some cases, we do not want to show a clickable widget in readonly.
     * In particular, we only want to make it clickable if the device can call
     * this particular number. This is controlled by the _canCall function.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'readonly' && !this._canCall()) {
            this.tagName = 'span';
        }
    },
    /**
     * Returns the associated link only if there is one.
     *
     * @override
     */
    getFocusableElement: function () {
        if (this.mode !== 'readonly' || this._canCall()) {
            return this._super.apply(this, arguments);
        }
        return $();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * In readonly, we only make the widget clickable if the device can call it.
     * Additionally, we obfuscate the phone number to prevent Skype from seeing it.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this._super();
        if (this._canCall()) {
            // Split phone number into two to prevent Skype app from finding it
            var text = this.$el.text();
            var part1 = _.escape(text.substr(0, text.length/2));
            var part2 = _.escape(text.substr(text.length/2));
            this.$el.html(part1 + "&shy;" + part2);
        } else {
            this.$el.removeClass('o_form_uri');
        }
        // This class should technically be there in case of a very very long
        // phone number, but it breaks the o_row mechanism, which is more
        // important right now.
        this.$el.removeClass('o_text_overflow');
    },

    /**
     * Remove possibly present &shy; characters when saving number
     *
     * @override
     * @private
     */
    _setValue: function (value, options) {
        // NOT NEEDED AS OF SAAS-11.3
        if (value) {
            // remove possibly pasted &shy; characters
            value = value.replace(/\u00AD/g, '');
        }
        return this._super(value, options);
    },

    /**
     * Phone fields are clickable in readonly on small screens ~= on phones.
     * This can be overriden by call-capable modules to display a clickable
     * link in different situations, like always regardless of screen size,
     * or only allow national calls for example.
     *
     * @override
     * @private
     */
    _canCall: function () {
        return config.device.size_class <= config.device.SIZES.XS;
    }
});

var UrlWidget = InputField.extend({
    className: 'o_field_url',
    events: _.extend({}, InputField.prototype.events, {
        'click': '_onClick',
    }),
    supportedFieldTypes: ['char'],

    /**
     * Urls are links in readonly mode.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = this.mode === 'readonly' ? 'a' : 'input';
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
        return this.mode === 'readonly' ? this.$el : this._super.apply(this, arguments);
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
        this.$el.text(this.attrs.text || this.value)
            .addClass('o_form_uri o_text_overflow')
            .attr('target', '_blank')
            .attr('href', this.value);
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
    events: _.extend({}, AbstractField.prototype.events, {
        'change .o_input_file': 'on_file_change',
        'click .o_select_file_button': function () {
            this.$('.o_input_file').click();
        },
        'click .o_clear_file_button': 'on_clear',
    }),
    init: function (parent, name, record) {
        this._super.apply(this, arguments);
        this.fields = record.fields;
        this.useFileAPI = !!window.FileReader;
        this.max_upload_size = 25 * 1024 * 1024; // 25Mo
        if (!this.useFileAPI) {
            var self = this;
            this.fileupload_id = _.uniqueId('o_fileupload');
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
                    this.do_warn(_t("File upload"), _.str.sprintf(msg, utils.human_size(this.max_upload_size)));
                    return false;
                }
                var filereader = new FileReader();
                filereader.readAsDataURL(file);
                filereader.onloadend = function (upload) {
                    var data = upload.target.result;
                    data = data.split(',')[1];
                    self.on_file_uploaded(file.size, file.name, file.type, data);
                };
            } else {
                this.$('form.o_form_binary_form input[name=session_id]').val(this.getSession().session_id);
                this.$('form.o_form_binary_form').submit();
            }
            this.$('.o_form_binary_progress').show();
            this.$('button').hide();
        }
    },
    on_file_uploaded: function (size, name) {
        if (size === false) {
            this.do_warn(_t("File Upload"), _t("There was a problem while uploading your file"));
            // TODO: use crashmanager
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
    on_clear: function () {
        this.set_filename('');
        this._setValue(false);
        this._render();
    },
});

var FieldBinaryImage = AbstractFieldBinary.extend({
    fieldDependencies: _.extend({}, AbstractFieldBinary.prototype.fieldDependencies, {
        __last_update: {type: 'datetime'},
    }),

    template: 'FieldBinaryImage',
    placeholder: "/web/static/src/img/placeholder.png",
    events: _.extend({}, AbstractFieldBinary.prototype.events, {
        'click img': function () {
            if (this.mode === "readonly") {
                this.trigger_up('bounce_edit');
            }
        },
    }),
    supportedFieldTypes: ['binary'],
    _render: function () {
        var self = this;
        var url = this.placeholder;
        if (this.value) {
            if (!utils.is_bin_size(this.value)) {
                url = 'data:image/png;base64,' + this.value;
            } else {
                url = session.url('/web/image', {
                    model: this.model,
                    id: JSON.stringify(this.res_id),
                    field: this.nodeOptions.preview_image || this.name,
                    // unique forces a reload of the image when the record has been updated
                    unique: field_utils.format.datetime(this.recordData.__last_update).replace(/[^0-9]/g, ''),
                });
            }
        }
        var $img = $(qweb.render("FieldBinaryImage-img", {widget: this, url: url}));
        this.$('> img').remove();
        this.$el.prepend($img);
        $img.on('error', function () {
            self.on_clear();
            $img.attr('src', self.placeholder);
            self.do_warn(_t("Image"), _t("Could not display the selected image."));
        });
    },
});

var FieldBinaryFile = AbstractFieldBinary.extend({
    template: 'FieldBinaryFile',
    events: _.extend({}, AbstractFieldBinary.prototype.events, {
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
        this.do_toggle(!!this.value);
        if (this.value) {
            this.$el.empty().append($("<span/>").addClass('fa fa-download'));
            if (this.recordData.id) {
                this.$el.css('cursor', 'pointer');
            } else {
                this.$el.css('cursor', 'not-allowed');
            }
            if (this.filename_value) {
                this.$el.append(" " + this.filename_value);
            }
        }
        if (!this.res_id) {
            this.$el.css('cursor', 'not-allowed');
        } else {
            this.$el.css('cursor', 'pointer');
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
            this.do_warn(_t("Save As..."), _t("The field is empty, there's nothing to save !"));
            ev.stopPropagation();
        } else if (this.res_id) {
            framework.blockUI();
            var c = crash_manager;
            var filename_fieldname = this.attrs.filename;
            this.getSession().get_file({
                'url': '/web/content',
                'data': {
                    'model': this.model,
                    'id': this.res_id,
                    'field': this.name,
                    'filename_field': filename_fieldname,
                    'filename': this.recordData[filename_fieldname] || null,
                    'download': true,
                    'data': utils.is_bin_size(this.value) ? null : this.value,
                },
                'complete': framework.unblockUI,
                'error': c.rpc_error.bind(c),
            });
            ev.stopPropagation();
        }
    },
});

var PriorityWidget = AbstractField.extend({
    // the current implementation of this widget makes it
    // only usable for fields of type selection
    className: "o_priority",
    events: {
        'mouseover > a': '_onMouseOver',
        'mouseout > a': '_onMouseOut',
        'click > a': '_onClick',
    },
    supportedFieldTypes: ['selection'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Like boolean fields, this widget always has a value, since the default
     * value is already a valid value.
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
     * Renders a star for each possible value, readonly or edit mode doesn't matter.
     *
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        var index_value = this.value ? _.findIndex(this.field.selection, function (v) {
            return v[0] === self.value;
        }) : 0;
        this.$el.empty();
        this.empty_value = this.field.selection[0][0];
        _.each(this.field.selection.slice(1), function (choice, index) {
            self.$el.append(self._renderStar('<a href="#">', index_value >= index+1, index+1, choice[1]));
        });
    },

    /**
     * Renders a star representing a particular value for this field.
     *
     * @param {string} tag html tag to be passed to jquery to hold the star
     * @param {boolean} isFull whether the star is a full star or not
     * @param {integer} index the index of the star in the series
     * @param {string} tip tooltip for this star's meaning
     * @private
     */
    _renderStar: function (tag, isFull, index, tip) {
        return $(tag)
            .attr('title', tip)
            .attr('data-index', index)
            .addClass('o_priority_star fa')
            .toggleClass('fa-star', isFull)
            .toggleClass('fa-star-o', !isFull);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Update the value of the field based on which star the user clicked on.
     *
     * @param {MouseEvent} event
     * @private
     */
    _onClick: function (event) {
        event.preventDefault();
        event.stopPropagation();
        var index = $(event.currentTarget).data('index');
        var newValue = this.field.selection[index][0];
        if (newValue === this.value) {
            newValue = this.empty_value;
        }
        this._setValue(newValue);
    },

    /**
     * Reset the star display status.
     *
     * @private
     */
    _onMouseOut: function () {
        clearTimeout(this.hoverTimer);
        var self = this;
        this.hoverTimer = setTimeout(function () {
            self._render();
        }, 200);
    },

    /**
     * Colors the stars to show the user the result when clicking on it.
     *
     * @param {MouseEvent} event
     * @private
     */
    _onMouseOver: function (event) {
        clearTimeout(this.hoverTimer);
        this.$('.o_priority_star').removeClass('fa-star-o').addClass('fa-star');
        $(event.currentTarget).nextAll().removeClass('fa-star').addClass('fa-star-o');
    },
});

var AttachmentImage = AbstractField.extend({
    className: 'o_attachment_image',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Reset cover image when widget value change
     *
     * @private
     */
    _render: function () {
        if (this.value) {
            this.$el.empty().append($('<img>/', {
                src: "/web/image/" + this.value.data.id + "?unique=1",
                title: this.value.data.display_name
            }));
        }
    }
});

var StateSelectionWidget = AbstractField.extend({
    template: 'FormSelection',
    events: {
        'click a': function (e) {
            e.preventDefault();
        },
        'click li': '_setSelection'
    },
    supportedFieldTypes: ['selection'],

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Prepares the state values to be rendered using the FormSelection.Items template.
     *
     * @private
     */
    _prepareDropdownValues: function () {
        var self = this;
        var _data = [];
        var current_stage_id = self.recordData.stage_id && self.recordData.stage_id[0];
        var stage_data = {
            id: current_stage_id,
            legend_normal: this.recordData.legend_normal || undefined,
            legend_blocked : this.recordData.legend_blocked || undefined,
            legend_done: this.recordData.legend_done || undefined,
        };
        _.map(this.field.selection || [], function (selection_item) {
            var value = {
                'name': selection_item[0],
                'tooltip': selection_item[1],
            };
            if (selection_item[0] === 'normal') {
                value.state_name = stage_data.legend_normal ? stage_data.legend_normal : selection_item[1];
            } else if (selection_item[0] === 'done') {
                value.state_class = 'o_status_green';
                value.state_name = stage_data.legend_done ? stage_data.legend_done : selection_item[1];
            } else {
                value.state_class = 'o_status_red';
                value.state_name = stage_data.legend_blocked ? stage_data.legend_blocked : selection_item[1];
            }
            _data.push(value);
        });
        return _data;
    },

    /**
     * This widget uses the FormSelection template but needs to customize it a bit.
     *
     * @private
     * @override
     */
    _render: function () {
        var self = this;
        var states = this._prepareDropdownValues();
        // Adapt "FormSelection"
        // Like priority, default on the first possible value if no value is given.
        var currentState = _.findWhere(states, {name: self.value}) || states[0];
        this.$('.o_status')
            .removeClass('o_status_red o_status_green')
            .addClass(currentState.state_class)
            .prop('special_click', true);

        // Render "FormSelection.Items" and move it into "FormSelection"
        var $items = $(qweb.render('FormSelection.items', {
            states: _.without(states, currentState)
        }));
        var $dropdown = this.$('.dropdown-menu');
        $dropdown.children().remove(); // remove old items
        $items.appendTo($dropdown);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Intercepts the click on the FormSelection.Item to set the widget value.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _setSelection: function (ev) {
        var li = $(ev.target).closest('li');
        if (li.length) {
            var value = String(li.data('value'));
            this._setValue(value);
            if (this.mode === 'edit') {
                this._render();
            }
        }
    },
});

var FavoriteWidget = AbstractField.extend({
    className: 'o_favorite',
    events: {
        'click': '_setFavorite'
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
     * Render favorite icon based on state
     *
     * @override
     * @private
     */
    _render: function () {
        var template = this.attrs.nolabel ? '<a href="#"><i class="fa %s" title="%s"></i></a>' : '<a href="#"><i class="fa %s"></i> %s</a>';
        this.$el.empty().append(_.str.sprintf(template, this.value ? 'fa-star' : 'fa-star-o', this.value ? _t('Remove from Favorites') : _t('Add to Favorites')));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle favorite state
     *
     * @private
     * @param {MouseEvent} event
     */
    _setFavorite: function (event) {
        event.preventDefault();
        event.stopPropagation();
        this._setValue(!this.value);
    },
});

var LabelSelection = AbstractField.extend({
    supportedFieldTypes: ['selection'],

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This widget renders a simple non-editable label. Color classes can be set
     * using the 'classes' key from the options tag, such as:
     * <field [...] options="{'classes': {'value': 'className', ...}}"/>
     *
     * @private
     * @override
     */
    _render: function () {
        this.classes = this.nodeOptions && this.nodeOptions.classes || {};
        var labelClass = this.classes[this.value] || 'primary';
        this.$el.addClass('label label-' + labelClass).text(this._formatValue(this.value));
    },
});

var FieldBooleanButton = AbstractField.extend({
    className: 'o_stat_info',
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
     * This widget is supposed to be used inside a stat button and, as such, is
     * rendered the same way in edit and readonly mode.
     *
     * @override
     * @private
     */
    _render: function () {
        this.$el.empty();
        var text, hover;
        switch (this.nodeOptions.terminology) {
            case "active":
                text = this.value ? _t("Active") : _t("Inactive");
                hover = this.value ? _t("Deactivate") : _t("Activate");
                break;
            case "archive":
                text = this.value ? _t("Active") : _t("Archived");
                hover = this.value ? _t("Archive") : _t("Restore");
                break;
            case "close":
                text = this.value ? _t("Active") : _t("Closed");
                hover = this.value ? _t("Close") : _t("Open");
                break;
            default:
                var opt_terms = this.nodeOptions.terminology || {};
                if (typeof opt_terms === 'string') {
                    opt_terms = {}; //unsupported terminology
                }
                text = this.value ? _t(opt_terms.string_true) || _t("On")
                                  : _t(opt_terms.string_false) || _t("Off");
                hover = this.value ? _t(opt_terms.hover_true) || _t("Switch Off")
                                   : _t(opt_terms.hover_false) || _t("Switch On");
        }
        var val_color = this.value ? 'text-success' : 'text-danger';
        var hover_color = this.value ? 'text-danger' : 'text-success';
        var $val = $('<span>').addClass('o_stat_text o_not_hover ' + val_color).text(text);
        var $hover = $('<span>').addClass('o_stat_text o_hover ' + hover_color).text(hover);
        this.$el.append($val).append($hover);
    },
});

var BooleanToggle = FieldBoolean.extend({
    events: {
        'click': '_onClick'
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        this._super.apply(this, arguments);
        this._renderToggleSwitch();
    },

    /**
     * Display toggle switch
     *
     * @private
     */
    _renderToggleSwitch: function () {
        this.$el.addClass("o_boolean_toggle");
        var $div = $('<div class="slider"></div>');
        $div.insertAfter(this.$("input[type=checkbox]"));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle active value
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClick: function (event) {
        event.stopPropagation();
        this._setValue(!this.value);
        this.$el.closest(".o_data_row").toggleClass('text-muted', this.value);
    },

});

var StatInfo = AbstractField.extend({
    supportedFieldTypes: ['integer', 'float'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * StatInfo widgets are always set since they basically only display info.
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
     * Renders the field value using the StatInfo template. The text part of the
     * widget is either the string attribute of this node in the view or the
     * label of the field itself if no string attribute is given.
     *
     * @override
     * @private
     */
    _render: function () {
        var options = {
            value: this._formatValue(this.value || 0),
        };
        if (! this.attrs.nolabel) {
            if (this.nodeOptions.label_field && this.recordData[this.nodeOptions.label_field]) {
                options.text = this.recordData[this.nodeOptions.label_field];
            } else {
                options.text = this.string;
            }
        }
        this.$el.html(qweb.render("StatInfo", options));
        this.$el.addClass('o_stat_info');
    },
});

var FieldPercentPie = AbstractField.extend({
    template: 'FieldPercentPie',
    supportedFieldTypes: ['integer', 'float'],

    /**
     * Register some useful references for later use throughout the widget.
     *
     * @override
     */
    start: function () {
        this.$leftMask = this.$('.o_mask').first();
        this.$rightMask = this.$('.o_mask').last();
        this.$pieValue = this.$('.o_pie_value');
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * PercentPie widgets are always set since they basically only display info.
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
     * This widget template needs javascript to apply the transformation
     * associated with the rotation of the pie chart.
     *
     * @override
     * @private
     */
    _render: function () {
        var value = this.value || 0;
        var degValue = 360*value/100;

        this.$rightMask.toggleClass('o_full', degValue >= 180);

        var leftDeg = 'rotate(' + ((degValue < 180)? 180 : degValue) + 'deg)';
        var rightDeg = 'rotate(' + ((degValue < 180)? degValue : 0) + 'deg)';
        this.$leftMask.css({transform: leftDeg, msTransform: leftDeg, mozTransform: leftDeg, webkitTransform: leftDeg});
        this.$rightMask.css({transform: rightDeg, msTransform: rightDeg, mozTransform: rightDeg, webkitTransform: rightDeg});

        this.$pieValue.text(Math.round(value) + '%');
    },
});

/**
 * Node options:
 *
 * - title: title of the bar, displayed on top of the bar options
 * - editable: boolean if value is editable
 * - current_value: get the current_value from the field that must be present in the view
 * - max_value: get the max_value from the field that must be present in the view
 * - edit_max_value: boolean if the max_value is editable
 * - title: title of the bar, displayed on top of the bar --> not translated,  use parameter "title" instead
 */
var FieldProgressBar = AbstractField.extend({
    template: "ProgressBar",
    events: {
        'change input': 'on_change_input',
        'input input': 'on_change_input',
        'keyup input': function (e) {
            if (e.which === $.ui.keyCode.ENTER) {
                this.on_change_input(e);
            }
        },
    },
    supportedFieldTypes: ['integer', 'float'],
    init: function () {
        this._super.apply(this, arguments);

        // the progressbar needs the values and not the field name, passed in options
        if (this.recordData[this.nodeOptions.current_value]) {
            this.value = this.recordData[this.nodeOptions.current_value];
        }
        this.max_value = this.recordData[this.nodeOptions.max_value] || 100;
        this.readonly = this.nodeOptions.readonly || !this.nodeOptions.editable;
        this.edit_max_value = this.nodeOptions.edit_max_value || false;
        this.title = _t(this.attrs.title || this.nodeOptions.title) || '';
        this.edit_on_click = !this.nodeOptions.edit_max_value || false;

        this.write_mode = false;
    },
    _render: function () {
        var self = this;
        this._render_value();

        if (!this.readonly) {
            if (this.edit_on_click) {
                this.$el.on('click', '.o_progress', function (e) {
                    var $target = $(e.currentTarget);
                    self.value = Math.floor((e.pageX - $target.offset().left) / $target.outerWidth() * self.max_value);
                    self._render_value();
                    self.on_update(self.value);
                });
            } else {
                this.$el.on('click', function () {
                    if (!self.write_mode) {
                        var $input = $('<input>', {type: 'text', class: 'o_progressbar_value o_input'});
                        $input.on('blur', _.bind(self.on_change_input, self));
                        self.$('.o_progressbar_value').replaceWith($input);
                        self.write_mode = true;
                        self._render_value();
                    }
                });
            }
        }
        return this._super();
    },
    on_update: function (value) {
        if (!isNaN(value)) {
            if (this.edit_max_value) {
                try {
                    this.max_value = this._parseValue(value);
                    this._isValid = true;
                } catch (e) {
                    this._isValid = false;
                }
                var changes = {};
                changes[this.nodeOptions.max_value] = this.max_value;
                this.trigger_up('field_changed', {
                    dataPointID: this.dataPointID,
                    changes: changes,
                });
            } else {
                this._setValue(value);
            }
        }
    },
    on_change_input: function (e) {
        var $input = $(e.target);
        if (e.type === 'change' && !$input.is(':focus')) {
            return;
        }
        if (isNaN($input.val())) {
            this.do_warn(_t("Wrong value entered!"), _t("Only Integer Value should be valid."));
        } else {
            if (e.type === 'input') {
                this._render_value($input.val());
                if (parseFloat($input.val()) === 0) {
                    $input.select();
                }
            } else {
                if (this.edit_max_value) {
                    this.max_value = $(e.target).val();
                } else {
                    this.value = $(e.target).val() || 0;
                }
                var $div = $('<div>', {class: 'o_progressbar_value'});
                this.$('.o_progressbar_value').replaceWith($div);
                this.write_mode = false;

                this._render_value();
                this.on_update(this.edit_max_value ? this.max_value : this.value);
            }
        }
    },
    _render_value: function (v) {
        var value = this.value;
        var max_value = this.max_value;
        if (!isNaN(v)) {
            if (this.edit_max_value) {
                max_value = v;
            } else {
                value = v;
            }
        }
        value = value || 0;
        max_value = max_value || 0;

        var widthComplete;
        if (value <= max_value) {
            widthComplete = value/max_value * 100;
        } else {
            widthComplete = 100;
        }

        this.$('.o_progress').toggleClass('o_progress_overflow', value > max_value);
        this.$('.o_progressbar_complete').css('width', widthComplete + '%');

        if (!this.write_mode) {
            if (max_value !== 100) {
                this.$('.o_progressbar_value').text(utils.human_number(value) + " / " + utils.human_number(max_value));
            } else {
                this.$('.o_progressbar_value').text(utils.human_number(value) + "%");
            }
        } else if (isNaN(v)) {
            this.$('.o_progressbar_value').val(this.edit_max_value ? max_value : value);
            this.$('.o_progressbar_value').focus().select();
        }
    },
    /**
     * The progress bar has more than one field/value to deal with
     * i.e. max_value
     *
     * @override
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        var new_max_value = this.recordData[this.nodeOptions.max_value];
        this.max_value =  new_max_value !== undefined ? new_max_value : this.max_value;
    },
    isSet: function () {
        return true;
    },
});

/**
 * This widget is intended to be used on boolean fields. It toggles a button
 * switching between a green bullet / gray bullet.
*/
var FieldToggleBoolean = AbstractField.extend({
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
        var title = this.value ? this.attrs.options.active : this.attrs.options.inactive;
        this.$el.attr('title', title);
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

var JournalDashboardGraph = AbstractField.extend({
    className: "o_dashboard_graph",
    cssLibs: [
        '/web/static/lib/nvd3/nv.d3.css'
    ],
    jsLibs: [
        '/web/static/lib/nvd3/d3.v3.js',
        '/web/static/lib/nvd3/nv.d3.js',
        '/web/static/src/js/libs/nvd3.js'
    ],
    init: function () {
        this._super.apply(this, arguments);
        this.graph_type = this.attrs.graph_type;
        this.data = JSON.parse(this.value);
    },
    start: function () {
        this._onResize = this._onResize.bind(this);
        nv.utils.windowResize(this._onResize);
        return this._super.apply(this, arguments);
    },
    destroy: function () {
        if ('nv' in window && nv.utils && nv.utils.offWindowResize) {
            // if the widget is destroyed before the lazy loaded libs (nv) are
            // actually loaded (i.e. after the widget has actually started),
            // nv is undefined, but the handler isn't bound yet anyway
            nv.utils.offWindowResize(this._onResize);
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _customizeChart: function () {
        if (this.graph_type === 'bar') {
            // Add classes related to time on each bar of the bar chart
            var bar_classes = _.map(this.data[0].values, function (v) {return v.type; });

            _.each(this.$('.nv-bar'), function (v, k){
                // classList doesn't work with phantomJS & addClass doesn't work with a SVG element
                $(v).attr('class', $(v).attr('class') + ' ' + bar_classes[k]);
            });
        }
    },
    /**
     * @private
     */
    _render: function () {
        // note: the rendering of this widget is aynchronous as nvd3 does a
        // setTimeout(0) before executing the callback given to addGraph
        var self = this;
        this.$el.empty();
        this.chart = null;
        nv.addGraph(function () {
            self.$svg = self.$el.append('<svg>');
            switch (self.graph_type) {
                case "line":
                    self.$svg.addClass('o_graph_linechart');

                    self.chart = nv.models.lineChart();
                    self.chart.forceY([0]);
                    self.chart.options({
                        x: function (d, u) { return u; },
                        margin: {'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
                        showYAxis: false,
                        showLegend: false,
                    });
                    self.chart.xAxis.tickFormat(function (d) {
                        var label = '';
                        _.each(self.data, function (v){
                            if (v.values[d] && v.values[d].x){
                                label = v.values[d].x;
                            }
                        });
                        return label;
                    });
                    self.chart.yAxis.tickFormat(d3.format(',.2f'));

                    self.chart.tooltip.contentGenerator(function (key) {
                        return qweb.render('GraphCustomTooltip', {
                            'color': key.point.color,
                            'key': self.data[0].key,
                            'value': d3.format(',.2f')(key.point.y)
                        });
                    });
                    break;

                case "bar":
                    self.$svg.addClass('o_graph_barchart');

                    self.chart = nv.models.discreteBarChart()
                        .x(function (d) { return d.label; })
                        .y(function (d) { return d.value; })
                        .showValues(false)
                        .showYAxis(false)
                        .color(['#875A7B', '#526774', '#FA8072'])
                        .margin({'left': 0, 'right': 0, 'top': 20, 'bottom': 20});

                    self.chart.xAxis.axisLabel(self.data[0].title);
                    self.chart.yAxis.tickFormat(d3.format(',.2f'));

                    self.chart.tooltip.contentGenerator(function (key) {
                        return qweb.render('GraphCustomTooltip', {
                            'color': key.color,
                            'key': self.data[0].key,
                            'value': d3.format(',.2f')(key.data.value)
                        });
                    });
                    break;
            }
            d3.select(self.$('svg')[0])
                .datum(self.data)
                .transition().duration(600)
                .call(self.chart);

            self._customizeChart();
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onResize: function () {
        if (this.chart) {
            this.chart.update();
            this._customizeChart();
        }
    },
});

/**
 * The "Domain" field allows the user to construct a technical-prefix domain
 * thanks to a tree-like interface and see the selected records in real time.
 * In debug mode, an input is also there to be able to enter the prefix char
 * domain directly (or to build advanced domains the tree-like interface does
 * not allow to).
 */
var FieldDomain = AbstractField.extend({
    /**
     * Fetches the number of records which are matched by the domain (if the
     * domain is not server-valid, the value is false) and the model the
     * field must work with.
     */
    specialData: "_fetchSpecialDomain",

    events: _.extend({}, AbstractField.prototype.events, {
        "click .o_domain_show_selection_button": "_onShowSelectionButtonClick",
        "click .o_field_domain_dialog_button": "_onDialogEditButtonClick",
    }),
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        domain_changed: "_onDomainSelectorValueChange",
        domain_selected: "_onDomainSelectorDialogValueChange",
        open_record: "_onOpenRecord",
    }),
    /**
     * @constructor
     * @override init from AbstractField
     */
    init: function () {
        this._super.apply(this, arguments);

        this.inDialog = !!this.nodeOptions.in_dialog;
        this.fsFilters = this.nodeOptions.fs_filters || {};

        this.className = "o_field_domain";
        if (this.mode === "edit") {
            this.className += " o_edit_mode";
        }
        if (!this.inDialog) {
            this.className += " o_inline_mode";
        }

        this._setState();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * A domain field is always set since the false value is considered to be
     * equal to "[]" (match all records).
     *
     * @override
     */
    isSet: function () {
        return true;
    },
    /**
     * @override isValid from AbstractField.isValid
     * Parsing the char value is not enough for this field. It is considered
     * valid if the internal domain selector was built correctly and that the
     * query to the model to test the domain did not fail.
     *
     * @returns {boolean}
     */
    isValid: function () {
        return (
            this._super.apply(this, arguments)
            && (!this.domainSelector || this.domainSelector.isValid())
            && this._isValidForModel
        );
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override _render from AbstractField
     * @returns {Deferred}
     */
    _render: function () {
        // If there is no model, only change the non-domain-selector content
        if (!this._domainModel) {
            this._replaceContent();
            return $.when();
        }

        // Convert char value to array value
        var value = this.value || "[]";

        // Create the domain selector or change the value of the current one...
        var def;
        if (!this.domainSelector) {
            this.domainSelector = new DomainSelector(this, this._domainModel, value, {
                readonly: this.mode === "readonly" || this.inDialog,
                filters: this.fsFilters,
                debugMode: session.debug,
            });
            def = this.domainSelector.prependTo(this.$el);
        } else {
            def = this.domainSelector.setDomain(value);
        }
        // ... then replace the other content (matched records, etc)
        return def.then(this._replaceContent.bind(this));
    },
    /**
     * Render the field DOM except for the domain selector part. The full field
     * DOM is composed of a DIV which contains the domain selector widget,
     * followed by other content. This other content is handled by this method.
     *
     * @private
     */
    _replaceContent: function () {
        if (this._$content) {
            this._$content.remove();
        }
        this._$content = $(qweb.render("FieldDomain.content", {
            hasModel: !!this._domainModel,
            isValid: !!this._isValidForModel,
            nbRecords: this.record.specialData[this.name].nbRecords || 0,
            inDialogEdit: this.inDialog && this.mode === "edit",
        }));
        this._$content.appendTo(this.$el);
    },
    /**
     * @override _reset from AbstractField
     * Check if the model the field works with has (to be) changed.
     *
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        var oldDomainModel = this._domainModel;
        this._setState();
        if (this.domainSelector && this._domainModel !== oldDomainModel) {
            // If the model has changed, destroy the current domain selector
            this.domainSelector.destroy();
            this.domainSelector = null;
        }
    },
    /**
     * Sets the model the field must work with and whether or not the current
     * domain value is valid for this particular model. This is inferred from
     * the received special data.
     *
     * @private
     */
    _setState: function () {
        var specialData = this.record.specialData[this.name];
        this._domainModel = specialData.model;
        this._isValidForModel = (specialData.nbRecords !== false);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "Show selection" button is clicked
     * -> Open a modal to see the matched records
     *
     * @param {Event} e
     */
    _onShowSelectionButtonClick: function (e) {
        e.preventDefault();
        new view_dialogs.SelectCreateDialog(this, {
            title: _t("Selected records"),
            res_model: this._domainModel,
            domain: this.value || "[]",
            no_create: true,
            readonly: true,
            disable_multiple_selection: true,
        }).open();
    },
    /**
     * Called when the "Edit domain" button is clicked (when using the in_dialog
     * option) -> Open a DomainSelectorDialog to edit the value
     *
     * @param {Event} e
     */
    _onDialogEditButtonClick: function (e) {
        e.preventDefault();
        new DomainSelectorDialog(this, this._domainModel, this.value || "[]", {
            readonly: this.mode === "readonly",
            filters: this.fsFilters,
            debugMode: session.debug,
        }).open();
    },
    /**
     * Called when the domain selector value is changed (do nothing if it is the
     * one which is in a dialog (@see _onDomainSelectorDialogValueChange))
     * -> Adapt the internal value state
     *
     * @param {OdooEvent} e
     */
    _onDomainSelectorValueChange: function (e) {
        if (this.inDialog) return;
        this._setValue(Domain.prototype.arrayToString(this.domainSelector.getDomain()));
    },
    /**
     * Called when the in-dialog domain selector value is confirmed
     * -> Adapt the internal value state
     *
     * @param {OdooEvent} e
     */
    _onDomainSelectorDialogValueChange: function (e) {
        this._setValue(Domain.prototype.arrayToString(e.data.domain));
    },
    /**
     * Stops the propagation of the 'open_record' event, as we don't want the
     * user to be able to open records from the list opened in a dialog.
     *
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
        event.stopPropagation();
    },
});

/**
 * This widget is intended to be used on Text fields. It will provide Ace Editor
 * for editing XML and Python.
 */
var AceEditor = DebouncedField.extend({
    template: "AceEditor",
    jsLibs: [
        '/web/static/lib/ace/ace.odoo-custom.js',
        [
            '/web/static/lib/ace/mode-python.js',
            '/web/static/lib/ace/mode-xml.js'
        ]
    ],
    events: {}, // events are triggered manually for this debounced widget
    /**
     * @override start from AbstractField (Widget)
     *
     * @returns {Deferred}
     */
    start: function () {
        this._startAce(this.$('.ace-view-editor')[0]);
        return this._super.apply(this, arguments);
    },
    /**
     * @override destroy from AbstractField (Widget)
     */
    destroy: function () {
        if (this.aceEditor) {
            this.aceEditor.destroy();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Format value
     *
     * Note: We have to overwrite this method to always return a string.
     * AceEditor works with string and not boolean value.
     *
     * @override
     * @private
     * @param {boolean|string} value
     * @returns {string}
     */
    _formatValue: function (value) {
        return this._super.apply(this, arguments) || '';
    },

    /**
     * @override
     * @private
     */
    _getValue: function () {
        return this.aceSession.getValue();
    },
    /**
     * @override _render from AbstractField
     * The rendering is the same for edit and readonly mode: changing the ace
     * session value. This is only done if the value in the ace editor is not
     * already the new one (prevent losing focus / retriggering changes / empty
     * the undo stack / ...).
     *
     * @private
     */
    _render: function () {
        var newValue = this._formatValue(this.value);
        if (this.aceSession.getValue() !== newValue) {
            this.aceSession.setValue(newValue);
        }
    },

    /**
     * Starts the ace library on the given DOM element. This initializes the
     * ace editor option according to the edit/readonly mode and binds ace
     * editor events.
     *
     * @private
     * @param {Node} node - the DOM element the ace library must initialize on
     */
    _startAce: function (node) {
        this.aceEditor = ace.edit(node);
        this.aceEditor.setOptions({
            maxLines: Infinity,
            showPrintMargin: false,
        });
        if (this.mode === 'readonly') {
            this.aceEditor.renderer.setOptions({
                displayIndentGuides: false,
                showGutter: false,
            });
            this.aceEditor.setOptions({
                highlightActiveLine: false,
                highlightGutterLine: false,
                readOnly: true,
            });
            this.aceEditor.renderer.$cursorLayer.element.style.display = "none";
        }
        this.aceEditor.$blockScrolling = true;
        this.aceSession = this.aceEditor.getSession();
        this.aceSession.setOptions({
            useWorker: false,
            mode: "ace/mode/" + (this.nodeOptions.mode || 'xml'),
            tabSize: 2,
            useSoftTabs: true,
        });
        if (this.mode === "edit") {
            this.aceEditor.on("change", this._doDebouncedAction.bind(this));
            this.aceEditor.on("blur", this._doAction.bind(this));
        }
    },
});

var ImageSelection = AbstractField.extend({
    supportedFieldTypes: ['selection'],
    events: _.extend({}, AbstractField.prototype.events, {
        'click img': '_onImgClicked',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _render: function () {
        var self = this;
        this.$el.empty();
        _.each(this.nodeOptions, function (val, key) {
            var $container = $('<div>').addClass('col-xs-3 text-center');
            var $img = $('<img>')
                .addClass('img img-responsive img-thumbnail ml16')
                .toggleClass('btn-info', key === self.value)
                .attr('src', val.image_link)
                .data('key', key);
            $container.append($img);
            if (val.preview_link) {
                var $previewLink = $('<a>')
                    .text('Preview')
                    .attr('href', val.preview_link)
                    .attr('target', '_blank');
                $container.append($previewLink);
            }
            self.$el.append($container);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {MouseEvent} event
     */
    _onImgClicked: function (event) {
        this._setValue($(event.currentTarget).data('key'));
    },
});

return {
    TranslatableFieldMixin: TranslatableFieldMixin,
    DebouncedField: DebouncedField,
    FieldEmail: FieldEmail,
    FieldBinaryFile: FieldBinaryFile,
    FieldBinaryImage: FieldBinaryImage,
    FieldBoolean: FieldBoolean,
    FieldBooleanButton: FieldBooleanButton,
    BooleanToggle: BooleanToggle,
    FieldChar: FieldChar,
    LinkButton: LinkButton,
    FieldDate: FieldDate,
    FieldDateTime: FieldDateTime,
    FieldDomain: FieldDomain,
    FieldFloat: FieldFloat,
    FieldFloatTime: FieldFloatTime,
    FieldInteger: FieldInteger,
    FieldMonetary: FieldMonetary,
    FieldPercentPie: FieldPercentPie,
    FieldPhone: FieldPhone,
    FieldProgressBar: FieldProgressBar,
    FieldText: FieldText,
    FieldToggleBoolean: FieldToggleBoolean,
    HandleWidget: HandleWidget,
    InputField: InputField,
    AttachmentImage: AttachmentImage,
    ImageSelection: ImageSelection,
    LabelSelection: LabelSelection,
    StateSelectionWidget: StateSelectionWidget,
    FavoriteWidget: FavoriteWidget,
    PriorityWidget: PriorityWidget,
    StatInfo: StatInfo,
    UrlWidget: UrlWidget,
    JournalDashboardGraph: JournalDashboardGraph,
    AceEditor: AceEditor,
};

});
