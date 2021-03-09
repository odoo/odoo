odoo.define('web_editor.snippets.options', function (require) {
'use strict';

var core = require('web.core');
const {ColorpickerWidget} = require('web.Colorpicker');
const Dialog = require('web.Dialog');
const rpc = require('web.rpc');
const time = require('web.time');
var Widget = require('web.Widget');
var ColorPaletteWidget = require('web_editor.ColorPalette').ColorPaletteWidget;
const weUtils = require('web_editor.utils');
const {
    normalizeColor,
    getBgImageURL,
} = weUtils;
var weWidgets = require('wysiwyg.widgets');
const {
    loadImage,
    loadImageInfo,
    applyModifications,
    removeOnImageChangeAttrs,
} = require('web_editor.image_processing');

var qweb = core.qweb;
var _t = core._t;

/**
 * @param {HTMLElement} el
 * @param {string} [title]
 * @param {Object} [options]
 * @param {string[]} [options.classes]
 * @param {string} [options.tooltip]
 * @param {string} [options.placeholder]
 * @param {Object} [options.dataAttributes]
 * @returns {HTMLElement} - the original 'el' argument
 */
function _addTitleAndAllowedAttributes(el, title, options) {
    let tooltipEl = el;
    if (title) {
        const titleEl = _buildTitleElement(title);
        tooltipEl = titleEl;
        el.appendChild(titleEl);
    }

    if (options && options.classes) {
        el.classList.add(...options.classes);
    }
    if (options && options.tooltip) {
        tooltipEl.title = options.tooltip;
    }
    if (options && options.placeholder) {
        el.setAttribute('placeholder', options.placeholder);
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
 * @param {string} src
 * @returns {HTMLElement}
 */
const _buildImgElementCache = {};
async function _buildImgElement(src) {
    if (!(src in _buildImgElementCache)) {
        _buildImgElementCache[src] = (async () => {
            if (src.split('.').pop() === 'svg') {
                const response = await window.fetch(src);
                const text = await response.text();
                const parser = new window.DOMParser();
                const xmlDoc = parser.parseFromString(text, 'text/xml');
                return xmlDoc.getElementsByTagName('svg')[0];
            } else {
                const imgEl = document.createElement('img');
                imgEl.src = src;
                return imgEl;
            }
        })();
    }
    const node = await _buildImgElementCache[src];
    return node.cloneNode(true);
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
 * Build the correct DOM for a we-collapse element.
 *
 * @param {string} [title] - @see _buildElement
 * @param {Object} [options] - @see _buildElement
 * @param {HTMLElement[]} [options.childNodes]
 * @returns {HTMLElement}
 */
function _buildCollapseElement(title, options) {
    const groupEl = _buildElement('we-collapse', title, options);
    const titleEl = groupEl.querySelector('we-title');

    const children = options && options.childNodes || [];
    if (titleEl) {
        titleEl.remove();
        children.unshift(titleEl);
    }
    let i = 0;
    for (i = 0; i < children.length; i++) {
        groupEl.appendChild(children[i]);
        if (children[i].nodeType === Node.ELEMENT_NODE) {
            break;
        }
    }

    const togglerEl = document.createElement('we-toggler');
    togglerEl.classList.add('o_we_collapse_toggler');
    groupEl.appendChild(togglerEl);

    const containerEl = document.createElement('div');
    children.slice(i + 1).forEach(node => containerEl.appendChild(node));
    groupEl.appendChild(containerEl);

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

const NULL_ID = '__NULL__';

/**
 * Base class for components to be used in snippet options widgets to retrieve
 * user values.
 */
const UserValueWidget = Widget.extend({
    className: 'o_we_user_value_widget',
    custom_events: {
        'user_value_update': '_onUserValueNotification',
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
    async willStart() {
        await this._super(...arguments);
        if (this.options.dataAttributes.img) {
            this.imgEl = await _buildImgElement(this.options.dataAttributes.img);
        }
    },
    /**
     * @override
     */
    _makeDescriptive: function () {
        const $el = this._super(...arguments);
        const el = $el[0];
        _addTitleAndAllowedAttributes(el, this.title, this.options);
        this.containerEl = document.createElement('div');

        if (this.imgEl) {
            this.containerEl.appendChild(this.imgEl);
        }

        el.appendChild(this.containerEl);
        return $el;
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        if (this.el.classList.contains('o_we_img_animate')) {
            const buildImgExtensionSwitcher = (from, to) => {
                const regex = new RegExp(`${from}$`, 'i');
                return ev => {
                    const img = ev.currentTarget.getElementsByTagName("img")[0];
                    img.src = img.src.replace(regex, to);
                };
            };
            this.$el.on('mouseenter.img_animate', buildImgExtensionSwitcher('png', 'gif'));
            this.$el.on('mouseleave.img_animate', buildImgExtensionSwitcher('gif', 'png'));
        }
    },
    /**
     * @override
     */
    destroy() {
        // Check if $el exists in case the widget is destroyed before it has
        // been fully initialized.
        // TODO there is probably better to do. This case was found only in
        // tours, where the editor is left before the widget icon is loaded.
        if (this.$el) {
            this.$el.off('.img_animate');
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Closes the widget (only meaningful for widgets that can be closed).
     */
    close: function () {
        if (!this.el) {
            // In case the method is called while the widget is not fully
            // initialized yet. No need to prevent that case: asking a non
            // initialized widget to close itself should just not be a problem
            // and just be ignored.
            return;
        }
        this.trigger_up('user_value_widget_closing');
        this.el.classList.remove('o_we_widget_opened');
        this._userValueWidgets.forEach(widget => widget.close());
    },
    /**
     * Simulates the correct event on the element to make it active.
     */
    enable() {
        this.$el.click();
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
        return this._value && this._value !== NULL_ID;
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
                && (this.el === focusEl || this.el.contains(focusEl))) {
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
        this._triggerWidgetsNames = [];
        this._triggerWidgetsValues = [];

        for (const key in this.el.dataset) {
            const dataValue = this.el.dataset[key].trim();

            if (key === 'dependencies') {
                this._dependencies.push(...dataValue.split(/\s*,\s*/g));
            } else if (key === 'trigger') {
                this._triggerWidgetsNames.push(...dataValue.split(/\s*,\s*/g));
            } else if (key === 'triggerValue') {
                this._triggerWidgetsValues.push(...dataValue.split(/\s*,\s*/g));
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
     * @param {boolean} [previewMode=false]
     * @param {boolean} [isSimulatedEvent=false]
     */
    notifyValueChange: function (previewMode, isSimulatedEvent) {
        // If the widget has no associated method, it should not notify user
        // value changes
        if (!this._methodsNames.length) {
            return;
        }

        // In the case we notify a change update, force a preview update if it
        // was not already previewed
        const isPreviewed = this.isPreviewed();
        if (!previewMode && !isPreviewed) {
            this.notifyValueChange(true);
        }

        const data = {
            previewMode: previewMode || false,
            isSimulatedEvent: !!isSimulatedEvent,
        };
        // TODO improve this. The preview state has to be updated only when the
        // actual option _select is gonna be called... but this is delayed by a
        // mutex. So, during test tours, we would notify both 'preview' and
        // 'reset' before the 'preview' handling is done: and so the widget
        // would not be considered in preview during that 'preview' handling.
        if (previewMode === true || previewMode === false) {
            // Note: the widgets need to be considered in preview mode during
            // non-preview handling (a previewed checkbox is considered having
            // an inverted state)... but if, for example, a modal opens before
            // handling that non-preview, a 'reset' will be thrown thus removing
            // the preview class. So we force it in non-preview too.
            data.prepare = () => this.el.classList.add('o_we_preview');
        } else if (previewMode === 'reset') {
            data.prepare = () => this.el.classList.remove('o_we_preview');
        }

        this.trigger_up('user_value_update', data);
    },
    /**
     * Opens the widget (only meaningful for widgets that can be opened).
     */
    open() {
        this.trigger_up('user_value_widget_opening');
        this.el.classList.add('o_we_widget_opened');
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
    async setValue(value, methodName) {
        this._value = value;
        this.el.classList.remove('o_we_preview');
    },
    /**
     * @param {boolean} show
     */
    toggleVisibility: function (show) {
        this.el.classList.toggle('d-none', !show);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent|Event}
     * @returns {boolean}
     */
    _handleNotifierEvent: function (ev) {
        if (!ev) {
            return true;
        }
        if (ev._seen) {
            return false;
        }
        ev._seen = true;
        if (ev.preventDefault) {
            ev.preventDefault();
        }
        return true;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Should be called when an user event on the widget indicates a value
     * change.
     *
     * @private
     * @param {OdooEvent|Event} [ev]
     */
    _onUserValueChange: function (ev) {
        if (this._handleNotifierEvent(ev)) {
            this.notifyValueChange(false);
        }
    },
    /**
     * Allows container widgets to add additional data if needed.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onUserValueNotification: function (ev) {
        ev.data.widget = this;

        if (!ev.data.triggerWidgetsNames) {
            ev.data.triggerWidgetsNames = [];
        }
        ev.data.triggerWidgetsNames.push(...this._triggerWidgetsNames);

        if (!ev.data.triggerWidgetsValues) {
            ev.data.triggerWidgetsValues = [];
        }
        ev.data.triggerWidgetsValues.push(...this._triggerWidgetsValues);
    },
    /**
     * Should be called when an user event on the widget indicates a value
     * preview.
     *
     * @private
     * @param {OdooEvent|Event} [ev]
     */
    _onUserValuePreview: function (ev) {
        if (this._handleNotifierEvent(ev)) {
            this.notifyValueChange(true);
        }
    },
    /**
     * Should be called when an user event on the widget indicates a value
     * reset.
     *
     * @private
     * @param {OdooEvent|Event} [ev]
     */
    _onUserValueReset: function (ev) {
        if (this._handleNotifierEvent(ev)) {
            this.notifyValueChange('reset');
        }
    },
});

const ButtonUserValueWidget = UserValueWidget.extend({
    tagName: 'we-button',
    events: {
        'click': '_onButtonClick',
        'click [role="button"]': '_onInnerButtonClick',
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
    async setValue(value, methodName) {
        await this._super(...arguments);
        let active = !!value;
        if (methodName) {
            if (!this._methodsNames.includes(methodName)) {
                return;
            }
            active = (this.getActiveValue(methodName) === value);
        }
        this.el.classList.toggle('active', active);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onButtonClick: function (ev) {
        if (!ev._innerButtonClicked) {
            this._onUserValueChange(ev);
        }
    },
    /**
     * @private
     */
    _onInnerButtonClick: function (ev) {
        // Cannot just stop propagation as the click needs to be propagated to
        // potential parent widgets for event delegation on those inner buttons.
        ev._innerButtonClicked = true;
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

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    enable() {
        this.$('we-checkbox').click();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onButtonClick(ev) {
        if (!ev.target.closest('we-title, we-checkbox')) {
            // Only consider clicks on the label and the checkbox control itself
            return;
        }
        return this._super(...arguments);
    },
});

const BaseSelectionUserValueWidget = UserValueWidget.extend({
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        this.menuEl = document.createElement('we-selection-items');
        if (this.options && this.options.childNodes) {
            this.options.childNodes.forEach(node => this.menuEl.appendChild(node));
        }
        this.containerEl.appendChild(this.menuEl);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams(methodName) {
        const params = this._super(...arguments);
        const activeWidget = this._getActiveSubWidget();
        if (!activeWidget) {
            return params;
        }
        return Object.assign(activeWidget.getMethodsParams(...arguments), params);
    },
    /**
     * @override
     */
    getValue(methodName) {
        const activeWidget = this._getActiveSubWidget();
        if (activeWidget) {
            return activeWidget.getActiveValue(methodName);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    isContainer() {
        return true;
    },
    /**
     * @override
     */
    async setValue(value, methodName) {
        const _super = this._super.bind(this);
        for (const widget of this._userValueWidgets) {
            await widget.setValue(NULL_ID, methodName);
        }
        for (const widget of [...this._userValueWidgets].reverse()) {
            await widget.setValue(value, methodName);
            if (widget.isActive()) {
                // Only one select item can be true at a time, we consider the
                // last one if multiple would be active.
                return;
            }
        }
        await _super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {UserValueWidget|undefined}
     */
    _getActiveSubWidget() {
        const previewedWidget = this._userValueWidgets.find(widget => widget.isPreviewed());
        if (previewedWidget) {
            return previewedWidget;
        }
        return this._userValueWidgets.find(widget => widget.isActive());
    },
});

const SelectUserValueWidget = BaseSelectionUserValueWidget.extend({
    tagName: 'we-select',
    events: {
        'click': '_onClick',
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        if (this.options && this.options.valueEl) {
            this.containerEl.insertBefore(this.options.valueEl, this.menuEl);
        }

        this.menuTogglerEl = document.createElement('we-toggler');
        this.icon = this.el.dataset.icon || false;
        if (this.icon) {
            this.el.classList.add('o_we_icon_select');
            const iconEl = document.createElement('i');
            iconEl.classList.add('fa', 'fa-fw', this.icon);
            this.menuTogglerEl.appendChild(iconEl);
        }
        this.containerEl.insertBefore(this.menuTogglerEl, this.menuEl);

        const dropdownCaretEl = document.createElement('span');
        dropdownCaretEl.classList.add('o_we_dropdown_caret');
        this.containerEl.appendChild(dropdownCaretEl);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    close: function () {
        this._super(...arguments);
        if (this.menuTogglerEl) {
            this.menuTogglerEl.classList.remove('active');
        }
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
    open() {
        this._super(...arguments);
        this.menuTogglerEl.classList.add('active');
    },
    /**
     * @override
     */
    async setValue() {
        await this._super(...arguments);

        if (this.icon) {
            return;
        }

        if (this.menuTogglerItemEl) {
            this.menuTogglerItemEl.remove();
            this.menuTogglerItemEl = null;
        }

        let textContent = '';
        const activeWidget = this._userValueWidgets.find(widget => !widget.isPreviewed() && widget.isActive());
        if (activeWidget) {
            const svgTag = activeWidget.el.querySelector('svg'); // useful to avoid searching text content in svg element
            const value = (activeWidget.el.dataset.selectLabel || (!svgTag && activeWidget.el.textContent.trim()));
            const imgSrc = activeWidget.el.dataset.img;
            if (value) {
                textContent = value;
            } else if (imgSrc) {
                this.menuTogglerItemEl = document.createElement('img');
                this.menuTogglerItemEl.src = imgSrc;
            } else {
                const fakeImgEl = activeWidget.el.querySelector('.o_we_fake_img_item');
                if (fakeImgEl) {
                    this.menuTogglerItemEl = fakeImgEl.cloneNode(true);
                }
            }
        } else {
            textContent = "/";
        }

        this.menuTogglerEl.textContent = textContent;
        if (this.menuTogglerItemEl) {
            this.menuTogglerEl.appendChild(this.menuTogglerItemEl);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the select is clicked anywhere -> open/close it.
     *
     * @private
     */
    _onClick: function (ev) {
        if (ev.target.closest('[role="button"]')) {
            return;
        }

        if (!this.menuTogglerEl.classList.contains('active')) {
            this.open();
        } else {
            this.close();
        }
        const activeButton = this._userValueWidgets.find(widget => widget.isActive());
        if (activeButton) {
            this.menuEl.scrollTop = activeButton.el.offsetTop - (this.menuEl.offsetHeight / 2);
        }
    },
});

const ButtonGroupUserValueWidget = BaseSelectionUserValueWidget.extend({
    tagName: 'we-button-group',
});

const UnitUserValueWidget = UserValueWidget.extend({
    /**
     * @override
     */
    start: async function () {
        const unit = this.el.dataset.unit || '';
        this.el.dataset.unit = unit;
        if (this.el.dataset.saveUnit === undefined) {
            this.el.dataset.saveUnit = unit;
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
        return isSuperActive && this._floatToStr(parseFloat(this._value)) !== '0';
    },
    /**
     * @override
     */
    async setValue(value, methodName) {
        const params = this._methodsParams;
        if (params.unit) {
            value = value.split(' ').map(v => {
                const numValue = weUtils.convertValueToUnit(v, params.unit, params.cssProperty, this.$target);
                if (isNaN(numValue)) {
                    return ''; // Something not supported
                }
                return this._floatToStr(numValue);
            }).join(' ');
        }
        return this._super(value, methodName);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Converts a floating value to a string, rounded to 5 digits without zeros.
     *
     * @private
     * @param {number} value
     * @returns {string}
     */
    _floatToStr: function (value) {
        return `${parseFloat(value.toFixed(5))}`;
    },
});

const InputUserValueWidget = UnitUserValueWidget.extend({
    tagName: 'we-input',
    events: {
        'input input': '_onInputInput',
        'blur input': '_onInputBlur',
        'keydown input': '_onInputKeydown',
    },

    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);

        const unit = this.el.dataset.unit;
        this.inputEl = document.createElement('input');
        this.inputEl.setAttribute('type', 'text');
        this.inputEl.setAttribute('autocomplete', 'chrome-off');
        this.inputEl.setAttribute('placeholder', this.el.getAttribute('placeholder') || '');
        this.inputEl.classList.toggle('text-left', !unit);
        this.inputEl.classList.toggle('text-right', !!unit);
        this.containerEl.appendChild(this.inputEl);

        var unitEl = document.createElement('span');
        unitEl.textContent = unit;
        this.containerEl.appendChild(unitEl);
        if (unit.length > 3) {
            this.el.classList.add('o_we_large_input');
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async setValue() {
        await this._super(...arguments);
        this.inputEl.value = this._value;
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
    async setValue(value, methodName) {
        let values = value.split(/\s*\|\s*/g);
        if (values.length === 1) {
            values = value.split(/\s+/g);
        }
        for (let i = 0; i < this._userValueWidgets.length - 1; i++) {
            await this._userValueWidgets[i].setValue(values.shift() || '', methodName);
        }
        await this._userValueWidgets[this._userValueWidgets.length - 1].setValue(values.join(' '), methodName);
    },
});

const ColorpickerUserValueWidget = SelectUserValueWidget.extend({
    className: (SelectUserValueWidget.prototype.className || '') + ' o_we_so_color_palette',
    custom_events: _.extend({}, SelectUserValueWidget.prototype.custom_events, {
        'custom_color_picked': '_onCustomColorPicked',
        'color_picked': '_onColorPicked',
        'color_hover': '_onColorHovered',
        'color_leave': '_onColorLeft',
        'enter_key_color_colorpicker': '_onEnterKey'
    }),

    /**
     * @override
     */
    start: async function () {
        const _super = this._super.bind(this);
        const args = arguments;

        // TODO review in master, this was done in stable to keep the speed fix
        // as stable as possible (to have a reference to a widget even if not a
        // colorPalette widget).
        this.colorPalette = new Widget(this);
        this.colorPalette.getColorNames = () => [];
        await this.colorPalette.appendTo(document.createDocumentFragment());

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
    open: function () {
        if (this.colorPalette.setSelectedColor) {
            this.colorPalette.setSelectedColor(this._value);
        } else {
            // TODO review in master, this does async stuff. Maybe the open
            // method should now be async. This is not really robust as the
            // colorPalette can be used without it to be fully rendered but
            // the use of the saved promise where we can should mitigate that
            // issue.
            this._colorPaletteRenderPromise = this._renderColorPalette();
        }
        this._super(...arguments);
    },
    /**
     * @override
     */
    close: function () {
        this._super(...arguments);
        if (this._customColorValue && this._customColorValue !== this._value) {
            this._value = this._customColorValue;
            this._customColorValue = false;
            this._onUserValueChange();
        }
    },
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
        if (typeof this._previewColor === 'string') {
            return this._previewColor;
        }
        if (typeof this._customColorValue === 'string') {
            return this._customColorValue;
        }
        let value = this._super(...arguments);
        if (value) {
            const useCssColor = this.options.dataAttributes.hasOwnProperty('useCssColor');
            const cssCompatible = this.options.dataAttributes.hasOwnProperty('cssCompatible');
            if ((useCssColor || cssCompatible) && !ColorpickerWidget.isCSSColor(value)) {
                if (useCssColor) {
                    value = weUtils.getCSSVariableValue(value);
                } else {
                    value = `var(--${value})`;
                }
            }
        }
        return value;
    },
    /**
     * @override
     */
    isContainer: function () {
        return false;
    },
    /**
     * @override
     */
    isActive: function () {
        return !weUtils.areCssValuesEqual(this._value, 'rgba(0, 0, 0, 0)');
    },
    /**
     * Updates the color preview + re-render the whole color palette widget.
     *
     * @override
     */
    async setValue(color) {
        await this._super(...arguments);

        await this._colorPaletteRenderPromise;

        const classes = weUtils.computeColorClasses(this.colorPalette.getColorNames());
        this.colorPreviewEl.classList.remove(...classes);
        this.colorPreviewEl.style.removeProperty('background-color');

        if (this._value) {
            if (ColorpickerWidget.isCSSColor(this._value)) {
                this.colorPreviewEl.style.backgroundColor = this._value;
            } else if (weUtils.isColorCombinationName(this._value)) {
                this.colorPreviewEl.classList.add('o_cc', `o_cc${this._value}`);
            } else {
                this.colorPreviewEl.classList.add(`bg-${this._value}`);
            }
        }
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {Promise}
     */
    _renderColorPalette: function () {
        const options = {
            selectedColor: this._value,
        };
        if (this.options.dataAttributes.excluded) {
            options.excluded = this.options.dataAttributes.excluded.replace(/ /g, '').split(',');
        }
        if (this.options.dataAttributes.withCombinations) {
            options.withCombinations = !!this.options.dataAttributes.withCombinations;
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a custom color is selected -> preview the color
     * and set the current value. Update of this value on close
     *
     * @private
     * @param {Event} ev
     */
    _onCustomColorPicked: function (ev) {
        this._customColorValue = ev.data.color;
    },
    /**
     * Called when a color button is clicked -> confirms the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorPicked: function (ev) {
        this._previewColor = false;
        this._customColorValue = false;
        this._value = ev.data.color;
        this._onUserValueChange(ev);
    },
    /**
     * Called when a color button is entered -> previews the background color.
     *
     * @private
     * @param {Event} ev
     */
    _onColorHovered: function (ev) {
        this._previewColor = ev.data.color;
        this._onUserValuePreview(ev);
    },
    /**
     * Called when a color button is left -> cancels the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onColorLeft: function (ev) {
        this._previewColor = false;
        this._onUserValueReset(ev);
    },
    /**
     * @private
     */
    _onEnterKey: function () {
        this.close();
    },
    /**
     * @override
     */
    _onClick: function (ev) {
        // Do not close the colorpalette on colorpicker click
        if (!ev.originalEvent.__isColorpickerClick) {
            this._super(...arguments);
        }
        ev.stopPropagation();
    },
});

const MediapickerUserValueWidget = UserValueWidget.extend({
    tagName: 'we-button',
    events: {
        'click': '_onEditMedia',
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        const iconEl = document.createElement('i');
        if (this.options.dataAttributes.buttonStyle) {
            iconEl.classList.add('fa', 'fa-fw', 'fa-camera');
        } else {
            iconEl.classList.add('fa', 'fa-fw', 'fa-refresh', 'mr-1');
            this.el.classList.add('o_we_no_toggle');
            this.containerEl.textContent = _t("Replace media");
        }
        $(this.containerEl).prepend(iconEl);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates and opens a media dialog to edit a given element's media.
     *
     * @private
     * @param {HTMLElement} el the element whose media should be edited
     * @param {boolean} [images] whether images should be available
     *   default: false
     * @param {boolean} [videos] whether videos should be available
     *   default: false
     */
    _openDialog(el, {images = false, videos = false}) {
        el.src = this._value;
        const $editable = this.$target.closest('.o_editable');
        const mediaDialog = new weWidgets.MediaDialog(this, {
            noImages: !images,
            noVideos: !videos,
            noIcons: true,
            noDocuments: true,
            isForBgVideo: true,
            'res_model': $editable.data('oe-model'),
            'res_id': $editable.data('oe-id'),
        }, el).open();
        return mediaDialog;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async setValue() {
        await this._super(...arguments);
        this.el.classList.toggle('active', this.isActive());
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the edit button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onEditMedia: function (ev) {},
});

const ImagepickerUserValueWidget = MediapickerUserValueWidget.extend({
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onEditMedia(ev) {
        // Need a dummy element for the media dialog to modify.
        const dummyEl = document.createElement('img');
        const dialog = this._openDialog(dummyEl, {images: true});
        dialog.on('save', this, data => {
            // Accessing the value directly through dummyEl.src converts the url to absolute,
            // using getAttribute allows us to keep the url as it was inserted in the DOM
            // which can be useful to compare it to values stored in db.
            this._value = dummyEl.getAttribute('src');
            this._onUserValueChange();
        });
    },
});

const VideopickerUserValueWidget = MediapickerUserValueWidget.extend({
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onEditMedia(ev) {
        // Need a dummy element for the media dialog to modify.
        const dummyEl = document.createElement('iframe');
        const dialog = this._openDialog(dummyEl, {videos: true});
        dialog.on('save', this, data => {
            this._value = data.bgVideoSrc;
            this._onUserValueChange();
        });
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
        this.el.classList.add('o_we_large_input');
        this.inputEl.classList.add('datetimepicker-input', 'mx-0', 'text-left');
        this.inputEl.setAttribute('id', datetimePickerId);
        this.inputEl.setAttribute('data-target', '#' + datetimePickerId);

        const datepickersOptions = {
            minDate: moment({ y: 1000 }),
            maxDate: moment().add(200, 'y'),
            calendarWeeks: true,
            defaultDate: moment().format(),
            icons: {
                close: 'fa fa-check primary',
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
    /**
     * @override
     */
    async setValue() {
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

const RangeUserValueWidget = UnitUserValueWidget.extend({
    tagName: 'we-range',
    events: {
        'change input': '_onInputChange',
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.input = document.createElement('input');
        this.input.type = "range";
        let min = this.el.dataset.min && parseFloat(this.el.dataset.min) || 0;
        let max = this.el.dataset.max && parseFloat(this.el.dataset.max) || 100;
        const step = this.el.dataset.step && parseFloat(this.el.dataset.step) || 1;
        if (min > max) {
            [min, max] = [max, min];
            this.input.classList.add('o_we_inverted_range');
        }
        this.input.setAttribute('min', min);
        this.input.setAttribute('max', max);
        this.input.setAttribute('step', step);
        this.containerEl.appendChild(this.input);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async setValue(value, methodName) {
        await this._super(...arguments);
        this.input.value = this._value;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInputChange(ev) {
        this._value = ev.target.value;
        this._onUserValueChange(ev);
    },
});

const SelectPagerUserValueWidget = SelectUserValueWidget.extend({
    className: (SelectUserValueWidget.prototype.className || '') + ' o_we_select_pager',
    events: Object.assign({}, SelectUserValueWidget.prototype.events, {
        'click .o_we_pager_next, .o_we_pager_prev': '_onPageChange',
    }),

    /**
     * @override
     */
    async start() {
        const _super = this._super.bind(this);
        this.pages = this.options.childNodes.filter(node => node.matches && node.matches('we-select-page'));
        this.numPages = this.pages.length;

        const prev = document.createElement('i');
        prev.classList.add('o_we_pager_prev', 'fa', 'fa-chevron-left');

        this.pageNum = document.createElement('span');
        this.currentPage = 0;

        const next = document.createElement('i');
        next.classList.add('o_we_pager_next', 'fa', 'fa-chevron-right');

        const pagerControls = document.createElement('div');
        pagerControls.classList.add('o_we_pager_controls');
        pagerControls.appendChild(prev);
        pagerControls.appendChild(this.pageNum);
        pagerControls.appendChild(next);

        this.pageName = document.createElement('b');
        const pagerHeader = document.createElement('div');
        pagerHeader.classList.add('o_we_pager_header');
        pagerHeader.appendChild(this.pageName);
        pagerHeader.appendChild(pagerControls);

        await _super(...arguments);
        this.menuEl.classList.add('o_we_has_pager');
        $(this.menuEl).prepend(pagerHeader);
        this._updatePage();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates the pager's page number display.
     *
     * @private
     */
    _updatePage() {
        this.pages.forEach((page, i) => page.classList.toggle('active', i === this.currentPage));
        this.pageNum.textContent = `${this.currentPage + 1}/${this.numPages}`;
        const activePage = this.pages.find((page, i) => i === this.currentPage);
        this.pageName.textContent = activePage.getAttribute('string');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Goes to the previous/next page with wrap-around.
     *
     * @private
     */
    _onPageChange(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const delta = ev.target.matches('.o_we_pager_next') ? 1 : -1;
        this.currentPage = (this.currentPage + this.numPages + delta) % this.numPages;
        this._updatePage();
    },
    /**
     * @override
     */
    _onClick(ev) {
        const activeButton = this._getActiveSubWidget();
        if (activeButton) {
            const currentPage = this.pages.indexOf(activeButton.el.closest('we-select-page'));
            if (currentPage !== -1) {
                this.currentPage = currentPage;
                this._updatePage();
            }
        }
        return this._super(...arguments);
    },
});

const userValueWidgetsRegistry = {
    'we-button': ButtonUserValueWidget,
    'we-checkbox': CheckboxUserValueWidget,
    'we-select': SelectUserValueWidget,
    'we-button-group': ButtonGroupUserValueWidget,
    'we-input': InputUserValueWidget,
    'we-multi': MultiUserValueWidget,
    'we-colorpicker': ColorpickerUserValueWidget,
    'we-datetimepicker': DatetimePickerUserValueWidget,
    'we-imagepicker': ImagepickerUserValueWidget,
    'we-videopicker': VideopickerUserValueWidget,
    'we-range': RangeUserValueWidget,
    'we-select-pager': SelectPagerUserValueWidget,
};

/**
 * Handles a set of options for one snippet. The registry returned by this
 * module contains the names of the specialized SnippetOptionWidget which can be
 * referenced thanks to the data-js key in the web_editor options template.
 */
const SnippetOptionWidget = Widget.extend({
    tagName: 'we-customizeblock-option',
    events: {
        'click .o_we_collapse_toggler': '_onCollapseTogglerClick',
    },
    custom_events: {
        'user_value_update': '_onUserValueUpdate',
        'user_value_widget_critical': '_onUserValueWidgetCritical',
    },
    /**
     * Indicates if the option should be displayed in the button group at the
     * top of the options panel, next to the clone/remove button.
     *
     * @type {boolean}
     */
    isTopOption: false,
    /**
     * Forces the target to not be possible to remove.
     *
     * @type {boolean}
     */
    forceNoDeleteButton: false,

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
        this._actionQueues = new Map();
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
        const value = this._selectAttributeHelper(widgetValue, params);
        this.$target[0].dataset[params.attributeName] = value;
    },
    /**
     * Default option method which allows to select a value and set it on the
     * associated snippet as an attribute. The name of the attribute is
     * given by the attributeName parameter.
     *
     * @param {boolean} previewMode - @see this.selectClass
     * @param {string} widgetValue
     * @param {Object} params
     * @returns {Promise|undefined}
     */
    selectAttribute: function (previewMode, widgetValue, params) {
        const value = this._selectAttributeHelper(widgetValue, params);
        this.$target[0].setAttribute(params.attributeName, value);
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
    selectStyle: function (previewMode, widgetValue, params) {
        // Disable all transitions for the duration of the method as many
        // comparisons will be done on the element to know if applying a
        // property has an effect or not. Also, changing a css property via the
        // editor should not show any transition as previews would not be done
        // immediately, which is not good for the user experience.
        this.$target[0].classList.add('o_we_force_no_transition');
        const _restoreTransitions = () => this.$target[0].classList.remove('o_we_force_no_transition');

        if (params.cssProperty === 'background-color') {
            this.$target.trigger('background-color-event', previewMode);
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
            const classes = weUtils.computeColorClasses(params.colorNames, params.colorPrefix);
            this.$target[0].classList.remove(...classes);

            if (weUtils.isColorCombinationName(widgetValue)) {
                // Those are the special color combinations classes. Just have
                // to add it (and adding the potential extra class) then leave.
                this.$target[0].classList.add('o_cc', `o_cc${widgetValue}`, params.extraClass);
                _restoreTransitions();
                return;
            }
            if (params.colorNames.includes(widgetValue)) {
                const originalCSSValue = window.getComputedStyle(this.$target[0])[cssProps[0]];
                const className = params.colorPrefix + widgetValue;
                this.$target[0].classList.add(className);
                if (originalCSSValue !== window.getComputedStyle(this.$target[0])[cssProps[0]]) {
                    // If applying the class did indeed changed the css
                    // property we are editing, nothing more has to be done.
                    // (except adding the extra class)
                    this.$target.addClass(params.extraClass);
                    _restoreTransitions();
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
        const htmlPropValue = weUtils.getCSSVariableValue(widgetValue);
        if (htmlPropValue) {
            widgetValue = `var(--${widgetValue})`;
        }

        // replacing ', ' by ',' to prevent attributes with internal space separators from being split:
        // eg: "rgba(55, 12, 47, 1.9) 47px" should be split as ["rgba(55,12,47,1.9)", "47px"]
        const values = widgetValue.replace(/,\s/g, ',').split(/\s+/g);
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

        _restoreTransitions();
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
    notify: function (name, data) {
        if (name === 'target') {
            this.setTarget(data);
        }
    },
    /**
     * Sometimes, an option is binded on an element but should in fact apply on
     * another one. For example, elements which contain slides: we want all the
     * per-slide options to be in the main menu of the whole snippet. This
     * function allows to set the option's target.
     *
     * Note: the UI is not updated accordindly automatically.
     *
     * @param {jQuery} $target - the new target element
     * @returns {Promise}
     */
    setTarget: function ($target) {
        this.$target = $target;
    },
    /**
     * Updates the UI. For widget update, @see _computeWidgetState.
     *
     * @param {boolean} [noVisibility=false]
     *     If true, only update widget values and their UI, not their visibility
     *     -> @see updateUIVisibility for toggling visibility only
     * @returns {Promise}
     */
    updateUI: async function ({noVisibility} = {}) {
        // For each widget, for each of their option method, notify to the
        // widget the current value they should hold according to the $target's
        // current state, related for that method.
        const proms = this._userValueWidgets.map(async widget => {
            // Update widget value (for each method)
            const methodsNames = widget.getMethodsNames();
            for (const methodName of methodsNames) {
                const params = widget.getMethodsParams(methodName);

                let obj = this;
                if (params.applyTo) {
                    const $firstSubTarget = this.$(params.applyTo).eq(0);
                    if (!$firstSubTarget.length) {
                        continue;
                    }
                    obj = createPropertyProxy(this, '$target', $firstSubTarget);
                }

                const value = await this._computeWidgetState.call(obj, methodName, params);
                if (value === undefined) {
                    continue;
                }
                const normalizedValue = this._normalizeWidgetValue(value);
                await widget.setValue(normalizedValue, methodName);
            }
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

            // Make sure to check the visibility of all sub-widgets. For
            // simplicity and efficiency, those will be checked with main
            // widgets params.
            const allSubWidgets = [widget];
            let i = 0;
            while (i < allSubWidgets.length) {
                allSubWidgets.push(...allSubWidgets[i]._userValueWidgets);
                i++;
            }
            const proms = allSubWidgets.map(async widget => {
                const show = await this._computeWidgetVisibility.call(obj, widget.getName(), params);
                if (!show) {
                    widget.toggleVisibility(false);
                    return;
                }

                const dependencies = widget.getDependencies();
                const dependenciesData = [];
                dependencies.forEach(depName => {
                    const toBeActive = (depName[0] !== '!');
                    if (!toBeActive) {
                        depName = depName.substr(1);
                    }

                    const widget = this._requestUserValueWidgets(depName)[0];
                    if (widget) {
                        dependenciesData.push({
                            widget: widget,
                            toBeActive: toBeActive,
                        });
                    }
                });
                const dependenciesOK = !dependenciesData.length || dependenciesData.some(depData => {
                    return (depData.widget.isActive() === depData.toBeActive);
                });

                widget.toggleVisibility(dependenciesOK);
            });
            return Promise.all(proms);
        });

        const showUI = await this._computeVisibility();
        this.el.classList.toggle('d-none', !showUI);

        await Promise.all(proms);

        // Hide layouting elements which contains only hidden widgets
        // TODO improve this, this is hackish to rely on DOM structure here.
        // Layouting elements should be handled as widgets or other.
        for (const el of this.$el.find('we-row')) {
            el.classList.toggle('d-none', !$(el).find('> div > .o_we_user_value_widget').not('.d-none').length);
        }
        for (const el of this.$el.find('we-collapse')) {
            const $el = $(el);
            el.classList.toggle('d-none', $el.children().first().hasClass('d-none'));
            const hasNoVisibleElInCollapseMenu = !$el.children().last().children().not('.d-none').length;
            if (hasNoVisibleElInCollapseMenu) {
                this._toggleCollapseEl(el, false);
            }
            el.querySelector('.o_we_collapse_toggler').classList.toggle('d-none', hasNoVisibleElInCollapseMenu);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {UserValueWidget[]} widgets
     * @returns {Promise<string>}
     */
    async _checkIfWidgetsUpdateNeedWarning(widgets) {
        const messages = [];
        for (const widget of widgets) {
            const message = widget.getMethodsParams().warnMessage;
            if (message) {
                messages.push(message);
            }
        }
        return messages.join(' ');
    },
    /**
     * @private
     * @param {UserValueWidget[]} widgets
     * @returns {Promise<boolean|string>}
     */
    async _checkIfWidgetsUpdateNeedReload(widgets) {
        return false;
    },
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
            case 'selectAttribute':
            case 'selectDataAttribute': {
                const attrName = params.attributeName;
                let attrValue;
                if (methodName === 'selectAttribute') {
                    attrValue = this.$target[0].getAttribute(attrName);
                } else if (methodName === 'selectDataAttribute') {
                    attrValue = this.$target[0].dataset[attrName];
                }
                attrValue = (attrValue || '').trim();
                if (params.saveUnit && !params.withUnit) {
                    attrValue = attrValue.split(/\s+/g).map(v => v + params.saveUnit).join(' ');
                }
                return attrValue || params.attributeDefaultValue || '';
            }
            case 'selectStyle': {
                if (params.colorPrefix && params.colorNames) {
                    for (const c of params.colorNames) {
                        const className = weUtils.computeColorClasses([c], params.colorPrefix)[0];
                        if (this.$target[0].classList.contains(className)) {
                            return c;
                        }
                    }
                }

                // Disable all transitions for the duration of the style check
                // as we want to know the final value of a property to properly
                // update the UI.
                this.$target[0].classList.add('o_we_force_no_transition');
                const _restoreTransitions = () => this.$target[0].classList.remove('o_we_force_no_transition');

                const styles = window.getComputedStyle(this.$target[0]);
                const cssProps = weUtils.CSS_SHORTHANDS[params.cssProperty] || [params.cssProperty];
                const cssValues = cssProps.map(cssProp => {
                    let value = styles[cssProp].trim();
                    if (cssProp === 'box-shadow') {
                        const inset = value.includes('inset');
                        let values = value.replace(/,\s/g, ',').replace('inset', '').trim().split(/\s+/g);
                        const color = values.find(s => !s.match(/^\d/));
                        values = values.join(' ').replace(color, '').trim();
                        value = `${color} ${values}${inset ? ' inset' : ''}`;
                    }
                    return value;
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

                _restoreTransitions();

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
        if (widgetName === 'move_up_opt' || widgetName === 'move_left_opt') {
            return !this.$target.is(':first-child');
        }
        if (widgetName === 'move_down_opt' || widgetName === 'move_right_opt') {
            return !this.$target.is(':last-child');
        }
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
                tooltip: el.title,
                placeholder: el.getAttribute('placeholder'),
                childNodes: [...el.childNodes],
            },
        };
    },
    /**
     * @private
     * @param {*}
     * @returns {string}
     */
    _normalizeWidgetValue: function (value) {
        value = `${value}`.trim(); // Force to a trimmed string
        value = ColorpickerWidget.normalizeCSSColor(value); // If is a css color, normalize it
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

        await this._renderCustomXML(uiFragment);

        // Build layouting components first
        for (const [itemName, build] of [['we-row', _buildRowElement], ['we-collapse', _buildCollapseElement]]) {
            uiFragment.querySelectorAll(itemName).forEach(el => {
                const infos = this._extraInfoFromDescriptionElement(el);
                const groupEl = build(infos.title, infos.options);
                el.parentNode.insertBefore(groupEl, el);
                el.parentNode.removeChild(el);
            });
        }

        // Load widgets
        await this._renderXMLWidgets(uiFragment);
        await this._renderCustomWidgets(uiFragment);

        if (this.isDestroyed()) {
            // TODO there is probably better to do. This case was found only in
            // tours, where the editor is left before the widget are fully
            // loaded (loadMethodsData doesn't work if the widget is destroyed).
            return uiFragment;
        }

        const validMethodNames = [];
        for (const key in this) {
            validMethodNames.push(key);
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
     * @param {...string} widgetNames
     * @returns {UserValueWidget[]}
     */
    _requestUserValueWidgets: function (...widgetNames) {
        const widgets = [];
        for (const widgetName of widgetNames) {
            let widget = null;
            this.trigger_up('user_value_widget_request', {
                name: widgetName,
                onSuccess: _widget => widget = _widget,
            });
            if (widget) {
                widgets.push(widget);
            }
        }
        return widgets;
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
        let $applyTo = null;

        // Call each option method sequentially
        for (const methodName of widget.getMethodsNames()) {
            const widgetValue = widget.getValue(methodName);
            const params = widget.getMethodsParams(methodName);

            if (params.applyTo) {
                if (!$applyTo) {
                    $applyTo = this.$(params.applyTo);
                }
                const proms = _.map($applyTo, subTargetEl => {
                    const proxy = createPropertyProxy(this, '$target', $(subTargetEl));
                    return this[methodName].call(proxy, previewMode, widgetValue, params);
                });
                await Promise.all(proms);
            } else {
                await this[methodName](previewMode, widgetValue, params);
            }
        }

        // We trigger the event on elements targeted by apply-to if any as
        // this.$target could not be in an editable element while the elements
        // targeted by apply-to are.
        ($applyTo || this.$target).trigger('content_changed');
    },
    /**
     * Used to handle attribute or data attribute value change
     *
     * @param {string} value
     * @param {Object} params
     * @returns {string|undefined}
     */
    _selectAttributeHelper(value, params) {
        if (!params.attributeName) {
            throw new Error('Attribute name missing');
        }
        if (params.saveUnit && !params.withUnit) {
            // Values that come with an unit are saved without unit as
            // data-attribute unless told otherwise.
            value = value.split(params.saveUnit).join('');
        }
        if (params.extraClass) {
            this.$target.toggleClass(params.extraClass, params.defaultValue !== value);
        }
        return value;
    },
    /**
     * @private
     * @param {HTMLElement} collapseEl
     * @param {boolean|undefined} [show]
     */
    _toggleCollapseEl(collapseEl, show) {
        collapseEl.classList.toggle('active', show);
        collapseEl.querySelector('.o_we_collapse_toggler').classList.toggle('active', show);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCollapseTogglerClick(ev) {
        const currentCollapseEl = ev.currentTarget.parentNode;
        this._toggleCollapseEl(currentCollapseEl);
        for (const collapseEl of currentCollapseEl.querySelectorAll('we-collapse')) {
            this._toggleCollapseEl(collapseEl, false);
        }
    },
    /**
     * Called when a widget notifies a preview/change/reset.
     *
     * @private
     * @param {Event} ev
     */
    _onUserValueUpdate: async function (ev) {
        ev.stopPropagation();
        const widget = ev.data.widget;
        const previewMode = ev.data.previewMode;

        // First check if the updated widget or any of the widgets it triggers
        // will require a reload or a confirmation choice by the user. If it is
        // the case, warn the user and potentially ask if he agrees to save its
        // current changes. If not, just do nothing.
        let requiresReload = false;
        if (!ev.data.previewMode && !ev.data.isSimulatedEvent) {
            const linkedWidgets = this._requestUserValueWidgets(...ev.data.triggerWidgetsNames);
            const widgets = [ev.data.widget].concat(linkedWidgets);

            const warnMessage = await this._checkIfWidgetsUpdateNeedWarning(widgets);
            if (warnMessage) {
                const okWarning = await new Promise(resolve => {
                    Dialog.confirm(this, warnMessage, {
                        confirm_callback: () => resolve(true),
                        cancel_callback: () => resolve(false),
                    });
                });
                if (!okWarning) {
                    return;
                }
            }

            const reloadMessage = await this._checkIfWidgetsUpdateNeedReload(widgets);
            requiresReload = !!reloadMessage;
            if (requiresReload) {
                const save = await new Promise(resolve => {
                    Dialog.confirm(this, _t("This change needs to reload the page, this will save all your changes and reload the page, are you sure you want to proceed?") + ' '
                            + (typeof reloadMessage === 'string' ? reloadMessage : ''), {
                        confirm_callback: () => resolve(true),
                        cancel_callback: () => resolve(false),
                    });
                });
                if (!save) {
                    return;
                }
            }
        }

        // Queue action so that we can later skip useless actions.
        if (!this._actionQueues.get(widget)) {
            this._actionQueues.set(widget, []);
        }
        const currentAction = {previewMode};
        this._actionQueues.get(widget).push(currentAction);

        // Ask a mutexed snippet update according to the widget value change
        const shouldRecordUndo = (!previewMode && !ev.data.isSimulatedEvent);
        this.trigger_up('snippet_edition_request', {exec: async () => {
            // If some previous snippet edition in the mutex removed the target from
            // the DOM, the widget can be destroyed, in that case the edition request
            // is now useless and can be discarded.
            if (this.isDestroyed()) {
                return;
            }
            // Filter actions that are counterbalanced by earlier/later actions
            const actionQueue = this._actionQueues.get(widget).filter(({previewMode}, i, actions) => {
                const prev = actions[i - 1];
                const next = actions[i + 1];
                if (previewMode === true && next && next.previewMode) {
                    return false;
                } else if (previewMode === 'reset' && prev && prev.previewMode) {
                    return false;
                }
                return true;
            });
            // Skip action if it's been counterbalanced
            if (!actionQueue.includes(currentAction)) {
                this._actionQueues.set(widget, actionQueue);
                return;
            }
            this._actionQueues.set(widget, actionQueue.filter(action => action !== currentAction));

            if (ev.data.prepare) {
                ev.data.prepare();
            }

            if (previewMode && (widget.$el.closest('[data-no-preview="true"]').length)) {
                // TODO the flag should be fetched through widget params somehow
                return;
            }

            // If it is not preview mode, the user selected the option for good
            // (so record the action)
            if (shouldRecordUndo) {
                this.trigger_up('request_history_undo_record', {$target: this.$target});
            }

            // Call widget option methods and update $target
            await this._select(previewMode, widget);
            if (previewMode) {
                return;
            }

            await new Promise(resolve => setTimeout(() => {
                // Will update the UI of the correct widgets for all options
                // related to the same $target/editor
                this.trigger_up('snippet_option_update', {
                    onSuccess: () => resolve(),
                });
            // Set timeout needed so that the user event which triggered the
            // option can bubble first.
            }));
        }});

        if (ev.data.isSimulatedEvent) {
            // If the user value update was simulated through a trigger, we
            // prevent triggering further widgets. This could be allowed at some
            // point but does not work correctly in complex website cases (see
            // customizeWebsite).
            return;
        }

        // Check linked widgets: force their value and simulate a notification
        const linkedWidgets = this._requestUserValueWidgets(...ev.data.triggerWidgetsNames);
        if (linkedWidgets.length !== ev.data.triggerWidgetsNames.length) {
            console.warn('Missing widget to trigger');
            return;
        }
        let i = 0;
        const triggerWidgetsValues = ev.data.triggerWidgetsValues;
        for (const linkedWidget of linkedWidgets) {
            const widgetValue = triggerWidgetsValues[i];
            if (widgetValue !== undefined) {
                // FIXME right now only make this work supposing it is a
                // colorpicker widget with big big hacks, this should be
                // improved a lot
                const normValue = this._normalizeWidgetValue(widgetValue);
                if (previewMode === true) {
                    linkedWidget._previewColor = normValue;
                } else if (previewMode === false) {
                    linkedWidget._previewColor = false;
                    linkedWidget._value = normValue;
                } else {
                    linkedWidget._previewColor = false;
                }
            }

            linkedWidget.notifyValueChange(previewMode, true);
            i++;
        }

        if (requiresReload) {
            this.trigger_up('request_save', {
                reloadEditor: true,
            });
        }
    },
    /**
     * @private
     */
    _onUserValueWidgetCritical() {
        this.trigger_up('remove_snippet', {
            $snippet: this.$target,
        });
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

            // First update size values as some element sizes may not have been
            // initialized on option start (hidden slides, etc)
            resizeValues = self._getSize();
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
                $(window).off('mouseup', bodyMouseUp);
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
            $(window).on('mouseup', bodyMouseUp);
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
    setTarget: function () {
        this._super(...arguments);
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

/*
 * Abstract option to be extended by the ImageOptimize and BackgroundOptimize
 * options that handles all the common parts.
 */
const ImageHandlerOption = SnippetOptionWidget.extend({

    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
        await this._loadImageInfo();
        return _super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    selectWidth(previewMode, widgetValue, params) {
        this._getImg().dataset.resizeWidth = widgetValue;
        return this._applyOptions();
    },
    /**
     * @see this.selectClass for parameters
     */
    setQuality(previewMode, widgetValue, params) {
        this._getImg().dataset.quality = widgetValue;
        return this._applyOptions();
    },
    /**
     * @see this.selectClass for parameters
     */
    glFilter(previewMode, widgetValue, params) {
        const dataset = this._getImg().dataset;
        if (widgetValue) {
            dataset.glFilter = widgetValue;
        } else {
            delete dataset.glFilter;
        }
        return this._applyOptions();
    },
    /**
     * @see this.selectClass for parameters
     */
    customFilter(previewMode, widgetValue, params) {
        const img = this._getImg();
        const {filterOptions} = img.dataset;
        const {filterProperty} = params;
        if (filterProperty === 'filterColor') {
            widgetValue = normalizeColor(widgetValue);
        }
        const newOptions = Object.assign(JSON.parse(filterOptions || "{}"), {[filterProperty]: widgetValue});
        img.dataset.filterOptions = JSON.stringify(newOptions);
        return this._applyOptions();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeVisibility() {
        const src = this._getImg().getAttribute('src');
        return src && src !== '/';
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const img = this._getImg();

        // Make sure image is loaded because we need its naturalWidth
        await new Promise((resolve, reject) => {
            if (img.complete) {
                resolve();
                return;
            }
            img.addEventListener('load', resolve, {once: true});
            img.addEventListener('error', resolve, {once: true});
        });

        switch (methodName) {
            case 'selectWidth':
                return img.naturalWidth;
            case 'setFilter':
                return img.dataset.filter;
            case 'glFilter':
                return img.dataset.glFilter || "";
            case 'setQuality':
                return img.dataset.quality || 75;
            case 'customFilter': {
                const {filterProperty} = params;
                const options = JSON.parse(img.dataset.filterOptions || "{}");
                const defaultValue = filterProperty === 'blend' ? 'normal' : 0;
                return options[filterProperty] || defaultValue;
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const isLocalURL = href => new URL(href, window.location.origin).origin === window.location.origin;

        const img = this._getImg();
        if (!this.originalSrc || !['image/png', 'image/jpeg'].includes(img.dataset.mimetype)) {
            return [...uiFragment.childNodes].forEach(node => {
                if (node.matches('.o_we_external_warning')) {
                    node.classList.remove('d-none');
                    if (isLocalURL(img.getAttribute('src'))) {
                        const title = node.querySelector('we-title');
                        title.textContent = ` ${_t("Quality options unavailable")}`;
                        $(title).prepend('<i class="fa fa-warning" />');
                        if (img.dataset.mimetype) {
                            title.setAttribute('title', _t("Only PNG and JPEG images support quality options and image filtering"));
                        } else {
                            title.setAttribute('title', _t("Due to technical limitations, you can only change optimization settings on this image by choosing it again in the media-dialog or reuploading it (double click on the image)"));
                        }
                    }
                } else {
                    node.remove();
                }
            });
        }
        const $select = $(uiFragment).find('we-select[data-name=width_select_opt]');
        (await this._computeAvailableWidths()).forEach(([value, label]) => {
            $select.append(`<we-button data-select-width="${value}">${label}</we-button>`);
        });

        if (img.dataset.mimetype !== 'image/jpeg') {
            uiFragment.querySelector('we-range[data-set-quality]').remove();
        }
    },
    /**
     * Returns a list of valid widths for a given image.
     *
     * @private
     */
    async _computeAvailableWidths() {
        const img = this._getImg();
        const original = await loadImage(this.originalSrc);
        const maxWidth = img.dataset.width ? img.naturalWidth : original.naturalWidth;
        const optimizedWidth = Math.min(maxWidth, this._computeMaxDisplayWidth());
        this.optimizedWidth = optimizedWidth;
        const widths = {
            128: '128px',
            256: '256px',
            512: '512px',
            1024: '1024px',
            1920: '1920px',
        };
        widths[img.naturalWidth] = _.str.sprintf(_t("%spx"), img.naturalWidth);
        widths[optimizedWidth] = _.str.sprintf(_t("%dpx (Suggested)"), optimizedWidth);
        widths[maxWidth] = _.str.sprintf(_t("%dpx (Original)"), maxWidth);
        return Object.entries(widths)
            .filter(([width]) => width <= maxWidth)
            .sort(([v1], [v2]) => v1 - v2);
    },
    /**
     * Applies all selected options on the original image.
     *
     * @private
     */
    async _applyOptions() {
        const img = this._getImg();
        if (!['image/jpeg', 'image/png'].includes(img.dataset.mimetype)) {
            this.originalId = null;
            return;
        }
        const dataURL = await applyModifications(img);
        const weight = dataURL.split(',')[1].length / 4 * 3;
        const $weight = this.$el.find('.o_we_image_weight');
        $weight.find('> small').text(_t("New size"));
        $weight.find('b').text(`${(weight / 1024).toFixed(1)} kb`);
        $weight.removeClass('d-none');
        img.classList.add('o_modified_image_to_save');
        const loadedImg = await loadImage(dataURL, img);
        this._applyImage(loadedImg);
        return loadedImg;
    },
    /**
     * Loads the image's attachment info.
     *
     * @private
     */
    async _loadImageInfo() {
        const img = this._getImg();
        await loadImageInfo(img, this._rpc.bind(this));
        if (!img.dataset.originalId) {
            this.originalId = null;
            this.originalSrc = null;
            return;
        }
        this.originalId = img.dataset.originalId;
        this.originalSrc = img.dataset.originalSrc;
    },
    /**
     * Sets the image's width to its suggested size.
     *
     * @private
     */
    async _autoOptimizeImage() {
        await this._loadImageInfo();
        await this._rerenderXML();
        this._getImg().dataset.resizeWidth = this.optimizedWidth;
        await this._applyOptions();
        await this.updateUI();
    },
    /**
     * Returns the image that is currently being modified.
     *
     * @private
     * @abstract
     * @returns {HTMLImageElement} the image to use for modifications
     */
    _getImg() {},
    /**
     * Computes the image's maximum display width.
     *
     * @private
     * @abstract
     * @returns {Int} the maximum width at which the image can be displayed
     */
    _computeMaxDisplayWidth() {},
    /**
     * Use the processed image when it's needed in the DOM.
     *
     * @private
     * @abstract
     * @param {HTMLImageElement} img
     */
    _applyImage(img) {},
});

/**
 * Controls image width and quality.
 */
registry.ImageOptimize = ImageHandlerOption.extend({
    /**
     * @override
     */
    start() {
        this.$target.on('image_changed.ImageOptimization', this._onImageChanged.bind(this));
        this.$target.on('image_cropped.ImageOptimization', this._onImageCropped.bind(this));
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this.$target.off('.ImageOptimization');
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeMaxDisplayWidth() {
        // TODO: read widths from computed style in case container widths are not default
        const displayWidth = this._getImg().clientWidth;
        // If the image is in a column, it might get bigger on smaller screens.
        // We use col-lg for this in snippets, so they get bigger on the md breakpoint
        if (this.$target.closest('[class*="col-lg"]').length) {
            // container and o_container_small have maximum inner width of 690px on the md breakpoint
            if (this.$target.closest('.container, .o_container_small').length) {
                return Math.min(1920, Math.max(displayWidth, 690));
            }
            // A container-fluid's max inner width is 962px on the md breakpoint
            return Math.min(1920, Math.max(displayWidth, 962));
        }
        // If it's not in a col-lg, it's probably not going to change size depending on breakpoints
        return displayWidth;
    },
    /**
     * @override
     */
    _getImg() {
        return this.$target[0];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Reloads image data and auto-optimizes the new image.
     *
     * @private
     * @param {Event} ev
     */
    async _onImageChanged(ev) {
        this.trigger_up('snippet_edition_request', {exec: async () => {
            await this._autoOptimizeImage();
            this.trigger_up('cover_update');
        }});
    },
    /**
     * Available widths will change, need to rerender the width select.
     *
     * @private
     * @param {Event} ev
     */
    async _onImageCropped(ev) {
        await this._rerenderXML();
    },
});

/**
 * Controls background image width and quality.
 */
registry.BackgroundOptimize = ImageHandlerOption.extend({
    /**
     * @override
     */
    start() {
        this.$target.on('background_changed.BackgroundOptimize', this._onBackgroundChanged.bind(this));
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this.$target.off('.BackgroundOptimize');
        return this._super(...arguments);
    },
    /**
     * Marks the target for creation of an attachment and copies data attributes
     * to the target so that they can be restored on this.img in later editions.
     *
     * @override
     */
    async cleanForSave() {
        const img = this._getImg();
        if (img.matches('.o_modified_image_to_save')) {
            this.$target.addClass('o_modified_image_to_save');
            Object.entries(img.dataset).forEach(([key, value]) => {
                this.$target[0].dataset[key] = value;
            });
            this.$target[0].dataset.bgSrc = img.getAttribute('src');
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getImg() {
        return this.img;
    },
    /**
     * @override
     */
    _computeMaxDisplayWidth() {
        return 1920;
    },
    /**
     * Initializes this.img to an image with the background image url as src.
     *
     * @override
     */
    async _loadImageInfo() {
        this.img = new Image();
        Object.entries(this.$target[0].dataset).filter(([key]) =>
            // Avoid copying dynamic editor attributes
            !['oeId','oeModel', 'oeField', 'oeXpath', 'noteId'].includes(key)
        ).forEach(([key, value]) => {
            this.img.dataset[key] = value;
        });
        const src = getBgImageURL(this.$target[0]);
        // Don't set the src if not relative (ie, not local image: cannot be modified)
        this.img.src = src.startsWith('/') ? src : '';
        return await this._super(...arguments);
    },
    /**
     * @override
     */
    _applyImage(img) {
        this.$target.css('background-image', `url('${img.getAttribute('src')}')`);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Reloads image data when the background is changed.
     *
     * @private
     */
    async _onBackgroundChanged(ev, previewMode) {
        if (!previewMode) {
            this.trigger_up('snippet_edition_request', {exec: async () => {
                await this._autoOptimizeImage();
            }});
        }
    },
});

registry.BackgroundToggler = SnippetOptionWidget.extend({
    /**
     * @override
     */
    start() {
        this.$target.on('content_changed.BackgroundToggler', this._onExternalUpdate.bind(this));
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target.off('.BackgroundToggler');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Toggles background image on or off.
     *
     * @see this.selectClass for parameters
     */
    toggleBgImage(previewMode, widgetValue, params) {
        if (!widgetValue) {
            // TODO: use setWidgetValue instead of calling background directly when possible
            const [bgImageWidget] = this._requestUserValueWidgets('bg_image_opt');
            const bgImageOpt = bgImageWidget.getParent();
            return bgImageOpt.background(false, '', bgImageWidget.getMethodsParams('background'));
        } else {
            // TODO: use trigger instead of el.click when possible
            this._requestUserValueWidgets('bg_image_opt')[0].el.click();
        }
    },
    /**
     * Toggles background shape on or off.
     *
     * @see this.selectClass for parameters
     */
    toggleBgShape(previewMode, widgetValue, params) {
        const [shapeWidget] = this._requestUserValueWidgets('bg_shape_opt');
        const shapeOption = shapeWidget.getParent();
        // TODO: open select after shape was selected?
        // TODO: use setWidgetValue instead of calling shapeOption method directly when possible
        return shapeOption._toggleShape();
    },
    /**
     * Toggles background filter on or off.
     *
     * @see this.selectClass for parameters
     */
    toggleBgFilter(previewMode, widgetValue, params) {
        if (widgetValue) {
            const bgFilterEl = document.createElement('div');
            bgFilterEl.classList.add('o_we_bg_filter', 'bg-black-50');
            const lastBackgroundEl = this._getLastPreFilterLayerElement();
            if (lastBackgroundEl) {
                $(lastBackgroundEl).after(bgFilterEl);
            } else {
                this.$target.prepend(bgFilterEl);
            }
        } else {
            this.$target.find('.o_we_bg_filter').remove();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'toggleBgImage': {
                const [bgImageWidget] = this._requestUserValueWidgets('bg_image_opt');
                const bgImageOpt = bgImageWidget.getParent();
                return !!bgImageOpt._computeWidgetState('background', bgImageWidget.getMethodsParams('background'));
            }
            case 'toggleBgFilter': {
                return this._hasBgFilter();
            }
            case 'toggleBgShape': {
                const [shapeWidget] = this._requestUserValueWidgets('bg_shape_opt');
                const shapeOption = shapeWidget.getParent();
                return !!shapeOption._computeWidgetState('shape', shapeWidget.getMethodsParams('shape'));
            }
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _getLastPreFilterLayerElement() {
        return null;
    },
    /**
     * @private
     * @returns {Boolean}
     */
    _hasBgFilter() {
        return !!this.$target.find('> .o_we_bg_filter').length;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onExternalUpdate() {
        if (this._hasBgFilter()
                && !this._getLastPreFilterLayerElement()
                && !getBgImageURL(this.$target)) {
            // No 'pre-filter' background layout anymore and no more background
            // image: remove the background filter option.
            // TODO there probably is a better system to implement to do that
            const widget = this._requestUserValueWidgets('bg_filter_toggle_opt')[0];
            widget.enable();
        }
    },
});

/**
 * Handles the edition of snippet's background image.
 */
registry.BackgroundImage = SnippetOptionWidget.extend({
    /**
     * @override
     */
    start: function () {
        this.__customImageSrc = getBgImageURL(this.$target[0]);
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles a background change.
     *
     * @see this.selectClass for parameters
     */
    background: async function (previewMode, widgetValue, params) {
        if (previewMode === true) {
            this.__customImageSrc = getBgImageURL(this.$target[0]);
        } else if (previewMode === 'reset') {
            widgetValue = this.__customImageSrc;
        } else {
            this.__customImageSrc = widgetValue;
        }

        this._setBackground(widgetValue);

        if (previewMode !== 'reset') {
            removeOnImageChangeAttrs.forEach(attr => delete this.$target[0].dataset[attr]);
            this.$target.trigger('background_changed', [previewMode]);
        }
    },
    /**
     * Changes the main color of dynamic SVGs.
     *
     * @see this.selectClass for parameters
     */
    async dynamicColor(previewMode, widgetValue, params) {
        const currentSrc = getBgImageURL(this.$target[0]);
        switch (previewMode) {
            case true:
                this.previousSrc = currentSrc;
                break;
            case 'reset':
                this.$target.css('background-image', `url('${this.previousSrc}')`);
                return;
        }
        const newURL = new URL(currentSrc, window.location.origin);
        newURL.searchParams.set('c1', normalizeColor(widgetValue));
        const src = newURL.pathname + newURL.search;
        await loadImage(src);
        this.$target.css('background-image', `url('${src}')`);
        if (!previewMode) {
            this.previousSrc = src;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    setTarget: function () {
        // When we change the target of this option we need to transfer the
        // background-image from the old target to the new one.
        const oldBgURL = getBgImageURL(this.$target);
        this._setBackground('');
        this._super(...arguments);
        if (oldBgURL) {
            this._setBackground(oldBgURL);
        }

        // TODO should be automatic for all options as equal to the start method
        this.__customImageSrc = getBgImageURL(this.$target[0]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName) {
        switch (methodName) {
            case 'background':
                return getBgImageURL(this.$target[0]);
            case 'dynamicColor':
                return new URL(getBgImageURL(this.$target[0]), window.location.origin).searchParams.get('c1');
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'dynamic_color_opt') {
            const src = new URL(getBgImageURL(this.$target[0]), window.location.origin);
            return src.origin === window.location.origin && src.pathname.startsWith('/web_editor/shape/');
        }
        return this._super(...arguments);
    },
    /**
     * @private
     * @param {string} backgroundURL
     */
    _setBackground(backgroundURL) {
        if (backgroundURL) {
            this.$target.css('background-image', `url('${backgroundURL}')`);
            this.$target.addClass('oe_img_bg');
        } else {
            this.$target.css('background-image', '');
            this.$target.removeClass('oe_img_bg');
        }
    },
});

/**
 * Handles background shapes.
 */
registry.BackgroundShape = SnippetOptionWidget.extend({
    /**
     * @override
     */
    updateUI() {
        if (this.rerender) {
            this.rerender = false;
            return this._rerenderXML();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Sets the current background shape.
     *
     * @see this.selectClass for params
     */
    shape(previewMode, widgetValue, params) {
        this._handlePreviewState(previewMode, () => {
            return {shape: widgetValue, colors: this._getDefaultColors(), flip: []};
        });
    },
    /**
     * Sets the current background shape's colors.
     *
     * @see this.selectClass for params
     */
    color(previewMode, widgetValue, params) {
        this._handlePreviewState(previewMode, () => {
            const {colorName} = params;
            const {colors: previousColors} = this._getShapeData();
            const newColor = normalizeColor(widgetValue) || this._getDefaultColors()[colorName];
            const newColors = Object.assign(previousColors, {[colorName]: newColor});
            return {colors: newColors};
        });
    },
    /**
     * Flips the shape on its x axis.
     *
     * @see this.selectClass for params
     */
    flipX(previewMode, widgetValue, params) {
        this._flipShape(previewMode, 'x');
    },
    /**
     * Flips the shape on its y axis.
     *
     * @see this.selectClass for params
     */
    flipY(previewMode, widgetValue, params) {
        this._flipShape(previewMode, 'y');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'shape': {
                return this._getShapeData().shape;
            }
            case 'color': {
                const {shape, colors: customColors} = this._getShapeData();
                const colors = Object.assign(this._getDefaultColors(), customColors);
                const color = shape && colors[params.colorName];
                return color || '';
            }
            case 'flipX': {
                // Compat: flip classes are no longer used but may be present in client db
                const hasFlipClass = this.$target.find('> .o_we_shape.o_we_flip_x').length !== 0;
                return hasFlipClass || this._getShapeData().flip.includes('x');
            }
            case 'flipY': {
                // Compat: flip classes are no longer used but may be present in client db
                const hasFlipClass = this.$target.find('> .o_we_shape.o_we_flip_y').length !== 0;
                return hasFlipClass || this._getShapeData().flip.includes('y');
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        Object.keys(this._getDefaultColors()).map(colorName => {
            uiFragment.querySelector('[data-name="colors"]')
                .prepend($(`<we-colorpicker data-color="true" data-color-name="${colorName}">`)[0]);
        });

        uiFragment.querySelectorAll('we-select-pager we-button[data-shape]').forEach(btn => {
            const btnContent = document.createElement('div');
            btnContent.classList.add('o_we_shape_btn_content', 'position-relative', 'border-dark');
            const btnContentInnerDiv = document.createElement('div');
            btnContentInnerDiv.classList.add('o_we_shape');
            btnContent.appendChild(btnContentInnerDiv);

            const {shape} = btn.dataset;
            const shapeEl = btnContent.querySelector('.o_we_shape');
            shapeEl.classList.add(`o_${shape.replace(/\//g, '_')}`);
            btn.append(btnContent);
        });
        return uiFragment;
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'shape_none_opt') {
            return false;
        }
        return this._super(...arguments);
    },
    /**
     * Flips the shape on its x/y axis.
     *
     * @param {boolean} previewMode
     * @param {'x'|'y'} axis the axis of the shape that should be flipped.
     */
    _flipShape(previewMode, axis) {
        this._handlePreviewState(previewMode, () => {
            const flip = new Set(this._getShapeData().flip);
            if (flip.has(axis)) {
                flip.delete(axis);
            } else {
                flip.add(axis);
            }
            return {flip: [...flip]};
        });
    },
    /**
     * Handles everything related to saving state before preview and restoring
     * it after a preview or locking in the changes when not in preview.
     *
     * @param {boolean} previewMode
     * @param {function} computeShapeData function to compute the new shape data.
     */
    _handlePreviewState(previewMode, computeShapeData) {
        const target = this.$target[0];
        const insertShapeContainer = newContainer => {
            const shapeContainer = target.querySelector(':scope > .o_we_shape');
            if (shapeContainer) {
                shapeContainer.remove();
            }
            if (newContainer) {
                const preShapeLayerElement = this._getLastPreShapeLayerElement();
                if (preShapeLayerElement) {
                    $(preShapeLayerElement).after(newContainer);
                } else {
                    this.$target.prepend(newContainer);
                }
            }
            return newContainer;
        };

        let changedShape = false;
        if (previewMode === 'reset') {
            insertShapeContainer(this.prevShapeContainer);
            if (this.prevShape) {
                target.dataset.oeShapeData = this.prevShape;
            } else {
                delete target.dataset.oeShapeData;
            }
            return;
        } else {
            if (previewMode === true) {
                const shapeContainer = target.querySelector(':scope > .o_we_shape');
                this.prevShapeContainer = shapeContainer && shapeContainer.cloneNode(true);
                this.prevShape = target.dataset.oeShapeData;
            }
            const curShapeData = target.dataset.oeShapeData || {};
            const newShapeData = computeShapeData();
            const {shape: curShape} = curShapeData;
            changedShape = newShapeData.shape !== curShape;
            this._markShape(newShapeData);
            if (previewMode === false && changedShape) {
                // Need to rerender for correct number of colorpickers
                this.rerender = true;
            }
        }

        // Updates/removes the shape container as needed and gives it the
        // correct background shape
        const json = target.dataset.oeShapeData;
        const {shape, colors, flip = []} = json ? JSON.parse(json) : {};
        let shapeContainer = target.querySelector(':scope > .o_we_shape');
        if (!shape) {
            return insertShapeContainer(null);
        }
        // When changing shape we want to reset the shape container (for transparency color)
        if (changedShape) {
            shapeContainer = insertShapeContainer(null);
        }
        if (!shapeContainer) {
            shapeContainer = insertShapeContainer(document.createElement('div'));
            target.style.position = 'relative';
            shapeContainer.className = `o_we_shape o_${shape.replace(/\//g, '_')}`;
        }
        // Compat: remove old flip classes as flipping is now done inside the svg
        shapeContainer.classList.remove('o_we_flip_x', 'o_we_flip_y');

        if (colors || flip.length) {
            // Custom colors/flip, overwrite shape that is set by the class
            $(shapeContainer).css('background-image', `url("${this._getShapeSrc()}")`);
            shapeContainer.style.backgroundPosition = '';
            if (flip.length) {
                let [xPos, yPos] = $(shapeContainer)
                    .css('background-position')
                    .split(' ')
                    .map(p => parseFloat(p));
                // -X + 2*Y is a symmetry of X around Y, this is a symmetry around 50%
                xPos = flip.includes('x') ? -xPos + 100 : xPos;
                yPos = flip.includes('y') ? -yPos + 100 : yPos;
                shapeContainer.style.backgroundPosition = `${xPos}% ${yPos}%`;
            }
        } else {
            // Remove custom bg image and let the shape class set the bg shape
            $(shapeContainer).css('background-image', '');
            $(shapeContainer).css('background-position', '');
        }
        if (previewMode === false) {
            this.prevShapeContainer = shapeContainer.cloneNode(true);
            this.prevShape = target.dataset.oeShapeData;
        }
    },
    /**
     * Overwrites shape properties with the specified data.
     *
     * @private
     * @param {Object} newData an object with the new data
     */
    _markShape(newData) {
        const defaultColors = this._getDefaultColors();
        const shapeData = Object.assign(this._getShapeData(), newData);
        const areColorsDefault = Object.entries(shapeData.colors).every(([colorName, colorValue]) => {
            return colorValue.toLowerCase() === defaultColors[colorName].toLowerCase();
        });
        if (areColorsDefault) {
            delete shapeData.colors;
        }
        if (!shapeData.shape) {
            delete this.$target[0].dataset.oeShapeData;
        } else {
            this.$target[0].dataset.oeShapeData = JSON.stringify(shapeData);
        }
    },
    /**
     * @private
     */
    _getLastPreShapeLayerElement() {
        const $filterEl = this.$target.find('> .o_we_bg_filter');
        if ($filterEl.length) {
            return $filterEl[0];
        }
        return null;
    },
    /**
     * Returns the src of the shape corresponding to the current parameters.
     *
     * @private
     */
    _getShapeSrc() {
        const {shape, colors, flip} = this._getShapeData();
        if (!shape) {
            return '';
        }
        const searchParams = Object.entries(colors)
            .map(([colorName, colorValue]) => {
                const encodedCol = encodeURIComponent(colorValue);
                return `${colorName}=${encodedCol}`;
            });
        if (flip.length) {
            searchParams.push(`flip=${flip.sort().join('')}`);
        }
        return `/web_editor/shape/${shape}.svg?${searchParams.join('&')}`;
    },
    /**
     * Retrieves current shape data from the target's dataset.
     *
     * @private
     * @param {HTMLElement} [target=this.$target[0]] the target on which to read
     *   the shape data.
     */
    _getShapeData(target = this.$target[0]) {
        const defaultData = {
            shape: '',
            colors: this._getDefaultColors(),
            flip: [],
        };
        const json = target.dataset.oeShapeData;
        return json ? Object.assign(defaultData, JSON.parse(json.replace(/'/g, '"'))) : defaultData;
    },
    /**
     * Returns the default colors for the currently selected shape.
     *
     * @private
     */
    _getDefaultColors() {
        const $shapeContainer = this.$target.find('> .o_we_shape')
            .clone()
            .addClass('d-none')
            // Needs to be in document for bg-image class to take effect
            .appendTo(document.body);
        const shapeContainer = $shapeContainer[0];
        $shapeContainer.css('background-image', '');
        const shapeSrc = shapeContainer && getBgImageURL(shapeContainer);
        $shapeContainer.remove();
        if (!shapeSrc) {
            return {};
        }
        const url = new URL(shapeSrc, window.location.origin);
        return Object.fromEntries(url.searchParams.entries());
    },
    /**
     * Toggles whether there is a shape or not, to be called from bg toggler.
     *
     * @private
     */
    _toggleShape() {
        if (this._getShapeData().shape) {
            return this._handlePreviewState(false, () => ({shape: ''}));
        } else {
            const target = this.$target[0];
            const previousSibling = target.previousElementSibling;
            const [shapeWidget] = this._requestUserValueWidgets('bg_shape_opt');
            const possibleShapes = shapeWidget.getMethodsParams('shape').possibleValues;
            let shapeToSelect;
            if (previousSibling) {
                const previousShape = this._getShapeData(previousSibling).shape;
                shapeToSelect = possibleShapes.find((shape, i) => {
                    return possibleShapes[i - 1] === previousShape;
                });
            } else {
                shapeToSelect = possibleShapes[1];
            }
            return this._handlePreviewState(false, () => ({shape: shapeToSelect}));
        }
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
            this.img.src = getBgImageURL(this.$target[0]);
        });

        const position = this.$target.css('background-position').split(' ').map(v => parseInt(v));
        const delta = this._getBackgroundDelta();
        // originalPosition kept in % for when movement in one direction doesn't make sense
        this.originalPosition = {
            left: position[0],
            top: position[1],
        };
        // Convert % values to pixels for current position because mouse movement is in pixels
        this.currentPosition = {
            left: position[0] / 100 * delta.x || 0,
            top: position[1] / 100 * delta.y || 0,
        };
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
        return this._super(...arguments) && !!getBgImageURL(this.$target[0]);
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

        const topPos = (parseInt(this.$overlay.css('top')) - parseInt(this.$overlayContent.css('top')));
        this.$overlayContent.find('.o_we_overlay_buttons').css('top', `${topPos}px`);
    },
    /**
     * Toggles the overlay's display and renders a background clone inside of it.
     *
     * @private
     * @param {boolean} activate toggle the overlay on (true) or off (false)
     */
    _toggleBgOverlay: function (activate) {
        if (!this.$backgroundOverlay || this.$backgroundOverlay.is('.oe_active') === activate) {
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
        // Prevent clone from being seen as editor if target is editor (eg. background on root tag)
        this.$bgDragger.removeClass('o_editable');
        // Some CSS child selector rules will not be applied since the clone has a different container from $target.
        // The background-attachment property should be the same in both $target & $bgDragger, this will keep the
        // preview more "wysiwyg" instead of getting different result when bg position saved (e.g. parallax snippet)
        // TODO: improve this to copy all style from $target and override it with overlay related style (copying all
        // css into $bgDragger will not work since it will change overlay content style too).
        this.$bgDragger.css('background-attachment', this.$target.css('background-attachment'));
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
        if (!$(ev.target).closest('.o_we_background_position_overlay')) {
            this._toggleBgOverlay(false);
        }
    },
});

/**
 * Marks color levels of any element that may get or has a color classes. This
 * is done for the specific main colorpicker option so that those are marked on
 * snippet drop (so that base snippet definition do not need to care about that)
 * and on first focus (for compatibility).
 */
registry.ColoredLevelBackground = registry.BackgroundToggler.extend({
    /**
     * @override
     */
    start: function () {
        this._markColorLevel();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    onBuilt: function () {
        this._markColorLevel();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a specific class indicating the element is colored so that nested
     * color classes work (we support one-level). Removing it is not useful,
     * technically the class can be added on anything that *may* receive a color
     * class: this does not come with any CSS rule.
     *
     * @private
     */
    _markColorLevel: function () {
        this.$target.addClass('o_colored_level');
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
                self.$overlay.removeClass('o_overlay_hidden');
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
            self.$target.text($li.data('name'));
        }

        this._clear();
    }
});

/**
 * Allows to display a warning message on outdated snippets.
 */
registry.VersionControl = SnippetOptionWidget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],

    /**
     * @override
     */
    start: function () {
        this.trigger_up('get_snippet_versions', {
            snippetName: this.$target[0].dataset.snippet,
            onSuccess: snippetVersions => {
                const isUpToDate = snippetVersions && ['vjs', 'vcss', 'vxml'].every(key => this.$target[0].dataset[key] === snippetVersions[key]);
                if (!isUpToDate) {
                    this.$el.prepend(qweb.render('web_editor.outdated_block_message'));
                }
            },
        });
        return this._super(...arguments);
    },
});

/**
 * Handle the save of a snippet as a template that can be reused later
 */
registry.SnippetSave = SnippetOptionWidget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    isTopOption: true,

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    saveSnippet: function (previewMode, widgetValue, params) {
        return new Promise(resolve => {
            const dialog = new Dialog(this, {
                title: _t("Save Your Block"),
                size: 'small',
                $content: $(qweb.render('web_editor.dialog.save_snippet', {
                    currentSnippetName: _.str.sprintf(_t("Custom %s"), this.data.snippetName),
                })),
                buttons: [{
                    text: _t("Save"),
                    classes: 'btn-primary',
                    close: true,
                    click: async () => {
                        const save = await new Promise(resolve => {
                            Dialog.confirm(this, _t("To save a snippet, we need to save all your previous modifications and reload the page."), {
                                buttons: [
                                    {
                                        text: _t("Save and Reload"),
                                        classes: 'btn-primary',
                                        close: true,
                                        click: () => resolve(true),
                                    }, {
                                        text: _t("Cancel"),
                                        close: true,
                                        click: () => resolve(false),
                                    }
                                ]
                            });
                        });
                        if (!save) {
                            return;
                        }
                        const snippetKey = this.$target[0].dataset.snippet;
                        let thumbnailURL;
                        this.trigger_up('snippet_thumbnail_url_request', {
                            key: snippetKey,
                            onSuccess: url => thumbnailURL = url,
                        });
                        let context;
                        this.trigger_up('context_get', {
                            callback: ctx => context = ctx,
                        });
                        this.trigger_up('request_save', {
                            reloadEditor: true,
                            onSuccess: async () => {
                                const snippetName = dialog.el.querySelector('.o_we_snippet_name_input').value;
                                const targetCopyEl = this.$target[0].cloneNode(true);
                                delete targetCopyEl.dataset.name;
                                // By the time onSuccess is called after request_save, the
                                // current widget has been destroyed and is orphaned, so this._rpc
                                // will not work as it can't trigger_up. For this reason, we need
                                // to bypass the service provider and use the global RPC directly
                                await rpc.query({
                                    model: 'ir.ui.view',
                                    method: 'save_snippet',
                                    kwargs: {
                                        'name': snippetName,
                                        'arch': targetCopyEl.outerHTML,
                                        'template_key': this.options.snippets,
                                        'snippet_key': snippetKey,
                                        'thumbnail_url': thumbnailURL,
                                        'context': context,
                                    },
                                });
                            },
                        });
                    },
                }, {
                    text: _t("Discard"),
                    close: true,
                }],
            }).open();
            dialog.on('closed', this, () => resolve());
        });
    },
});

/**
 * Handles the dynamic colors for dynamic SVGs.
 */
registry.DynamicSvg = SnippetOptionWidget.extend({
    /**
     * @override
     */
    start() {
        this.$target.on('image_changed.DynamicSvg', this._onImageChanged.bind(this));
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this.$target.off('.DynamicSvg');
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Sets the dynamic SVG's dynamic color.
     *
     * @see this.selectClass for params
     */
    async color(previewMode, widgetValue, params) {
        const target = this.$target[0];
        switch (previewMode) {
            case true:
                this.previousSrc = target.getAttribute('src');
                break;
            case 'reset':
                target.src = this.previousSrc;
                return;
        }
        const newURL = new URL(target.src, window.location.origin);
        newURL.searchParams.set('c1', normalizeColor(widgetValue));
        const src = newURL.pathname + newURL.search;
        await loadImage(src);
        target.src = src;
        if (!previewMode) {
            this.previousSrc = src;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'color':
                return new URL(this.$target[0].src, window.location.origin).searchParams.get('c1');
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeVisibility(methodName, params) {
        return this.$target.is("img[src^='/web_editor/shape/']");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onImageChanged(methodName, params) {
        return this.updateUI();
    },
});

return {
    SnippetOptionWidget: SnippetOptionWidget,
    snippetOptionRegistry: registry,

    NULL_ID: NULL_ID,
    UserValueWidget: UserValueWidget,
    userValueWidgetsRegistry: userValueWidgetsRegistry,
    UnitUserValueWidget: UnitUserValueWidget,

    addTitleAndAllowedAttributes: _addTitleAndAllowedAttributes,
    buildElement: _buildElement,
    buildTitleElement: _buildTitleElement,
    buildRowElement: _buildRowElement,
    buildCollapseElement: _buildCollapseElement,

    // Other names for convenience
    Class: SnippetOptionWidget,
    registry: registry,
};
});
