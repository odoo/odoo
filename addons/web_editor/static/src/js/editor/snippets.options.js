odoo.define('web_editor.snippets.options', function (require) {
'use strict';

const { ComponentWrapper } = require('web.OwlCompatibility');
const { MediaDialogWrapper } = require('@web_editor/components/media_dialog/media_dialog');
var core = require('web.core');
const {ColorpickerWidget} = require('web.Colorpicker');
const Dialog = require('web.Dialog');
const {scrollTo} = require('web.dom');
const rpc = require('web.rpc');
const time = require('web.time');
const utils = require('web.utils');
var Widget = require('web.Widget');
var ColorPaletteWidget = require('web_editor.ColorPalette').ColorPaletteWidget;
const weUtils = require('web_editor.utils');
const {
    normalizeColor,
    getBgImageURL,
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
    DEFAULT_PALETTE,
} = weUtils;
var weWidgets = require('wysiwyg.widgets');
const {
    loadImage,
    loadImageInfo,
    applyModifications,
    removeOnImageChangeAttrs,
    isImageSupportedForProcessing,
    isImageSupportedForStyle,
    createDataURL,
    isGif,
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
        titleEl.classList.add('o_we_collapse_toggler');
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
/**
 * Creates and registers a UserValueWidget by tag-name
 *
 * @param {string} widgetName
 * @param {SnippetOptionWidget|UserValueWidget|null} parent
 * @param {string} title
 * @param {Object} options
 * @returns {UserValueWidget}
 */
function registerUserValueWidget(widgetName, parent, title, options, $target) {
    const widget = new userValueWidgetsRegistry[widgetName](parent, title, options, $target);
    parent.registerSubWidget(widget);
    return widget;
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
            this.containerEl.appendChild(document.createTextNode('\u200B')); // Ensures proper vertical centering.
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
        if (!this.el.classList.contains('o_we_widget_opened')) {
            // Small optimization: it would normally not matter asking to
            // remove a class of an element if it does not already have it but
            // in this case we do more: we trigger_up an event and ask to close
            // all sub widgets. When we ask the editor to close all widgets...
            // it makes sense not letting every sub button of every select
            // trigger_up an event. This allows to avoid tens of thousands of
            // instructions being done at each click in the editor.
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
     * Focus the main focusable element of the widget.
     */
    focus() {
        const el = this._getFocusableElement();
        if (el) {
            el.focus();
        }
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

        // Method names come from the widget's dataset whose keys' order cannot
        // be relied on. We explicitely sort them by alphabetical order allowing
        // consistent behavior, while relying on order for such methods should
        // not be done when possible (the methods should be independent from
        // each other when possible).
        this._methodsNames.sort();
    },
    /**
     * @param {boolean} [previewMode=false]
     * @param {boolean} [isSimulatedEvent=false]
     */
    notifyValueChange: function (previewMode, isSimulatedEvent) {
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
        let doFocus = false;
        if (show) {
            const wasInvisible = this.el.classList.contains('d-none');
            doFocus = wasInvisible && this.el.dataset.requestFocus === "true";
        }
        this.el.classList.toggle('d-none', !show);
        if (doFocus) {
            this.focus();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the main focusable element of the widget. By default supposes
     * nothing is focusable.
     *
     * @todo review all specific widget's method
     * @private
     * @returns {HTMLElement}
     */
    _getFocusableElement: function () {
        return null;
    },
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
    async willStart() {
        await this._super(...arguments);
        if (this.options.dataAttributes.activeImg) {
            this.activeImgEl = await _buildImgElement(this.options.dataAttributes.activeImg);
        }
    },
    /**
     * @override
     */
    _makeDescriptive() {
        const $el = this._super(...arguments);
        if (this.imgEl) {
            $el[0].classList.add('o_we_icon_button');
        }
        if (this.activeImgEl) {
            this.containerEl.appendChild(this.activeImgEl);
        }
        return $el;
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
        if (this.imgEl && this.activeImgEl) {
            this.imgEl.classList.toggle('d-none', active);
            this.activeImgEl.classList.toggle('d-none', !active);
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
            this.options.childNodes.forEach(node => {
                if (node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        node.insertBefore(document.createTextNode('\u200B'), node.firstChild); // Ensures proper height.
                    }
                    this.menuEl.appendChild(node);
                }
            });
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
                break;
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
        this.menuTogglerEl.appendChild(document.createTextNode('\u200B')); // Ensures proper height.
        this.iconEl = this.imgEl || null;
        const icon = this.el.dataset.icon;
        if (icon) {
            this.iconEl = document.createElement('i');
            this.iconEl.classList.add('fa', 'fa-fw', icon);
        }
        if (this.iconEl) {
            this.el.classList.add('o_we_icon_select');
            this.menuTogglerEl.appendChild(this.iconEl);
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

        if (this.iconEl) {
            return;
        }

        if (this.menuTogglerItemEl) {
            this.menuTogglerItemEl.remove();
            this.menuTogglerItemEl = null;
        }

        let textContent = '\u200B'; // Ensures proper height.
        const activeWidget = this._userValueWidgets.find(widget => !widget.isPreviewed() && widget.isActive());
        if (activeWidget) {
            const svgTag = activeWidget.el.querySelector('svg'); // useful to avoid searching text content in svg element
            const value = (activeWidget.el.dataset.selectLabel || (!svgTag && activeWidget.el.textContent.replace('\u200B', '').trim()));
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
    /**
     * @override
     */
    enable() {
        if (!this.menuTogglerEl.classList.contains('active')) {
            this.menuTogglerEl.click();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _shouldIgnoreClick(ev) {
        return !!ev.target.closest('[role="button"]');
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
        if (this._shouldIgnoreClick(ev)) {
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
        'change input': '_onUserValueChange',
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
        this.inputEl.classList.toggle('text-start', !unit);
        this.inputEl.classList.toggle('text-end', !!unit);
        this.containerEl.appendChild(this.inputEl);

        var unitEl = document.createElement('span');
        unitEl.textContent = unit;
        this.containerEl.appendChild(unitEl);
        if (unit.length > 3) {
            this.el.classList.add('o_we_large');
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
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getFocusableElement() {
        return this.inputEl;
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
     * TODO remove in master
     */
    _onInputBlur: function (ev) {},
    /**
     * @private
     * @param {Event} ev
     */
    _onInputKeydown: function (ev) {
        switch (ev.which) {
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

        if (this.options.dataAttributes.lazyPalette === 'true') {
            // TODO review in master, this was done in stable to keep the speed
            // fix as stable as possible (to have a reference to a widget even
            // if not a colorPalette widget).
            this.colorPalette = new Widget(this);
            this.colorPalette.getColorNames = () => [];
            await this.colorPalette.appendTo(document.createDocumentFragment());
        } else {
            await this._renderColorPalette();
        }

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
            this.colorPalette.setSelectedColor(this._ccValue, this._value);
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
        const isCCMethod = (this._methodsParams.withCombinations === methodName);
        let value = this._super(...arguments);
        if (isCCMethod) {
            value = this._ccValue;
        } else if (typeof this._customColorValue === 'string') {
            value = this._customColorValue;
        }

        // TODO strange there is some processing below for the normal value but
        // not for the preview value? To check in older stable versions as well.
        if (typeof this._previewColor === 'string') {
            return isCCMethod ? this._previewCC : this._previewColor;
        }

        if (value) {
            // TODO probably something to be done to handle gradients properly
            // in this code.
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
        return !!this._ccValue
            || !weUtils.areCssValuesEqual(this._value, 'rgba(0, 0, 0, 0)');
    },
    /**
     * Updates the color preview + re-render the whole color palette widget.
     *
     * @override
     */
    async setValue(color, methodName, ...rest) {
        // The colorpicker widget can hold two values: a color combination and
        // a normal color or a gradient. The base `_value` will hold the normal
        // color or the gradient value. The color combination one will be
        // available in `_ccValue`.
        const isCCMethod = (this._methodsParams.withCombinations === methodName);
        // Always call _super but don't change _value if meant for the CC value.
        await this._super(isCCMethod ? this._value : color, methodName, ...rest);
        if (isCCMethod) {
            this._ccValue = color;
        }

        await this._colorPaletteRenderPromise;

        this.colorPreviewEl.style.removeProperty('background-color');
        this.colorPreviewEl.style.removeProperty('background-image');
        const prefix = this.options.dataAttributes.colorPrefix || 'bg';
        if (this._ccValue) {
            this.colorPreviewEl.style.backgroundColor = `var(--we-cp-o-cc${this._ccValue}-${prefix.replace(/-/, '')})`;
        }
        if (this._value) {
            if (ColorpickerWidget.isCSSColor(this._value)) {
                this.colorPreviewEl.style.backgroundColor = this._value;
            } else if (!weUtils.isColorGradient(this._value)) {
                if (weUtils.EDITOR_COLOR_CSS_VARIABLES.includes(this._value)) {
                    this.colorPreviewEl.style.backgroundColor = `var(--we-cp-${this._value}`;
                } else {
                    this.colorPreviewEl.classList.add(`bg-${this._value}`);
                }
            } else {
                this.colorPreviewEl.style.backgroundImage = this._value;
            }
        }
        // If the palette was already opened (e.g. modifying a gradient), the new DOM state must be
        // reflected in the palette, but the tab selection must not be impacted.
        if (this.colorPalette.setSelectedColor) {
            this.colorPalette.setSelectedColor(this._ccValue, this._value, false);
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
            selectedCC: this._ccValue,
            selectedColor: this._value,
        };
        if (this.options.dataAttributes.excluded) {
            options.excluded = this.options.dataAttributes.excluded.replace(/ /g, '').split(',');
        }
        if (this.options.dataAttributes.opacity) {
            options.opacity = this.options.dataAttributes.opacity;
        }
        if (this.options.dataAttributes.withCombinations) {
            options.withCombinations = !!this.options.dataAttributes.withCombinations;
        }
        if (this.options.dataAttributes.withGradients) {
            options.withGradients = !!this.options.dataAttributes.withGradients;
        }
        if (this.options.dataAttributes.noTransparency) {
            options.noTransparency = !!this.options.dataAttributes.noTransparency;
            options.excluded = [...(options.excluded || []), 'transparent_grayscale'];
        }
        if (this.options.dataAttributes.selectedTab) {
            options.selectedTab = this.options.dataAttributes.selectedTab;
        }
        const wysiwyg = this.getParent().options.wysiwyg;
        if (wysiwyg) {
            options.ownerDocument = wysiwyg.el.ownerDocument;
            options.editable = wysiwyg.$editable[0];
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
     * @override
     */
    _shouldIgnoreClick(ev) {
        return ev.originalEvent.__isColorpickerClick || this._super(...arguments);
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
        this._previewCC = false;
        this._previewColor = false;
        this._customColorValue = false;

        this._ccValue = ev.data.ccValue;
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
        this._previewCC = ev.data.ccValue;
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
        this._previewCC = false;
        this._previewColor = false;
        this._onUserValueReset(ev);
    },
    /**
     * @private
     */
    _onEnterKey: function () {
        this.close();
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
        if (this.options.dataAttributes.buttonStyle) {
            const iconEl = document.createElement('i');
            iconEl.classList.add('fa', 'fa-fw', 'fa-camera');
            $(this.containerEl).prepend(iconEl);
        } else {
            this.el.classList.add('o_we_no_toggle', 'o_we_bg_success');
            this.containerEl.textContent = _t("Replace");
        }
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
    _openDialog(el, {images = false, videos = false, save}) {
        el.src = this._value;
        const $editable = this.$target.closest('.o_editable');
        const mediaDialogWrapper = new ComponentWrapper(this, MediaDialogWrapper, {
            noImages: !images,
            noVideos: !videos,
            noIcons: true,
            noDocuments: true,
            isForBgVideo: true,
            vimeoPreviewIds: ['299225971', '414790269', '420192073', '368484050', '334729960', '417478345',
                '312451183', '415226028', '367762632', '340475898', '374265101', '370467553'],
            'res_model': $editable.data('oe-model'),
            'res_id': $editable.data('oe-id'),
            save,
            media: el,
        });
        return mediaDialogWrapper.mount(this.el);
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
        this._openDialog(dummyEl, {
            images: true,
            save: (media) => {
                // Accessing the value directly through dummyEl.src converts the url to absolute,
                // using getAttribute allows us to keep the url as it was inserted in the DOM
                // which can be useful to compare it to values stored in db.
                this._value = media.getAttribute('src');
                this._onUserValueChange();
            }
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
        this._openDialog(dummyEl, {
            videos: true,
            save: (media) => {
                this._value = media.querySelector('iframe').src;
                this._onUserValueChange();
        }});
    },
});

const DatetimePickerUserValueWidget = InputUserValueWidget.extend({
    events: { // Explicitely not consider all InputUserValueWidget events
        'blur input': '_onInputBlur',
        'change.datetimepicker': '_onDateTimePickerChange',
        'error.datetimepicker': '_onDateTimePickerError',
        'input input': '_onDateInputInput',
    },
    defaultFormat: time.getLangDatetimeFormat(),

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
        this.el.classList.add('o_we_large');
        this.inputEl.classList.add('datetimepicker-input', 'mx-0', 'text-start');
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
            format: this.defaultFormat,
            sideBySide: true,
            buttons: {
                showClear: true,
                showClose: true,
                showToday: true,
            },
            widgetParent: 'body',

            // Open the datetimepicker on focus not on click. This allows to
            // take care of a bug which is due to the wysiwyg editor:
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
    getMethodsParams: function () {
        return _.extend(this._super(...arguments), {
            format: this.defaultFormat,
        });
    },
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
        let momentObj = null;
        if (this._value) {
            momentObj = moment.unix(this._value);
            if (!momentObj.isValid()) {
                momentObj = moment();
            }
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
            this._value = '';
        } else {
            this._value = ev.date.unix().toString();
        }
        this._onUserValuePreview(ev);
    },
    /**
     * Prevents crash manager to throw CORS error. Note that library already
     * clears the wrong date format.
     */
    _onDateTimePickerError: function (ev) {
        ev.stopPropagation();
    },
    /**
     * Handles the clear button of the datepicker.
     *
     * @private
     * @param {Event} ev
     */
    _onDateInputInput(ev) {
        if (!this.inputEl.value) {
            this._value = '';
            this._onUserValuePreview(ev);
        }
    },
});

const DatePickerUserValueWidget = DatetimePickerUserValueWidget.extend({
    defaultFormat: time.getLangDateFormat(),
});

const ListUserValueWidget = UserValueWidget.extend({
    tagName: 'we-list',
    events: {
        'click we-button.o_we_select_remove_option': '_onRemoveItemClick',
        'click we-button.o_we_list_add_optional': '_onAddCustomItemClick',
        'click we-button.o_we_list_add_existing': '_onAddExistingItemClick',
        'click we-select.o_we_user_value_widget.o_we_add_list_item': '_onAddItemSelectClick',
        'click we-button.o_we_checkbox_wrapper': '_onAddItemCheckboxClick',
        'change table input': '_onListItemChange',
    },

    /**
     * @override
     */
    willStart() {
        if (this.options.createWidget) {
            this.createWidget = this.options.createWidget;
            this.createWidget.setParent(this);
            this.registerSubWidget(this.createWidget);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    start() {
        this.addItemTitle = this.el.dataset.addItemTitle || _t("Add");
        if (this.el.dataset.availableRecords) {
            this.records = JSON.parse(this.el.dataset.availableRecords);
        } else {
            this.isCustom = !this.el.dataset.notEditable;
        }
        if (this.el.dataset.defaults || this.el.dataset.hasDefault) {
            this.hasDefault = this.el.dataset.hasDefault || 'unique';
            this.selected = this.el.dataset.defaults ? JSON.parse(this.el.dataset.defaults) : [];
        }
        this.listTable = document.createElement('table');
        const tableWrapper = document.createElement('div');
        tableWrapper.classList.add('o_we_table_wrapper');
        tableWrapper.appendChild(this.listTable);
        this.containerEl.appendChild(tableWrapper);
        this.el.classList.add('o_we_fw');
        this._makeListItemsSortable();
        if (this.createWidget) {
            return this.createWidget.appendTo(this.containerEl);
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams() {
        return _.extend(this._super(...arguments), {
            records: this.records,
        });
    },
    /**
     * @override
     */
    setValue() {
        this._super(...arguments);
        const currentValues = this._value ? JSON.parse(this._value) : [];
        this.listTable.innerHTML = '';
        if (this.addItemButton) {
            this.addItemButton.remove();
        }

        if (this.createWidget) {
            const selectedIds = currentValues.map(({ id }) => id)
                .filter(id => typeof id === 'number');
            const selectedIdsDomain = ['id', 'not in', selectedIds];
            const selectedIdsDomainIndex = this.createWidget.options.domain.findIndex(domain => domain[0] === 'id' && domain[1] === 'not in');
            if (selectedIdsDomainIndex > -1) {
                this.createWidget.options.domain[selectedIdsDomainIndex] = selectedIdsDomain;
            } else {
                this.createWidget.options.domain = [...this.createWidget.options.domain, selectedIdsDomain];
            }
            this.createWidget.setValue('');
            this.createWidget.inputEl.value = '';
            $(this.createWidget.inputEl).trigger('input');
        } else {
            if (this.isCustom) {
                this.addItemButton = document.createElement('we-button');
                this.addItemButton.textContent = this.addItemTitle;
                this.addItemButton.classList.add('o_we_list_add_optional');
            } else {
                // TODO use a real select widget ?
                this.addItemButton = document.createElement('we-select');
                this.addItemButton.classList.add('o_we_user_value_widget', 'o_we_add_list_item');
                const divEl = document.createElement('div');
                this.addItemButton.appendChild(divEl);
                const togglerEl = document.createElement('we-toggler');
                togglerEl.textContent = this.addItemTitle;
                divEl.appendChild(togglerEl);
                this.selectMenuEl = document.createElement('we-selection-items');
                divEl.appendChild(this.selectMenuEl);
            }
            this.containerEl.appendChild(this.addItemButton);
        }
        currentValues.forEach(value => {
            if (typeof value === 'object') {
                const recordData = value;
                const { id, display_name } = recordData;
                delete recordData.id;
                delete recordData.display_name;
                this._addItemToTable(id, display_name, recordData);
            } else {
                this._addItemToTable(value, value);
            }
        });
        if (!this.createWidget && !this.isCustom) {
            this._reloadSelectDropdown(currentValues);
        }
        this._makeListItemsSortable();
    },
    /**
     * @override
     */
    getValue(methodName) {
        if (this.createWidget && this.createWidget.getMethodsNames().includes(methodName)) {
            return this.createWidget.getValue(methodName);
        }
        return this._value;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string || integer} id
     * @param {string} [value]
     * @param {Object} [recordData] key, values that will be added to the
     *     element's dataset
     */
    _addItemToTable(id, value = this.el.dataset.defaultValue || _t("Item"), recordData) {
        const trEl = document.createElement('tr');
        if (!this.el.dataset.unsortable) {
            const draggableEl = document.createElement('we-button');
            draggableEl.classList.add('o_we_drag_handle', 'o_we_link', 'fa', 'fa-fw', 'fa-arrows');
            draggableEl.dataset.noPreview = 'true';
            const draggableTdEl = document.createElement('td');
            draggableTdEl.appendChild(draggableEl);
            trEl.appendChild(draggableTdEl);
        }
        let recordDataSelected = false;
        const inputEl = document.createElement('input');
        inputEl.type = this.el.dataset.inputType || 'text';
        if (value) {
            inputEl.value = value;
        }
        if (id) {
            inputEl.name = id;
        }
        if (recordData) {
            recordDataSelected = recordData.selected;
            if (recordData.placeholder) {
                inputEl.placeholder = recordData.placeholder;
            }
            for (const key of Object.keys(recordData)) {
                inputEl.dataset[key] = recordData[key];
            }
        }
        inputEl.disabled = !this.isCustom;
        const inputTdEl = document.createElement('td');
        inputTdEl.classList.add('o_we_list_record_name');
        inputTdEl.appendChild(inputEl);
        trEl.appendChild(inputTdEl);
        if (this.hasDefault) {
            const checkboxEl = document.createElement('we-button');
            checkboxEl.classList.add('o_we_user_value_widget', 'o_we_checkbox_wrapper');
            if (this.selected.includes(id) || recordDataSelected) {
                checkboxEl.classList.add('active');
            }
            if (!recordData || !recordData.notToggleable) {
                const div = document.createElement('div');
                const checkbox = document.createElement('we-checkbox');
                div.appendChild(checkbox);
                checkboxEl.appendChild(div);
                checkboxEl.appendChild(checkbox);
                const checkboxTdEl = document.createElement('td');
                checkboxTdEl.appendChild(checkboxEl);
                trEl.appendChild(checkboxTdEl);
            }
        }
        if (!recordData || !recordData.undeletable) {
            const buttonTdEl = document.createElement('td');
            const buttonEl = document.createElement('we-button');
            buttonEl.classList.add('o_we_select_remove_option', 'o_we_link', 'o_we_text_danger', 'fa', 'fa-fw', 'fa-minus');
            buttonEl.dataset.removeOption = id;
            buttonTdEl.appendChild(buttonEl);
            trEl.appendChild(buttonTdEl);
        }
        this.listTable.appendChild(trEl);
    },
    /**
     * @override
     */
    _getFocusableElement() {
        return this.listTable.querySelector('input');
    },
    /**
     * @private
     */
    _makeListItemsSortable() {
        if (this.el.dataset.unsortable) {
            return;
        }
        $(this.listTable).sortable({
            axis: 'y',
            handle: '.o_we_drag_handle',
            items: 'tr',
            cursor: 'move',
            opacity: 0.6,
            stop: (event, ui) => {
                this._notifyCurrentState();
            },
        });
    },
    /**
     * @private
     */
    _notifyCurrentState() {
        const values = [...this.listTable.querySelectorAll('.o_we_list_record_name input')].map(el => {
            let id = this.isCustom ? el.value : el.name;
            if (this.el.dataset.idMode && this.el.dataset.idMode === "name") {
                id = el.name;
            }
            const idInt = parseInt(id);
            return Object.assign({
                id: isNaN(idInt) ? id : idInt,
                name: el.value,
                display_name: el.value,
            }, el.dataset);
        });
        if (this.hasDefault) {
            const checkboxes = [...this.listTable.querySelectorAll('we-button.o_we_checkbox_wrapper.active')];
            this.selected = checkboxes.map(el => {
                const input = el.parentElement.previousSibling.firstChild;
                const id = input.name || input.value;
                const idInt = parseInt(id);
                return isNaN(idInt) ? id : idInt;
            });
            values.forEach(v => {
                // Elements not toggleable are considered as always selected.
                // We have to check that it is equal to the string 'true'
                // because this information comes from the dataset.
                v.selected = this.selected.includes(v.id) || v.notToggleable === 'true';
            });
        }
        this._value = JSON.stringify(values);
        this.notifyValueChange(false);
        if (!this.createWidget && !this.isCustom) {
            this._reloadSelectDropdown(values);
        }
    },
    /**
     * @private
     * @param {Array} currentValues
     */
    _reloadSelectDropdown(currentValues) {
        this.selectMenuEl.innerHTML = '';
        this.records.forEach(el => {
            if (!currentValues.find(v => v.id === el.id)) {
                const option = document.createElement('we-button');
                option.classList.add('o_we_list_add_existing');
                option.dataset.addOption = el.id;
                option.dataset.noPreview = 'true';
                const divEl = document.createElement('div');
                divEl.textContent = el.display_name;
                option.appendChild(divEl);
                this.selectMenuEl.appendChild(option);
            }
        });
        if (!this.selectMenuEl.children.length) {
            const title = document.createElement('we-title');
            title.textContent = _t("No more records");
            this.selectMenuEl.appendChild(title);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddCustomItemClick() {
        const recordData = {};
        if (this.el.dataset.newElementsNotToggleable) {
            recordData.notToggleable = true;
        }
        this._addItemToTable(undefined, this.el.dataset.defaultValue, recordData);
        this._notifyCurrentState();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onAddExistingItemClick(ev) {
        const value = ev.currentTarget.dataset.addOption;
        this._addItemToTable(value, ev.currentTarget.textContent);
        this._notifyCurrentState();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onAddItemSelectClick(ev) {
        ev.currentTarget.querySelector('we-toggler').classList.toggle('active');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onAddItemCheckboxClick: function (ev) {
        const isActive = ev.currentTarget.classList.contains('active');
        if (this.hasDefault === 'unique') {
            this.listTable.querySelectorAll('we-button.o_we_checkbox_wrapper.active').forEach(el => el.classList.remove('active'));
        }
        ev.currentTarget.classList.toggle('active', !isActive);
        this._notifyCurrentState();
    },
    /**
     * @private
     */
    _onListItemChange() {
        this._notifyCurrentState();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onRemoveItemClick(ev) {
        const minElements = this.el.dataset.allowEmpty ? 0 : 1;
        if (ev.target.closest('table').querySelectorAll('tr').length > minElements) {
            ev.target.closest('tr').remove();
            this._notifyCurrentState();
        }
    },
    /**
     * @override
     */
    _onUserValueNotification(ev) {
        const { widget, previewMode, prepare } = ev.data;
        if (widget && widget === this.createWidget) {
            if (widget.options.createMethod && widget.getValue(widget.options.createMethod)) {
                return this._super(ev);
            }
            ev.stopPropagation();
            if (previewMode) {
                return;
            }
            prepare();
            const recordData = JSON.parse(widget.getMethodsParams('addRecord').recordData);
            const { id, display_name } = recordData;
            delete recordData.id;
            delete recordData.display_name;
            this._addItemToTable(id, display_name, recordData);
            this._notifyCurrentState();
        }
        return this._super(ev);
    },
});

const RangeUserValueWidget = UnitUserValueWidget.extend({
    tagName: 'we-range',
    events: {
        'change input': '_onInputChange',
        'input input': '_onInputInput',
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
        this._setInputAttributes(min, max, step);
        this.containerEl.appendChild(this.input);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    loadMethodsData(validMethodNames) {
        this._super(...arguments);
        for (const methodName of this._methodsNames) {
            const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
            if (possibleValues.length > 1) {
                this._setInputAttributes(0, possibleValues.length - 1, 1);
                break;
            }
        }
    },
    /**
     * @override
     */
    async setValue(value, methodName) {
        await this._super(...arguments);
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        this.input.value = possibleValues.length > 1 ? possibleValues.indexOf(value) : this._value;
    },
    /**
     * @override
     */
    getValue(methodName) {
        const value = this._super(...arguments);
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        return possibleValues.length > 1 ? possibleValues[+value] : value;
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
    /**
     * @private
     * @param {Event} ev
     */
    _onInputInput(ev) {
        this._value = ev.target.value;
        this._onUserValuePreview(ev);
    },
    /**
     * @private
     */
    _setInputAttributes(min, max, step) {
        this.input.setAttribute('min', min);
        this.input.setAttribute('max', max);
        this.input.setAttribute('step', step);
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
     * @override
     */
    _shouldIgnoreClick(ev) {
        return !!ev.target.closest('.o_we_pager_header') || this._super(...arguments);
    },
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

const Many2oneUserValueWidget = SelectUserValueWidget.extend({
    className: (SelectUserValueWidget.prototype.className || '') + ' o_we_many2one',
    events: Object.assign({}, SelectUserValueWidget.prototype.events, {
        'input .o_we_m2o_search input': '_onSearchInput',
        'keydown .o_we_m2o_search input': '_onSearchKeydown',
        'click .o_we_m2o_search_more': '_onSearchMoreClick',
    }),
    // Data-attributes that will be read into `this.options` on init and not
    // transfered to inner buttons.
    configAttributes: ['model', 'fields', 'limit', 'domain', 'callWith', 'createMethod'],

    /**
     * @override
     */
    init(parent, title, options, $target) {
        this.afterSearch = [];
        this.displayNameCache = {};
        this._rpcCache = {};
        const {dataAttributes} = options;
        Object.assign(options, {
            limit: '5',
            fields: '[]',
            domain: '[]',
            callWith: 'id',
        });
        this.configAttributes.forEach(attr => {
            if (dataAttributes.hasOwnProperty(attr)) {
                options[attr] = dataAttributes[attr];
                delete dataAttributes[attr];
            }
        });
        options.limit = parseInt(options.limit);
        options.fields = JSON.parse(options.fields);
        if (!options.fields.includes('display_name')) {
            options.fields.push('display_name');
        }
        options.domain = JSON.parse(options.domain);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        this.inputEl = document.createElement('input');
        this.inputEl.setAttribute('placeholder', _t("Search for records..."));
        const searchEl = document.createElement('div');
        searchEl.classList.add('o_we_m2o_search');
        searchEl.appendChild(this.inputEl);
        this.menuEl.appendChild(searchEl);

        this.searchMore = document.createElement('div');
        this.searchMore.classList.add('o_we_m2o_search_more');
        this.searchMore.textContent = _t("Search more...");
        this.searchMore.title = _t("Search to show more records");

        if (this.options.createMethod) {
            this.createInput = new InputUserValueWidget(this, undefined, {
                classes: ['o_we_large'],
                dataAttributes: { noPreview: 'true' },
            }, this.$target);
            this.createButton = new ButtonUserValueWidget(this, undefined, {
                classes: ['flex-grow-0'],
                dataAttributes: {
                    noPreview: 'true',
                    [this.options.createMethod]: '', // Value through getValue.
                },
                childNodes: [document.createTextNode(_t("Create"))],
            }, this.$target);
            // Override isActive so it doesn't show up in toggler
            this.createButton.isActive = () => false;

            await Promise.all([
                this.createInput.appendTo(document.createDocumentFragment()),
                this.createButton.appendTo(document.createDocumentFragment()),
            ]);
            this.registerSubWidget(this.createInput);
            this.registerSubWidget(this.createButton);
            this.createWidget = _buildRowElement('', {
                classes: ['o_we_full_row', 'o_we_m2o_create', 'p-1'],
                childNodes: [this.createInput.el, this.createButton.el],
            });
        }

        return this._search('');
    },
    /**
     * @override
     */
    async setValue(value, methodName) {
        await this._super(...arguments);
        if (this.menuTogglerEl.textContent === '/') {
            // The currently selected value is not present in the search, need to read
            // its display name.
            if (value !== '') {
                // FIXME: value may not be an id if callWith is specified!
                this.menuTogglerEl.textContent = await this._getDisplayName(parseInt(value));
            } else {
                this.menuTogglerEl.textContent = _t("Choose a record...");
            }
        }
    },
    /**
     * @override
     */
    getValue(methodName) {
        if (methodName === this.options.createMethod && this.createInput) {
            return this.createInput._value;
        }
        return this._super(...arguments);
    },
    /**
     * Prevents double widget instanciation for we-buttons that have been
     * created manually by _search (container widgets will have their innner
     * html searched for userValueWidgets to instanciate during option startup)
     *
     * @override
     */
    isContainer() {
        return false;
    },
    /**
     * @override
     */
    open() {
        if (this.createInput) {
            this.createInput.setValue('');
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Caches the rpc.
     *
     * @override
     */
    async _rpc() {
        const cacheId = JSON.stringify(...arguments);
        if (!this._rpcCache[cacheId]) {
            this._rpcCache[cacheId] = this._super(...arguments);
        }
        return this._rpcCache[cacheId];
    },
    /**
     * Searches the database for corresponding records and updates the dropdown
     *
     * @private
     */
    async _search(needle) {
        this._userValueWidgets = this._userValueWidgets.filter(widget => !widget.isDestroyed());
        // Remove select options
        this._userValueWidgets
            .filter(widget => {
                return widget instanceof ButtonUserValueWidget &&
                    widget.el.parentElement.matches('we-selection-items');
            }).forEach(button => {
                if (button.isPreviewed()) {
                    button.notifyValueChange('reset');
                }
                button.destroy();
            });
        const recTuples = await this._rpc({
            model: this.options.model,
            method: 'name_search',
            kwargs: {
                name: needle,
                args: this.options.domain,
                operator: "ilike",
                limit: this.options.limit + 1,
            },
        });
        const records = await this._rpc({
            model: this.options.model,
            method: 'read',
            args: [recTuples.map(([id, _name]) => id), this.options.fields],
        });
        records.forEach(record => {
            this.displayNameCache[record.id] = record.display_name;
        });

        await Promise.all(records.slice(0, this.options.limit).map(async record => {
            // Copy over the data-attributes from the main element, and default the value
            // to the callWith field of the record so that if it's a method, it will
            // be called with that value
            const buttonDataAttributes = Object.assign({}, this.options.dataAttributes);
            Object.keys(buttonDataAttributes).forEach(key => {
                buttonDataAttributes[key] = buttonDataAttributes[key] || record[this.options.callWith];
            });
            // REMARK: this syntax is very similar to React.createComponent, maybe we could
            // write a transformer like there is for JSX?
            const buttonWidget = new ButtonUserValueWidget(this, undefined, {
                dataAttributes: Object.assign({recordData: JSON.stringify(record)}, buttonDataAttributes),
                childNodes: [document.createTextNode(record.display_name)],
            }, this.$target);
            this.registerSubWidget(buttonWidget);
            await buttonWidget.appendTo(this.menuEl);
            if (this._methodsNames) {
                buttonWidget.loadMethodsData(this._methodsNames);
            }
        }));
        // Load methodsData for new buttons if possible. It will not be possible
        // when the widget is first created (as this._methodsNames will be undefined)
        // but the snippetOption lifecycle will load the methods data explicitely
        // just after creating the widget
        if (this._methodsNames) {
            this._methodsNames.forEach(methodName => {
                this.setValue(this._value, methodName);
            });
        }

        const hasMore = records.length > this.options.limit;
        if (hasMore) {
            this.menuEl.appendChild(this.searchMore);
            this.searchMore.classList.remove('d-none');
        } else {
            this.searchMore.classList.add('d-none');
        }

        if (this.createWidget) {
            this.menuEl.appendChild(this.createWidget);
        }

        this.waitingForSearch = false;
        this.afterSearch.forEach(cb => cb());
        this.afterSearch = [];
    },
    /**
     * Returns the display name for a given record.
     *
     * @private
     */
    async _getDisplayName(recordId) {
        if (!this.displayNameCache.hasOwnProperty(recordId)) {
            this.displayNameCache[recordId] = (await this._rpc({
                model: this.options.model,
                method: 'read',
                args: [[recordId], ['display_name']],
            }))[0].display_name;
        }
        return this.displayNameCache[recordId];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onClick(ev) {
        // Prevent dropdown from closing if you click on the search or has_more
        if (ev.target.closest('.o_we_m2o_search_more, .o_we_m2o_search, .o_we_m2o_create') &&
                !ev.target.closest('we-button')) {
            ev.stopPropagation();
            return;
        }
        return this._super(...arguments);
    },
    /**
     * Handles changes to the search bar.
     *
     * @private
     */
    _onSearchInput(ev) {
        // maybe there is a concurrency primitive we can use instead of manual record-keeping?
        // Basically we want to queue the enter action to go after the current search if there
        // is one that is ongoing (ie currently waiting for the debounce or RPC)
        clearTimeout(this.searchIntent);
        this.waitingForSearch = true;
        this.searchIntent = setTimeout(() => {
            this._search(ev.target.value);
        }, 500);
    },
    /**
     * Selects the first option when pressing enter in the search input.
     *
     * @private
     */
    _onSearchKeydown(ev) {
        if (ev.which !== $.ui.keyCode.ENTER) {
            return;
        }
        const action = () => {
            const firstButton = this.menuEl.querySelector(':scope > we-button');
            if (firstButton) {
                firstButton.click();
            }
        };
        if (this.waitingForSearch) {
            this.afterSearch.push(action);
        } else {
            action();
        }
    },
    /**
     * Focuses the search input when clicking on the "Search more..." button.
     *
     * @private
     */
    _onSearchMoreClick(ev) {
        this.inputEl.focus();
    },
    /**
     * @override
     */
    _onUserValueNotification(ev) {
        const { widget } = ev.data;
        if (widget && widget === this.createInput) {
            ev.stopPropagation();
            return;
        }
        if (widget && widget === this.createButton) {
            if (!this.createInput._value) {
                ev.stopPropagation();
            }
            return;
        }
        if (widget !== this.createButton && this.createInput) {
            this.createInput._value = '';
        }
        return this._super(ev);
    },
});

const Many2manyUserValueWidget = UserValueWidget.extend({
    configAttributes: ['model', 'recordId', 'm2oField', 'createMethod', 'fakem2m'],

    /**
     * @override
     */
    init(parent, title, options, $target) {
        const { dataAttributes } = options;
        this.configAttributes.forEach(attr => {
            if (dataAttributes.hasOwnProperty(attr)) {
                options[attr] = dataAttributes[attr];
                delete dataAttributes[attr];
            }
        });
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        // If the widget does not have a real m2m field in the database
        // We do not need to fetch anything from the DB
        if (this.options.fakem2m) {
            this.m2oModel = this.options.model;
            return;
        }
        const { model, recordId, m2oField } = this.options;
        const [record] = await this._rpc({
            model: model,
            method: 'read',
            args: [[parseInt(recordId)], [m2oField]],
        });
        const selectedRecordIds = record[m2oField];
        // TODO: handle no record
        const modelData = await this._rpc({
            model: model,
            method: 'fields_get',
            args: [[m2oField]],
        });
        // TODO: simultaneously fly both RPCs
        this.m2oModel = modelData[m2oField].relation;
        this.m2oName = modelData[m2oField].field_description; // Use as string attr?

        const selectedRecords = await this._rpc({
            model: this.m2oModel,
            method: 'read',
            args: [selectedRecordIds, ['display_name']],
        });
        // TODO: reconcile the fact that this widget sets its own initial value
        // instead of it coming through setValue(_computeWidgetState)
        this._value = JSON.stringify(selectedRecords);
    },
    /**
     * @override
     */
    async start() {
        this.el.classList.add('o_we_m2m');
        const m2oDataAttributes = Object.entries(this.options.dataAttributes).filter(([attrName]) => {
            return Many2oneUserValueWidget.prototype.configAttributes.includes(attrName);
        });
        m2oDataAttributes.push(
            ['model', this.m2oModel],
            ['addRecord', ''],
            ['createMethod', this.options.createMethod],
        );
        // Don't register this one as a subWidget because it will be a subWidget
        // of the listWidget
        this.createWidget = new Many2oneUserValueWidget(null, undefined, {
            dataAttributes: Object.fromEntries(m2oDataAttributes),
        }, this.$target);

        this.listWidget = registerUserValueWidget('we-list', this, undefined, {
            dataAttributes: { unsortable: 'true', notEditable: 'true', allowEmpty: 'true' },
            createWidget: this.createWidget,
        }, this.$target);
        await this.listWidget.appendTo(this.containerEl);

        // Make this.el the select's offsetParent so the we-selection-items has
        // the correct width
        this.listWidget.el.querySelector('we-select').style.position = 'static';
        this.el.style.position = 'relative';
    },
    /**
     * @override
     */
    loadMethodsData(validMethodNames, ...rest) {
        // TODO: check that addRecord is still needed.
        this._super(['addRecord', ...validMethodNames], ...rest);
        this._methodsNames = this._methodsNames.filter(name => name !== 'addRecord');
    },
    /**
     * @override
     */
    setValue(value, methodName) {
        if (methodName === this.options.createMethod) {
            return this.createWidget.setValue(value, methodName);
        }
        if (!value) {
            // TODO: why do we need this.
            value = this._value;
        }
        this._super(value, methodName);
        this.listWidget.setValue(this._value);
    },
    /**
     * @override
     */
    getValue(methodName) {
        return this.listWidget.getValue(methodName);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onUserValueNotification(ev) {
        const { widget, previewMode } = ev.data;
        if (!widget) {
            return this._super(ev);
        }
        if (widget === this.listWidget) {
            ev.stopPropagation();
            this._value = widget._value;
            this.notifyValueChange(previewMode);
        }
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
    'we-datepicker': DatePickerUserValueWidget,
    'we-list': ListUserValueWidget,
    'we-imagepicker': ImagepickerUserValueWidget,
    'we-videopicker': VideopickerUserValueWidget,
    'we-range': RangeUserValueWidget,
    'we-select-pager': SelectPagerUserValueWidget,
    'we-many2one': Many2oneUserValueWidget,
    'we-many2many': Many2manyUserValueWidget,
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
     * Indicates if the option should be the first one displayed in the button
     * group at the top of the options panel, next to the clone/remove button.
     *
     * @type {boolean}
     */
    isTopFirstOption: false,
    /**
     * Forces the target to not be possible to remove.
     *
     * @type {boolean}
     */
    forceNoDeleteButton: false,
    /**
     * The option needs the handles overlay to be displayed on the snippet.
     *
     * @type {boolean}
     */
    displayOverlayOptions: false,

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
     * @returns {Promise|undefined}
     */
    async onFocus() {},
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * for the first time, when it is a new snippet dropped from the d&d snippet
     * menu. Note: this is called after the start and onFocus methods.
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    async onBuilt() {},
    /**
     * Called when the parent edition overlay is removed from the associated
     * snippet (another snippet enters edition for example).
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    async onBlur() {},
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
     * @returns {Promise|undefined}
     */
    onRemove: async function () {},
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
    /**
     * Adds the given widget to the known list of user value widgets
     *
     * @param {UserValueWidget} widget
     */
    registerSubWidget(widget) {
        this._userValueWidgets.push(widget);
    },

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
        if (value) {
            this.$target[0].setAttribute(params.attributeName, value);
        } else {
            this.$target[0].removeAttribute(params.attributeName);
        }
    },
    /**
     * Default option method which allows to select a value and set it on the
     * associated snippet as a property. The name of the property is
     * given by the propertyName parameter.
     *
     * @param {boolean} previewMode - @see this.selectClass
     * @param {string} widgetValue
     * @param {Object} params
     */
    selectProperty: function (previewMode, widgetValue, params) {
        if (!params.propertyName) {
            throw new Error('Property name missing');
        }
        const value = this._selectValueHelper(widgetValue, params);
        this.$target[0][params.propertyName] = value;
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

        // Always reset the inline style first to not put inline style on an
        // element which already have this style through css stylesheets.
        let cssProps = weUtils.CSS_SHORTHANDS[params.cssProperty] || [params.cssProperty];
        for (const cssProp of cssProps) {
            this.$target[0].style.setProperty(cssProp, '');
        }
        if (params.extraClass) {
            this.$target.removeClass(params.extraClass);
        }
        // Plain color and gradient are mutually exclusive as background so in
        // case we edit a background-color we also have to reset the gradient
        // part of the background-image property (the opposite is handled by the
        // fact that editing a gradient as background is done by calling this
        // method with background-color as property too, so it is automatically
        // reset anyway).
        let bgImageParts = undefined;
        if (params.withGradients && params.cssProperty === 'background-color') {
            const styles = getComputedStyle(this.$target[0]);
            bgImageParts = backgroundImageCssToParts(styles['background-image']);
            delete bgImageParts.gradient;
            const combined = backgroundImagePartsToCss(bgImageParts);
            this.$target[0].style.setProperty('background-image', '');
            applyCSS.call(this, 'background-image', combined, styles);
        }

        // Only allow to use a color name as a className if we know about the
        // other potential color names (to remove) and if we know about a prefix
        // (otherwise we suppose that we should use the actual related color).
        // Note: color combinations classes are handled by a dedicated method,
        // as they can be combined with normal classes.
        if (params.colorNames && params.colorPrefix) {
            const colorNames = params.colorNames.filter(name => !weUtils.isColorCombinationName(name));
            const classes = weUtils.computeColorClasses(colorNames, params.colorPrefix);
            this.$target[0].classList.remove(...classes);

            if (colorNames.includes(widgetValue)) {
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

        const styles = window.getComputedStyle(this.$target[0]);

        // At this point, the widget value is either a property/color name or
        // an actual css property value. If it is a property/color name, we will
        // apply a css variable as style value.
        const htmlPropValue = weUtils.getCSSVariableValue(widgetValue);
        if (htmlPropValue) {
            widgetValue = `var(--${widgetValue})`;
        }

        // In case of background-color edition, we could receive a gradient, in
        // which case the value has to be combined with the potential background
        // image (real image).
        if (params.withGradients && params.cssProperty === 'background-color' && weUtils.isColorGradient(widgetValue)) {
            cssProps = ['background-image'];
            bgImageParts.gradient = widgetValue;
            widgetValue = backgroundImagePartsToCss(bgImageParts);

            // Also force the background-color to transparent as otherwise it
            // won't act as a "gradient replacing the color combination
            // background" but be applied over it (which would be the opposite
            // of what happens when editing the background color).
            applyCSS.call(this, 'background-color', 'rgba(0, 0, 0, 0)', styles);
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

        let hasUserValue = false;
        for (let i = cssProps.length - 1; i > 0; i--) {
            hasUserValue = applyCSS.call(this, cssProps[i], values.pop(), styles) || hasUserValue;
        }
        hasUserValue = applyCSS.call(this, cssProps[0], values.join(' '), styles) || hasUserValue;

        function applyCSS(cssProp, cssValue, styles) {
            // This condition requires extraClass to NOT be set.
            if (!weUtils.areCssValuesEqual(styles[cssProp], cssValue, cssProp, this.$target[0])) {
                // Property must be set => extraClass will be enabled.
                if (params.extraClass) {
                    // The extraClass is temporarily removed during selectStyle
                    // because it is enabled only if the element style is set
                    // by the option. (E.g. add the bootstrap border class only
                    // if there is a border width.) Unfortunately the
                    // extraClass might specify default !important properties,
                    // therefore determining whether !important is needed
                    // requires the class to be applied.
                    this.$target[0].classList.add(params.extraClass);
                    // Set inline style only if different from value defined
                    // with extraClass.
                    if (!weUtils.areCssValuesEqual(styles[cssProp], cssValue, cssProp, this.$target[0])) {
                        this.$target[0].style.setProperty(cssProp, cssValue);
                    }
                } else {
                    // Inline style required.
                    this.$target[0].style.setProperty(cssProp, cssValue);
                }
                // If change had no effect then make it important.
                // This condition requires extraClass to be set.
                if (!weUtils.areCssValuesEqual(styles[cssProp], cssValue, cssProp, this.$target[0])) {
                    this.$target[0].style.setProperty(cssProp, cssValue, 'important');
                }
                if (params.extraClass) {
                    this.$target[0].classList.remove(params.extraClass);
                }
                return true;
            }
            return false;
        }

        if (params.extraClass) {
            this.$target.toggleClass(params.extraClass, hasUserValue);
        }

        _restoreTransitions();
    },
    /**
     * Sets a color combination.
     *
     * @see this.selectClass for parameters
     */
    async selectColorCombination(previewMode, widgetValue, params) {
        if (params.colorNames) {
            const names = params.colorNames.filter(weUtils.isColorCombinationName);
            const classes = weUtils.computeColorClasses(names);
            this.$target[0].classList.remove(...classes);

            if (widgetValue) {
                this.$target[0].classList.add('o_cc', `o_cc${widgetValue}`);
            }
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

                    const widget = this._requestUserValueWidgets(depName, true)[0];
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
            const $userValueWidget = $(el).find('> div > .o_we_user_value_widget');
            el.classList.toggle('d-none', $userValueWidget.length && !$userValueWidget.not('.d-none').length);
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
                for (const classNames of params.possibleValues) {
                    if (!classNames) {
                        continue;
                    }
                    const classes = classNames.split(/\s+/g);
                    if (params.stateToFirstClass) {
                        if (this.$target[0].classList.contains(classes[0])) {
                            return classNames;
                        } else {
                            continue;
                        }
                    }

                    if (classes.length >= maxNbClasses
                            && classes.every(className => this.$target[0].classList.contains(className))) {
                        maxNbClasses = classes.length;
                        activeClassNames = classNames;
                    }
                }
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
                let usedCC = undefined;
                if (params.colorPrefix && params.colorNames) {
                    for (const c of params.colorNames) {
                        const className = weUtils.computeColorClasses([c], params.colorPrefix)[0];
                        if (this.$target[0].classList.contains(className)) {
                            if (weUtils.isColorCombinationName(c)) {
                                usedCC = c;
                                continue;
                            }
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

                if (params.withGradients && params.cssProperty === 'background-color') {
                    // Check if there is a gradient, in that case this is the
                    // value to be returned, we normally not allow color and
                    // gradient at the same time (the option would remove one
                    // if editing the other).
                    const parts = backgroundImageCssToParts(styles['background-image']);
                    if (parts.gradient) {
                        _restoreTransitions();
                        return parts.gradient;
                    }
                }

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

                const value = cssValues.join(' ');

                if (params.cssProperty === 'background-color' && params.withCombinations) {
                    if (usedCC) {
                        const ccValue = weUtils.getCSSVariableValue(`o-cc${usedCC}-bg`).trim();
                        if (weUtils.areCssValuesEqual(value, ccValue)) {
                            // Prevent to consider that a color is used as CC
                            // override in case that color is the same as the
                            // one used in that CC.
                            return '';
                        }
                    } else {
                        const rgba = ColorpickerWidget.convertCSSColorToRgba(value);
                        if (rgba && rgba.opacity < 0.001) {
                            // Prevent to consider a transparent color is
                            // applied as background unless it is to override a
                            // CC. Simply allows to add a CC on a transparent
                            // snippet in the first place.
                            return '';
                        }
                    }
                }

                return value;
            }
            case 'selectColorCombination': {
                if (params.colorNames) {
                    for (const c of params.colorNames) {
                        if (!weUtils.isColorCombinationName(c)) {
                            continue;
                        }
                        const className = weUtils.computeColorClasses([c])[0];
                        if (this.$target[0].classList.contains(className)) {
                            return c;
                        }
                    }
                }
                return '';
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
            const widget = registerUserValueWidget(widgetName, parentWidget || this, infos.title, infos.options, this.$target);
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
     * @param {boolean} [allowParentOption=false]
     * @returns {UserValueWidget[]}
     */
    _requestUserValueWidgets: function (...args) {
        const widgetNames = args;
        let allowParentOption = false;
        const lastArg = args[args.length - 1];
        if (typeof lastArg === 'boolean') {
            widgetNames.pop();
            allowParentOption = lastArg;
        }

        const widgets = [];
        for (const widgetName of widgetNames) {
            let widget = null;
            this.trigger_up('user_value_widget_request', {
                name: widgetName,
                onSuccess: _widget => widget = _widget,
                allowParentOption: allowParentOption,
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

        if (previewMode === true) {
            this.options.wysiwyg.odooEditor.automaticStepUnactive('preview_option');
        }

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

        if (previewMode === 'reset' || previewMode === false) {
            this.options.wysiwyg.odooEditor.automaticStepActive('preview_option');
        }

        // We trigger the event on elements targeted by apply-to if any as
        // this.$target could not be in an editable element while the elements
        // targeted by apply-to are.
        ($applyTo || this.$target).trigger('content_changed');
    },
    /**
     * Used to handle attribute or data attribute value change
     *
     * @see this._selectValueHelper for parameters
     */
    _selectAttributeHelper(value, params) {
        if (!params.attributeName) {
            throw new Error('Attribute name missing');
        }
        return this._selectValueHelper(value, params);
    },
    /**
     * Used to handle value of a select
     *
     * @param {string} value
     * @param {Object} params
     * @returns {string|undefined}
     */
    _selectValueHelper(value, params) {
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
        collapseEl.querySelector('we-toggler.o_we_collapse_toggler').classList.toggle('active', show);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCollapseTogglerClick(ev) {
        const currentCollapseEl = ev.currentTarget.closest('we-collapse');
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

            requiresReload = !!await this._checkIfWidgetsUpdateNeedReload(widgets);
        }

        // Queue action so that we can later skip useless actions.
        if (!this._actionQueues.get(widget)) {
            this._actionQueues.set(widget, []);
        }
        const currentAction = {previewMode};
        this._actionQueues.get(widget).push(currentAction);

        // Ask a mutexed snippet update according to the widget value change
        const shouldRecordUndo = (!previewMode && !ev.data.isSimulatedEvent);
        if (shouldRecordUndo) {
            this.options.wysiwyg.odooEditor.unbreakableStepUnactive();
        }
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

            // Call widget option methods and update $target
            await this._select(previewMode, widget);

            // If it is not preview mode, the user selected the option for good
            // (so record the action)
            if (shouldRecordUndo) {
                this.options.wysiwyg.odooEditor.historyStep();
            }

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
                optionSelector: this.data.selector,
                url: this.data.reload,
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
    displayOverlayOptions: true,

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
                    self.options.wysiwyg.odooEditor.historyStep();
                }, 0);
            };
            $body.on('mousemove', bodyMouseMove);
            $body.on('mouseup', bodyMouseUp);
        });

        _.each(resizeValues, (value, key) => {
            this.$handles.filter('.' + key).toggleClass('readonly', !value);
        });

        return def;
    },
    /**
     * @override
     */
    onFocus: function () {
        this._onResize();
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
registry['sizing_x'] = registry.sizing.extend({
    /**
     * @override
     */
    onClone: function (options) {
        this._super.apply(this, arguments);
        // Below condition is added to remove offset of target element only
        // and not its children to avoid design alteration of a container/block.
        if (options.isCurrent) {
            var _class = this.$target.attr('class').replace(/\s*(offset-xl-|offset-lg-)([0-9-]+)/g, '');
            this.$target.attr('class', _class);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getSize: function () {
        var width = this.$target.closest('.row').width();
        var gridE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        var gridW = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
        this.grid = {
            e: [_.map(gridE, v => ('col-lg-' + v)), _.map(gridE, v => width / 12 * v), 'width'],
            w: [_.map(gridW, v => ('offset-lg-' + v)), _.map(gridW, v => width / 12 * v), 'margin-left'],
        };
        return this.grid;
    },
    /**
     * @override
     */
    _onResize: function (compass, beginClass, current) {
        if (compass === 'w') {
            // don't change the right border position when we change the offset (replace col size)
            var beginCol = Number(beginClass.match(/col-lg-([0-9]+)|$/)[1] || 0);
            var beginOffset = Number(beginClass.match(/offset-lg-([0-9-]+)|$/)[1] || beginClass.match(/offset-xl-([0-9-]+)|$/)[1] || 0);
            var offset = Number(this.grid.w[0][current].match(/offset-lg-([0-9-]+)|$/)[1] || 0);
            if (offset < 0) {
                offset = 0;
            }
            var colSize = beginCol - (offset - beginOffset);
            if (colSize <= 0) {
                colSize = 1;
                offset = beginOffset + beginCol - 1;
            }
            this.$target.attr('class', this.$target.attr('class').replace(/\s*(offset-xl-|offset-lg-|col-lg-)([0-9-]+)/g, ''));

            this.$target.addClass('col-lg-' + (colSize > 12 ? 12 : colSize));
            if (offset > 0) {
                this.$target.addClass('offset-lg-' + offset);
            }
        }
        this.trigger_up('option_update', {
            optionName: 'StepsConnector',
            name: 'change_column_size',
        });
        this._super.apply(this, arguments);
    },
});

/**
 * Controls box properties.
 */
registry.Box = SnippetOptionWidget.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * TODO this should be reviewed in master to avoid the need of using the
     * 'reset' previewMode and having to remember the previous box-shadow value.
     * We are forced to remember the previous box shadow before applying a new
     * one as the whole box-shadow value is handled by multiple widgets.
     *
     * @see this.selectClass for parameters
     */
    async setShadow(previewMode, widgetValue, params) {
        // Check if the currently configured shadow is not using the same shadow
        // mode, in which case nothing has to be done.
        const styles = window.getComputedStyle(this.$target[0]);
        const currentBoxShadow = styles['box-shadow'] || 'none';
        const currentMode = currentBoxShadow === 'none'
            ? ''
            : currentBoxShadow.includes('inset') ? 'inset' : 'outset';
        if (currentMode === widgetValue) {
            return;
        }

        if (previewMode === true) {
            this._prevBoxShadow = currentBoxShadow;
        }

        // Add/remove the shadow class
        this.$target.toggleClass(params.shadowClass, !!widgetValue);

        // Change the mode of the old box shadow. If no shadow was currently
        // set then get the shadow value that is supposed to be set according
        // to the shadow mode. Try to apply it via the selectStyle method so
        // that it is either ignored because the shadow class had its effect or
        // forced (to the shadow value or none) if toggling the class is not
        // enough (e.g. if the item has a default shadow coming from CSS rules,
        // removing the shadow class won't be enough to remove the shadow but in
        // most other cases it will).
        let shadow = 'none';
        if (previewMode === 'reset') {
            shadow = this._prevBoxShadow;
        } else {
            if (currentBoxShadow === 'none') {
                shadow = this._getDefaultShadow(widgetValue, params.shadowClass);
            } else {
                if (widgetValue === 'outset') {
                    shadow = currentBoxShadow.replace('inset', '').trim();
                } else if (widgetValue === 'inset') {
                    shadow = currentBoxShadow + ' inset';
                }
            }
        }
        await this.selectStyle(previewMode, shadow, Object.assign({cssProperty: 'box-shadow'}, params));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'setShadow') {
            const shadowValue = this.$target.css('box-shadow');
            if (!shadowValue || shadowValue === 'none') {
                return '';
            }
            return this.$target.css('box-shadow').includes('inset') ? 'inset' : 'outset';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'fake_inset_shadow_opt') {
            return false;
        }
        return this._super(...arguments);
    },
    /**
     * @private
     * @param {string} type
     * @param {string} shadowClass
     * @returns {string}
     */
    _getDefaultShadow(type, shadowClass) {
        if (!type) {
            return 'none';
        }

        const el = document.createElement('div');
        el.classList.add(shadowClass);
        document.body.appendChild(el);
        const shadow = `${$(el).css('box-shadow')}${type === 'inset' ? ' inset' : ''}`;
        el.remove();
        return shadow;
    },
});



registry.layout_column = SnippetOptionWidget.extend({
    /**
     * @override
     */
    start: function () {
        // Needs to be done manually for now because _computeWidgetVisibility
        // doesn't go through this option for buttons inside of a select.
        // TODO: improve this.
        this.$el.find('we-button[data-name="zero_cols_opt"]')
            .toggleClass('d-none', !this.$target.is('.s_allow_columns'));
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the number of columns.
     *
     * @see this.selectClass for parameters
     */
    selectCount: async function (previewMode, widgetValue, params) {
        const previousNbColumns = this.$('> .row').children().length;
        let $row = this.$('> .row');
        if (!$row.length) {
            $row = this.$target.contents().wrapAll($('<div class="row"><div class="col-lg-12"/></div>')).parent().parent();
        }

        const nbColumns = parseInt(widgetValue);
        await this._updateColumnCount($row, (nbColumns || 1) - $row.children().length);
        // Yield UI thread to wait for event to bubble before activate_snippet is called.
        // In this case this lets the select handle the click event before we switch snippet.
        // TODO: make this more generic in activate_snippet event handler.
        await new Promise(resolve => setTimeout(resolve));
        if (nbColumns === 0) {
            $row.contents().unwrap().contents().unwrap();
            this.trigger_up('activate_snippet', {$snippet: this.$target});
        } else if (previousNbColumns === 0) {
            this.trigger_up('activate_snippet', {$snippet: this.$('> .row').children().first()});
        }
        this.trigger_up('option_update', {
            optionName: 'StepsConnector',
            name: 'change_columns',
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'selectCount') {
            return this.$('> .row').children().length;
        }
        return this._super(...arguments);
    },
    /**
     * Adds new columns which are clones of the last column or removes the
     * last x columns.
     *
     * @private
     * @param {jQuery} $row - the row in which to update the columns
     * @param {integer} count - positif to add, negative to remove
     */
    _updateColumnCount: async function ($row, count) {
        if (!count) {
            return;
        }

        if (count > 0) {
            var $lastColumn = $row.children().last();
            for (var i = 0; i < count; i++) {
                await new Promise(resolve => {
                    this.trigger_up('clone_snippet', {$snippet: $lastColumn, onSuccess: resolve});
                });
            }
        } else {
            var self = this;
            for (const el of $row.children().slice(count)) {
                await new Promise(resolve => {
                    self.trigger_up('remove_snippet', {$snippet: $(el), onSuccess: resolve, shouldRecordUndo: false});
                });
            }
        }

        this._resizeColumns($row.children());
        this.trigger_up('cover_update');
    },
    /**
     * Resizes the columns so that they are kept on one row.
     *
     * @private
     * @param {jQuery} $columns - the columns to resize
     */
    _resizeColumns: function ($columns) {
        const colsLength = $columns.length;
        var colSize = Math.floor(12 / colsLength) || 1;
        var colOffset = Math.floor((12 - colSize * colsLength) / 2);
        var colClass = 'col-lg-' + colSize;
        _.each($columns, function (column) {
            var $column = $(column);
            $column.attr('class', $column.attr('class').replace(/\b(col|offset)-lg(-\d+)?\b/g, ''));
            $column.addClass(colClass);
        });
        if (colOffset) {
            $columns.first().addClass('offset-lg-' + colOffset);
        }
    },
});

/**
 * Allows snippets to be moved before the preceding element or after the following.
 */
registry.SnippetMove = SnippetOptionWidget.extend({
    displayOverlayOptions: true,

    /**
     * @override
     */
    start: function () {
        var $buttons = this.$el.find('we-button');
        var $overlayArea = this.$overlay.find('.o_overlay_move_options');
        $overlayArea.prepend($buttons[0]);
        $overlayArea.append($buttons[1]);

        return this._super(...arguments);
    },
    /**
     * @override
     */
    onFocus: function () {
        // TODO improve this: hack to hide options section if snippet move is
        // the only one.
        const $allOptions = this.$el.parent();
        if ($allOptions.find('we-customizeblock-option').length <= 1) {
            $allOptions.addClass('d-none');
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Moves the snippet around.
     *
     * @see this.selectClass for parameters
     */
    moveSnippet: function (previewMode, widgetValue, params) {
        const isNavItem = this.$target[0].classList.contains('nav-item');
        const $tabPane = isNavItem ? $(this.$target.find('.nav-link')[0].hash) : null;
        switch (widgetValue) {
            case 'prev':
                this.$target.prev().before(this.$target);
                if (isNavItem) {
                    $tabPane.prev().before($tabPane);
                }
                break;
            case 'next':
                this.$target.next().after(this.$target);
                if (isNavItem) {
                    $tabPane.next().after($tabPane);
                }
                break;
        }
        if (!this.$target.is(this.data.noScroll)
                && (params.name === 'move_up_opt' || params.name === 'move_down_opt')) {
            scrollTo(this.$target[0], {
                extraOffset: 50,
                easing: 'linear',
                duration: 550,
            });
        }
        this.trigger_up('option_update', {
            optionName: 'StepsConnector',
            name: 'move_snippet',
        });
    },
});

/**
 * Allows for media to be replaced.
 */
registry.ReplaceMedia = SnippetOptionWidget.extend({

    /**
     * @override
     */
    onFocus() {
        core.bus.on('activate_image_link_tool', this, this._activateLinkTool);
        // When we start editing an image, rerender the UI to ensure the
        // we-select that suggests the anchors is in a consistent state.
        this.rerender = true;
    },
    /**
     * @override
     */
    onBlur() {
        core.bus.off('activate_image_link_tool', this, this._activateLinkTool);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Replaces the media.
     *
     * @see this.selectClass for parameters
     */
    async replaceMedia() {
        // TODO for now, this simulates a double click on the media,
        // to be refactored when the new editor is merged
        this.$target.dblclick();
    },
    /**
     * Makes the image a clickable link by wrapping it in an <a>.
     * This function is also called for the opposite operation.
     *
     * @see this.selectClass for parameters
     */
    setLink(previewMode, widgetValue, params) {
        const parentEl = this.$target[0].parentNode;
        if (parentEl.tagName !== 'A') {
            const wrapperEl = document.createElement('a');
            this.$target[0].after(wrapperEl);
            wrapperEl.appendChild(this.$target[0]);
        } else {
            parentEl.replaceWith(this.$target[0]);
        }
    },
    /**
     * Changes the image link so that the URL is opened on another tab or not
     * when it is clicked.
     *
     * @see this.selectClass for parameters
     */
    setNewWindow(previewMode, widgetValue, params) {
        const linkEl = this.$target[0].parentElement;
        if (widgetValue) {
            linkEl.setAttribute('target', '_blank');
        } else {
            linkEl.removeAttribute('target');
        }
    },
    /**
     * Records the target url of the hyperlink.
     *
     * @see this.selectClass for parameters
     */
    setUrl(previewMode, widgetValue, params) {
        const linkEl = this.$target[0].parentElement;
        let url = widgetValue;
        if (!url) {
            // As long as there is no URL, the image is not considered a link.
            linkEl.removeAttribute('href');
            return;
        }
        if (!url.startsWith('/') && !url.startsWith('#')
                && !/^([a-zA-Z]*.):.+$/gm.test(url)) {
            // We permit every protocol (http:, https:, ftp:, mailto:,...).
            // If none is explicitly specified, we assume it is a http.
            url = 'http://' + url;
        }
        linkEl.setAttribute('href', url);
        this.rerender = true;
    },
    /**
     * @override
     */
    async updateUI() {
        if (this.rerender) {
            this.rerender = false;
            await this._rerenderXML();
            return;
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _activateLinkTool() {
        if (this.$target[0].parentElement.tagName === 'A') {
            this._requestUserValueWidgets('media_url_opt')[0].focus();
        } else {
            this._requestUserValueWidgets('media_link_opt')[0].enable();
        }
    },
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        const parentEl = this.$target[0].parentElement;
        const linkEl = parentEl.tagName === 'A' ? parentEl : null;
        switch (methodName) {
            case 'setLink': {
                return linkEl ? 'true' : '';
            }
            case 'setUrl': {
                let href = linkEl ? linkEl.getAttribute('href') : '';
                return href || '';
            }
            case 'setNewWindow': {
                const target = linkEl ? linkEl.getAttribute('target') : '';
                return target && target === '_blank' ? 'true' : '';
            }
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'media_link_opt') {
            if (this.$target[0].matches('img')) {
                return isImageSupportedForStyle(this.$target[0]);
            }
            return !this.$target[0].classList.contains('media_iframe_video');
        }
        return this._super(...arguments);
    },
});

/*
 * Abstract option to be extended by the ImageTools and BackgroundOptimize
 * options that handles all the common parts.
 */
const ImageHandlerOption = SnippetOptionWidget.extend({
    /**
     * @override
     */
    async willStart() {
        const _super = this._super.bind(this);
        await this._initializeImage();
        return _super(...arguments);
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        const weightEl = document.createElement('span');
        weightEl.classList.add('o_we_image_weight', 'o_we_tag', 'd-none');
        weightEl.title = _t("Size");
        this.$weight = $(weightEl);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        await this._super(...arguments);

        if (this._filesize === undefined) {
            this.$weight.addClass('d-none');
            await this._applyOptions(false);
        }
        if (this._filesize !== undefined) {
            this.$weight.text(`${this._filesize.toFixed(1)} kb`);
            this.$weight.removeClass('d-none');
            this._relocateWeightEl();
        }
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
    async setQuality(previewMode, widgetValue, params) {
        if (previewMode) {
            return;
        }
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
        const _super = this._super.bind(this);

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
        return _super(...arguments);
    },
    /**
     * @abstract
     */
    _relocateWeightEl() {},
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const img = this._getImg();
        if (!this.originalSrc || !this._isImageSupportedForProcessing(img)) {
            return;
        }
        const $select = $(uiFragment).find('we-select[data-name=width_select_opt]');
        (await this._computeAvailableWidths()).forEach(([value, label]) => {
            $select.append(`<we-button data-select-width="${value}">${label}</we-button>`);
        });

        if (this._getImageMimetype(img) !== 'image/jpeg') {
            const optQuality = uiFragment.querySelector('we-range[data-set-quality]');
            if (optQuality) {
                optQuality.remove();
            }
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
     * @param {boolean} [update=true] If this is false, this does not actually
     *     modifies the image but only simulates the modifications on it to
     *     be able to update the filesize UI.
     */
    async _applyOptions(update = true) {
        const img = this._getImg();
        if (!update && !(img && img.complete)) {
            return;
        }
        if (!this._isImageSupportedForProcessing(img)) {
            this.originalId = null;
            this._filesize = undefined;
            return;
        }
        const dataURL = await applyModifications(img, {mimetype: this._getImageMimetype(img)});
        this._filesize = dataURL.split(',')[1].length / 4 * 3 / 1024;

        if (update) {
            img.classList.add('o_modified_image_to_save');
            const loadedImg = await loadImage(dataURL, img);
            this._applyImage(loadedImg);
            return loadedImg;
        }
        return img;
    },
    /**
     * Loads the image's attachment info.
     *
     * @private
     */
    async _loadImageInfo(attachmentSrc = '') {
        const img = this._getImg();
        await loadImageInfo(img, this._rpc.bind(this), attachmentSrc);
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
    /**
     * @private
     * @param {HTMLImageElement} img
     * @returns {String} The right mimetype used to apply options on image.
     */
    _getImageMimetype(img) {
        return img.dataset.mimetype;
    },
    /**
     * @private
     */
    async _initializeImage() {
        return this._loadImageInfo();
    },
     /**
     * @private
     * @param {HTMLImageElement} img
     * @param {Boolean} [strict=false]
     * @returns {Boolean}
     */
    _isImageSupportedForProcessing(img, strict = false) {
        return isImageSupportedForProcessing(this._getImageMimetype(img), strict);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (this._isImageProcessingWidget(widgetName, params)) {
            const img = this._getImg();
            return this._isImageSupportedForProcessing(img, true);
        }
        return isImageSupportedForStyle(this._getImg());
    },
    /**
     * Indicates if an option should be applied only on supported mimetypes.
     *
     * @param {String} widgetName
     * @param {Object} params
     * @returns {Boolean}
     */
    _isImageProcessingWidget(widgetName, params) {
        return params.optionsPossibleValues.glFilter
            || 'customFilter' in params.optionsPossibleValues
            || params.optionsPossibleValues.setQuality
            || widgetName === 'width_select_opt';
    },
});

/**
 * @param {Element} containerEl
 * @returns {Element}
 */
const _addAnimatedShapeLabel = function addAnimatedShapeLabel(containerEl) {
    const labelEl = document.createElement('span');
    labelEl.classList.add('o_we_shape_animated_label');
    const labelStr = _t("Animated");
    labelEl.textContent = labelStr[0];
    const spanEl = document.createElement('span');
    spanEl.textContent = labelStr.substr(1);
    labelEl.appendChild(spanEl);
    containerEl.classList.add('position-relative');
    containerEl.appendChild(labelEl);
    return labelEl;
};

/**
 * Controls image width and quality.
 */
registry.ImageTools = ImageHandlerOption.extend({
    MAX_SUGGESTED_WIDTH: 1920,

    /**
     * @constructor
     */
    init() {
        this.shapeCache = {};
        return this._super(...arguments);
    },
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
    // Options
    //--------------------------------------------------------------------------

    /**
     * Displays the image cropping tools
     *
     * @see this.selectClass for parameters
     */
    async crop() {
        this.trigger_up('hide_overlay');
        this.trigger_up('disable_loading_effect');
        const img = this._getImg();
        new weWidgets.ImageCropWidget(this, img, {mimetype: this._getImageMimetype(img)}).appendTo(this.$el[0].ownerDocument.body);

        await new Promise(resolve => {
            this.$target.one('image_cropper_destroyed', async () => {
                if (isGif(this._getImageMimetype(img))) {
                    img.dataset[img.dataset.shape ? 'originalMimetype' : 'mimetype'] = 'image/png';
                }
                await this._reapplyCurrentShape();
                resolve();
            });
        });
        this.trigger_up('enable_loading_effect');
    },
    /**
     * Displays the image transformation tools
     *
     * @see this.selectClass for parameters
     */
    async transform() {
        this.trigger_up('hide_overlay');
        this.trigger_up('disable_loading_effect');

        const document = this.$target[0].ownerDocument;
        const playState = this.$target[0].style.animationPlayState;
        const transition = this.$target[0].style.transition;
        this.$target.transfo({document});
        const mousedown = mousedownEvent => {
            if (!$(mousedownEvent.target).closest('.transfo-container').length) {
                this.$target.transfo('destroy');
                $(document).off('mousedown', mousedown);
                // Restore animation css properties potentially affected by the
                // jQuery transfo plugin.
                this.$target[0].style.animationPlayState = playState;
                this.$target[0].style.transition = transition;
            }
        };
        $(document).on('mousedown', mousedown);

        await new Promise(resolve => {
            document.addEventListener('mouseup', resolve, {once: true});
        });
        this.trigger_up('enable_loading_effect');
    },
    /**
     * Resets the image cropping
     *
     * @see this.selectClass for parameters
     */
    async resetCrop() {
        const img = this._getImg();
        const cropper = new weWidgets.ImageCropWidget(this, img, {mimetype: this._getImageMimetype(img)});
        await cropper.appendTo(this.$el[0].ownerDocument.body);
        await cropper.reset();
        await this._reapplyCurrentShape();
    },
    /**
     * Resets the image rotation and translation
     *
     * @see this.selectClass for parameters
     */
    async resetTransform() {
        this.$target
            .attr('style', (this.$target.attr('style') || '')
            .replace(/[^;]*transform[\w:]*;?/g, ''));
    },
    /**
     * @see this.selectClass for parameters
     */
    async setImgShape(previewMode, widgetValue, params) {
        const img = this._getImg();
        const saveData = previewMode === false;
        if (widgetValue) {
            await this._loadShape(widgetValue);
            if (previewMode === 'reset' && img.dataset.shapeColors) {
                // When we reset the shape we need to reapply the colors the
                // user had selected.
                await this._applyShapeAndColors(false, img.dataset.shapeColors.split(';'));
            } else {
                // If the preview mode === false we want to save the colors
                // as the user chose their shape
                await this._applyShapeAndColors(saveData);
                if (saveData && img.dataset.mimetype !== 'image/svg+xml') {
                    img.dataset.originalMimetype = img.dataset.mimetype;
                    img.dataset.mimetype = 'image/svg+xml';
                }
            }
        } else {
            // Re-applying the modifications and deleting the shapes
            img.src = await applyModifications(img, {mimetype: this._getImageMimetype(img)});
            delete img.dataset.shape;
            delete img.dataset.shapeColors;
            delete img.dataset.fileName;
            if (saveData) {
                img.dataset.mimetype = img.dataset.originalMimetype;
                delete img.dataset.originalMimetype;
            }
        }
        img.classList.add('o_modified_image_to_save');
    },
    /**
     * Handles color assignment on the shape. Widget is a color picker.
     * If no value, we reset to the current color palette.
     *
     * @see this.selectClass for parameters
     */
    async setImgShapeColor(previewMode, widgetValue, params) {
        const img = this._getImg();
        const newColorId = parseInt(params.colorId);
        const oldColors = img.dataset.shapeColors.split(';');
        const newColors = oldColors.slice(0);
        newColors[newColorId] = this._getCSSColorValue(widgetValue === '' ? `o-color-${(newColorId + 1)}` : widgetValue);
        await this._applyShapeAndColors(true, newColors);
        img.classList.add('o_modified_image_to_save');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
￼    * @private
￼    */
    _isTransformed() {
        return this.$target.is('[style*="transform"]');
    },
    /**
￼    * @private
￼    */
    _isCropped() {
        return this.$target.hasClass('o_we_image_cropped');
    },
    /**
     * @override
     */
    async _applyOptions() {
        const img = await this._super(...arguments);
        if (img && img.dataset.shape) {
            await this._loadShape(img.dataset.shape);
            if (/^data:/.test(img.src)) {
                // Reapplying the shape
                await this._applyShapeAndColors(true, (img.dataset.shapeColors && img.dataset.shapeColors.split(';')));
            }
        }
        return img;
    },
    /**
     * Loads the shape into cache if not already and sets it in the dataset of
     * the img
     *
     * @param {string} shapeName identifier of the shape
     */
    async _loadShape(shapeName) {
        const [module, directory, fileName] = shapeName.split('/');
        let shape = this.shapeCache[fileName];
        if (!shape) {
            const shapeURL = `/${module}/static/image_shapes/${directory}/${fileName}.svg`;
            shape = await (await fetch(shapeURL)).text();
            this.shapeCache[fileName] = shape;
        }
        this._getImg().dataset.shape = shapeName;
    },

    /**
     * Applies the shape in img.dataset.shape and replaces the previous hex
     * color values with new ones or current theme
     * ones then calls _writeShape()
     *
     * @param {boolean} save true if the colors need to be saved in the
     * data-attribute
     * @param {string[]} [newColors] Array of HEX color code, default
     * theme colors are applied if not supplied
     */
    async _applyShapeAndColors(save, newColors) {
        const img = this._getImg();
        let shape = this.shapeCache[img.dataset.shape.split('/')[2]];

        // Map the default palette colors to an array if the shape includes them
        // If they do not map a NULL, this way we know if a default color is in
        // the shape
        const oldColors = Object.values(DEFAULT_PALETTE).map(color => shape.includes(color) ? color : null);
        if (!newColors) {
            // If we do not have newColors, we still replace the default
            // shape's colors by the current palette's
            newColors = oldColors.map((color, i) => color !== null ? this._getCSSColorValue(`o-color-${(i + 1)}`) : null);
        }
        newColors.forEach((color, i) => shape = shape.replace(new RegExp(oldColors[i], 'g'), this._getCSSColorValue(color)));
        await this._writeShape(shape);
        if (save) {
            img.dataset.shapeColors = newColors.join(';');
        }
    },
    /**
     * Sets the image in the supplied SVG and replace the src with a dataURL
     *
     * @param {string} svgText svg file as text
     * @returns {Promise} resolved once the svg is properly loaded
     * in the document
     */
    async _writeShape(svgText) {
        const img = this._getImg();
        const initialImageWidth = img.naturalWidth;

        const svg = new DOMParser().parseFromString(svgText, 'image/svg+xml').documentElement;
        const svgAspectRatio = parseInt(svg.getAttribute('width')) / parseInt(svg.getAttribute('height'));
        // We will store the image in base64 inside the SVG.
        // applyModifications will return a dataURL with the current filters
        // and size options.
        const options = {
            mimetype: this._getImageMimetype(img),
            perspective: svg.dataset.imgPerspective || null,
            imgAspectRatio: svg.dataset.imgAspectRatio || null,
            svgAspectRatio: svgAspectRatio,
        };
        const imgDataURL = await applyModifications(img, options);
        svg.removeChild(svg.querySelector('#preview'));
        svg.querySelector('image').setAttribute('xlink:href', imgDataURL);
        // Force natural width & height (note: loading the original image is
        // needed for Safari where natural width & height of SVG does not return
        // the correct values).
        const originalImage = await loadImage(imgDataURL, img);
        // If the svg forces the size of the shape we still want to have the resized
        // width
        if (!svg.dataset.forcedSize) {
            svg.setAttribute('width', originalImage.naturalWidth);
            svg.setAttribute('height', originalImage.naturalHeight);
        } else {
            const imageWidth = Math.trunc(img.dataset.resizeWidth || img.dataset.width || initialImageWidth);
            const newHeight = imageWidth / svgAspectRatio;
            svg.setAttribute('width', imageWidth);
            svg.setAttribute('height', newHeight);
        }
        // Transform the current SVG in a base64 file to be saved by the server
        const blob = new Blob([svg.outerHTML], {
            type: 'image/svg+xml',
        });
        const dataURL = await createDataURL(blob);
        const imgFilename = (img.dataset.originalSrc.split('/').pop()).split('.')[0];
        img.dataset.fileName = `${imgFilename}.svg`;
        return loadImage(dataURL, img);
    },
    /**
     * @override
     */
    _computeMaxDisplayWidth() {
        const img = this._getImg();
        const computedStyles = window.getComputedStyle(img);
        const displayWidth = parseFloat(computedStyles.getPropertyValue('width'));
        const gutterWidth = parseFloat(computedStyles.getPropertyValue('--o-grid-gutter-width')) || 30;

        // For the logos we don't want to suggest a width too small.
        if (this.$target[0].closest('nav')) {
            return Math.round(Math.min(displayWidth * 3, this.MAX_SUGGESTED_WIDTH));
        // If the image is in a container(-small), it might get bigger on
        // smaller screens. So we suggest the width of the current image unless
        // it is smaller than the size of the container on the md breapoint
        // (which is where our bootstrap columns fallback to full container
        // width since we only use col-lg-* in Odoo).
        } else if (img.closest('.container, .o_container_small')) {
            const mdContainerMaxWidth = parseFloat(computedStyles.getPropertyValue('--o-md-container-max-width')) || 720;
            const mdContainerInnerWidth = mdContainerMaxWidth - gutterWidth;
            return Math.round(utils.confine(displayWidth, mdContainerInnerWidth, this.MAX_SUGGESTED_WIDTH));
        // If the image is displayed in a container-fluid, it might also get
        // bigger on smaller screens. The same way, we suggest the width of the
        // current image unless it is smaller than the max size of the container
        // on the md breakpoint (which is the LG breakpoint since the container
        // fluid is full-width).
        } else if (img.closest('.container-fluid')) {
            const lgBp = parseFloat(computedStyles.getPropertyValue('--breakpoint-lg')) || 992;
            const mdContainerFluidMaxInnerWidth = lgBp - gutterWidth;
            return Math.round(utils.confine(displayWidth, mdContainerFluidMaxInnerWidth, this.MAX_SUGGESTED_WIDTH));
        }
        // If it's not in a container, it's probably not going to change size
        // depending on breakpoints. We still keep a margin safety.
        return Math.round(Math.min(displayWidth * 1.5, this.MAX_SUGGESTED_WIDTH));
    },
    /**
     * @override
     */
    _getImg() {
        return this.$target[0];
    },
    /**
     * @override
     */
    _relocateWeightEl() {
        const leftPanelEl = this.$overlay.data('$optionsSection')[0];
        const titleTextEl = leftPanelEl.querySelector('we-title > span');
        this.$weight.appendTo(titleTextEl);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName.startsWith('img-shape-color')) {
            const img = this._getImg();
            const shapeName = img.dataset.shape;
            if (!shapeName) {
                return false;
            }
            const colors = img.dataset.shapeColors.split(';');
            return colors[parseInt(params.colorId)];
        }
        if (params.optionsPossibleValues.resetTransform) {
            return this._isTransformed();
        }
        if (params.optionsPossibleValues.resetCrop) {
            return this._isCropped();
        }
        if (params.optionsPossibleValues.crop) {
            const img = this._getImg();
            return isImageSupportedForStyle(img) || this._isImageSupportedForProcessing(img);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'selectStyle': {
                if (params.cssProperty === 'width') {
                    // TODO check how to handle this the right way (here using
                    // inline style instead of computed because of the messy
                    // %-px convertion and the messy auto keyword).
                    const width = this.$target[0].style.width.trim();
                    if (width[width.length - 1] === '%') {
                        return `${parseInt(width)}%`;
                    }
                    return '';
                }
                break;
            }
            case 'transform': {
                return this._isTransformed() ? 'true' : '';
            }
            case 'crop': {
                return this._isCropped() ? 'true' : '';
            }
            case 'setImgShape': {
                return this._getImg().dataset.shape || '';
            }
            case 'setImgShapeColor': {
                const img = this._getImg();
                return (img.dataset.shapeColors && img.dataset.shapeColors.split(';')[parseInt(params.colorId)]) || '';
            }
        }
        return this._super(...arguments);
    },
    /**
     * Appends the SVG as an image.
     * Due to the nature of image_shapes' SVGs, it is easier to render them as
     * img compared to appending their content to the DOM
     * (which is what the current data-img does)
     *
     * @override
     */
    async _renderCustomXML(uiFragment) {
        await this._super(...arguments);
        uiFragment.querySelectorAll('we-select-page we-button[data-set-img-shape]').forEach(btn => {
            const image = document.createElement('img');
            const [moduleName, directory, shapeName] = btn.dataset.setImgShape.split('/');
            image.src = `/${moduleName}/static/image_shapes/${directory}/${shapeName}.svg`;
            $(btn).prepend(image);

            if (btn.dataset.animated) {
                _addAnimatedShapeLabel(btn);
            }
        });
    },
    /**
     * @override
     */
    _getImageMimetype(img) {
        if (img.dataset.shape && img.dataset.originalMimetype) {
            return img.dataset.originalMimetype;
        }
        return this._super(...arguments);
    },
    /**
     * Gets the CSS value of a color variable name so it can be used on shapes.
     *
     * @param {string} color
     * @returns {string}
     */
    _getCSSColorValue(color) {
        if (!color || ColorpickerWidget.isCSSColor(color)) {
            return color;
        }
        return weUtils.getCSSVariableValue(color);
    },
    /**
     * Overridden to set attachment data on theme images (with default shapes).
     *
     * @override
     * @private
     */
    async _initializeImage() {
        const img = this._getImg();
        let match = img.src.match(/\/web_editor\/image_shape\/(\w+\.\w+)/);
        if (img.dataset.shape && match) {
            match = match[1];
            if (match.endsWith("_perspective")) {
                // As an image might already have been modified with a
                // perspective for some customized snippets in themes. We need
                // to find the original image to set the 'data-original-src'
                // attribute.
                match = match.slice(0, -12);
            }
            return this._loadImageInfo(`/web/image/${match}`);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     * @private
     */
    async _loadImageInfo() {
        await this._super(...arguments);
        const img = this._getImg();
        if (img.dataset.shape && img.dataset.mimetype !== 'image/svg+xml') {
            img.dataset.originalMimetype = img.dataset.mimetype;
            if (!this._isImageSupportedForProcessing(img)) {
                delete img.dataset.shape;
                delete img.dataset.shapeColors;
                delete img.dataset.fileName;
                delete img.dataset.originalMimetype;
                return;
            }
            // Image data-mimetype should be changed to SVG since loadImageInfo()
            // will set the original attachment mimetype on it.
            img.dataset.mimetype = 'image/svg+xml';
        }
    },
    /**
     * @private
     */
    async _reapplyCurrentShape() {
        const img = this._getImg();
        if (img.dataset.shape) {
            await this._loadShape(img.dataset.shape);
            await this._applyShapeAndColors(true, (img.dataset.shapeColors && img.dataset.shapeColors.split(';')));
        }
    },
    /**
     * @override
     */
    _isImageProcessingWidget(widgetName, params) {
        if (widgetName === 'shape_img_opt') {
            return !isGif(this._getImageMimetype(this._getImg()));
        }
        return this._super(...arguments);
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
    _relocateWeightEl() {
        this.trigger_up('option_update', {
            optionNames: ['BackgroundImage'],
            name: 'add_size_indicator',
            data: this.$weight,
        });
        // Hack to align on the right
        this.$weight.css({
            'width': '200px', // Make parent row grow by faking a width
            'flex': '0 0 0', // But force no forced width
            'margin-left': 'auto',
        });
    },
    /**
     * @override
     */
    _applyImage(img) {
        const parts = backgroundImageCssToParts(this.$target.css('background-image'));
        parts.url = `url('${img.getAttribute('src')}')`;
        const combined = backgroundImagePartsToCss(parts);
        this.$target.css('background-image', combined);
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
            this.$target.find('> .o_we_bg_filter').remove();
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
     * Sets a color filter.
     *
     * @see this.selectClass for parameters
     */
    async selectFilterColor(previewMode, widgetValue, params) {
        // Find the filter element.
        let filterEl = this.$target[0].querySelector(':scope > .o_we_bg_filter');

        // If the filter would be transparent, remove it / don't create it.
        const rgba = widgetValue && ColorpickerWidget.convertCSSColorToRgba(widgetValue);
        if (!widgetValue || rgba && rgba.opacity < 0.001) {
            if (filterEl) {
                filterEl.remove();
            }
            return;
        }

        // Create the filter if necessary.
        if (!filterEl) {
            filterEl = document.createElement('div');
            filterEl.classList.add('o_we_bg_filter');
            const lastBackgroundEl = this._getLastPreFilterLayerElement();
            if (lastBackgroundEl) {
                $(lastBackgroundEl).after(filterEl);
            } else {
                this.$target.prepend(filterEl);
            }
        }

        // Apply the color on the filter.
        const obj = createPropertyProxy(this, '$target', $(filterEl));
        params.cssProperty = 'background-color';
        return this.selectStyle.call(obj, previewMode, widgetValue, params);
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
            case 'toggleBgShape': {
                const [shapeWidget] = this._requestUserValueWidgets('bg_shape_opt');
                const shapeOption = shapeWidget.getParent();
                return !!shapeOption._computeWidgetState('shape', shapeWidget.getMethodsParams('shape'));
            }
            case 'selectFilterColor': {
                const filterEl = this.$target[0].querySelector(':scope > .o_we_bg_filter');
                if (!filterEl) {
                    return '';
                }
                const obj = createPropertyProxy(this, '$target', $(filterEl));
                params.cssProperty = 'background-color';
                return this._computeWidgetState.call(obj, 'selectStyle', params);
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
                this._setBackground(this.previousSrc);
                return;
        }
        const newURL = new URL(currentSrc, window.location.origin);
        newURL.searchParams.set(params.colorName, normalizeColor(widgetValue));
        const src = newURL.pathname + newURL.search;
        await loadImage(src);
        this._setBackground(src);
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
    notify(name, data) {
        if (name === 'add_size_indicator') {
            this._requestUserValueWidgets('bg_image_opt')[0].$el.after(data);
        } else {
            this._super(...arguments);
        }
    },
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
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'background':
                return getBgImageURL(this.$target[0]);
            case 'dynamicColor':
                return new URL(getBgImageURL(this.$target[0]), window.location.origin).searchParams.get(params.colorName);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if ('colorName' in params) {
            const src = new URL(getBgImageURL(this.$target[0]), window.location.origin);
            return src.searchParams.has(params.colorName);
        } else if (widgetName === 'main_color_opt') {
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
        const parts = backgroundImageCssToParts(this.$target.css('background-image'));
        if (backgroundURL) {
            parts.url = `url('${backgroundURL}')`;
            this.$target.addClass('oe_img_bg o_bg_img_center');
        } else {
            delete parts.url;
            this.$target.removeClass('oe_img_bg o_bg_img_center');
        }
        const combined = backgroundImagePartsToCss(parts);
        this.$target.css('background-image', combined);
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
            return {shape: widgetValue, colors: this._getImplicitColors(widgetValue, this._getShapeData().colors), flip: []};
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
                .prepend($(`<we-colorpicker data-color="true" data-color-name="${colorName}"></we-colorpicker>`)[0]);
        });

        uiFragment.querySelectorAll('we-select-pager we-button[data-shape]').forEach(btn => {
            const btnContent = document.createElement('div');
            btnContent.classList.add('o_we_shape_btn_content', 'position-relative', 'border-dark');
            const btnContentInnerDiv = document.createElement('div');
            btnContentInnerDiv.classList.add('o_we_shape');
            btnContent.appendChild(btnContentInnerDiv);

            if (btn.dataset.animated) {
                _addAnimatedShapeLabel(btnContent);
            }

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
     * Inserts or removes the given container at the right position in the
     * document.
     *
     * @param {HTMLElement} [newContainer] container to insert, null to remove
     */
    _insertShapeContainer(newContainer) {
        const target = this.$target[0];

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
    },
    /**
     * Creates and inserts a container for the shape with the right classes.
     *
     * @param {string} shape the shape name for which to create a container
     */
    _createShapeContainer(shape) {
        const shapeContainer = this._insertShapeContainer(document.createElement('div'));
        this.$target[0].style.position = 'relative';
        shapeContainer.className = `o_we_shape o_${shape.replace(/\//g, '_')}`;
        return shapeContainer;
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

        let changedShape = false;
        if (previewMode === 'reset') {
            this._insertShapeContainer(this.prevShapeContainer);
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
            return this._insertShapeContainer(null);
        }
        // When changing shape we want to reset the shape container (for transparency color)
        if (changedShape) {
            shapeContainer = this._createShapeContainer(shape);
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
            return defaultColors[colorName] && colorValue.toLowerCase() === defaultColors[colorName].toLowerCase();
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
            colors: this._getDefaultColors($(target)),
            flip: [],
        };
        const json = target.dataset.oeShapeData;
        return json ? Object.assign(defaultData, JSON.parse(json.replace(/'/g, '"'))) : defaultData;
    },
    /**
     * Returns the default colors for the currently selected shape.
     *
     * @private
     * @param {jQueryElement} [$target=this.$target] the target on which to read
     *   the shape data.
     */
    _getDefaultColors($target = this.$target) {
        const $shapeContainer = $target.find('> .o_we_shape')
            .clone()
            .addClass('d-none')
            // Needs to be in document for bg-image class to take effect
            .appendTo(this.$target[0].ownerDocument.body);
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
     * Returns the default colors for the a shape in the selector.
     *
     * @private
     * @param {String} shapeId identifier of the shape
     */
    _getShapeDefaultColors(shapeId) {
        const $shapeContainer = this.$el.find(".o_we_shape_menu we-button[data-shape='" + shapeId + "'] div.o_we_shape");
        const shapeContainer = $shapeContainer[0];
        const shapeSrc = shapeContainer && getBgImageURL(shapeContainer);
        const url = new URL(shapeSrc, window.location.origin);
        return Object.fromEntries(url.searchParams.entries());
    },
    /**
     * Returns the implicit colors for the currently selected shape.
     *
     * The implicit colors are use upon shape selection. They are computed as:
     * - the default colors
     * - patched with each set of colors of previous siblings shape
     * - patched with the colors of the previously selected shape
     * - filtered to only keep the colors involved in the current shape
     *
     * @private
     * @param {String} shape identifier of the selected shape
     * @param {Object} previousColors colors of the shape before its replacement
     */
    _getImplicitColors(shape, previousColors) {
        const defaultColors = this._getShapeDefaultColors(shape);
        let colors = previousColors || {};
        let sibling = this.$target[0].previousElementSibling;
        while (sibling) {
            colors = Object.assign(this._getShapeData(sibling).colors || {}, colors);
            sibling = sibling.previousElementSibling;
        }
        const defaultKeys = Object.keys(defaultColors);
        colors = Object.assign(defaultColors, colors);
        return _.pick(colors, defaultKeys);
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
            this.trigger_up('snippet_edition_request', {exec: () => {
                // options for shape will only be available after _toggleShape() returned
                this._requestUserValueWidgets('bg_shape_opt')[0].enable();
            }});
            this._createShapeContainer(shapeToSelect);
            return this._handlePreviewState(false, () => ({shape: shapeToSelect, colors: this._getImplicitColors(shapeToSelect)}));
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
        // Make sure the element is in a visible area.
        const rect = this.$target[0].getBoundingClientRect();
        const viewportTop = $(window).scrollTop();
        const viewportBottom = viewportTop + $(window).height();
        const visibleHeight = rect.top < viewportTop
            ? Math.max(0, Math.min(viewportBottom, rect.bottom) - viewportTop) // Starts above
            : rect.top < viewportBottom
                ? Math.min(viewportBottom, rect.bottom) - rect.top // Starts inside
                : 0; // Starts after
        if (visibleHeight < 200) {
            await scrollTo(this.$target[0], {extraOffset: 50});
        }
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
        const $wrapwrap = $(this.ownerDocument.body).find("#wrapwrap");
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

        const topPos = Math.max(0, $(window).scrollTop() - this.$target.offset().top);
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
        const $document = $(document);
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
        if (!$(ev.target).closest('.o_we_background_position_overlay').length) {
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
        this.options.wysiwyg.odooEditor.observerUnactive('_markColorLevel');
        this.$target.addClass('o_colored_level');
        this.options.wysiwyg.odooEditor.observerActive('_markColorLevel');
    },
});

registry.ContainerWidth = SnippetOptionWidget.extend({
    /**
     * @override
     */
    cleanForSave: function () {
        this.$target.removeClass('o_container_preview');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    selectClass: async function (previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (previewMode === 'reset') {
            this.$target.removeClass('o_container_preview');
        } else if (previewMode) {
            this.$target.addClass('o_container_preview');
        }
        this.trigger_up('option_update', {
            optionName: 'StepsConnector',
            name: 'change_container_width',
        });
    },
});

/**
 * Allows to replace a text value with the name of a database record.
 * @todo replace this mechanism with real backend m2o field ?
 */
registry.many2one = SnippetOptionWidget.extend({
    /**
     * @override
     */
    async willStart() {
        const {oeMany2oneModel, oeMany2oneId} = this.$target[0].dataset;
        this.fields = ['name', 'display_name'];
        return Promise.all([
            this._super(...arguments),
            this._rpc({
                model: oeMany2oneModel,
                method: 'read',
                args: [[parseInt(oeMany2oneId)], this.fields],
            }).then(([initialRecord]) => {
                this.initialRecord = initialRecord;
            }),
        ]);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for params
     */
    async changeRecord(previewMode, widgetValue, params) {
        const target = this.$target[0];
        if (previewMode === 'reset') {
            // Have to set the jQ data because it's used to update the record in other
            // parts of the page, but have to set the dataset because used for saving.
            this.$target.data('oeMany2oneId', this.prevId);
            target.dataset.oeMany2oneId = this.prevId;
            this.$target.empty().append(this.$prevContents);
            return this._rerenderContacts(this.prevId, this.prevRecordName);
        }

        const record = JSON.parse(params.recordData);
        if (previewMode === true) {
            this.prevId = parseInt(target.dataset.oeMany2oneId);
            this.$prevContents = this.$target.contents();
            this.prevRecordName = this.prevRecordName || this.initialRecord.name;
        }

        this.$target.data('oeMany2oneId', record.id);
        target.dataset.oeMany2oneId = record.id;

        if (target.dataset.oeType !== 'contact') {
            target.textContent = record.name;
        }
        await this._rerenderContacts(record.id, record.name);

        if (previewMode === false) {
            this.prevId = record.id;
            this.$prevContents = this.$target.contents();
            this.prevRecordName = record.name;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'changeRecord') {
            return this.$target[0].dataset.oeMany2oneId;
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        const many2oneWidget = document.createElement('we-many2one');
        many2oneWidget.dataset.changeRecord = '';

        const model = this.$target[0].dataset.oeMany2oneModel;
        const [{name: modelName}] = await this._rpc({
            model: 'ir.model',
            method: 'search_read',
            args: [[['model', '=', model]], ['name']],
        });
        many2oneWidget.setAttribute('String', modelName);
        many2oneWidget.dataset.model = model;
        many2oneWidget.dataset.fields = JSON.stringify(this.fields);
        uiFragment.appendChild(many2oneWidget);
    },
    /**
     * @private
     */
    async _rerenderContacts(contactId, defaultText) {
        // Rerender this same field in other places in the page (with different
        // contact-options). Many2ones with the same contact options will just
        // copy the HTML of the current m2o on content_changed. Not sure why we
        // only do this for contacts, or why we do this here instead of in the
        // wysiwyg like we do for replacing text on content_changed
        const selector = [
            `[data-oe-model="${this.$target.data('oe-model')}"]`,
            `[data-oe-id="${this.$target.data('oe-id')}"]`,
            `[data-oe-field="${this.$target.data('oe-field')}"]`,
            `[data-oe-contact-options!='${this.$target[0].dataset.oeContactOptions}']`,
        ].join('');
        let $toRerender = $(selector);
        if (this.$target[0].dataset.oeType === 'contact') {
            $toRerender = $toRerender.add(this.$target);
        }
        await Promise.all($toRerender
            .attr('data-oe-many2one-id', contactId).data('oe-many2one-id', contactId)
            .map(async (i, node) => {
                if (node.dataset.oeType === 'contact') {
                    const html = await this._rpc({
                        model: 'ir.qweb.field.contact',
                        method: 'get_record_to_html',
                        args: [[contactId]],
                        kwargs: {options: JSON.parse(node.dataset.oeContactOptions)},
                    });
                    $(node).html(html);
                } else {
                    node.textContent = defaultText;
                }
            }));
    },
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
            Dialog.confirm(this, _t("To save a snippet, we need to save all your previous modifications and reload the page."), {
                cancel_callback: () => resolve(false),
                buttons: [
                    {
                        text: _t("Save and Reload"),
                        classes: 'btn-primary',
                        close: true,
                        click: () => {
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
                                invalidateSnippetCache: true,
                                onSuccess: async () => {
                                    const defaultSnippetName = _.str.sprintf(_t("Custom %s"), this.data.snippetName);
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
                                            'name': defaultSnippetName,
                                            'arch': targetCopyEl.outerHTML,
                                            'template_key': this.options.snippets,
                                            'snippet_key': snippetKey,
                                            'thumbnail_url': thumbnailURL,
                                            'context': context,
                                        },
                                    });
                                },
                            });
                            resolve(true);
                        }
                    }, {
                        text: _t("Cancel"),
                        close: true,
                        click: () => resolve(false),
                    }
                ]
            });
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
        newURL.searchParams.set(params.colorName, normalizeColor(widgetValue));
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
                return new URL(this.$target[0].src, window.location.origin).searchParams.get(params.colorName);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if ('colorName' in params) {
            return new URL(this.$target[0].src, window.location.origin).searchParams.get(params.colorName);
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

/**
 * Allows to handle snippets with a list of items.
 */
registry.MultipleItems = SnippetOptionWidget.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    async addItem(previewMode, widgetValue, params) {
        const $target = this.$(params.item);
        const addBeforeItem = params.addBefore === 'true';
        if ($target.length) {
            await new Promise(resolve => {
                this.trigger_up('clone_snippet', {
                    $snippet: $target,
                    onSuccess: resolve,
                });
            });
            if (addBeforeItem) {
                $target.before($target.next());
            }
            if (params.selectItem !== 'false') {
                this.trigger_up('activate_snippet', {
                    $snippet: addBeforeItem ? $target.prev() : $target.next(),
                });
            }
            this._addItemCallback($target);
        }
    },
    /**
     * @see this.selectClass for parameters
     */
    async removeItem(previewMode, widgetValue, params) {
        const $target = this.$(params.item);
        if ($target.length) {
            await new Promise(resolve => {
                this.trigger_up('remove_snippet', {
                    $snippet: $target,
                    onSuccess: resolve,
                });
            });
            this._removeItemCallback($target);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Allows to add behaviour when item added.
     *
     * @private
     * @abstract
     * @param {jQueryElement} $target
     */
    _addItemCallback($target) {},
    /**
     * @private
     * @abstract
     * @param {jQueryElement} $target
     */
    _removeItemCallback($target) {},
});

registry.SelectTemplate = SnippetOptionWidget.extend({
    custom_events: Object.assign({}, SnippetOptionWidget.prototype.custom_events, {
        'user_value_widget_opening': '_onWidgetOpening',
    }),

    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        this.containerSelector = '';
        this.selectTemplateWidgetName = '';
    },
    /**
     * @constructor
     */
    async start() {
        this.containerEl = this.containerSelector ? this.$target.find(this.containerSelector)[0] : this.$target[0];
        this._templates = {};
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the snippet layout.
     *
     * @see this.selectClass for parameters
     */
    async selectTemplate(previewMode, widgetValue, params) {
        await this._templatesLoading;

        if (previewMode === 'reset') {
            if (!this.beforePreviewNodes) {
                // FIXME should not be necessary: only needed because we have a
                // strange 'reset' sent after a non-preview
                return;
            }

            // Empty the container and restore the original content
            while (this.containerEl.lastChild) {
                this.containerEl.removeChild(this.containerEl.lastChild);
            }
            for (const node of this.beforePreviewNodes) {
                this.containerEl.appendChild(node);
            }
            this.beforePreviewNodes = null;
            return;
        }

        if (!this.beforePreviewNodes) {
            // We are about the apply a template on non-previewed content,
            // save that content's nodes.
            this.beforePreviewNodes = [...this.containerEl.childNodes];
        }
        // Empty the container and add the template content
        while (this.containerEl.lastChild) {
            this.containerEl.removeChild(this.containerEl.lastChild);
        }
        this.containerEl.insertAdjacentHTML('beforeend', this._templates[widgetValue]);

        if (!previewMode) {
            // The original content to keep saved has to be retrieved just
            // before the preview (if we save it now, we might miss other items
            // added by other options or custo).
            this.beforePreviewNodes = null;
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Retrieves a template either from cache or through RPC.
     *
     * @private
     * @param {string} xmlid
     * @returns {string}
     */
    async _getTemplate(xmlid) {
        if (!this._templates[xmlid]) {
            this._templates[xmlid] = await this._rpc({
                model: 'ir.ui.view',
                method: 'render_public_asset',
                args: [`${xmlid}`, {}],
                kwargs: {
                    context: this.options.context,
                },
            });
        }
        return this._templates[xmlid];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onWidgetOpening(ev) {
        if (this._templatesLoading || ev.target.getName() !== this.selectTemplateWidgetName) {
            return;
        }
        const templateParams = ev.target.getMethodsParams('selectTemplate');
        const proms = templateParams.possibleValues.map(async xmlid => {
            if (!xmlid) {
                return;
            }
            // TODO should be better and retrieve all rendering in one RPC (but
            // those ~10 RPC are only done once per edit mode if the option is
            // opened, so I guess this is acceptable).
            await this._getTemplate(xmlid);
        });
        this._templatesLoading = Promise.all(proms);
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

    addAnimatedShapeLabel: _addAnimatedShapeLabel,

    // Other names for convenience
    Class: SnippetOptionWidget,
    registry: registry,
};
});
