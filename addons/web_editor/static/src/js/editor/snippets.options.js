odoo.define('web_editor.snippets.options', function (require) {
'use strict';

var core = require('web.core');
const ColorpickerDialog = require('web.ColorpickerDialog');
const time = require('web.time');
var Widget = require('web.Widget');
var ColorPaletteWidget = require('web_editor.ColorPalette').ColorPaletteWidget;
const weUtils = require('web_editor.utils');
var weWidgets = require('wysiwyg.widgets');
const MutexedDropPrevious = require('web.concurrency').MutexedDropPrevious;

var qweb = core.qweb;
var _t = core._t;

/**
 * @param {HTMLElement} el
 * @param {string} [title]
 * @param {Object} [options]
 * @param {string[]} [options.classes]
 * @param {Object} [options.dataAttributes]
 * @returns {HTMLElement} - the original 'el' argument
 */
function _addTitleAndAllowedAttributes(el, title, options) {
    if (title) {
        const titleEl = _buildTitleElement(title);
        el.appendChild(titleEl);
    }

    if (options && options.classes) {
        el.classList.add(...options.classes);
    }
    if (options && options.dataAttributes) {
        for (const key in options.dataAttributes) {
            el.dataset[key] = options.dataAttributes[key];
        }
    }

    return el;
}
/**
 * @param {string} tagName
 * @param {string} title - @see _addTitleAndAllowedAttributes
 * @param {Object} options - @see _addTitleAndAllowedAttributes
 * @returns {HTMLElement}
 */
function _buildElement(tagName, title, options) {
    const el = document.createElement(tagName);
    return _addTitleAndAllowedAttributes(el, title, options);
}
/**
 * @param {string} title
 * @returns {HTMLElement}
 */
function _buildTitleElement(title) {
    const titleEl = document.createElement('we-title');
    titleEl.textContent = title;
    return titleEl;
}
/**
 * Build the correct DOM for a we-row element.
 *
 * @param {string} [title] - @see _buildElement
 * @param {Object} [options] - @see _buildElement
 * @param {HTMLElement[]} [options.childNodes]
 * @returns {HTMLElement}
 */
function _buildRowElement(title, options) {
    const groupEl = _buildElement('we-row', title, options);

    const rowEl = document.createElement('div');
    groupEl.appendChild(rowEl);

    if (options && options.childNodes) {
        options.childNodes.forEach(node => rowEl.appendChild(node));
    }

    return groupEl;
}
/**
 * Creates a proxy for an object where one property is replaced by a different
 * value. This value is captured in the closure and can be read and written to.
 *
 * @param {Object} obj - the object for which to create a proxy
 * @param {string} propertyName - the name/key of the property to replace
 * @param {*} value - the initial value to give to the property's copy
 * @returns {Proxy} a proxy of the object with the property replaced
 */
function createPropertyProxy(obj, propertyName, value) {
    return new Proxy(obj, {
        get: function (obj, prop) {
            if (prop === propertyName) {
                return value;
            }
            return obj[prop];
        },
        set: function (obj, prop, val) {
            if (prop === propertyName) {
                return (value = val);
            }
            return Reflect.set(...arguments);
        },
    });
}

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * Base class for components to be used in snippet options widgets to retrieve
 * user values.
 */
const UserValueWidget = Widget.extend({
    className: 'o_we_user_value_widget',
    custom_events: {
        'user_value_change': '_onUserValueNotification',
        'user_value_preview': '_onUserValueNotification',
        'user_value_reset': '_onUserValueNotification',
    },

    /**
     * @constructor
     */
    init: function (parent, title, options, $target) {
        this._super(...arguments);
        this.title = title;
        this.options = options;
        this._userValueWidgets = [];
        this._value = '';
        this.$target = $target;
    },
    /**
     * @override
     */
    _makeDescriptive: function () {
        const $el = this._super(...arguments);
        _addTitleAndAllowedAttributes($el[0], this.title, this.options);
        this.containerEl = document.createElement('div');
        $el.append(this.containerEl);
        return $el;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Closes the widget (only meaningful for widgets that can be closed).
     */
    close: function () {
        this._userValueWidgets.forEach(widget => widget.close());
    },
    /**
     * @param {string} name
     * @returns {UserValueWidget|null}
     */
    findWidget: function (name) {
        for (const widget of this._userValueWidgets) {
            if (widget.getName() === name) {
                return widget;
            }
            const depWidget = widget.findWidget(name);
            if (depWidget) {
                return depWidget;
            }
        }
        return null;
    },
    /**
     * Returns the value that the widget would hold if it was active, by default
     * the internal value it holds.
     *
     * @param {string} [methodName]
     * @returns {string}
     */
    getActiveValue: function (methodName) {
        return this._value;
    },
    /**
     * Returns the default value the widget holds when inactive, by default the
     * first "possible value".
     *
     * @param {string} [methodName]
     * @returns {string}
     */
    getDefaultValue: function (methodName) {
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        return possibleValues && possibleValues[0] || '';
    },
    /**
     * @returns {string[]}
     */
    getDependencies: function () {
        return this._dependencies;
    },
    /**
     * Returns the names of the option methods associated to the widget. Those
     * are loaded with @see loadMethodsData.
     *
     * @returns {string[]}
     */
    getMethodsNames: function () {
        return this._methodsNames;
    },
    /**
     * Returns the option parameters associated to the widget (for a given
     * method name or not). Most are loaded with @see loadMethodsData.
     *
     * @param {string} [methodName]
     * @returns {Object}
     */
    getMethodsParams: function (methodName) {
        const params = _.extend({}, this._methodsParams);
        if (methodName) {
            params.possibleValues = params.optionsPossibleValues[methodName] || [];
            params.activeValue = this.getActiveValue(methodName);
            params.defaultValue = this.getDefaultValue(methodName);
        }
        return params;
    },
    /**
     * @returns {string} empty string if no name is used by the widget
     */
    getName: function () {
        return this._methodsParams.name || '';
    },
    /**
     * Returns the user value that the widget currently holds. The value is a
     * string, this is the value that will be received in the option methods
     * of SnippetOptionWidget instances.
     *
     * @param {string} [methodName]
     * @returns {string}
     */
    getValue: function (methodName) {
        const isActive = this.isActive();
        if (!methodName || !this._methodsNames.includes(methodName)) {
            return isActive ? 'true' : '';
        }
        if (isActive) {
            return this.getActiveValue(methodName);
        }
        return this.getDefaultValue(methodName);
    },
    /**
     * Returns whether or not the widget is active (holds a value).
     *
     * @returns {boolean}
     */
    isActive: function () {
        return !!this._value;
    },
    /**
     * Indicates if the widget can contain sub user value widgets or not.
     *
     * @returns {boolean}
     */
    isContainer: function () {
        return false;
    },
    /**
     * Indicates if the widget is being previewed or not: the user is
     * manipulating it. Base case: if an internal <input/> element is focused.
     *
     * @returns {boolean}
     */
    isPreviewed: function () {
        const focusEl = document.activeElement;
        if (focusEl && focusEl.tagName === 'INPUT'
                && (this.el === focusEl || this.el.contains(focusEl))
                && !this._validating) {
            return true;
        }
        return this.el.classList.contains('o_we_preview');
    },
    /**
     * Loads option method names and option method parameters.
     *
     * @param {string[]} validMethodNames
     * @param {Object} extraParams
     */
    loadMethodsData: function (validMethodNames, extraParams) {
        this._methodsNames = [];
        this._methodsParams = _.extend({}, extraParams);
        this._methodsParams.optionsPossibleValues = {};
        this._dependencies = [];

        for (const key in this.el.dataset) {
            const dataValue = this.el.dataset[key].trim();

            if (key === 'dependencies') {
                this._dependencies.push(...dataValue.split(/\s*,\s*/g));
            } else if (validMethodNames.includes(key)) {
                this._methodsNames.push(key);
                this._methodsParams.optionsPossibleValues[key] = dataValue.split(/\s*\|\s*/g);
            } else {
                this._methodsParams[key] = dataValue;
            }
        }
        this._userValueWidgets.forEach(widget => {
            const inheritedParams = _.extend({}, this._methodsParams);
            inheritedParams.optionsPossibleValues = null;
            widget.loadMethodsData(validMethodNames, inheritedParams);
            const subMethodsNames = widget.getMethodsNames();
            const subMethodsParams = widget.getMethodsParams();

            for (const methodName of subMethodsNames) {
                if (!this._methodsNames.includes(methodName)) {
                    this._methodsNames.push(methodName);
                    this._methodsParams.optionsPossibleValues[methodName] = [];
                }
                for (const subPossibleValue of subMethodsParams.optionsPossibleValues[methodName]) {
                    this._methodsParams.optionsPossibleValues[methodName].push(subPossibleValue);
                }
            }
        });
        for (const methodName of this._methodsNames) {
            const arr = this._methodsParams.optionsPossibleValues[methodName];
            const uniqArr = arr.filter((v, i, arr) => i === arr.indexOf(v));
            this._methodsParams.optionsPossibleValues[methodName] = uniqArr;
        }
    },
    /**
     * Adds the given widget to the known list of user value sub-widgets (useful
     * for container widgets).
     *
     * @param {UserValueWidget} widget
     */
    registerSubWidget: function (widget) {
        this._userValueWidgets.push(widget);
    },
    /**
     * Sets the user value that the widget should currently hold, for the
     * given method name.
     *
     * Note: a widget typically only holds one value for the only method it
     * supports. However, widgets can have several methods; in that case, the
     * value is typically received for a first method and receiving the value
     * for other ones should not affect the widget (otherwise, it means the
     * methods are conflicting with each other).
     *
     * @param {string} value
     * @param {string} [methodName]
     */
    setValue: function (value, methodName) {
        this._value = value;
    },
    /**
     * @param {boolean} show
     */
    toggleVisibility: function (show) {
        this.el.classList.toggle('d-none', !show);
    },
    /**
     * Updates the UI to match the user value the widget currently holds, only
     * if the UI can currently be updated.
     *
     * Note: this method is only needed if @see setValue can make the widget
     * hold a value which is not synchronized with its current UI (for focus
     * reasons or other ones) or if the widget is not one capable of holding
     * a value (but may have an UI which depends on other elements).
     *
     * @todo if the UI cannot be updated, we do nothing while it should ideally
     *       updates as soon as it can be.
     * @param {boolean} [force=false]
     * @returns {Promise}
     */
    updateUI: async function (force) {
        if (force || !this.isPreviewed()) {
            await this._updateUI();
        }
        this._validating = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {boolean} [previewMode=false]
     */
    _notifyValueChange: function (previewMode) {
        if (!this._methodsNames.length) {
            return;
        }

        const data = {
            widget: this,
        };
        switch (previewMode) {
            case undefined:
            case false: {
                this.trigger_up('user_value_change', data);
                break;
            }
            case true: {
                // TODO improve this. The preview state has to be updated only
                // when the actual option _select is gonna be called... but this
                // is delayed by a mutex. So, during test tours, we would notify
                // both 'preview' and 'reset' before the 'preview' handling is
                // done: and so the widget would be considered not in preview
                // during that preview action handling.
                data.prepare = () => this.el.classList.add('o_we_preview');
                this.trigger_up('user_value_preview', data);
                break;
            }
            default: {
                // TODO improve this. The preview state has to be updated only
                // when the actual option _select is gonna be called... but this
                // is delayed by a mutex. So, during test tours, we would notify
                // both 'preview' and 'reset' before the 'preview' handling is
                // done: and so the widget would be considered not in preview
                // during that preview action handling.
                data.prepare = () => this.el.classList.remove('o_we_preview');
                this.trigger_up('user_value_reset', data);
            }
        }
    },
    /**
     * Updates the UI to match the user value the widget currently holds (this
     * method is called by @see updateUI and does not perform a check to verify
     * if the UI can be updated).
     *
     * @private
     * @returns {Promise}
     */
    _updateUI: async function () {
        this.el.classList.remove('o_we_preview');
        const proms = this._userValueWidgets.map(widget => widget.updateUI(true));
        return Promise.all(proms);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Should be called when an user event on the widget indicates a value
     * change.
     *
     * @private
     * @param {Event} ev
     */
    _onUserValueChange: function (ev) {
        if (ev.isDefaultPrevented()) {
            return;
        }
        if (!this.isPreviewed()) {
            this._onUserValuePreview(ev);
        }
        ev.preventDefault();

        this._notifyValueChange(false);
    },
    /**
     * Allows container widgets to add additional data if needed.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onUserValueNotification: function (ev) {
        ev.data.widget = this;
    },
    /**
     * Should be called when an user event on the widget indicates a value
     * preview.
     *
     * @private
     * @param {Event} ev
     */
    _onUserValuePreview: function (ev) {
        if (ev.isDefaultPrevented()) {
            return;
        }
        ev.preventDefault();

        this._notifyValueChange(true);
    },
    /**
     * Should be called when an user event on the widget indicates a value
     * reset.
     *
     * @private
     * @param {Event} ev
     */
    _onUserValueReset: function (ev) {
        if (!this.isPreviewed()) {
            return;
        }
        if (ev.isDefaultPrevented()) {
            return;
        }
        ev.preventDefault();

        this._notifyValueChange('reset');
    },
});

const ButtonUserValueWidget = UserValueWidget.extend({
    tagName: 'we-button',
    events: {
        'click': '_onUserValueChange',
        'mouseenter': '_onUserValuePreview',
        'mouseleave': '_onUserValueReset',
    },

    /**
     * @override
     */
    start: function (parent, title, options) {
        if (this.options && this.options.childNodes) {
            this.options.childNodes.forEach(node => this.containerEl.appendChild(node));
        }

        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getActiveValue: function (methodName) {
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        return possibleValues && possibleValues[possibleValues.length - 1] || '';
    },
    /**
     * @override
     */
    isActive: function () {
        return (this.isPreviewed() !== this.el.classList.contains('active'));
    },
    /**
     * @override
     */
    loadMethodsData: function (validMethodNames) {
        this._super.apply(this, arguments);
        for (const methodName of this._methodsNames) {
            const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
            if (possibleValues.length <= 1) {
                possibleValues.unshift('');
            }
        }
    },
    /**
     * @override
     */
    setValue: function (value, methodName) {
        let active = !!value;
        if (methodName) {
            if (!this._methodsNames.includes(methodName)) {
                return;
            }
            active = (this.getActiveValue(methodName) === value);
        }
        this.el.classList.toggle('active', active);
    },
});

const CheckboxUserValueWidget = ButtonUserValueWidget.extend({
    className: (ButtonUserValueWidget.prototype.className || '') + ' o_we_checkbox_wrapper',

    /**
     * @override
     */
    start: function () {
        const checkboxEl = document.createElement('we-checkbox');
        this.containerEl.appendChild(checkboxEl);

        return this._super(...arguments);
    },
});

const SelectUserValueWidget = UserValueWidget.extend({
    tagName: 'we-select',
    events: {
        'click': '_onClick',
    },

    /**
     * @override
     */
    start: function () {
        if (this.options && this.options.valueEl) {
            this.containerEl.appendChild(this.options.valueEl);
        }

        this.menuTogglerEl = document.createElement('we-toggler');
        this.containerEl.appendChild(this.menuTogglerEl);

        this.menuEl = document.createElement('we-select-menu');
        if (this.options && this.options.childNodes) {
            this.options.childNodes.forEach(node => this.menuEl.appendChild(node));
        }
        this.containerEl.appendChild(this.menuEl);

        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close: function () {
        this._super(...arguments);
        this.menuTogglerEl.classList.remove('active');
    },
    /**
     * @override
     */
    getValue: function (methodName) {
        let activeWidget = this._userValueWidgets.find(widget => widget.isPreviewed());
        if (!activeWidget) {
            activeWidget = this._userValueWidgets.find(widget => widget.isActive());
        }
        if (activeWidget) {
            return activeWidget.getActiveValue(methodName);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    isContainer: function () {
        return true;
    },
    /**
     * @override
     */
    isPreviewed: function () {
        return this._super(...arguments) || this.menuTogglerEl.classList.contains('active');
    },
    /**
     * @override
     */
    setValue: function (value, methodName) {
        this._userValueWidgets.forEach(widget => {
            widget.setValue('__NULL__', methodName);
        });
        for (const widget of [...this._userValueWidgets].reverse()) {
            widget.setValue(value, methodName);
            if (widget.isActive()) {
                // Only one select item can be true at a time, we consider the
                // last one if multiple would be active.
                return;
            }
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateUI: async function () {
        await this._super(...arguments);
        const activeWidget = this._userValueWidgets.find(widget => !widget.isPreviewed() && widget.isActive());
        this.menuTogglerEl.textContent = activeWidget ? activeWidget.el.textContent : "/";
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the select is clicked anywhere -> open/close it.
     *
     * @private
     */
    _onClick: function () {
        if (!this.menuTogglerEl.classList.contains('active')) {
            this.trigger_up('user_value_widget_opening');
        }
        this.menuTogglerEl.classList.toggle('active');
    },
});

const InputUserValueWidget = UserValueWidget.extend({
    tagName: 'we-input',
    events: {
        'input input': '_onInputInput',
        'blur input': '_onInputBlur',
        'keydown input': '_onInputKeydown',
    },

    /**
     * @override
     */
    start: function () {
        const unit = this.el.dataset.unit || '';
        this.el.dataset.unit = unit;
        if (this.el.dataset.saveUnit === undefined) {
            this.el.dataset.saveUnit = unit;
        }

        this.inputEl = document.createElement('input');
        this.inputEl.setAttribute('type', 'text');
        this.inputEl.setAttribute('placeholder', this.el.dataset.placeholder || '');
        this.inputEl.classList.toggle('text-left', !unit);
        this.inputEl.classList.toggle('text-right', !!unit);
        this.containerEl.appendChild(this.inputEl);

        var unitEl = document.createElement('span');
        unitEl.textContent = unit;
        this.containerEl.appendChild(unitEl);

        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getActiveValue: function (methodName) {
        const activeValue = this._super(...arguments);

        const params = this._methodsParams;
        if (!params.unit) {
            return activeValue;
        }

        const defaultValue = this.getDefaultValue(methodName, false);

        return activeValue.split(/\s+/g).map(v => {
            const numValue = parseFloat(v);
            if (isNaN(numValue)) {
                return defaultValue;
            } else {
                const value = weUtils.convertNumericToUnit(numValue, params.unit, params.saveUnit, params.cssProperty, this.$target);
                return `${this._floatToStr(value)}${params.saveUnit}`;
            }
        }).join(' ');
    },
    /**
     * @override
     * @param {boolean} [useInputUnit=false]
     */
    getDefaultValue: function (methodName, useInputUnit) {
        const defaultValue = this._super(...arguments);

        const params = this._methodsParams;
        if (!params.unit) {
            return defaultValue;
        }

        const unit = useInputUnit ? params.unit : params.saveUnit;
        const numValue = weUtils.convertValueToUnit(defaultValue || '0', unit, params.cssProperty, this.$target);
        if (isNaN(numValue)) {
            return defaultValue;
        }
        return `${this._floatToStr(numValue)}${unit}`;
    },
    /**
     * @override
     */
    isActive: function () {
        const isSuperActive = this._super(...arguments);
        const params = this._methodsParams;
        if (!params.unit) {
            return isSuperActive;
        }
        return isSuperActive && parseInt(this._value) !== 0;
    },
    /**
     * @override
     */
    setValue: function (value, methodName) {
        const params = this._methodsParams;
        if (!params.unit) {
            return this._super(value, methodName);
        }

        value = value.split(' ').map(v => {
            const numValue = weUtils.convertValueToUnit(v, params.unit, params.cssProperty, this.$target);
            if (isNaN(numValue)) {
                return ''; // Something not supported
            }
            return this._floatToStr(numValue);
        }).join(' ');

        this._super(value, methodName);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateUI: async function () {
        await this._super(...arguments);
        this.inputEl.value = this._value;
    },
    /**
     * Converts a floating value to a string, rounded to 3 digits without zeros.
     *
     * @private
     * @param {number} value
     * @returns {string}
     */
    _floatToStr: function (value) {
        return `${parseFloat(value.toFixed(3))}`;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onInputInput: function (ev) {
        this._value = this.inputEl.value;
        this._onUserValuePreview(ev);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onInputBlur: function (ev) {
        // Sometimes, an input is focusout for internal reason (like an undo
        // recording) then focused again manually in the same JS stack
        // execution. In that case, the blur should not trigger an option
        // selection as the user did not leave the input. We thus defer the blur
        // handling to then check that the target is indeed still blurred before
        // executing the actual option selection.
        setTimeout(() => {
            if (ev.currentTarget === document.activeElement) {
                return;
            }
            this._onUserValueChange(ev);
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onInputKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.ENTER: {
                this._validating = true;
                this._onUserValueChange(ev);
                break;
            }
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN: {
                const input = ev.currentTarget;
                const params = this._methodsParams;
                if (!params.unit && !params.step) {
                    break;
                }
                let value = parseFloat(input.value || input.placeholder);
                if (isNaN(value)) {
                    value = 0.0;
                }
                let step = parseFloat(params.step);
                if (isNaN(step)) {
                    step = 1.0;
                }
                value += (ev.which === $.ui.keyCode.UP ? step : -step);
                input.value = this._floatToStr(value);
                $(input).trigger('input');
                break;
            }
        }
    },
});

const MultiUserValueWidget = UserValueWidget.extend({
    tagName: 'we-multi',

    /**
     * @override
     */
    start: function () {
        this.containerEl.appendChild(_buildRowElement('', this.options));
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getValue: function (methodName) {
        const value = this._userValueWidgets.map(widget => {
            return widget.getValue(methodName);
        }).join(' ').trim();

        return value || this._super(...arguments);
    },
    /**
     * @override
     */
    isContainer: function () {
        return true;
    },
    /**
     * @override
     */
    setValue: function (value, methodName) {
        let values = value.split(/\s*\|\s*/g);
        if (values.length === 1) {
            values = value.split(/\s+/g);
        }
        for (let i = 0; i < this._userValueWidgets.length - 1; i++) {
            this._userValueWidgets[i].setValue(values.shift() || '', methodName);
        }
        this._userValueWidgets[this._userValueWidgets.length - 1].setValue(values.join(' '), methodName);
    },
});

const ColorpickerUserValueWidget = SelectUserValueWidget.extend({
    className: (ButtonUserValueWidget.prototype.className || '') + ' o_we_so_color_palette',
    custom_events: {
        'color_picked': '_onColorPicked',
        'color_hover': '_onColorHovered',
        'color_leave': '_onColorLeft',
        'color_reset': '_onColorReset',
    },

    /**
     * @override
     */
    start: async function () {
        const _super = this._super.bind(this);
        const args = arguments;

        // Pre-instanciate the color palette widget
        await this._renderColorPalette();

        // Build the select element with a custom span to hold the color preview
        this.colorPreviewEl = document.createElement('span');
        this.colorPreviewEl.classList.add('o_we_color_preview');
        this.options.childNodes = [this.colorPalette.el];
        this.options.valueEl = this.colorPreviewEl;

        return _super(...args);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams: function () {
        return _.extend(this._super(...arguments), {
            colorNames: this.colorPalette.getColorNames(),
        });
    },
    /**
     * @override
     */
    getValue: function (methodName) {
        return this._previewColor || this._super(...arguments);
    },
    /**
     * @override
     */
    isContainer: function () {
        return false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Promise}
     */
    _renderColorPalette: function () {
        const options = {};
        options.selectedColor = this._value;
        if (this.options.dataAttributes.excluded) {
            options.excluded = this.options.dataAttributes.excluded.replace(/ /g, '').split(',');
        }
        const oldColorPalette = this.colorPalette;
        this.colorPalette = new ColorPaletteWidget(this, options);
        if (oldColorPalette) {
            return this.colorPalette.insertAfter(oldColorPalette.el).then(() => {
                oldColorPalette.destroy();
            });
        }
        return this.colorPalette.appendTo(document.createDocumentFragment());
    },
    /**
     * Updates the color preview + re-render the whole color palette widget.
     *
     * @override
     */
    _updateUI: async function (color) {
        await this._super(...arguments);

        this.colorPreviewEl.classList.remove(...this.colorPalette.getColorNames().map(c => 'bg-' + c));
        this.colorPreviewEl.style.removeProperty('background-color');

        if (this._value) {
            if (ColorpickerDialog.isCSSColor(this._value)) {
                this.colorPreviewEl.style.backgroundColor = this._value;
            } else {
                this.colorPreviewEl.classList.add('bg-' + this._value);
            }
        }

        await this._renderColorPalette();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a color button is clicked -> confirms the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorPicked: function (ev) {
        this._previewColor = false;
        this._value = ev.data.color;
        this._notifyValueChange(false);
    },
    /**
     * Called when a color button is entered -> previews the background color.
     *
     * @private
     * @param {Event} ev
     */
    _onColorHovered: function (ev) {
        this._previewColor = ev.data.color;
        this._notifyValueChange(true);
    },
    /**
     * Called when a color button is left -> cancels the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorLeft: function (ev) {
        this._previewColor = false;
        this._notifyValueChange('reset');
    },
    /**
     * Called when the color reset button is clicked -> removes all color
     * classes and color styles.
     *
     * @private
     */
    _onColorReset: function () {
        this._value = '';
        this._notifyValueChange(false);
    },
});

const DatetimePickerUserValueWidget = InputUserValueWidget.extend({
    events: { // Explicitely not consider all InputUserValueWidget events
        'blur input': '_onInputBlur',
        'change.datetimepicker': '_onDateTimePickerChange',
        'error.datetimepicker': '_onDateTimePickerError',
    },

    /**
     * @override
     */
    init: function () {
        this._super(...arguments);
        this._value = moment().unix().toString();
        this.__libInput = 0;
    },
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);

        const datetimePickerId = _.uniqueId('datetimepicker');
        this.inputEl.setAttribute('class', 'datetimepicker-input mx-0 text-left');
        this.inputEl.setAttribute('id', datetimePickerId);
        this.inputEl.setAttribute('data-target', '#' + datetimePickerId);

        const datepickersOptions = {
            minDate: moment({y: 1900}),
            maxDate: moment().add(200, 'y'),
            calendarWeeks: true,
            defaultDate: moment().format(),
            icons: {
                close: 'fa fa-check primary',
                today: 'far fa-calendar-check',
            },
            locale: moment.locale(),
            format: time.getLangDatetimeFormat(),
            sideBySide: true,
            buttons: {
                showClose: true,
                showToday: true,
            },
            widgetParent: 'body',

            // Open the datetimepicker on focus not on click. This allows to
            // take care of a bug which is due to the summernote editor:
            // sometimes, the datetimepicker loses the focus then get it back
            // in the same execution flow. This was making the datepicker close
            // for no apparent reason. Now, it only closes then reopens directly
            // without it be possible to notice.
            allowInputToggle: true,
        };
        this.__libInput++;
        const $input = $(this.inputEl);
        $input.datetimepicker(datepickersOptions);
        this.__libInput--;

        // Monkey-patch the library option to add custom classes on the pickers
        const libObject = $input.data('datetimepicker');
        const oldFunc = libObject._getTemplate;
        libObject._getTemplate = function () {
            const $template = oldFunc.call(this, ...arguments);
            $template.addClass('o_we_no_overlay o_we_datetimepicker');
            return $template;
        };
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isPreviewed: function () {
        return this._super(...arguments) || !!$(this.inputEl).data('datetimepicker').widget;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateUI: async function () {
        await this._super(...arguments);
        let momentObj = moment.unix(this._value);
        if (!momentObj.isValid()) {
            momentObj = moment();
        }
        this.__libInput++;
        $(this.inputEl).datetimepicker('date', momentObj);
        this.__libInput--;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onDateTimePickerChange: function (ev) {
        if (this.__libInput > 0) {
            return;
        }
        if (!ev.date || !ev.date.isValid()) {
            return;
        }
        this._value = ev.date.unix().toString();
        this._onUserValuePreview(ev);
    },
    /**
     * Prevents crash manager to throw CORS error. Note that library already
     * clears the wrong date format.
     */
    _onDateTimePickerError: function (ev) {
        ev.stopPropagation();
    },
});

const userValueWidgetsRegistry = {
    'we-button': ButtonUserValueWidget,
    'we-checkbox': CheckboxUserValueWidget,
    'we-select': SelectUserValueWidget,
    'we-input': InputUserValueWidget,
    'we-multi': MultiUserValueWidget,
    'we-colorpicker': ColorpickerUserValueWidget,
    'we-datetimepicker': DatetimePickerUserValueWidget,
};

/**
 * Handles a set of options for one snippet. The registry returned by this
 * module contains the names of the specialized SnippetOptionWidget which can be
 * referenced thanks to the data-js key in the web_editor options template.
 */
const SnippetOptionWidget = Widget.extend({
    tagName: 'we-customizeblock-option',
    custom_events: {
        'user_value_change': '_onOptionSelection',
        'user_value_preview': '_onOptionPreview',
        'user_value_reset': '_onOptionCancel',
    },
    /**
     * Indicates if the option should be displayed in the button group at the
     * top of the options panel, next to the clone/remove button.
     *
     * @type {boolean}
     */
    isTopOption: false,

    /**
     * The option `$el` is supposed to be the associated DOM UI element.
     * The option controls another DOM element: the snippet it
     * customizes, which can be found at `$target`. Access to the whole edition
     * overlay is possible with `$overlay` (this is not recommended though).
     *
     * @constructor
     */
    init: function (parent, $uiElements, $target, $overlay, data, options) {
        this._super.apply(this, arguments);

        this.$originalUIElements = $uiElements;

        this.$target = $target;
        this.$overlay = $overlay;
        this.data = data;
        this.options = options;

        this.className = 'snippet-option-' + this.data.optionName;

        this.ownerDocument = this.$target[0].ownerDocument;

        this._userValueWidgets = [];
    },
    /**
     * @override
     */
    willStart: async function () {
        await this._super(...arguments);
        return this._renderOriginalXML().then(uiFragment => {
            this.uiFragment = uiFragment;
        });
    },
    /**
     * @override
     */
    renderElement: function () {
        this._super(...arguments);
        this.el.appendChild(this.uiFragment);
        this.uiFragment = null;
    },
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * (the first time, this follows the call to the @see start method).
     *
     * @abstract
     */
    onFocus: function () {},
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * for the first time, when it is a new snippet dropped from the d&d snippet
     * menu. Note: this is called after the start and onFocus methods.
     *
     * @abstract
     */
    onBuilt: function () {},
    /**
     * Called when the parent edition overlay is removed from the associated
     * snippet (another snippet enters edition for example).
     *
     * @abstract
     */
    onBlur: function () {},
    /**
     * Called when the associated snippet is the result of the cloning of
     * another snippet (so `this.$target` is a cloned element).
     *
     * @abstract
     * @param {Object} options
     * @param {boolean} options.isCurrent
     *        true if the associated snippet is a clone of the main element that
     *        was cloned (so not a clone of a child of this main element that
     *        was cloned)
     */
    onClone: function (options) {},
    /**
     * Called when the associated snippet is moved to another DOM location.
     *
     * @abstract
     */
    onMove: function () {},
    /**
     * Called when the associated snippet is about to be removed from the DOM.
     *
     * @abstract
     */
    onRemove: function () {},
    /**
     * Called when the target is shown, only meaningful if the target was hidden
     * at some point (typically used for 'invisible' snippets).
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    onTargetShow: async function () {},
    /**
     * Called when the target is hidden (typically used for 'invisible'
     * snippets).
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    onTargetHide: async function () {},
    /**
     * Called when the template which contains the associated snippet is about
     * to be saved.
     *
     * @abstract
     * @return {Promise|undefined}
     */
    cleanForSave: async function () {},

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Default option method which allows to select one and only one class in
     * the option classes set and set it on the associated snippet. The common
     * case is having a select with each item having a `data-select-class`
     * value allowing to choose the associated class, or simply an unique
     * checkbox to allow toggling a unique class.
     *
     * @param {boolean|string} previewMode
     *        - truthy if the option is enabled for preview or if leaving it (in
     *          that second case, the value is 'reset')
     *        - false if the option should be activated for good
     * @param {string} widgetValue
     * @param {Object} params
     * @returns {Promise|undefined}
     */
    selectClass: function (previewMode, widgetValue, params) {
        for (const classNames of params.possibleValues) {
            if (classNames) {
                this.$target[0].classList.remove(...classNames.trim().split(/\s+/g));
            }
        }
        if (widgetValue) {
            this.$target[0].classList.add(...widgetValue.trim().split(/\s+/g));
        }
    },
    /**
     * Default option method which allows to select a value and set it on the
     * associated snippet as a data attribute. The name of the data attribute is
     * given by the attributeName parameter.
     *
     * @param {boolean} previewMode - @see this.selectClass
     * @param {string} widgetValue
     * @param {Object} params
     * @returns {Promise|undefined}
     */
    selectDataAttribute: function (previewMode, widgetValue, params) {
        const dataName = params.attributeName;
        if (dataName) {
            if (params.saveUnit && !params.withUnit) {
                // Values that come with an unit are saved without unit as
                // data-attribute unless told otherwise.
                widgetValue = widgetValue.split(params.saveUnit).join('');
            }
            this.$target[0].dataset[dataName] = widgetValue;
        }
        if (params.extraClass) {
            this.$target.toggleClass(params.extraClass, params.defaultValue !== widgetValue);
        }
    },
    /**
     * Default option method which allows to select a value and set it on the
     * associated snippet as a css style. The name of the css property is
     * given by the cssProperty parameter.
     *
     * @param {boolean} previewMode - @see this.selectClass
     * @param {string} widgetValue
     * @param {Object} params
     * @returns {Promise|undefined}
     */
    selectStyle: async function (previewMode, widgetValue, params) {
        if (params.cssProperty === 'background-color') {
            // Need a way for event handlers to signal that they need this code to wait.
            // Can't just wait blindly because there might be no event listener for this event
            await new Promise(resolve => this.$target.trigger('background-color-event', {previewMode, callback: resolve}));
        }

        const cssProps = weUtils.CSS_SHORTHANDS[params.cssProperty] || [params.cssProperty];
        for (const cssProp of cssProps) {
            // Always reset the inline style first to not put inline style on an
            // element which already have this style through css stylesheets.
            this.$target[0].style.setProperty(cssProp, '');
        }
        if (params.extraClass) {
            this.$target.removeClass(params.extraClass);
        }

        // Only allow to use a color name as a className if we know about the
        // other potential color names (to remove) and if we know about a prefix
        // (otherwise we suppose that we should use the actual related color).
        if (params.colorNames && params.colorPrefix) {
            const classes = params.colorNames.map(c => params.colorPrefix + c);
            this.$target[0].classList.remove(...classes);

            if (params.colorNames.includes(widgetValue)) {
                const originalCSSValue = window.getComputedStyle(this.$target[0])[cssProps[0]];
                const className = params.colorPrefix + widgetValue;
                this.$target[0].classList.add(className);
                if (originalCSSValue !== window.getComputedStyle(this.$target[0])[cssProps[0]]) {
                    // If applying the class did indeed changed the css
                    // property we are editing, nothing more has to be done.
                    // (except adding the extra class)
                    this.$target.addClass(params.extraClass);
                    return;
                }
                // Otherwise, it means that class probably does not exist,
                // we remove it and continue. Especially useful for some
                // prefixes which only work with some color names but not all.
                this.$target[0].classList.remove(className);
            }
        }

        // At this point, the widget value is either a property/color name or
        // an actual css property value. If it is a property/color name, we will
        // apply a css variable as style value.
        const htmlStyle = window.getComputedStyle(document.documentElement);
        const htmlPropValue = htmlStyle.getPropertyValue('--' + widgetValue);
        if (htmlPropValue) {
            widgetValue = `var(--${widgetValue})`;
        }

        const values = widgetValue.split(/\s+/g);
        while (values.length < cssProps.length) {
            switch (values.length) {
                case 1:
                case 2: {
                    values.push(values[0]);
                    break;
                }
                case 3: {
                    values.push(values[1]);
                    break;
                }
                default: {
                    values.push(values[values.length - 1]);
                }
            }
        }

        const styles = window.getComputedStyle(this.$target[0]);
        let hasUserValue = false;
        for (let i = cssProps.length - 1; i > 0; i--) {
            hasUserValue = applyCSS.call(this, cssProps[i], values.pop(), styles) || hasUserValue;
        }
        hasUserValue = applyCSS.call(this, cssProps[0], values.join(' '), styles) || hasUserValue;

        function applyCSS(cssProp, cssValue, styles) {
            if (!weUtils.areCssValuesEqual(styles[cssProp], cssValue)) {
                this.$target[0].style.setProperty(cssProp, cssValue, 'important');
                return true;
            }
            return false;
        }

        if (params.extraClass) {
            this.$target.toggleClass(params.extraClass, hasUserValue);
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override the helper method to search inside the $target element instead
     * of the UI item element.
     *
     * @override
     */
    $: function () {
        return this.$target.find.apply(this.$target, arguments);
    },
    /**
     * Closes all user value widgets.
     */
    closeWidgets: function () {
        this._userValueWidgets.forEach(widget => widget.close());
    },
    /**
     * @param {string} name
     * @returns {UserValueWidget|null}
     */
    findWidget: function (name) {
        for (const widget of this._userValueWidgets) {
            if (widget.getName() === name) {
                return widget;
            }
            const depWidget = widget.findWidget(name);
            if (depWidget) {
                return depWidget;
            }
        }
        return null;
    },
    /**
     * Sometimes, options may need to notify other options, even in parent
     * editors. This can be done thanks to the 'option_update' event, which
     * will then be handled by this function.
     *
     * @param {string} name - an identifier for a type of update
     * @param {*} data
     * @returns {Promise}
     */
    notify: async function (name, data) {
        if (name === 'target') {
            await this.setTarget(data);
        }
    },
    /**
     * Sometimes, an option is binded on an element but should in fact apply on
     * another one. For example, elements which contain slides: we want all the
     * per-slide options to be in the main menu of the whole snippet. This
     * function allows to set the option's target.
     *
     * @param {jQuery} $target - the new target element
     * @returns {Promise}
     */
    setTarget: async function ($target) {
        this.$target = $target;
        await this.updateUI();
    },
    /**
     * Updates the UI. For widget update, @see _computeWidgetState.
     *
     * @param {UserValueWidget} [forced=null]
     *     Only non-previewed widgets are updated, except for the one given here
     * @param {boolean} [noVisibility=false]
     *     If true, only update widget values and their UI, not their visibility
     *     -> @see updateUIVisibility for toggling visibility only
     * @returns {Promise}
     */
    updateUI: async function ({forced, noVisibility} = {}) {
        // For each widget, for each of their option method, notify to the
        // widget the current value they should hold according to the $target's
        // current state, related for that method.
        const proms = this._userValueWidgets.map(async widget => {
            // Update widget value (for each method)
            const methodsNames = widget.getMethodsNames();
            const proms = methodsNames.map(async methodName => {
                const params = widget.getMethodsParams(methodName);

                let obj = this;
                if (params.applyTo) {
                    const $firstSubTarget = this.$(params.applyTo).eq(0);
                    if (!$firstSubTarget.length) {
                        return;
                    }
                    obj = createPropertyProxy(this, '$target', $firstSubTarget);
                }

                const value = await this._computeWidgetState.call(obj, methodName, params);
                if (value === undefined) {
                    return;
                }
                const normalizedValue = this._normalizeWidgetValue(value);
                widget.setValue(normalizedValue, methodName);
            });
            await Promise.all(proms);

            // Refresh the UI of all widgets (after all the current values they
            // hold have been updated).
            return widget.updateUI(widget === forced);
        });
        await Promise.all(proms);

        if (!noVisibility) {
            await this.updateUIVisibility();
        }
    },
    /**
     * Updates the UI visibility - @see _computeVisibility. For widget update,
     * @see _computeWidgetVisibility.
     *
     * @returns {Promise}
     */
    updateUIVisibility: async function () {
        const proms = this._userValueWidgets.map(async widget => {
            const params = widget.getMethodsParams();

            let obj = this;
            if (params.applyTo) {
                const $firstSubTarget = this.$(params.applyTo).eq(0);
                if (!$firstSubTarget.length) {
                    widget.toggleVisibility(false);
                    return;
                }
                obj = createPropertyProxy(this, '$target', $firstSubTarget);
            }

            const show = await this._computeWidgetVisibility.call(obj, widget.getName(), params);
            if (!show) {
                widget.toggleVisibility(false);
                return;
            }

            const dependencies = widget.getDependencies();
            const dependenciesOK = !dependencies.length || dependencies.some(depName => {
                const toBeActive = (depName[0] !== '!');
                if (!toBeActive) {
                    depName = depName.substr(1);
                }

                let widget = null;
                this.trigger_up('user_value_widget_request', {
                    name: depName,
                    onSuccess: _widget => widget = _widget,
                });
                return widget && (widget.isActive() === toBeActive);
            });

            widget.toggleVisibility(dependenciesOK);
        });

        const showUI = await this._computeVisibility();
        this.el.classList.toggle('d-none', !showUI);

        return Promise.all(proms);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Promise<boolean>|boolean}
     */
    _computeVisibility: async function () {
        return true;
    },
    /**
     * Returns the string value that should be hold by the widget which is
     * related to the given method name.
     *
     * If the value is irrelevant for a method, it must return undefined.
     *
     * @private
     * @param {string} methodName
     * @param {Object} params
     * @returns {Promise<string|undefined>|string|undefined}
     */
    _computeWidgetState: async function (methodName, params) {
        switch (methodName) {
            case 'selectClass': {
                let maxNbClasses = 0;
                let activeClassNames = '';
                params.possibleValues.forEach(classNames => {
                    if (!classNames) {
                        return;
                    }
                    const classes = classNames.split(/\s+/g);
                    if (classes.length >= maxNbClasses
                            && classes.every(className => this.$target[0].classList.contains(className))) {
                        maxNbClasses = classes.length;
                        activeClassNames = classNames;
                    }
                });
                return activeClassNames;
            }
            case 'selectDataAttribute': {
                const dataName = params.attributeName;
                let dataValue = (this.$target[0].dataset[dataName] || '').trim();
                if (params.saveUnit && !params.withUnit) {
                    dataValue = dataValue.split(/\s+/g).map(v => v + params.saveUnit).join(' ');
                }
                return dataValue || params.attributeDefaultValue || '';
            }
            case 'selectStyle': {
                if (params.colorPrefix && params.colorNames) {
                    for (const c of params.colorNames) {
                        if (this.$target[0].classList.contains(params.colorPrefix + c)) {
                            return c;
                        }
                    }
                }

                const styles = window.getComputedStyle(this.$target[0]);
                const cssProps = weUtils.CSS_SHORTHANDS[params.cssProperty] || [params.cssProperty];
                const cssValues = cssProps.map(cssProp => {
                    return styles[cssProp].trim();
                });
                if (cssValues.length === 4 && weUtils.areCssValuesEqual(cssValues[3], cssValues[1], params.cssProperty, this.$target)) {
                    cssValues.pop();
                }
                if (cssValues.length === 3 && weUtils.areCssValuesEqual(cssValues[2], cssValues[0], params.cssProperty, this.$target)) {
                    cssValues.pop();
                }
                if (cssValues.length === 2 && weUtils.areCssValuesEqual(cssValues[1], cssValues[0], params.cssProperty, this.$target)) {
                    cssValues.pop();
                }
                return cssValues.join(' ');
            }
        }
    },
    /**
     * @private
     * @param {string} widgetName
     * @param {Object} params
     * @returns {Promise<boolean>|boolean}
     */
    _computeWidgetVisibility: async function (widgetName, params) {
        return true;
    },
    /**
     * @private
     * @param {HTMLElement} el
     * @returns {Object}
     */
    _extraInfoFromDescriptionElement: function (el) {
        return {
            title: el.getAttribute('string'),
            options: {
                classes: el.classList,
                dataAttributes: el.dataset,
                childNodes: [...el.childNodes],
            },
        };
    },
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {boolean|string} previewMode
     */
    _handleUserValueEvent: function (ev, previewMode) {
        ev.stopPropagation();
        this.trigger_up('snippet_edition_request', {exec: async () => {
            if (ev.data.prepare) {
                ev.data.prepare();
            }

            const widget = ev.data.widget;
            if (previewMode && (widget.$el.closest('[data-no-preview="true"]').length)) {
                // TODO the flag should be fetched through widget params somehow
                return;
            }

            // If it is not preview mode, the user selected the option for good
            // (so record the action)
            if (!previewMode) {
                this.trigger_up('request_history_undo_record', {$target: this.$target});
            }

            // Call widget option methods and update $target
            await this._select(previewMode, widget);
            this.$target.trigger('content_changed');

            await new Promise(resolve => {
                // Will update the UI of the correct widgets for all options
                // related to the same $target/editor if necessary
                this.trigger_up('snippet_option_update', {
                    widget: widget,
                    previewMode: previewMode,
                    onSuccess: () => resolve(),
                });
            });
        }});
    },
    /**
     * @private
     * @param {*}
     * @returns {string}
     */
    _normalizeWidgetValue: function (value) {
        value = `${value}`.trim(); // Force to a trimmed string
        value = ColorpickerDialog.normalizeCSSColor(value); // If is a css color, normalize it
        return value;
    },
    /**
     * @private
     * @param {string} widgetName
     * @param {UserValueWidget|this|null} parent
     * @param {string} title
     * @param {Object} options
     * @returns {UserValueWidget}
     */
    _registerUserValueWidget: function (widgetName, parent, title, options) {
        const widget = new userValueWidgetsRegistry[widgetName](parent, title, options, this.$target);
        if (!parent || parent === this) {
            this._userValueWidgets.push(widget);
        } else {
            parent.registerSubWidget(widget);
        }
        return widget;
    },
    /**
     * @private
     * @param {HTMLElement} uiFragment
     * @returns {Promise}
     */
    _renderCustomWidgets: function (uiFragment) {
        return Promise.resolve();
    },
    /**
     * @private
     * @param {HTMLElement} uiFragment
     * @returns {Promise}
     */
    _renderCustomXML: function (uiFragment) {
        return Promise.resolve();
    },
    /**
     * @private
     * @param {jQuery} [$xml] - default to original xml content
     * @returns {Promise}
     */
    _renderOriginalXML: async function ($xml) {
        const uiFragment = document.createDocumentFragment();
        ($xml || this.$originalUIElements).clone(true).appendTo(uiFragment);

        // Build layouting components first
        uiFragment.querySelectorAll('we-row').forEach(el => {
            const infos = this._extraInfoFromDescriptionElement(el);
            const groupEl = _buildRowElement(infos.title, infos.options);
            el.parentNode.insertBefore(groupEl, el);
            el.parentNode.removeChild(el);
        });

        // Load widgets
        await this._renderCustomXML(uiFragment);
        await this._renderXMLWidgets(uiFragment);
        await this._renderCustomWidgets(uiFragment);

        const validMethodNames = [];
        for (const key in this) {
            if (typeof this[key] === 'function') {
                validMethodNames.push(key);
            }
        }
        this._userValueWidgets.forEach(widget => {
            widget.loadMethodsData(validMethodNames);
        });

        return uiFragment;
    },
    /**
     * @private
     * @param {HTMLElement} parentEl
     * @param {SnippetOptionWidget|UserValueWidget} parentWidget
     * @returns {Promise}
     */
    _renderXMLWidgets: function (parentEl, parentWidget) {
        const proms = [...parentEl.children].map(el => {
            const widgetName = el.tagName.toLowerCase();
            if (!userValueWidgetsRegistry.hasOwnProperty(widgetName)) {
                return this._renderXMLWidgets(el, parentWidget);
            }

            const infos = this._extraInfoFromDescriptionElement(el);
            const widget = this._registerUserValueWidget(widgetName, parentWidget || this, infos.title, infos.options);
            return widget.insertAfter(el).then(() => {
                // Remove the original element afterwards as the insertion
                // operation may move some of its inner content during
                // widget start.
                parentEl.removeChild(el);

                if (widget.isContainer()) {
                    return this._renderXMLWidgets(widget.el, widget);
                }
            });
        });
        return Promise.all(proms);
    },
    /**
     * @private
     * @param {function<Promise<jQuery>>} [callback]
     * @returns {Promise}
     */
    _rerenderXML: async function (callback) {
        this._userValueWidgets.forEach(widget => widget.destroy());
        this._userValueWidgets = [];
        this.$el.empty();

        let $xml = undefined;
        if (callback) {
            $xml = await callback.call(this);
        }

        return this._renderOriginalXML($xml).then(uiFragment => {
            this.$el.append(uiFragment);
            return this.updateUI();
        });
    },
    /**
     * Activates the option associated to the given DOM element.
     *
     * @private
     * @param {boolean|string} previewMode
     *        - truthy if the option is enabled for preview or if leaving it (in
     *          that second case, the value is 'reset')
     *        - false if the option should be activated for good
     * @param {UserValueWidget} widget - the widget which triggered the option change
     * @returns {Promise}
     */
    _select: async function (previewMode, widget) {
        // Call each option method sequentially
        for (const methodName of widget.getMethodsNames()) {
            const widgetValue = widget.getValue(methodName);
            const params = widget.getMethodsParams(methodName);

            if (params.applyTo) {
                const $subTargets = this.$(params.applyTo);
                const proms = _.each($subTargets, subTargetEl => {
                    const proxy = createPropertyProxy(this, '$target', $(subTargetEl));
                    return this[methodName].call(proxy, previewMode, widgetValue, params);
                });
                await Promise.all(proms);
            } else {
                await this[methodName](previewMode, widgetValue, params);
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a option link is entered or an option input content is being
     * modified -> activates the related option in preview mode.
     *
     * @private
     * @param {Event} ev
     */
    _onOptionPreview: function (ev) {
        this._handleUserValueEvent(ev, true);
    },
    /**
     * Called when an option link is clicked or an option input content is
     * validated -> activates the related option.
     *
     * @private
     * @param {Event} ev
     */
    _onOptionSelection: function (ev) {
        this._handleUserValueEvent(ev, false);
    },
    /**
     * Called when an option link/menu is left -> reactivate the options that
     * were activated before previews.
     *
     * @private
     * @param {Event} ev
     */
    _onOptionCancel: function (ev) {
        this._handleUserValueEvent(ev, 'reset');
    },
});
const registry = {};

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

registry.sizing = SnippetOptionWidget.extend({
    /**
     * @override
     */
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);

        this.$handles = this.$overlay.find('.o_handle');

        var resizeValues = this._getSize();
        this.$handles.on('mousedown', function (ev) {
            ev.preventDefault();

            var $handle = $(ev.currentTarget);

            var compass = false;
            var XY = false;
            if ($handle.hasClass('n')) {
                compass = 'n';
                XY = 'Y';
            } else if ($handle.hasClass('s')) {
                compass = 's';
                XY = 'Y';
            } else if ($handle.hasClass('e')) {
                compass = 'e';
                XY = 'X';
            } else if ($handle.hasClass('w')) {
                compass = 'w';
                XY = 'X';
            }

            var resize = resizeValues[compass];
            if (!resize) {
                return;
            }

            var current = 0;
            var cssProperty = resize[2];
            var cssPropertyValue = parseInt(self.$target.css(cssProperty));
            _.each(resize[0], function (val, key) {
                if (self.$target.hasClass(val)) {
                    current = key;
                } else if (resize[1][key] === cssPropertyValue) {
                    current = key;
                }
            });
            var begin = current;
            var beginClass = self.$target.attr('class');
            var regClass = new RegExp('\\s*' + resize[0][begin].replace(/[-]*[0-9]+/, '[-]*[0-9]+'), 'g');

            var cursor = $handle.css('cursor') + '-important';
            var $body = $(this.ownerDocument.body);
            $body.addClass(cursor);

            var xy = ev['page' + XY];
            var bodyMouseMove = function (ev) {
                ev.preventDefault();

                var dd = ev['page' + XY] - xy + resize[1][begin];
                var next = current + (current + 1 === resize[1].length ? 0 : 1);
                var prev = current ? (current - 1) : 0;

                var change = false;
                if (dd > (2 * resize[1][next] + resize[1][current]) / 3) {
                    self.$target.attr('class', (self.$target.attr('class') || '').replace(regClass, ''));
                    self.$target.addClass(resize[0][next]);
                    current = next;
                    change = true;
                }
                if (prev !== current && dd < (2 * resize[1][prev] + resize[1][current]) / 3) {
                    self.$target.attr('class', (self.$target.attr('class') || '').replace(regClass, ''));
                    self.$target.addClass(resize[0][prev]);
                    current = prev;
                    change = true;
                }

                if (change) {
                    self._onResize(compass, beginClass, current);
                    self.trigger_up('cover_update');
                    $handle.addClass('o_active');
                }
            };
            var bodyMouseUp = function () {
                $body.off('mousemove', bodyMouseMove);
                $body.off('mouseup', bodyMouseUp);
                $body.removeClass(cursor);
                $handle.removeClass('o_active');

                // Highlights the previews for a while
                var $handlers = self.$overlay.find('.o_handle');
                $handlers.addClass('o_active').delay(300).queue(function () {
                    $handlers.removeClass('o_active').dequeue();
                });

                if (begin === current) {
                    return;
                }
                setTimeout(function () {
                    self.trigger_up('request_history_undo_record', {
                        $target: self.$target,
                        event: 'resize_' + XY,
                    });
                }, 0);
            };
            $body.on('mousemove', bodyMouseMove);
            $body.on('mouseup', bodyMouseUp);
        });

        return def;
    },
    /**
     * @override
     */
    onFocus: function () {
        this._onResize();
    },
    /**
     * @override
     */
    onBlur: function () {
        this.$handles.addClass('readonly');
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setTarget: async function () {
        await this._super(...arguments);
        this._onResize();
    },
    /**
     * @override
     */
    updateUI: async function () {
        await this._super(...arguments);
        const resizeValues = this._getSize();
        _.each(resizeValues, (value, key) => {
            this.$handles.filter('.' + key).toggleClass('readonly', !value);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns an object mapping one or several cardinal direction (n, e, s, w)
     * to an Array containing:
     * 1) A list of classes to toggle when using this cardinal direction
     * 2) A list of values these classes are supposed to set on a given CSS prop
     * 3) The mentioned CSS prop
     *
     * Note: this object must also be saved in this.grid before being returned.
     *
     * @abstract
     * @private
     * @returns {Object}
     */
    _getSize: function () {},
    /**
     * Called when the snippet is being resized and its classes changes.
     *
     * @private
     * @param {string} [compass] - resize direction ('n', 's', 'e' or 'w')
     * @param {string} [beginClass] - attributes class at the beginning
     * @param {integer} [current] - current increment in this.grid
     */
    _onResize: function (compass, beginClass, current) {
        var self = this;

        // Adapt the resize handles according to the classes and dimensions
        var resizeValues = this._getSize();
        var $handles = this.$overlay.find('.o_handle');
        _.each(resizeValues, function (resizeValue, direction) {
            var classes = resizeValue[0];
            var values = resizeValue[1];
            var cssProperty = resizeValue[2];

            var $handle = $handles.filter('.' + direction);

            var current = 0;
            var cssPropertyValue = parseInt(self.$target.css(cssProperty));
            _.each(classes, function (className, key) {
                if (self.$target.hasClass(className)) {
                    current = key;
                } else if (values[key] === cssPropertyValue) {
                    current = key;
                }
            });

            $handle.toggleClass('o_handle_start', current === 0);
            $handle.toggleClass('o_handle_end', current === classes.length - 1);
        });

        // Adapt the handles to fit the left, top and bottom sizes
        var ml = this.$target.css('margin-left');
        this.$overlay.find('.o_handle.w').css({
            width: ml,
            left: '-' + ml,
        });
        this.$overlay.find('.o_handle.e').css({
            width: 0,
        });
        _.each(this.$overlay.find(".o_handle.n, .o_handle.s"), function (handle) {
            var $handle = $(handle);
            var direction = $handle.hasClass('n') ? 'top' : 'bottom';
            $handle.height(self.$target.css('padding-' + direction));
        });
        this.$target.trigger('content_changed');
    },
});

/**
 * Handles the edition of padding-top and padding-bottom.
 */
registry['sizing_y'] = registry.sizing.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getSize: function () {
        var nClass = 'pt';
        var nProp = 'padding-top';
        var sClass = 'pb';
        var sProp = 'padding-bottom';
        if (this.$target.is('hr')) {
            nClass = 'mt';
            nProp = 'margin-top';
            sClass = 'mb';
            sProp = 'margin-bottom';
        }

        var grid = [];
        for (var i = 0; i <= (256 / 8); i++) {
            grid.push(i * 8);
        }
        grid.splice(1, 0, 4);
        this.grid = {
            n: [grid.map(v => nClass + v), grid, nProp],
            s: [grid.map(v => sClass + v), grid, sProp],
        };
        return this.grid;
    },
});

// Abstract option, used to manage images' size and quality.
const ImageHandlerOption = SnippetOptionWidget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    events: _.extend({}, SnippetOptionWidget.prototype.events || {}, {
        'input .custom-range': '_onQualityChange',
    }),
    // Static default image settings.
    defaultSettings: Object.freeze({
        quality: 100,
        filter: '#00000000',
    }),

    /**
     * @override
     */
    willStart: async function () {
        const _super = this._super.bind(this);
        this._onQualityChange = _.debounce(this._onQualityChange.bind(this), 200);
        this.settings = await this._loadDataFromTarget();
        await this._changeSrc(await this._applyOptions());
        await _super(...arguments);
    },
    /**
     * @override
     */
    cleanForSave: async function () {
        this._tagElement();
        // FIXME: make new route that will take originalSrc to determine model, id.
        // and delete the previous attachment in that slot if applicable.
        const dataURL = await this._applyOptions();
        if (dataURL === this.settings.originalSrc) {
            return;
        }
        const $editable = this.$target.closest('.o_editable');
        const newAttachment = await this._rpc({
            route: '/web_editor/attachment/add_data',
            params: {
                'name': 'dataURL_attachment',
                'data': dataURL.split(',')[1],
                'res_id': $editable.data('oe-id'),
                'res_model': $editable.data('oe-model'),
            },
        });
        await this._changeSrc(`/web/image/${newAttachment.id}/${newAttachment.name}`);
    },
    /**
     * @override
     */
    updateUI: async function () {
        await this._super(...arguments);
        this._updateWeight();
        // Quality option is not a UserValueWidget so value and visibility are manual.
        this.$el.find('input.custom-range').val(this.settings.quality);
        this.$el.find('.o_we_quality_option').toggleClass('d-none', !this.canModifyImage);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Opens a media dialog to pick a different image.
     *
     * @see this.selectClass for params
     */
    editImage: async function (previewMode, widgetValue, params) {
        const {parent, options, targetEl} = this._getMediaDialogArgs(params);
        const mediaDialog = new weWidgets.MediaDialog(parent, options, targetEl).open();
        await new Promise(resolve => {
            mediaDialog.on('save', this, async (...args) => {
                await this._onMediaDialogSave(...args);
                resolve();
            });
            mediaDialog.on('cancel', this, resolve);
        });
    },
    /**
     * Removes the currently set image.
     *
     * @see this.selectClass for params
     */
    removeImage: async function (previewMode, widgetValue, params) {
        await this._changeSrc('', previewMode);
    },
    /**
     * Puts a color filter on the image.
     *
     * @see this.selectClass for params
     */
    filter: async function (previewMode, widgetValue, params) {
        switch (previewMode) {
            case false:
                this.prevFilter = widgetValue;
                break;
            case 'reset':
                widgetValue = this.prevFilter;
                break;
        }
        this.settings.filter = widgetValue || this.defaultSettings.filter;
        await this._changeSrc(await this._applyOptions(), previewMode);
    },
    /**
     * Sets the image width.
     *
     * @see this.selectClass for params
     */
    width: async function (previewMode, widgetValue, params) {
        this.settings.width = parseInt(widgetValue);
        await this._changeSrc(await this._applyOptions());
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        const {filter, originalSrc, width} = this.settings;
        switch (methodName) {
            case 'filter':
                return filter;
            case 'editImage':
                return originalSrc ? 'true' : '';
            case 'width':
                return width;
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility: function (widgetName, params) {
        if (['filter', 'width'].includes(widgetName)) {
            return this.canModifyImage;
        } else if (widgetName === 'remove') {
            return !!this.settings.originalSrc;
        }
        return this._super(...arguments);
    },
    /**
     * Called in other methods when the image src needs to be updated.
     *
     * @override
     */
    _changeSrc: async function (value, previewMode) {
        if (!value && !previewMode) {
            this.settings = _.extend({}, this.defaultSettings);
            this.canModifyImage = false;
        }
    },
    /**
     * Applies all selected options on the original image.
     *
     * @private
     * @returns {string} URL to the new image (or original URL if the image
     *     cannot be modified)
     */
    _applyOptions: async function () {
        const {quality, originalSrc, width, filter} = this.settings;
        this.canModifyImage = true;
        try {
            const img = await this._loadImage(originalSrc);
            const {naturalWidth, naturalHeight} = img;
            if (naturalWidth === 0) {
                throw new Error(`Couldn't load image: ${img.src}`);
            }
            const canvas = document.createElement('canvas');
            // Width
            this.originalWidth = naturalWidth;
            canvas.width = width;
            canvas.height = naturalHeight * canvas.width / naturalWidth;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, naturalWidth, naturalHeight, 0, 0, canvas.width, canvas.height);
            // Color filter
            ctx.fillStyle = this._colorToCss(filter);
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            // Quality
            const dataURL = canvas.toDataURL('image/jpeg', quality / 100);
            this.weight = dataURL.split(',')[1].length / 4 * 3;
            return dataURL;
        } catch (error) {
            // Can't load image for whatever reason (usually an invalid src) OR
            // SecurityError when attempting to convert canvas to dataURL,
            // because is tainted with cross-origin data. Need to disable options.
            console.warn(error);
            this.canModifyImage = false;
            return originalSrc;
        }
    },
    /**
     * Fills the width select with the available widths.
     *
     * @override
     */
    _renderCustomXML: async function (uiFragment) {
        const widthSelect = uiFragment.querySelector('.o_we_width_select');
        const availableWidths = await this._computeAvailableWidths();
        Object.entries(availableWidths).forEach(([width, labels]) => {
            widthSelect.appendChild($(`<we-button data-width="${width}">${width} ${labels.length ? `(${labels.join(', ')})` : ''}</we-button>`)[0]);
        });
    },
    /**
     * Returns an object containing the available widths for the image, where
     * the keys are the widths themselves, and values are an array of labels.
     *
     * @private
     */
    _computeAvailableWidths: async function () {
        const {originalSrc} = this.settings;
        const originalWidth = (await this._loadImage(originalSrc)).naturalWidth;
        const optimizedWidth = await this._computeOptimizedWidth(originalSrc);
        const widths = [128, 256, 512, 1024, 1920, optimizedWidth, originalWidth];
        const widthsAndLabels = Object.fromEntries(widths.map(w => [w, []]));
        widthsAndLabels[optimizedWidth].push(_t("recommended"));
        widthsAndLabels[originalWidth].push(_t("original"));
        Object.keys(widthsAndLabels).forEach(width => {
            if (width > originalWidth) {
                delete widthsAndLabels[width];
            }
        });
        return widthsAndLabels;
    },
    /**
     * Computes the image's maximum display width.
     *
     * @private
     */
    _computeOptimizedWidth: function () {
        // FIXME: read widths from computed style in case container widths are not default
        const displayWidth = this.$target[0].clientWidth;
        // If the image is in a column, it might get bigger on smaller screens.
        // We use col-lg for this in most (all?) snippets.
        if (this.$target.closest('[class*="col-lg"]').length) {
            // A container's maximum inner width is 690px on the md breakpoint
            if (this.$target.closest('.container').length) {
                return Math.min(1920, Math.max(displayWidth, 690));
            }
            // A container-fluid's max inner width is 962px on the md breakpoint
            return Math.min(1920, Math.max(displayWidth, 962));
        }
        // If it's not in a col-lg, it's *probably* not going to change size depending on breakpoints
        return displayWidth;
    },
    /**
     * Saves the edit data onto the target as data attributes.
     *
     * @private
     */
    _tagElement: function () {
        ['quality', 'originalSrc', 'filter'].forEach(property => {
            delete this.$target[0].dataset[property];
            if (this.settings[property] !== this.defaultSettings[property]) {
                this.$target[0].dataset[property] = this.settings[property];
            }
        });
    },
    /**
     * Loads the edit data from the target.
     *
     * @private
     */
    _loadDataFromTarget: async function () {
        const settings = {};
        ['quality', 'originalSrc', 'filter'].forEach(property => {
            settings[property] = this.$target[0].dataset[property];
        });
        _.defaults(settings, this.defaultSettings);
        return settings;
    },
    /**
     * Updates the image's weight in the UI.
     *
     * @private
     */
    _updateWeight: async function () {
        this.$el.find('.o_we_image_file_size').text(`${(this.weight / 1024).toFixed(0)} kb`);
    },
    /**
     * Returns an object containing the required arguments for creating the
     * MediaDialog, this is done here to allow overriding.
     *
     * @param {Object} params @see this.selectClass third argument.
     */
    _getMediaDialogArgs: function (params) {
        const {originalSrc} = this.settings;
        const dummyEl = document.createElement('img');
        const $editable = this.$target.closest('.o_editable');
        dummyEl.src = originalSrc;
        return {
            parent: this,
            options: {
                noIcons: true,
                noDocuments: true,
                noVideos: true,
                res_model: $editable.data('oe-model'),
                res_id: $editable.data('oe-id'),
                firstFilters: params.firstFilters ? params.firstFilters.split(' ') : [],
            },
            targetEl: dummyEl
        };
    },

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------

    /**
     * Creates an img element and returns a promise that resolves to it once the
     * image is loaded.
     *
     * @private
     * @param {String} src the URL of the image to load
     * @param {Image} img optional img element in which to load the image
     * @returns {Image} the loaded image
     */
    _loadImage: async function (src, img = document.createElement('img')) {
        try {
            await new Promise((resolve, reject) => {
                img.addEventListener('load', resolve, {once: true});
                img.addEventListener('error', reject, {once: true});
                img.src = src;
            });
        } catch (e) {
            console.warn(e);
        }
        return img;
    },
    /**
     * Converts a color from the colorpicker widget to a css color usable by
     * the CanvasRenderingContext2D.
     *
     * @private
     * @param {string} color
     * @returns {string}
     */
    _colorToCss: function (color) {
        if (ColorpickerDialog.isCSSColor(color)) {
            return color;
        }
        const style = window.getComputedStyle(document.documentElement);
        return style.getPropertyValue('--' + color).trim();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Handles changes to the quality range input. Since this doesn't use a
     * UserValueWidget it needs to update its UI manually.
     *
     * @private
     * @param {Event|OdooEvent} ev
     */
    _onQualityChange: async function (ev) {
        this.settings.quality = parseInt(ev.target.value);
        await this._changeSrc(await this._applyOptions());
        this._updateWeight();
    },
    /**
     * Handles saving in the MediaDialog.
     *
     * @private
     * @param {Object} data data returned by the MediaDialog.
     */
    _onMediaDialogSave: async function (data) {
        const originalSrc = data.getAttribute('src');
        await this._changeSrc(originalSrc);
        const width = await this._computeOptimizedWidth(originalSrc);
        this.settings = _.defaults({originalSrc, width, quality: 80}, this.defaultSettings);
        await this._rerenderXML();
        this.$el.find('input.custom-range').val(this.settings.quality);
        await this._changeSrc(await this._applyOptions());
    },
});
/**
 * Handles the edition of non-background images.
 */
registry.Image = ImageHandlerOption.extend({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _changeSrc: async function (src, previewMode) {
        await this._super(...arguments);
        await this._loadImage(src, this.$target[0]);
    },
    /**
     * @override
     */
    _loadDataFromTarget: async function () {
        const settings = await this._super(...arguments);
        settings.initialSrc = this.$target[0].getAttribute('src');
        if (!settings.originalSrc) {
            settings.originalSrc = settings.initialSrc;
        }
        settings.width = this.$target[0].naturalWidth;
        return settings;
    },
});
/**
 * Handles the edition of snippet's background image.
 */
registry.background = ImageHandlerOption.extend({
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        // Initialize background and events
        this.bindBackgroundEvents();
    },
    /**
     * @override
     */
    cleanForSave: async function () {
        if (this.__customImageSrc === '') {
            this.settings = _.extend({}, this.defaultSettings);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setTarget: async function () {
        await this._super(...arguments);
        // TODO should be automatic for all options as equal to the start method
        this.bindBackgroundEvents();
    },
    /**
     * Attaches events so that when a background-color is set, the background
     * image is removed.
     */
    bindBackgroundEvents: function () {
        if (this.$target.is('.parallax, .s_parallax_bg')) {
            return;
        }
        // This event is not unbound on destroy, oversight?
        this.$target.off('.background-option')
            .on('background-color-event.background-option', this._onBackgroundColorUpdate.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _changeSrc: async function (src, previewMode = false) {
        await this._super(...arguments);
        switch (previewMode) {
            case false:
                this.__customImageSrc = src;
                break;
            case 'reset':
                src = this.__customImageSrc;
                break;
        }

        if (src) {
            this.$target.css('background-image', `url('${src}')`);
            this.$target.addClass('oe_img_bg');
        } else {
            this.$target.css('background-image', '');
            this.$target.removeClass('oe_img_bg');
        }
    },
    /**
     * For backgrounds, the display width is usually smaller than the maximum
     * display width because of the left panel, so we override this to return
     * the original image's width capped at 1920.
     *
     * @override
     */
    _computeOptimizedWidth: async function (src) {
        const naturalWidth = (await this._loadImage(src)).naturalWidth;
        return Math.min(1920, naturalWidth);
    },
    /**
     * @override
     */
    _loadDataFromTarget: async function () {
        const settings = await this._super(...arguments);
        settings.initialSrc = this._getSrcFromCssValue();
        if (!settings.originalSrc) {
            settings.originalSrc = settings.initialSrc;
        }
        settings.width = (await this._loadImage(settings.initialSrc)).naturalWidth;
        return settings;
    },

    //--------------------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------------------

    /**
     * Returns the src value from a css value related to a background image
     * (e.g. "url('blabla')" => "blabla" / "none" => "").
     *
     * @private
     * @param {string} value
     * @returns {string}
     */
    _getSrcFromCssValue: function (value) {
        // FIXME: reading from style.backgroundImage won't get non inline URLs,
        // but using jQuery's css will yield absolute paths which can't be used for
        // searching the original in DB.
        value = value || this.$target[0].style.backgroundImage || this.$target.css('background-image');
        var srcValueWrapper = /url\(['"]*|['"]*\)|^none$/g;
        return value && value.replace(srcValueWrapper, '') || '';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called on background-color update (useful to remove the background to be
     * able to see the chosen color).
     *
     * @private
     * @param {Event} ev
     * @param {boolean|string} previewMode
     */
    _onBackgroundColorUpdate: async function (ev, data) {
        const {previewMode, callback} = data;
        ev.stopPropagation();
        if (ev.currentTarget !== ev.target) {
            return callback();
        }
        await this._changeSrc('', previewMode);
        return callback();
    },
});

/**
 * Handles the edition of snippets' background image position.
 */
registry.BackgroundPosition = SnippetOptionWidget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);

        this._initOverlay();

        // Resize overlay content on window resize because background images
        // change size, and on carousel slide because they sometimes take up
        // more space and move elements around them.
        $(window).on('resize.bgposition', () => this._dimensionOverlay());
    },
    /**
     * @override
     */
    destroy: function () {
        this._toggleBgOverlay(false);
        $(window).off('.bgposition');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Sets the background type (cover/repeat pattern).
     *
     * @see this.selectClass for params
     */
    backgroundType: function (previewMode, widgetValue, params) {
        this.$target.toggleClass('o_bg_img_opt_repeat', widgetValue === 'repeat-pattern');
        this.$target.css('background-position', '');
        this.$target.css('background-size', '');
    },
    /**
     * Saves current background position and enables overlay.
     *
     * @see this.selectClass for params
     */
    backgroundPositionOverlay: async function (previewMode, widgetValue, params) {
        // Updates the internal image
        await new Promise(resolve => {
            this.img = document.createElement('img');
            this.img.addEventListener('load', () => resolve());
            this.img.src = this._getSrcFromCssValue();
        });

        const position = this.$target.css('background-position').split(' ').map(v => parseInt(v));
        // Convert % values to pixels (because mouse movement is in pixels)
        const delta = this._getBackgroundDelta();
        this.originalPosition = {
            left: position[0] / 100 * delta.x || 0,
            top: position[1] / 100 * delta.y || 0,
        };
        this.currentPosition = _.clone(this.originalPosition);

        this._toggleBgOverlay(true);
    },
    /**
     * @override
     */
    selectStyle: function (previewMode, widgetValue, params) {
        if (params.cssProperty === 'background-size'
                && !this.$target.hasClass('o_bg_img_opt_repeat')) {
            // Disable the option when the image is in cover mode, otherwise
            // the background-size: auto style may be forced.
            return;
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeVisibility: function () {
        return this._super(...arguments) && (this.$target.css('background-image') !== 'none');
    },
    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'backgroundType') {
            return this.$target.css('background-repeat') === 'repeat' ? 'repeat-pattern' : 'cover';
        }
        return this._super(...arguments);
    },
    /**
     * Initializes the overlay, binds events to the buttons, inserts it in
     * the DOM.
     *
     * @private
     */
    _initOverlay: function () {
        this.$backgroundOverlay = $(qweb.render('web_editor.background_position_overlay'));
        this.$overlayContent = this.$backgroundOverlay.find('.o_we_overlay_content');
        this.$overlayBackground = this.$overlayContent.find('.o_overlay_background');

        this.$backgroundOverlay.on('click', '.o_btn_apply', () => {
            this.$target.css('background-position', this.$bgDragger.css('background-position'));
            this._toggleBgOverlay(false);
        });
        this.$backgroundOverlay.on('click', '.o_btn_discard', () => {
            this._toggleBgOverlay(false);
        });

        this.$backgroundOverlay.insertAfter(this.$overlay);
    },
    /**
     * Sets the overlay in the right place so that the draggable background
     * renders over the target, and size the background item like the target.
     *
     * @private
     */
    _dimensionOverlay: function () {
        if (!this.$backgroundOverlay.is('.oe_active')) {
            return;
        }
        // TODO: change #wrapwrap after web_editor rework.
        const $wrapwrap = $('#wrapwrap');
        const targetOffset = this.$target.offset();

        this.$backgroundOverlay.css({
            width: $wrapwrap.innerWidth(),
            height: $wrapwrap.innerHeight(),
        });

        this.$overlayContent.offset(targetOffset);

        this.$bgDragger.css({
            width: `${this.$target.innerWidth()}px`,
            height: `${this.$target.innerHeight()}px`,
        });
    },
    /**
     * Toggles the overlay's display and renders a background clone inside of it.
     *
     * @private
     * @param {boolean} activate toggle the overlay on (true) or off (false)
     */
    _toggleBgOverlay: function (activate) {
        if (this.$backgroundOverlay.is('.oe_active') === activate) {
            return;
        }

        if (!activate) {
            this.$backgroundOverlay.removeClass('oe_active');
            this.trigger_up('unblock_preview_overlays');
            this.trigger_up('activate_snippet', {$snippet: this.$target});

            $(document).off('click.bgposition');
            return;
        }

        this.trigger_up('hide_overlay');
        this.trigger_up('activate_snippet', {
            $snippet: this.$target,
            previewMode: true,
        });
        this.trigger_up('block_preview_overlays');

        // Create empty clone of $target with same display size, make it draggable and give it a tooltip.
        this.$bgDragger = this.$target.clone().empty();
        this.$bgDragger.on('mousedown', this._onDragBackgroundStart.bind(this));
        this.$bgDragger.tooltip({
            title: 'Click and drag the background to adjust its position!',
            trigger: 'manual',
            container: this.$backgroundOverlay
        });

        // Replace content of overlayBackground, activate the overlay and give it the right dimensions.
        this.$overlayBackground.empty().append(this.$bgDragger);
        this.$backgroundOverlay.addClass('oe_active');
        this._dimensionOverlay();
        this.$bgDragger.tooltip('show');

        // Needs to be deferred or the click event that activated the overlay deactivates it as well.
        // This is caused by the click event which we are currently handling bubbling up to the document.
        window.setTimeout(() => $(document).on('click.bgposition', this._onDocumentClicked.bind(this)), 0);
    },
    /**
     * Returns the src value from a css value related to a background image
     * (e.g. "url('blabla')" => "blabla" / "none" => "").
     *
     * @private
     * @param {string} value
     * @returns {string}
     */
    _getSrcFromCssValue: function (value) {
        if (value === undefined) {
            value = this.$target.css('background-image');
        }
        var srcValueWrapper = /url\(['"]*|['"]*\)|^none$/g;
        return value && value.replace(srcValueWrapper, '') || '';
    },
    /**
     * Returns the difference between the target's size and the background's
     * rendered size. Background position values in % are a percentage of this.
     *
     * @private
     */
    _getBackgroundDelta: function () {
        const bgSize = this.$target.css('background-size');
        if (bgSize !== 'cover') {
            let [width, height] = bgSize.split(' ');
            if (width === 'auto' && (height === 'auto' || !height)) {
                return {
                    x: this.$target.outerWidth() - this.img.naturalWidth,
                    y: this.$target.outerHeight() - this.img.naturalHeight,
                };
            }
            // At least one of width or height is not auto, so we can use it to calculate the other if it's not set
            [width, height] = [parseInt(width), parseInt(height)];
            return {
                x: this.$target.outerWidth() - (width || (height * this.img.naturalWidth / this.img.naturalHeight)),
                y: this.$target.outerHeight() - (height || (width * this.img.naturalHeight / this.img.naturalWidth)),
            };
        }

        const renderRatio = Math.max(
            this.$target.outerWidth() / this.img.naturalWidth,
            this.$target.outerHeight() / this.img.naturalHeight
        );

        return {
            x: this.$target.outerWidth() - Math.round(renderRatio * this.img.naturalWidth),
            y: this.$target.outerHeight() - Math.round(renderRatio * this.img.naturalHeight),
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Drags the overlay's background image, copied to target on "Apply".
     *
     * @private
     */
    _onDragBackgroundStart: function (ev) {
        ev.preventDefault();
        this.$bgDragger.addClass('o_we_grabbing');
        const $document = $(this.ownerDocument);
        $document.on('mousemove.bgposition', this._onDragBackgroundMove.bind(this));
        $document.one('mouseup', () => {
            this.$bgDragger.removeClass('o_we_grabbing');
            $document.off('mousemove.bgposition');
        });
    },
    /**
     * Drags the overlay's background image, copied to target on "Apply".
     *
     * @private
     */
    _onDragBackgroundMove: function (ev) {
        ev.preventDefault();

        const delta = this._getBackgroundDelta();
        this.currentPosition.left = clamp(this.currentPosition.left + ev.originalEvent.movementX, [0, delta.x]);
        this.currentPosition.top = clamp(this.currentPosition.top + ev.originalEvent.movementY, [0, delta.y]);

        const percentPosition = {
            left: this.currentPosition.left / delta.x * 100,
            top: this.currentPosition.top / delta.y * 100,
        };
        // In cover mode, one delta will be 0 and dividing by it will yield Infinity.
        // Defaulting to originalPosition in that case (can't be dragged)
        percentPosition.left = isFinite(percentPosition.left) ? percentPosition.left : this.originalPosition.left;
        percentPosition.top = isFinite(percentPosition.top) ? percentPosition.top : this.originalPosition.top;

        this.$bgDragger.css('background-position', `${percentPosition.left}% ${percentPosition.top}%`);

        function clamp(val, bounds) {
            // We sort the bounds because when one dimension of the rendered background is
            // larger than the container, delta is negative, and we want to use it as lower bound
            bounds = bounds.sort();
            return Math.max(bounds[0], Math.min(val, bounds[1]));
        }
    },
    /**
     * Deactivates the overlay if the user clicks outside of it.
     *
     * @private
     */
    _onDocumentClicked: function (ev) {
        if (!ev.target.closest('.o_we_background_position_overlay')) {
            this._toggleBgOverlay(false);
        }
    },
});

/**
 * Allows to replace a text value with the name of a database record.
 * @todo replace this mechanism with real backend m2o field ?
 */
registry.many2one = SnippetOptionWidget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    /**
     * @override
     */
    start: function () {
        var self = this;
        this.trigger_up('getRecordInfo', _.extend(this.options, {
            callback: function (recordInfo) {
                _.defaults(self.options, recordInfo);
            },
        }));

        this.Model = this.$target.data('oe-many2one-model');
        this.ID = +this.$target.data('oe-many2one-id');

        // create search button and bind search bar
        this.$btn = $(qweb.render('web_editor.many2one.button'))
            .prependTo(this.$el);

        this.$ul = this.$btn.find('ul');
        this.$search = this.$ul.find('li:first');
        this.$search.find('input').on('mousedown click mouseup keyup keydown', function (e) {
            e.stopPropagation();
        });

        // move menu item
        setTimeout(function () {
            self.$btn.find('a').on('click', function (e) {
                self._clear();
            });
        }, 0);

        // bind search input
        this.$search.find('input')
            .focus()
            .on('keyup', function (e) {
                self.$overlay.removeClass('o_keypress');
                self._findExisting($(this).val());
            });

        // bind result
        this.$ul.on('click', 'li:not(:first) a', function (e) {
            self._selectRecord($(e.currentTarget));
        });

        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        this.$target.attr('contentEditable', 'false');
        this._clear();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Removes the input value and suggestions.
     *
     * @private
     */
    _clear: function () {
        var self = this;
        this.$search.siblings().remove();
        self.$search.find('input').val('');
        setTimeout(function () {
            self.$search.find('input').focus();
        }, 0);
    },
    /**
     * Find existing record with the given name and suggest them.
     *
     * @private
     * @param {string} name
     * @returns {Promise}
     */
    _findExisting: function (name) {
        var self = this;
        var domain = [];
        if (!name || !name.length) {
            self.$search.siblings().remove();
            return;
        }
        if (isNaN(+name)) {
            if (this.Model !== 'res.partner') {
                domain.push(['name', 'ilike', name]);
            } else {
                domain.push('|', ['name', 'ilike', name], ['email', 'ilike', name]);
            }
        } else {
            domain.push(['id', '=', name]);
        }

        return this._rpc({
            model: this.Model,
            method: 'search_read',
            args: [domain, this.Model === 'res.partner' ? ['name', 'display_name', 'city', 'country_id'] : ['name', 'display_name']],
            kwargs: {
                order: [{name: 'name', asc: false}],
                limit: 5,
                context: this.options.context,
            },
        }).then(function (result) {
            self.$search.siblings().remove();
            self.$search.after(qweb.render('web_editor.many2one.search', {contacts: result}));
        });
    },
    /**
     * Selects the given suggestion and displays it the proper way.
     *
     * @private
     * @param {jQuery} $li
     */
    _selectRecord: function ($li) {
        var self = this;

        this.ID = +$li.data('id');
        this.$target.attr('data-oe-many2one-id', this.ID).data('oe-many2one-id', this.ID);

        this.trigger_up('request_history_undo_record', {$target: this.$target});
        this.$target.trigger('content_changed');

        if (self.$target.data('oe-type') === 'contact') {
            $('[data-oe-contact-options]')
                .filter('[data-oe-model="' + self.$target.data('oe-model') + '"]')
                .filter('[data-oe-id="' + self.$target.data('oe-id') + '"]')
                .filter('[data-oe-field="' + self.$target.data('oe-field') + '"]')
                .filter('[data-oe-contact-options!="' + self.$target.data('oe-contact-options') + '"]')
                .add(self.$target)
                .attr('data-oe-many2one-id', self.ID).data('oe-many2one-id', self.ID)
                .each(function () {
                    var $node = $(this);
                    var options = $node.data('oe-contact-options');
                    self._rpc({
                        model: 'ir.qweb.field.contact',
                        method: 'get_record_to_html',
                        args: [[self.ID]],
                        kwargs: {
                            options: options,
                            context: self.options.context,
                        },
                    }).then(function (html) {
                        $node.html(html);
                    });
                });
        } else {
            self.$target.html($li.data('name'));
        }

        _.defer(function () {
            self.trigger_up('deactivate_snippet');
        });
    }
});

return {
    SnippetOptionWidget: SnippetOptionWidget,
    snippetOptionRegistry: registry,

    UserValueWidget: UserValueWidget,
    userValueWidgetsRegistry: userValueWidgetsRegistry,

    addTitleAndAllowedAttributes: _addTitleAndAllowedAttributes,
    buildElement: _buildElement,
    buildTitleElement: _buildTitleElement,
    buildRowElement: _buildRowElement,

    // Other names for convenience
    Class: SnippetOptionWidget,
    registry: registry,
};
});
