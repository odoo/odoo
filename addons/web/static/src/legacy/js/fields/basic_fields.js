/* global ace */
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
var datepicker = require('web.datepicker');
var deprecatedFields = require('web.basic_fields.deprecated');
var dom = require('web.dom');
var Domain = require('web.Domain');
var DomainSelector = require('web.DomainSelector');
var DomainSelectorDialog = require('web.DomainSelectorDialog');
var ModelFieldSelectorPopover = require("web.ModelFieldSelectorPopover");
var framework = require('web.framework');
var py_utils = require('web.py_utils');
var session = require('web.session');
var utils = require('web.utils');
var view_dialogs = require('web.view_dialogs');
var field_utils = require('web.field_utils');
var time = require('web.time');
const {ColorpickerDialog} = require('web.Colorpicker');
const { hidePDFJSButtons } = require('@web/legacy/js/libs/pdfjs');

let FieldBoolean = deprecatedFields.FieldBoolean;

require("web.zoomodoo");

var qweb = core.qweb;
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

var DynamicPlaceholderFieldMixin = {
    DYNAMIC_PLACEHOLDER_TRIGGER_KEY: '#',
    /**
     * Overridable method that ensure the modelSelectorPopover is
     * positioned properly.
     *
     * @public
     * @param {ModelFieldSelectorPopover} modelSelector
     */
    positionModelSelector: function (modelSelector) {
        let relativeParent = this.el.closest('div.modal-content');
        if (!relativeParent) {
            relativeParent = this.el;
            while(!relativeParent || !['absolute', 'relative'].includes(getComputedStyle(relativeParent).position)) {
                relativeParent = relativeParent.offsetParent;
            }
        }

        const relatedElementPosition = this.el.getBoundingClientRect();
        const relativeParentPosition = relativeParent.getBoundingClientRect();

        let topPosition = relatedElementPosition.top + relatedElementPosition.height - relativeParentPosition.top
        let leftPosition = relatedElementPosition.left - relativeParentPosition.left;

        modelSelector.el.style.top = topPosition + 'px';
        modelSelector.el.style.left = leftPosition + 'px';
    },
    /**
     * Open and return new Model Field Selector with the provided options
     *
     * @private
     * @param {String} baseModel
     * @param {Array} chain
     * @param {Function} onFieldChanged
     * @param {Function} onFieldCancel
     *
     * @returns {ModelFieldSelectorPopover}
     */
    _openNewModelSelector: async function (baseModel, chain, onFieldChanged = null, onFieldCancel = null) {
        const triggerKeyReplaceRegex = new RegExp(`${this.DYNAMIC_PLACEHOLDER_TRIGGER_KEY}$`);

        const modelSelector = new ModelFieldSelectorPopover(
            this,
            baseModel,
            [],
            {
                readonly: false,
                needDefaultValue: true,
                cancelOnEscape: true,
                chainedTitle: true,
                filter: (model) => !["one2many", "boolean", "many2many"].includes(model.type)
            }
        );
        if (!onFieldChanged) {
            onFieldChanged = (ev) => {
                this.$el.focus();
                if (ev.data.chain.length) {
                    let dynamicPlaceholder = "{{object." + ev.data.chain.join('.');
                    const defaultValue = ev.data.defaultValue;
                    dynamicPlaceholder += defaultValue && defaultValue !== '' ? ` or '''${defaultValue}'''}}` : '}}';
                    this.el.value =
                        this.el.value.replace(triggerKeyReplaceRegex, '') + dynamicPlaceholder;
                }
                modelSelector.destroy();
            };
        }

        if (onFieldCancel === null) {
            onFieldCancel = () => {
                this.$el.focus();
                modelSelector.destroy();
            };

        }

        modelSelector.on("field_chain_changed", undefined, onFieldChanged);
        modelSelector.on("field_chain_cancel", undefined, onFieldCancel);

        // If we are inside a modal environment,
        // we need to append the ModelFieldSelectorPopover outside the
        // modal body, to be sure the overflow will be visible.
        const modalParent = this.el.closest('div.modal-content');
        if (modalParent) {
            await modelSelector.appendTo(modalParent);
        } else {
            await modelSelector.insertAfter(this.el);
        }
        this.positionModelSelector(modelSelector);

        modelSelector.open(chain, true);
        return modelSelector;
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
    custom_events: _.extend({}, DebouncedField.prototype.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    events: _.extend({}, DebouncedField.prototype.events, {
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
            inputAttrs = _.extend(inputAttrs, { type: 'password', autocomplete: this.attrs.autocomplete || 'new-password' });
            inputVal = this.value || '';
        } else {
            inputAttrs = _.extend(inputAttrs, { type: 'text', autocomplete: this.attrs.autocomplete || 'off'});
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
            } catch (_err) {
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

var FieldChar = InputField.extend(TranslatableFieldMixin, DynamicPlaceholderFieldMixin, {
    description: _lt("Text"),
    className: 'o_field_char',
    tagName: 'span',
    supportedFieldTypes: ['char'],
    isQuickEditable: true,

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------


    /**
     * @override
     */
    init: function () {
        this._super(...arguments);
        if (this.nodeOptions && this.nodeOptions.dynamic_placeholder) {
            // When the dynamic placeholder is active, the recordData
            // need to be updated when `mailing_model_real` change
            this.resetOnAnyFieldChange = true;
        }
    },
    /**
     * Open the dynamic placeholder if trigger key match
     *
     * @private
     * @override
     * @param {KeyboardEvent} ev
     */
    async _onKeydown(ev) {
        this._super(...arguments);
        if (this.nodeOptions &&
            this.nodeOptions.dynamic_placeholder &&
            ev.key === this.DYNAMIC_PLACEHOLDER_TRIGGER_KEY) {
            ev.preventDefault();
            const baseModel = this.recordData && this.recordData.mailing_model_real ? this.recordData.mailing_model_real : undefined;
            if (baseModel) {
                await this._openNewModelSelector(baseModel);
            }
            this.el.value += ev.key;
        }
    },
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

var FieldDateRange = InputField.extend({
    className: 'o_field_date_range',
    tagName: 'span',
    jsLibs: [
        '/web/static/lib/daterangepicker/daterangepicker.js',
        '/web/static/src/legacy/js/libs/daterangepicker.js',
    ],
    supportedFieldTypes: ['date', 'datetime'],
    isQuickEditable: true,
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.formatType = this.nodeOptions.format_type || this.formatType;
        this.isDateField = this.formatType === 'date';
        this.dateRangePickerOptions = _.defaults(
            {},
            this.nodeOptions.picker_options || {},
            {
                timePicker: !this.isDateField,
                timePicker24Hour: _t.database.parameters.time_format.search('%H') !== -1,
                autoUpdateInput: false,
                timePickerIncrement: 5,
                locale: {
                    applyLabel: _t('Apply'),
                    cancelLabel: _t('Cancel'),
                    format: this.isDateField ? time.getLangDateFormat() : time.getLangDatetimeFormat(),
                },
            }
        );
        this.relatedEndDate = this.nodeOptions.related_end_date;
        this.relatedStartDate = this.nodeOptions.related_start_date;
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$pickerContainer) {
            this.$pickerContainer.remove();
        }
        if (this._onScroll) {
            window.removeEventListener('scroll', this._onScroll, true);
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Field widget is valid if value entered can convered to date/dateime value
     * while parsing input value to date/datetime throws error then widget considered
     * invalid
     *
     * @override
     */
    isValid: function () {
        const value = this.mode === "readonly" ? this.value : this.$input.val();
        try {
            return field_utils.parse[this.formatType](value, this.field, { timezone: true }) || true;
        } catch (_error) {
            return false;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return the date written in the input, in UTC.
     *
     * @private
     * @returns {Moment|false}
     */
    _getValue: function () {
        try {
            // user may enter manual value in input and it may not be parsed as date/datetime value
            this.removeInvalidClass();
            return field_utils.parse[this.formatType](this.$input.val(), this.field, { timezone: true });
        } catch (_error) {
            this.setInvalidClass();
            return false;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * @param {Object} picker
     */
    _applyChanges: function (ev, picker) {
        var changes = {};
        var displayStartDate = field_utils.format[this.formatType](picker.startDate, {}, {timezone: false});
        var displayEndDate = field_utils.format[this.formatType](picker.endDate, {}, {timezone: false});
        var changedStartDate = picker.startDate;
        var changedEndDate = picker.endDate;
        if (this.isDateField) {
            // In date mode, the library will give moment object of start and end date having
            // time at 00:00:00. So, Odoo will consider it as UTC. To fix this added browser
            // timezone offset in dates to get a correct selected date.
            changedStartDate = picker.startDate.add(session.getTZOffset(picker.startDate), 'minutes');
            changedEndDate = picker.endDate.startOf('day').add(session.getTZOffset(picker.endDate), 'minutes');
        }
        if (this.relatedEndDate) {
            this.$el.val(displayStartDate);
            changes[this.name] = this._parseValue(changedStartDate);
            changes[this.relatedEndDate] = this._parseValue(changedEndDate);
        }
        if (this.relatedStartDate) {
            this.$el.val(displayEndDate);
            changes[this.name] = this._parseValue(changedEndDate);
            changes[this.relatedStartDate] = this._parseValue(changedStartDate);
        }
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            viewType: this.viewType,
            changes: changes,
        });
    },
    /**
     * @override
     */
    _renderEdit: function () {
        this._super.apply(this, arguments);
        var self = this;
        const [startDate, endDate] = this._getDateRangeFromInputField();
        this.dateRangePickerOptions.startDate = startDate || moment();
        this.dateRangePickerOptions.endDate = endDate || moment();

        this.$el.daterangepicker(this.dateRangePickerOptions);
        this.$el.on('apply.daterangepicker', this._applyChanges.bind(this));
        this.$el.on('show.daterangepicker', this._onDateRangePickerShow.bind(this));
        this.$el.on('hide.daterangepicker', this._onDateRangePickerHide.bind(this));
        this.$el.off('keyup.daterangepicker');
        this.$pickerContainer = this.$el.data('daterangepicker').container;

        // Prevent from leaving the edition of a row in editable list view
        this.$pickerContainer.on('click', function (ev) {
            ev.stopPropagation();
            if ($(ev.target).hasClass('applyBtn')) {
                self.$el.data('daterangepicker').hide();
            }
        });

        // Prevent bootstrap from focusing on modal (which breaks hours drop-down in firefox)
        this.$pickerContainer.on('focusin.bs.modal', 'select', function (ev) {
            ev.stopPropagation();
        });
    },

    /**
     * @private
     * @override
     */
     _quickEdit: function () {
        if (this.$el) {
            this.$el.click()
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Unbind the scroll event handler when the daterangepicker is closed.
     *
     * @private
     */
    _onDateRangePickerHide() {
        if (this._onScroll) {
            window.removeEventListener('scroll', this._onScroll, true);
        }
    },
    /**
     * Bind the scroll event handle when the daterangepicker is open.
     * Update the begin and end date with the dates from the input values
     *
     * @private
     */
    _onDateRangePickerShow() {
        const daterangepicker = this.$el.data('daterangepicker');
        this._onScroll = ev => {
            if (!config.device.isMobile && !this.$pickerContainer.get(0).contains(ev.target)) {
                daterangepicker.hide();
            }
        };
        window.addEventListener('scroll', this._onScroll, true);
        const [startDate, endDate] = this._getDateRangeFromInputField();
        daterangepicker.setStartDate(startDate? startDate.utcOffset(session.getTZOffset(startDate)): moment());
        daterangepicker.setEndDate(endDate? endDate.utcOffset(session.getTZOffset(endDate)): moment());
        daterangepicker.updateView();
    },
    /**
     * Get the startDate and endDate of the daterangepicker from the input fields
     * @returns [Date (moment object), Date (moment object)]
     * @private
     */
    _getDateRangeFromInputField() {
        let startDate, endDate;
        if (this.relatedEndDate) {
            startDate = this.value;
            endDate = this.recordData[this.relatedEndDate];
        }
        if (this.relatedStartDate) {
            startDate = this.recordData[this.relatedStartDate];
            endDate = this.value;
        }
        return [startDate, endDate];
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
        this.datepickerOptions = _.defaults(
            {},
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
            } catch (_err) {}
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

const RemainingDays = AbstractField.extend({
    description: _lt("Remaining Days"),
    supportedFieldTypes: ['date', 'datetime'],

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        // use the session timezone when formatting dates
        this.formatOptions.timezone = true;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the associated <input/> element.
     *
     * @override
     */
    getFocusableElement() {
        return this.datewidget && this.datewidget.$input || $();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {string} the content of the input
     */
    _getValue() {
        let value = this.datewidget.getValue();
        if (this.field.type === "datetime") {
            value = value && value.add(-this.getSession().getTZOffset(value), 'minutes');
        }
        return value;
    },
    /**
     * Instantiates a new DateWidget datepicker.
     *
     * @private
     */
    _makeDatePicker() {
        this.datepickerOptions = _.defaults({}, { defaultDate: this.value });
        if (this.field.type === "datetime" && this.value) {
            const offset = this.getSession().getTZOffset(this.value);
            const displayedValue = this.value.clone().add(offset, 'minutes');
            this.datepickerOptions.defaultDate = displayedValue;
        }
        if (this.field.type === "date") {
            return new datepicker.DateWidget(this, this.datepickerOptions);
        }
        return new datepicker.DateTimeWidget(this, this.datepickerOptions);
    },
    /**
     * Displays date/datetime picker in edit mode.
     *
     * @override
     */
    async _renderEdit() {
        await this._super(...arguments);
        if (this.datewidget) {
            this.datewidget.destroy();
        }

        this.datewidget = this._makeDatePicker();
        this.datewidget.on('datetime_changed', this, () => {
            const value = this._getValue();
            if ((!value && this.value) || (value && !this._isSameValue(value))) {
                this._setValue(value);
            }
        });

        await this.datewidget.appendTo('<div>');
        this.$el.append(this.datewidget.$el);
    },

    /**
     * Displays the delta (in days) between the value of the field and today. If
     * the delta is larger than 99 days, displays the date as usual (without
     * time).
     *
     * @override
     */
    _renderReadonly() {
        if (this.value === false) {
            this.$el.removeClass('fw-bold text-danger text-warning');
            return;
        }
        // compare the value (in the user timezone) with now (also in the user
        // timezone), to get a meaningful delta for the user
        const nowUTC = moment().utc();
        const nowUserTZ = nowUTC.clone().add(session.getTZOffset(nowUTC), 'minutes');
        const fieldValue = this.field.type == "datetime" ? this.value.clone().add(session.getTZOffset(this.value), 'minutes') : this.value;
        const diffDays = fieldValue.startOf('day').diff(nowUserTZ.startOf('day'), 'days');
        let text;
        if (Math.abs(diffDays) > 99) {
            text = this._formatValue(this.value, 'date');
        } else if (diffDays === 0) {
            text = _t("Today");
        } else if (diffDays < 0) {
            text = diffDays === -1 ? _t("Yesterday") : _.str.sprintf(_t('%s days ago'), -diffDays);
        } else {
            text = diffDays === 1 ? _t("Tomorrow") : _.str.sprintf(_t('In %s days'), diffDays);
        }
        this.$el.text(text).attr('title', this._formatValue(this.value, 'date'));
        this.$el.toggleClass('fw-bold', diffDays <= 0);
        this.$el.toggleClass('text-danger', diffDays < 0);
        this.$el.toggleClass('text-warning', diffDays === 0);
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
        var index = _.indexOf(range, val);
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
     * @private
     * @override
     */
    _quickEdit: function () {
        this.activate({noselect: true, noAutomaticCreate: true});
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

var ListFieldText = FieldText.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.autoResizeOptions.min_height = 0;
    },
});

/**
 * Displays a handle to modify the sequence.
 */
var HandleWidget = AbstractField.extend({
    description: _lt("Handle"),
    noLabel: true,
    className: 'o_row_handle fa fa-sort ui-sortable-handle',
    widthInList: '33px',
    tagName: 'span',
    supportedFieldTypes: ['integer'],

    /*
     * @override
     */
    isSet: function () {
        return true;
    },
});

var FieldEmail = InputField.extend({
    description: _lt("Email"),
    className: 'o_field_email',
    events: _.extend({}, InputField.prototype.events, {
        'click': '_onClickLink',
    }),
    prefix: 'mailto',
    supportedFieldTypes: ['char'],
    isQuickEditable: true,

    /**
     * In readonly, emails should be a link, not a span.
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = this.mode === 'readonly' ? 'div' : 'input';
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
     * In readonly, emails should be a mailto: link with proper formatting.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        if (this.value) {
            this.el.innerHTML = '';
            this.el.classList.add("o_form_uri", "o_text_overflow");
            const anchorEl = Object.assign(document.createElement('a'), {
                text: this.value,
                href: `${this.prefix}:${this.value}`,
            });
            this.el.appendChild(anchorEl);
        }
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Prevent the URL click from opening the record (when used on a list).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLink: function (ev) {
        if (ev.target.matches("a")) {
            ev.stopImmediatePropagation();
        }
    },
});

var FieldPhone = FieldEmail.extend({
    description: _lt("Phone"),
    className: 'o_field_phone',
    prefix: 'tel',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _renderReadonly: function () {
        this._super();

        // This class should technically be there in case of a very very long
        // phone number, but it breaks the o_row mechanism, which is more
        // important right now.
        this.$el.removeClass('o_text_overflow');
    },
});

var UrlWidget = InputField.extend({
    description: _lt("URL"),
    className: 'o_field_url',
    events: _.extend({}, InputField.prototype.events, {
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

var CopyClipboard = {
    quickEditExclusion: [
        '.o_clipboard_button',
    ],

    /**
     * @override
     */
    destroy: function () {
        this._super.apply(this, arguments);
        if (this.clipboard) {
            this.clipboard.destroy();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instatiates the Clipboad lib.
     */
    _initClipboard: function () {
        var self = this;
        var $clipboardBtn = this.$('.o_clipboard_button');
        $clipboardBtn.tooltip({title: _t('Copied !'), trigger: 'manual', placement: 'right'});
        this.clipboard = new ClipboardJS($clipboardBtn[0], {
            text: function () {
                return self.value.trim();
            },
            // Container added because of Bootstrap modal that give the focus to another element.
            // We need to give to correct focus to ClipboardJS (see in ClipboardJS doc)
            // https://github.com/zenorocha/clipboard.js/issues/155
            container: self.$el[0]
        });
        this.clipboard.on('success', function () {
            _.defer(function () {
                $clipboardBtn.tooltip('show');
                _.delay(function () {
                    $clipboardBtn.tooltip('hide');
                }, 800);
            });
        });
    },
    /**
     * @override
     */
    _renderReadonly: function () {
        this._super.apply(this, arguments);
        if (this.value) {
            this.$el.append($(qweb.render(this.clipboardTemplate)));
            this._initClipboard();
        }
    }
};

var ButtonCopyClipboard = AbstractField.extend(CopyClipboard, {
    description: _lt('Copy to Clipboard'),
    clipboardTemplate: 'CopyClipboardButton',
    className: '',
    events: _.extend({}, AbstractField.prototype.events, {
        'click': '_onClick',
    }),
    /**
     * @param {Event} event
     */
    _onClick: event => {
        event.stopPropagation();
    },
    /**
     * @override
     */
    _renderReadonly: function () {
        this._super.apply(this, arguments);
        if (this.value) {
            const $btn = $(qweb.render(this.clipboardTemplate));
            $btn.addClass(this.nodeOptions && this.nodeOptions.classes || 'btn-primary');
            if (this.nodeOptions && this.nodeOptions.label) {
                $btn.text(_t(this.nodeOptions.label));
            }
            this.$el.empty().append($btn);
            this._initClipboard();
        }
    },
});

var TextCopyClipboard = FieldText.extend(CopyClipboard, {
    description: _lt("Copy to Clipboard"),
    clipboardTemplate: 'CopyClipboardText',
    className: "o_field_copy",
});

var CharCopyClipboard = FieldChar.extend(CopyClipboard, {
    description: _lt("Copy to Clipboard"),
    clipboardTemplate: 'CopyClipboardChar',
    className: 'o_field_copy o_text_overflow',
});

var URLCopyClipboard = FieldChar.extend(CopyClipboard, {
    description: _lt("Copy to Clipboard"),
    clipboardTemplate: 'CopyClipboardChar',
    className: 'o_field_copy o_text_overflow o_field_copy_url',
    events: _.extend({}, FieldChar.prototype.events, {
        'click': '_onClick',
    }),

    _onClick: function(ev) {
        if(ev.target.className.includes('o_field_copy_url')) {
            ev.stopPropagation();

            window.open(this.value, '_blank');
        }
    }
});

var AbstractFieldBinary = AbstractField.extend({
    events: _.extend({}, AbstractField.prototype.events, {
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
                    this.displayNotification({ title: _t("File upload"), message: _.str.sprintf(msg, utils.human_size(this.max_upload_size)), type: 'danger' });
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

var FieldBinaryImage = AbstractFieldBinary.extend({
    description: _lt("Image"),
    fieldDependencies: _.extend({}, AbstractFieldBinary.prototype.fieldDependencies, {
        __last_update: {type: 'datetime'},
    }),

    template: 'FieldBinaryImage',
    placeholder: "/web/static/img/placeholder.png",
    events: _.extend({}, AbstractFieldBinary.prototype.events, {
        'click img': '_onImageClick',
    }),
    supportedFieldTypes: ['binary'],
    file_type_magic_word: {
        '/': 'jpg',
        'R': 'gif',
        'i': 'png',
        'P': 'svg+xml',
    },
    accepted_file_extensions: 'image/*',
    /**
     * Returns the image URL from a model.
     *
     * @private
     * @param {string} model    model from which to retrieve the image
     * @param {string} res_id   id of the record
     * @param {string} field    name of the image field
     * @param {string} unique   an unique integer for the record, usually __last_update
     * @returns {string} URL of the image
     */
    _getImageUrl: function (model, res_id, field, unique) {
        return session.url('/web/image', {
            model: model,
            id: JSON.stringify(res_id),
            field: field,
            // unique forces a reload of the image when the record has been updated
            unique: field_utils.format.datetime(unique).replace(/[^0-9]/g, ''),
        });
    },
    _render: function () {
        var self = this;
        var url = this.placeholder;
        if (this.value) {
            if (!utils.is_bin_size(this.value)) {
                // Use magic-word technique for detecting image type
                url = 'data:image/' + (this.file_type_magic_word[this.value[0]] || 'png') + ';base64,' + this.value;
            } else {
                var field = this.nodeOptions.preview_image || this.name;
                var unique = this.recordData.__last_update;
                url = this._getImageUrl(this.model, this.res_id, field, unique);
            }
        }
        var $img = $(qweb.render("FieldBinaryImage-img", {widget: this, url: url}));
        // override css size attributes (could have been defined in css files)
        // if specified on the widget
        var width = this.nodeOptions.size ? this.nodeOptions.size[0] : this.attrs.width;
        var height = this.nodeOptions.size ? this.nodeOptions.size[1] : this.attrs.height;
        if (width) {
            $img.attr('width', width);
            $img.css('max-width', width + 'px');
            if (!height) {
                $img.css('height', 'auto');
                $img.css('max-height', '100%');
            }
        }
        if (height) {
            $img.attr('height', height);
            $img.css('max-height', height + 'px');
            if (!width) {
                $img.css('width', 'auto');
                $img.css('max-width', '100%');
            }
        }
        this.$('> img').remove();
        this.$el.prepend($img);

        $img.one('error', function () {
            $img.attr('src', self.placeholder);
            self.displayNotification({ message: _t("Could not display the selected image"), type: 'danger' });
        });

        return this._super.apply(this, arguments);
    },
    /**
     * Only enable the zoom on image in read-only mode, and if the option is enabled.
     *
     * @override
     * @private
     */
    _renderReadonly: function () {
        this._super.apply(this, arguments);

        var unique = this.recordData.__last_update;
        var url = this._getImageUrl(this.model, this.res_id, 'image_1920', unique);
        var $img;
        var imageField = _.find(Object.keys(this.recordData), function(o) {
            return o.startsWith('image_');
        });

        if(this.nodeOptions.background)
        {
            if('tag' in this.nodeOptions) {
                this.tagName = this.nodeOptions.tag;
            }

            if('class' in this.attrs) {
                this.$el.addClass(this.attrs.class);
            }

            var urlThumb = this._getImageUrl(this.model, this.res_id, this.name, unique);

            this.$el.empty();
            $img = this.$el;
            $img.css('backgroundImage', 'url(' + urlThumb + ')');
        } else {
            $img = this.$('img');
        }
        if(this.nodeOptions.zoom) {
            var zoomDelay = 0;
            if (this.nodeOptions.zoom_delay) {
                zoomDelay = this.nodeOptions.zoom_delay;
            }
            if(this.recordData[imageField]) {
                $img.attr('data-zoom', 1);
                $img.attr('data-zoom-image', url);

                $img.zoomOdoo({
                    event: 'mouseenter',
                    timer: zoomDelay,
                    attach: '.o_content',
                    attachToTarget: true,
                    disabledOnMobile: false,
                    onShow: function () {
                        var zoomHeight = Math.ceil(this.$zoom.height());
                        var zoomWidth = Math.ceil(this.$zoom.width());
                        if( zoomHeight < 128 && zoomWidth < 128) {
                            this.hide();
                        }
                        core.bus.on('keydown', this, this.hide);
                        core.bus.on('click', this, this.hide);
                    },
                    beforeAttach: function () {
                        this.$flyout.css({ width: '512px', height: '512px' });
                    },
                    preventClicks: this.nodeOptions.preventClicks,
                });
            }
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onImageClick: function (ev) {
        if (this.mode === "readonly") {
            this.trigger_up('bounce_edit');
        }
    },
});

var CharImageUrl = AbstractField.extend({
    className: 'o_field_image',
    description: _lt("Image"),
    supportedFieldTypes: ['char'],
    placeholder: "/web/static/img/placeholder.png",

    _renderReadonly: function () {
        var self = this;
        const url = this.value;
        if (url) {
            var $img = $(qweb.render("FieldBinaryImage-img", {widget: this, url: url}));
            // override css size attributes (could have been defined in css files)
            // if specified on the widget
            const width = this.nodeOptions.size ? this.nodeOptions.size[0] : this.attrs.width;
            const height = this.nodeOptions.size ? this.nodeOptions.size[1] : this.attrs.height;
            if (width) {
                $img.attr('width', width);
                $img.css('max-width', width + 'px');
                if (!height) {
                    $img.css('height', 'auto');
                    $img.css('max-height', '100%');
                }
            }
            if (height) {
                $img.attr('height', height);
                $img.css('max-height', height + 'px');
                if (!width) {
                    $img.css('width', 'auto');
                    $img.css('max-width', '100%');
                }
            }
            this.$('> img').remove();
            this.$el.prepend($img);

            $img.one('error', function () {
                $img.attr('src', self.placeholder);
                self.displayNotification({
                    type: 'info',
                    message: _t("Could not display the specified image url."),
                });
            });
        }

        return this._super.apply(this, arguments);
    },
});

var KanbanFieldBinaryImage = FieldBinaryImage.extend({
    // In kanban views, there is a weird logic to determine whether or not a
    // click on a card should open the record in a form view.  This logic checks
    // if the clicked element has click handlers bound on it, and if so, does
    // not open the record (assuming that the click will be handle by someone
    // else).  In the case of this widget, there are clicks handler but they
    // only apply in edit mode, which is never the case in kanban views, so we
    // simply remove them.
    events: {},
});

var KanbanCharImageUrl = CharImageUrl.extend({
    // In kanban views, there is a weird logic to determine whether or not a
    // click on a card should open the record in a form view.  This logic checks
    // if the clicked element has click handlers bound on it, and if so, does
    // not open the record (assuming that the click will be handled by someone
    // else).  In the case of this widget, there are clicks handler but they
    // only apply in edit mode, which is never the case in kanban views, so we
    // simply remove them.
    events: {},
});

var FieldBinaryFile = AbstractFieldBinary.extend({
    description: _lt("File"),
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

var FieldPdfViewer = FieldBinaryFile.extend({
    description: _lt("PDF Viewer"),
    supportedFieldTypes: ['binary'],
    template: 'FieldPdfViewer',
    accepted_file_extensions: 'application/pdf',
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.PDFViewerApplication = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} [fileURI] file URI if specified
     * @returns {string} the pdf viewer URI
     */
    _getURI: function (fileURI) {
        var page = this.recordData[this.name + '_page'] || 1;
        if (!fileURI) {
            var queryObj = {
                model: this.model,
                field: this.name,
                id: this.res_id,
            };
            var queryString = $.param(queryObj);
            fileURI = '/web/content?' + queryString;
        }
        fileURI = encodeURIComponent(fileURI);
        var viewerURL = '/web/static/lib/pdfjs/web/viewer.html?file=';
        return viewerURL + fileURI + '#page=' + page;
    },
    /**
     * @private
     * @override
     */
    _render: function () {
        var self = this;
        var $pdfViewer = this.$('.o_form_pdf_controls').children().add(this.$('.o_pdfview_iframe'));
        var $selectUpload = this.$('.o_select_file_button').first();
        var $iFrame = this.$('.o_pdfview_iframe');

        $iFrame.on('load', function () {
            self.PDFViewerApplication = this.contentWindow.window.PDFViewerApplication;
        });
        if (this.mode === "readonly" && this.value) {
            $iFrame.attr('src', this._getURI());
        } else {
            if (this.value) {
                var binSize = utils.is_bin_size(this.value);
                $pdfViewer.removeClass('o_hidden');
                $selectUpload.addClass('o_hidden');
                if (binSize) {
                    $iFrame.attr('src', this._getURI());
                }
            } else {
                $pdfViewer.addClass('o_hidden');
                $selectUpload.removeClass('o_hidden');
            }
        }
        hidePDFJSButtons($iFrame[0]);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @param {Event} ev
     */
    on_file_change: function (ev) {
        this._super.apply(this, arguments);
        var files = ev.target.files;
        if (!files || files.length === 0) {
            return;
        }
        // TOCheck: is there requirement to fallback on FileReader if browser don't support URL
        var fileURI = URL.createObjectURL(files[0]);
        if (this.PDFViewerApplication) {
            this.PDFViewerApplication.open(fileURI, 0);
        } else {
            this.$('.o_pdfview_iframe').attr('src', this._getURI(fileURI));
        }
    },
    /**
     * Remove the behaviour of on_save_as in FieldBinaryFile.
     *
     * @override
     * @private
     * @param {MouseEvent} ev
     */
    on_save_as: function (ev) {
        ev.stopPropagation();
    },

});

var PriorityWidget = AbstractField.extend({
    description: _lt("Priority"),
    // the current implementation of this widget makes it
    // only usable for fields of type selection
    className: "o_priority",
    attributes: {
        'role': 'radiogroup',
    },
    events: {
        'mouseover > a': '_onMouseOver',
        'mouseout > a': '_onMouseOut',
        'click > a': '_onPriorityClick',
        'keydown > a': '_onKeydown',
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

    /**
     * Returns the currently-checked star, or the first one if no star is
     * checked.
     *
     * @override
     */
    getFocusableElement: function () {
        var checked = this.$("[aria-checked='true']");
        return checked.length ? checked : this.$("[data-index='1']");
    },

    on_attach_callback() {
        const self = this;
        if (self.viewType === "form") {
            let provide = () => {
                return self.field.selection.map((value) => ({
                    name: value[1],
                    action: () => {
                        this._setValue(value[0]);
                    }
                }))
            }
            let getCommandDefinition = (env) => ({
                name: env._t("Set priority..."),
                options: {
                    activeElement: env.services.ui.getActiveElementOf(self.el),
                    category: "smart_action",
                    hotkey: "alt+r",
                },
                action() {
                    return {
                        placeholder: env._t("Set a priority..."),
                        providers: [{ provide }],
                    };
                },
            });
            core.bus.trigger("set_legacy_command", "web.PriorityWidget.setPriority", getCommandDefinition);
        }
    },

    on_detach_callback() {
        core.bus.trigger("remove_legacy_command", "web.PriorityWidget.setPriority");
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
        this.$el.attr('aria-label', this.string);
        const isReadonly = this.record.evalModifiers(this.attrs.modifiers).readonly;
        _.each(this.field.selection.slice(1), function (choice, index) {
            const tag = isReadonly ? '<span>' : '<a href="#">';
            self.$el.append(self._renderStar(tag, index_value >= index + 1, index + 1, `${self.string}: ${choice[1]}`, index_value));
        });
    },

    /**
     * Renders a star representing a particular value for this field.
     *
     * @param {string} tag html tag to be passed to jquery to hold the star
     * @param {boolean} isFull whether the star is a full star or not
     * @param {integer} index the index of the star in the series
     * @param {string} tip tooltip for this star's meaning
     * @param {integer} indexValue the index of the last full star or 0
     * @private
     */
    _renderStar: function (tag, isFull, index, tip, indexValue) {
        var isChecked = indexValue === index;
        var defaultFocus = indexValue === 0 && index === 1;
        return $(tag)
            .attr('role', 'radio')
            .attr('aria-checked', isChecked)
            .attr('title', tip)
            .attr('aria-label', tip)
            .attr('tabindex', isChecked || defaultFocus ? 0 : -1)
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
    _onPriorityClick: function (event) {
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

    /**
     * Runs the default behavior when <enter> is pressed over a star
     * (the same as if it was clicked); otherwise forwards event to the widget.
     *
     * @param {KeydownEvent} event
     * @private
     */
    _onKeydown: function (event) {
        if (event.which === $.ui.keyCode.ENTER) {
            return;
        }
        this._super.apply(this, arguments);
    },

    _onNavigationMove: function (ev) {
        var $curControl = this.$('a:focus');
        var $nextControl;
        if (ev.data.direction === 'right' || ev.data.direction === 'down') {
            $nextControl = $curControl.next('a');
        } else if (ev.data.direction === 'left' || ev.data.direction === 'up') {
            $nextControl = $curControl.prev('a');
        }
        if ($nextControl && $nextControl.length) {
            ev.stopPropagation();
            $nextControl.focus();
            return;
        }
        this._super.apply(this, arguments);
    },
});

var AttachmentImage = AbstractField.extend({
    className: 'o_attachment_image',
    // Remove event handlers on this widget to ensure that the kanban 'global
    // click' opens the clicked record, click on abstractField is useful in
    // Form and List view only.
    events: _.omit(AbstractField.prototype.events, 'click'),

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
                title: this.value.data.display_name,
                alt: _t("Image")
            }));
        }
    }
});

var StateSelectionWidget = AbstractField.extend({
    template: 'FormSelection',
    events: {
        'click .dropdown-item': '_setSelection',
    },
    supportedFieldTypes: ['selection'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the drop down button.
     *
     * @override
     */
    getFocusableElement: function () {
        return this.$("a[data-bs-toggle='dropdown']");
    },

    on_attach_callback() {
        const self = this;
        if (self.viewType === "form") {
            let provide = () => {
                return self.field.selection.map((value) => ({
                    name: value[1],
                    action: () => {
                        this._setValue(value[0]);
                    }
                }))
            }
            let getCommandDefinition = (env) => ({
                name: env._t("Set kanban state..."),
                options: {
                    activeElement: env.services.ui.getActiveElementOf(self.el),
                    category: "smart_action",
                    hotkey: "alt+shift+r",
                 },
                action() {
                    return {
                        placeholder: env._t("Set a kanban state..."),
                        providers: [{ provide }],
                    }
                },
            });
            core.bus.trigger("set_legacy_command", "web.StateSelectionWidget.setKanbanState", getCommandDefinition);
        }
    },

    on_detach_callback() {
        core.bus.trigger("remove_legacy_command", "web.StateSelectionWidget.setKanbanState");
    },
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
        var states = this._prepareDropdownValues();
        // Adapt "FormSelection"
        // Like priority, default on the first possible value if no value is given.
        var currentState = _.findWhere(states, {name: this.value}) || states[0];
        this.$('.o_status')
            .removeClass('o_status_red o_status_green')
            .addClass(currentState.state_class)
            .prop('special_click', true)
            .parent().attr('title', currentState.state_name)
            .attr('aria-label', this.string + ": " + currentState.state_name);

        // Render "FormSelection.Items" and move it into "FormSelection"
        var $items = $(qweb.render('FormSelection.items', {
            states: _.without(states, currentState)
        }));
        var $dropdown = this.$('.dropdown-menu');
        $dropdown.children().remove(); // remove old items
        $items.appendTo($dropdown);

        // Disable edition if the field is readonly
        var isReadonly = this.record.evalModifiers(this.attrs.modifiers).readonly;
        this.$('a[data-bs-toggle=dropdown]').toggleClass('disabled', isReadonly || false);
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
        ev.preventDefault();
        if (this.mode !== 'edit') {
            ev.stopPropagation();
        }
        var $item = $(ev.currentTarget);
        var value = String($item.data('value'));
        this._setValue(value);
        if (this.mode === 'edit') {
            this._render();
        }
    },
});

const ListStateSelectionWidget = StateSelectionWidget.extend({
    /**
     * display the label next to the icon
     * @override
     */
    _render() {
        this._super.apply(this, arguments);

        const hideLabel = utils.toBoolElse(this.nodeOptions.hide_label || '', false);
        if (!hideLabel) {
            const states = this._prepareDropdownValues();
            const currentState = states.find(state => state.name === this.value) || states[0];
            const statusEL = this.el.querySelector('.o_status_label');
            if (statusEL) {
                statusEL.innerText = currentState.state_name;
            } else {
                const labelEL = Object.assign(document.createElement('span'), {
                    innerText: currentState.state_name,
                    className: 'o_status_label align-middle',
                });
                this.el.appendChild(labelEL);
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
        var tip = this.value ? _t('Remove from Favorites') : _t('Add to Favorites');
        var template = this.attrs.nolabel ? '<a href="#"><i class="fa %s" title="%s" aria-label="%s" role="img"></i></a>' : '<a href="#"><i class="fa %s" role="img" aria-label="%s"></i> %s</a>';
        this.$el.empty().append(_.str.sprintf(template, this.value ? 'fa-star' : 'fa-star-o', tip, tip));
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
        this.$el.addClass('badge text-bg-' + labelClass).text(this._formatValue(this.value));
    },
});

var BooleanToggle = FieldBoolean.extend({
    description: _lt("Toggle"),
    className: FieldBoolean.prototype.className + ' o_boolean_toggle form-switch',
    isQuickEditable: true,
    events: {
        'click': '_onClick'
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds the icon fa-check-circle if value is true else adds icon
     * fa-times-circle
     *
     * The boolean_toggle should only be disabled when there is a readonly modifier
     * not when the view is in readonly mode
     *
     * @override
     */
    async _render() {
        await this._super(...arguments);
        const isReadonly = this.record.evalModifiers(this.attrs.modifiers).readonly || false;
        this.$input.prop('disabled', isReadonly);
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
    _onClick: async function (event) {
        event.stopPropagation();
        if (!this.$input.prop('disabled')) {
            await this._setValue(!this.value);
            this._render();
        }
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
    description: _lt("Percentage Pie"),
    template: 'FieldPercentPie',
    supportedFieldTypes: ['integer', 'float'],
    isQuickEditable: true,

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
    description: _lt("Progress Bar"),
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

        // The few next lines determine if the widget can write on the record or not
        this.editable_readonly = !!this.nodeOptions.editable_readonly;
        // "hard" readonly
        this.readonly = this.nodeOptions.readonly || !this.nodeOptions.editable;

        this.canWrite = !this.readonly && (
            this.mode === 'edit' ||
            (this.editable_readonly && this.mode === 'readonly') ||
            (this.viewType === 'kanban') // Keep behavior before commit
        );

        // Boolean to toggle if we edit the numerator (value) or the denominator (max_value)
        this.edit_max_value = !!this.nodeOptions.edit_max_value;
        this.max_value = this.recordData[this.nodeOptions.max_value] || 100;

        this.title = _t(this.attrs.title || this.nodeOptions.title) || '';

        // Ability to edit the field through the bar
        // /!\ this feature is disabled
        this.enableBarAsInput = false;
        this.edit_on_click = this.enableBarAsInput && this.mode === 'readonly' && !this.edit_max_value;

        this.write_mode = false;
    },
    _render: function () {
        var self = this;
        this._render_value();

        if (this.canWrite) {
            if (this.edit_on_click) {
                this.$el.on('click', '.o_progress', function (e) {
                    var $target = $(e.currentTarget);
                    var numValue = Math.floor((e.pageX - $target.offset().left) / $target.outerWidth() * self.max_value);
                    self.on_update(numValue);
                    self._render_value();
                });
            } else {
                this.$el.on('click', function () {
                    if (!self.write_mode) {
                        var $input = $('<input>', {type: 'text', class: 'o_progressbar_value o_input'});
                        $input.on('blur', self.on_change_input.bind(self));
                        self.$('.o_progressbar_value').replaceWith($input);
                        self.write_mode = true;
                        self._render_value();
                    }
                });
            }
        }
        return this._super();
    },
    /**
     * Updates the widget with value
     *
     * @param {Number} value
     */
    on_update: function (value) {
        if (this.edit_max_value) {
            this.max_value = value;
            this._isValid = true;
            var changes = {};
            changes[this.nodeOptions.max_value] = this.max_value;
            this.trigger_up('field_changed', {
                dataPointID: this.dataPointID,
                changes: changes,
            });
        } else {
            // _setValues accepts string and will parse it
            var formattedValue = this._formatValue(value);
            this._setValue(formattedValue);
        }
    },
    on_change_input: function (e) {
        var $input = $(e.target);
        if (e.type === 'change' && !$input.is(':focus')) {
            return;
        }

        var parsedValue;
        try {
            // Cover all numbers with parseFloat
            parsedValue = field_utils.parse.float($input.val());
        } catch (_error) {
            this.displayNotification({ message: _t("Please enter a numerical value"), type: 'danger' });
        }

        if (parsedValue !== undefined) {
            if (e.type === 'input') { // ensure what has just been typed in the input is a number
                // returns NaN if not a number
                this._render_value(parsedValue);
                if (parsedValue === 0) {
                    $input.select();
                }
            } else { // Implicit type === 'blur': we commit the value
                if (this.edit_max_value) {
                    parsedValue = parsedValue || 100;
                }

                var $div = $('<div>', {class: 'o_progressbar_value'});
                this.$('.o_progressbar_value').replaceWith($div);
                this.write_mode = false;

                this.on_update(parsedValue);
                this._render_value();
            }
        }
    },
    /**
     * Renders the value
     *
     * @private
     * @param {Number} v
     */
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

        this.$('.o_progress').toggleClass('o_progress_overflow', value > max_value)
            .attr('aria-valuemin', '0')
            .attr('aria-valuemax', max_value)
            .attr('aria-valuenow', value);
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

var JournalDashboardGraph = AbstractField.extend({
    className: "o_dashboard_graph",
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
    init: function () {
        this._super.apply(this, arguments);
        this.graph_type = this.attrs.graph_type;
        this.data = JSON.parse(this.value);
    },
    /**
     * The widget view uses the ChartJS lib to render the graph. This lib
     * requires that the rendering is done directly into the DOM (so that it can
     * correctly compute positions). However, the views are always rendered in
     * fragments, and appended to the DOM once ready (to prevent them from
     * flickering). We here use the on_attach_callback hook, called when the
     * widget is attached to the DOM, to perform the rendering. This ensures
     * that the rendering is always done in the DOM.
     */
    on_attach_callback: function () {
        this._isInDOM = true;
        this._renderInDOM();
    },
    /**
     * Called when the field is detached from the DOM.
     */
    on_detach_callback: function () {
        this._isInDOM = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render the widget only when it is in the DOM.
     *
     * @override
     * @private
     */
    _render: function () {
        if (this._isInDOM) {
            return this._renderInDOM();
        }
        return Promise.resolve();
    },
    /**
     * Render the widget. This function assumes that it is attached to the DOM.
     *
     * @private
     */
    _renderInDOM: function () {
        this.$el.empty();
        var config, cssClass;
        if (this.graph_type === 'line') {
            config = this._getLineChartConfig();
            cssClass = 'o_graph_linechart';
        } else if (this.graph_type === 'bar') {
            config = this._getBarChartConfig();
            cssClass = 'o_graph_barchart';
        }
        this.$canvas = $('<canvas/>');
        this.$el.addClass(cssClass);
        this.$el.empty();
        this.$el.append(this.$canvas);
        var context = this.$canvas[0].getContext('2d');
        this.chart = new Chart(context, config);
    },
    _getLineChartConfig: function () {
        var labels = this.data[0].values.map(function (pt) {
            return pt.x;
        });
        var borderColor = this.data[0].is_sample_data ? '#dddddd' : '#875a7b';
        var backgroundColor = this.data[0].is_sample_data ? '#ebebeb' : '#dcd0d9';
        return {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: this.data[0].values,
                    fill: 'start',
                    label: this.data[0].key,
                    backgroundColor: backgroundColor,
                    borderColor: borderColor,
                    borderWidth: 2,
                }]
            },
            options: {
                legend: {display: false},
                scales: {
                    yAxes: [{display: false}],
                    xAxes: [{display: false}]
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001
                    }
                },
                tooltips: {
                    intersect: false,
                    position: 'nearest',
                    caretSize: 0,
                },
            },
        };
    },
    _getBarChartConfig: function () {
        var data = [];
        var labels = [];
        var backgroundColor = [];

        this.data[0].values.forEach(function (pt) {
            data.push(pt.value);
            labels.push(pt.label);
            var color = pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : '#ebebeb');
            backgroundColor.push(color);
        });
        return {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    fill: 'start',
                    label: this.data[0].key,
                    backgroundColor: backgroundColor,
                }]
            },
            options: {
                legend: {display: false},
                scales: {
                    yAxes: [{display: false}],
                },
                maintainAspectRatio: false,
                tooltips: {
                    intersect: false,
                    position: 'nearest',
                    caretSize: 0,
                },
                elements: {
                    line: {
                        tension: 0.000001
                    }
                },
            },
        };
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
    resetOnAnyFieldChange: true,
    events: _.extend({}, AbstractField.prototype.events, {
        "click .o_domain_show_selection_button": "_onShowSelectionButtonClick",
        "click .o_field_domain_dialog_button": "_onDialogEditButtonClick",
        "click .o_refresh_count": "_onRefreshCountClick",
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

        this._isValidForModel = true;
        this.nbRecords = null;
        this.lastCountFetchKey = null; // used to prevent from unnecessary fetching the count
        this.debugEdition = false; // true iff the domain was edited with the textarea (in debug only)
    },
    /**
     * We use the on_attach_callback hook here when widget is attached to the DOM, so that
     * the inline 'DomainSelector' widget allows field selector to overflow if widget is
     * attached within a modal.
     */
    on_attach_callback() {
        if (this.domainSelector && !this.inDialog) {
            this.domainSelector.on_attach_callback();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * The record is about to be saved, we need to ensure that the current
     * domain is valid, if we manually edited it with the textarea. To do so,
     * we perform a search_count with that domain.
     *
     * @override
     * @returns {Promise|undefined}
     */
    commitChanges() {
        if (this.debugEdition) {
            return this._fetchCount();
        }
    },
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
     * Fetches the number of records matching the current domain.
     *
     * @private
     * @param {boolean} [force=false] if true, performs the rpc, even if the
     *   domain is the same as before
     * @returns {Promise}
     */
     _fetchCount(force = false) {
        if (!this._domainModel) {
            this._isValidForModel = true;
            this.nbRecords = 0;
            return Promise.resolve();
        }

        // do not re-fetch the count if nothing has changed
        const value = this.value || "[]"; // false stands for the empty domain
        const key = `${this._domainModel}/${value}`;
        if (!force && this.lastCountFetchKey === key) {
            return this.lastCountFetchProm;
        }
        this.lastCountFetchKey = key;

        this.nbRecords = null;

        const context = this.record.getContext({ fieldName: this.name });
        this.lastCountFetchProm = new Promise((resolve) => {
            this._rpc({
                model: this._domainModel,
                method: 'search_count',
                args: [Domain.prototype.stringToArray(value, this.record.evalContext)],
                context: context
            }, { shadow: true }).then((nbRecords) => {
                this._isValidForModel = true;
                this.nbRecords = nbRecords;
                resolve();
            }).guardedCatch((reason) => {
                reason.event.preventDefault(); // prevent traceback (the search_count might be intended to break)
                this._isValidForModel = false;
                this.nbRecords = 0;
                resolve();
            });
        });
        return this.lastCountFetchProm;
    },
    /**
     * @private
     * @override _render from AbstractField
     * @returns {Promise}
     */
    _render: async function () {
        // If there is no model, only change the non-domain-selector content
        if (!this._domainModel) {
            this._replaceContent();
            return Promise.resolve();
        }

        // Convert char value to array value
        var value = this.value || "[]";

        // Create the domain selector or change the value of the current one...
        var def;
        if (!this.domainSelector) {
            this.domainSelector = new DomainSelector(this, this._domainModel, value, {
                readonly: this.mode === "readonly" || this.inDialog,
                filters: this.fsFilters,
                debugMode: config.isDebug(),
            });
            def = this.domainSelector.prependTo(this.$el);
        } else if (!this.debugEdition) {
            // do not update the domainSelector if we edited the domain with the textarea
            // as we don't want it to format what we just wrote
            def = this.domainSelector.setDomain(value);
        }

        // ... then replace the other content (matched records, etc)
        await Promise.resolve(def);
        this._replaceContent();

        // Finally, fetch the number of records matching the domain, but do not
        // wait for it to render the field widget (simply update the number of
        // records when we know it)
        if (!this.debugEdition) {
            // do not automatically recompute the count if we're editing the
            // domain with the textarea
            this._fetchCount().then(() => this._replaceContent());
        }
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
            nbRecords: this.nbRecords,
            inDialog: this.inDialog,
            editMode: this.mode === "edit",
            isDebug: config.isDebug(),
        }));
        this._$content.appendTo(this.$el);
    },
    /**
     * @override _reset from AbstractField
     * Check if the model the field works with has (to be) changed.
     *
     * @private
     */
    _reset: function (record, ev) {
        this._super.apply(this, arguments);
        var oldDomainModel = this._domainModel;
        this._setState();
        if (this.domainSelector && this._domainModel !== oldDomainModel) {
            // If the model has changed, destroy the current domain selector
            this.domainSelector.destroy();
            this.domainSelector = null;
        }
        if (!ev || ev.target !== this) {
            this.debugEdition = false;
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
        let domainModel = this.nodeOptions.model;
        if (Object.prototype.hasOwnProperty.call(this.record.data, domainModel)) {
            domainModel = this.record.data[domainModel];
        }
        this._domainModel = domainModel;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Recompute the number of records matching the domain when the user clicks
     * on the refresh button. Useful after manually editing the domain through
     * the textarea in debug mode, as in this case, the count isn't automatically
     * recomputed.
     *
     * @param {MouseEvent} ev
     */
    async _onRefreshCountClick(ev) {
        ev.stopPropagation();
        ev.currentTarget.setAttribute("disabled", "disabled");
        await this._fetchCount(true);
        this._replaceContent();
    },
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
            context: this.record.getContext({fieldName: this.name, viewType: this.viewType}),
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
            debugMode: config.isDebug(),
        }).open();
    },
    /**
     * Called when the domain selector value is changed
     * -> Adapt the internal value state
     *
     * @param {OdooEvent} e
     * @param {Domain} e.data.domain
     */
    _onDomainSelectorValueChange: function (e) {
        // we don't want to recompute the count if the domain has been edited
        // from the debug textarea (for performance reasons, as it might be costly)
        this.debugEdition = !!e.data.debug;
        this._setValue(e.data.domain);
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
    /**
     * Stops the enter navigation in a DomainSelector's textarea.
     *
     * @private
     * @param {OdooEvent} ev
     */
     _onKeydown: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER && ev.target.tagName === "TEXTAREA") {
            ev.stopPropagation();
            return;
        }
        this._super.apply(this, arguments);
    },
});

/**
 * This widget is intended to be used on Text fields. It will provide Ace Editor
 * for editing XML and Python.
 */
var AceEditor = DebouncedField.extend({
    template: "AceEditor",
    jsLibs: [
        '/web/static/lib/ace/ace.js',
        [
            '/web/static/lib/ace/mode-python.js',
            '/web/static/lib/ace/mode-xml.js',
            '/web/static/lib/ace/mode-qweb.js'
        ]
    ],
    events: {}, // events are triggered manually for this debounced widget
    /**
     * @override start from AbstractField (Widget)
     *
     * @returns {Promise}
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
        this._super.apply(this, arguments);
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
        const mode = this.nodeOptions.mode || 'qweb';
        this.aceSession.setOptions({
            useWorker: false,
            mode: "ace/mode/" + (mode === 'xml' ? 'qweb' : mode),
            tabSize: 2,
            useSoftTabs: true,
        });
        if (this.mode === "edit") {
            this.aceEditor.on("change", this._doDebouncedAction.bind(this));
            this.aceEditor.on("blur", this._doAction.bind(this));
        }
    },
});


/**
 * The FieldColor widget give a visual representation of a color
 * Clicking on it bring up an instance of ColorpickerDialog
 */
var FieldColor = AbstractField.extend({
    template: 'FieldColor',
    events: _.extend({}, AbstractField.prototype.events, {
        'click .o_field_color': '_onColorClick',
    }),
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        'colorpicker:saved': '_onColorpickerSaved',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getFocusableElement: function () {
        return this.$('.o_field_color');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
    * @override
    * @private
    */
    _render: function () {
        this.$('.o_field_color').data('value', this.value)
            .css('background-color', this.value)
            .attr('title', this.value);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
    * @private
    */
    _onColorClick: function () {
        if (this.mode === 'edit') {
            const dialog = new ColorpickerDialog(this, {
                defaultColor: this.value,
                noTransparency: true,
            }).open();
            dialog.on('closed', this, () => {
                // we need to wait for the modal to execute its whole close function.
                Promise.resolve().then(() => {
                    this.getFocusableElement().focus();
                });
            });
        }
    },

    /**
    * @private
    * @param {OdooEvent} ev
    */
    _onColorpickerSaved: function (ev) {
        this._setValue(ev.data.hex);
    },

    /**
     * @override
     * @private
     */
    _onKeydown: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER) {
            ev.preventDefault();
            ev.stopPropagation();
            this._onColorClick(ev);
        } else {
            this._super.apply(this, arguments);
        }
    },
});

var FieldColorPicker = FieldInteger.extend({
    RECORD_COLORS: [
        _t('No color'),
        _t('Red'),
        _t('Orange'),
        _t('Yellow'),
        _t('Light blue'),
        _t('Dark purple'),
        _t('Salmon pink'),
        _t('Medium blue'),
        _t('Dark blue'),
        _t('Fushia'),
        _t('Green'),
        _t('Purple'),
    ],
    widthInList: '1',
    /**
     * Prepares the rendering, since we are based on an input but not using it
     * setting tagName after parent init force the widget to not render an input
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.tagName = 'div';
    },
    /**
     * Render the widget when it is edited.
     *
     * @override
     */
    _renderEdit: function () {
        this.$el.html(qweb.render('ColorPicker'));
        this._setupColorPicker();
        this._highlightSelectedColor();
    },
    /**
     * Render the widget when it is NOT edited.
     *
     * @override
     */
    _renderReadonly: function () {
        var selectedColorName = this.RECORD_COLORS[this.value];
        this.$el.html(qweb.render('ColorPickerReadonly', { active_color: this.value, name_color: selectedColorName }));
        this.$el.on('click', 'a', function(ev){ ev.preventDefault(); });
    },
    /**
     * Render the kanban colors inside first ul element.
     * This is the same template as in KanbanRecord.
     *
     * <a> elements click are bound to _onColorChanged
     *
     */
    _setupColorPicker: function () {
        var $colorpicker = this.$('ul');
        if (!$colorpicker.length) {
            return;
        }
        $colorpicker.html(qweb.render('web.Legacy.KanbanColorPicker', { colors: this.RECORD_COLORS }));
        $colorpicker.on('click', 'a', this._onColorChanged.bind(this));
    },
    /**
     * Returns the widget value.
     * Since NumericField is based on an input, but we don't use it,
     * we override this function to use the internal value of the widget.
     *
     *
     * @override
     * @returns {string}
     */
    _getValue: function (){
        return this.value;
    },
    /**
     * Listener in edit mode for click on a color.
     * The actual color can be found in the data-color
     * attribute of the target element.
     *
     * We re-render the widget after the update because
     * the selected color has changed and it should
     * be reflected in the ui.
     *
     * @param ev
     */
    _onColorChanged: function(ev) {
        ev.preventDefault();
        var color = null;
        if(ev.currentTarget && ev.currentTarget.dataset && ev.currentTarget.dataset.color){
            color = ev.currentTarget.dataset.color;
        }
        if(color){
            this.value = color;
            this._onChange();
            this._renderEdit();
        }
    },
    /**
     * Helper to modify the active color's style
     * while in edit mode.
     *
     */
    _highlightSelectedColor: function(){
        try{
            $(this.$('li')[parseInt(this.value)]).css('border', '2px solid teal');
        } catch(_err) {

        }
    },
    _onNavigationMove() {
        // disable navigation from FieldInput, to prevent a crash
    }
});

return {
    TranslatableFieldMixin: TranslatableFieldMixin,
    DynamicPlaceholderFieldMixin: DynamicPlaceholderFieldMixin,
    DebouncedField: DebouncedField,
    FieldEmail: FieldEmail,
    FieldBinaryFile: FieldBinaryFile,
    FieldPdfViewer: FieldPdfViewer,
    AbstractFieldBinary: AbstractFieldBinary,
    FieldBinaryImage: FieldBinaryImage,
    KanbanFieldBinaryImage: KanbanFieldBinaryImage,
    CharImageUrl: CharImageUrl,
    KanbanCharImageUrl: KanbanCharImageUrl,
    FieldBoolean: FieldBoolean,
    BooleanToggle: BooleanToggle,
    FieldChar: FieldChar,
    FieldDate: FieldDate,
    FieldDateTime: FieldDateTime,
    FieldDateRange: FieldDateRange,
    RemainingDays: RemainingDays,
    FieldDomain: FieldDomain,
    FieldFloat: FieldFloat,
    FieldFloatTime: FieldFloatTime,
    FieldFloatFactor: FieldFloatFactor,
    FieldFloatToggle: FieldFloatToggle,
    FieldPercentage: FieldPercentage,
    FieldInteger: FieldInteger,
    FieldMonetary: FieldMonetary,
    FieldPercentPie: FieldPercentPie,
    FieldPhone: FieldPhone,
    FieldProgressBar: FieldProgressBar,
    FieldText: FieldText,
    ListFieldText: ListFieldText,
    FieldToggleBoolean: FieldToggleBoolean,
    HandleWidget: HandleWidget,
    InputField: InputField,
    NumericField: NumericField,
    AttachmentImage: AttachmentImage,
    LabelSelection: LabelSelection,
    StateSelectionWidget: StateSelectionWidget,
    ListStateSelectionWidget: ListStateSelectionWidget,
    FavoriteWidget: FavoriteWidget,
    PriorityWidget: PriorityWidget,
    StatInfo: StatInfo,
    UrlWidget: UrlWidget,
    ButtonCopyClipboard: ButtonCopyClipboard,
    TextCopyClipboard: TextCopyClipboard,
    CharCopyClipboard: CharCopyClipboard,
    URLCopyClipboard: URLCopyClipboard,
    JournalDashboardGraph: JournalDashboardGraph,
    AceEditor: AceEditor,
    FieldColor: FieldColor,
    FieldColorPicker: FieldColorPicker,
};

});
