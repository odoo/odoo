/** @odoo-module **/

import { attachComponent } from "@web_editor/js/core/owl_utils";
import { uniqueId } from "@web/core/utils/functions";
import { registry } from "@web/core/registry";
import { MediaDialog } from "@web_editor/components/media_dialog/media_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { KeepLast } from "@web/core/utils/concurrency";
import { useSortable } from "@web/core/utils/sortable_owl";
import { camelToKebab } from "@web/core/utils/strings";
import { useThrottleForAnimation, debounce } from "@web/core/utils/timing";
import { clamp } from "@web/core/utils/numbers";
import { scrollTo } from "@web/core/utils/scrolling";
import Widget from "@web_editor/js/core/widget";
import { ColorPalette } from "@web_editor/js/wysiwyg/widgets/color_palette";
import weUtils from "@web_editor/js/common/utils";
import * as gridUtils from "@web_editor/js/common/grid_layout_utils";
import { ColumnLayoutMixin } from "@web_editor/js/common/column_layout_mixin";
const {
    normalizeColor,
    getBgImageURL,
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
    DEFAULT_PALETTE,
    isBackgroundImageAttribute,
} = weUtils;
import { ImageCrop } from '@web_editor/js/wysiwyg/widgets/image_crop';
import {
    loadImage,
    loadImageInfo,
    applyModifications,
    removeOnImageChangeAttrs,
    isImageSupportedForProcessing,
    isImageSupportedForStyle,
    createDataURL,
    isGif,
    getDataURLBinarySize,
} from "@web_editor/js/editor/image_processing";
import * as OdooEditorLib from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { pick } from "@web/core/utils/objects";
import { _t } from "@web/core/l10n/translation";
import {
    isCSSColor,
    convertCSSColorToRgba,
    normalizeCSSColor,
 } from '@web/core/utils/colors';
import { renderToElement } from "@web/core/utils/render";
import { rpc } from "@web/core/network/rpc";
import snippetsOptionsLegacy from "./snippets.options.legacy";
import {
    Component,
    markup,
    onMounted,
    onWillStart,
    onWillUpdateProps,
    onPatched,
    onWillDestroy,
    reactive,
    useEffect,
    useChildSubEnv,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { registerOption } from "./snippets.registry";

const preserveCursor = OdooEditorLib.preserveCursor;
const { DateTime } = luxon;
const resetOuids = OdooEditorLib.resetOuids;
let _serviceCache = {
    orm: {},
    rpc: {},
};
export const clearServiceCache = () => {
    _serviceCache = {
        orm: {},
        rpc: {},
    };
};

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
// TODO: This should be removed when all options are propperly migrated to OWL
const SnippetOptionWidget = snippetsOptionsLegacy.SnippetOptionWidget;
//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

// Regex definitions to apply speed modification in SVG files
// Note : These regex patterns are duplicated on the server side for
// background images that are part of a CSS rule "background-image: ...". The
// client-side regex patterns are used for images that are part of an
// "src" attribute with a base64 encoded svg in the <img> tag. Perhaps we should
// consider finding a solution to define them only once? The issue is that the
// regex patterns in Python are slightly different from those in JavaScript.
// See : controllers/main.py
const CSS_ANIMATION_RULE_REGEX =
    /(?<declaration>animation(?:-duration)?: .*?)(?<value>(?:\d+(?:\.\d+)?)|(?:\.\d+))(?<unit>ms|s)(?<separator>\s|;|"|$)/gm;
const SVG_DUR_TIMECOUNT_VAL_REGEX =
    /(?<attribute_name>\sdur="\s*)(?<value>(?:\d+(?:\.\d+)?)|(?:\.\d+))(?<unit>h|min|ms|s)?\s*"/gm;
const CSS_ANIMATION_RATIO_REGEX = /(--animation_ratio: (?<ratio>\d*(\.\d+)?));/m;
/**
 * Caches rpc/orm service
 * @param {Function} service
 * @param  {...any} args
 * @returns
 */
function serviceCached(service) {
    const cache = _serviceCache;
    return Object.assign(Object.create(service), {
        call() {
            // FIXME
            const serviceName = Object.prototype.hasOwnProperty.call(service, "call")
                ? "orm"
                : "rpc";
            const cacheId = JSON.stringify(arguments);
            if (!cache[serviceName][cacheId]) {
                cache[serviceName][cacheId] = service.call(...arguments);
            }
            return cache[serviceName][cacheId];
        },
    });
}
// Outdated snippets whose alert has been discarded.
const controlledSnippets = new Set();
export const clearControlledSnippets = () => controlledSnippets.clear();
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
        if (options && options.dataAttributes && options.dataAttributes.fontFamily) {
            titleEl.style.fontFamily = options.dataAttributes.fontFamily;
        }
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
            let text;
            if (src.split('.').pop() === 'svg') {
                try {
                    const response = await window.fetch(src);
                    text = await response.text();
                } catch {
                    // In some tours, the tour finishes before the fetch is done
                    // and when a tour is finished, the python side will ask the
                    // browser to stop loading resources. This causes the fetch
                    // to fail and throw an error which crashes the test even
                    // though it completed successfully.
                    // So return an empty SVG to ensure everything completes
                    // correctly.
                    text = "<svg></svg>";
                }
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

const _buildSvgElementCache = {};
async function buildSvgElement(src) {
    if (!(src in _buildSvgElementCache)) {
        _buildSvgElementCache[src] = (async () => {
            let text;
            try {
                const response = await window.fetch(src);
                text = await response.text();
            } catch {
                // In some tours, the tour finishes before the fetch is done
                // and when a tour is finished, the python side will ask the
                // browser to stop loading resources. This causes the fetch
                // to fail and throw an error which crashes the test even
                // though it completed successfully.
                // So return an empty SVG to ensure everything completes
                // correctly.
                text = "<svg></svg>";
            }
            return markup(text);
        })();
    }
    const svgMarkup = await _buildSvgElementCache[src];
    return svgMarkup;
}

export class WeTitle extends Component {
    static template = "web_editor.WeTitle";
    static props = {
        title: { type: String, optional: true },
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        "*": { optional: true },
    };
}

class WeRow extends Component {
    static template = "web_editor.WeRow";
    static props = {
        class: { type: String, optional: true },
        fontFamily: { type: String, optional: true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
        tooltip: { type: String, optional: true },
        "*": { optional: true },
    };
    static components = { WeTitle };
    setup() {
        /** @type {Object.<string, UserValue>} */
        this.userValues = {};
        this.state = useState({
            show: false,
        });
        this.env.registerLayoutElement({ state: this.state, userValues: this.userValues }, true);
        useChildSubEnv({
            registerUserValue: (userValue) => {
                this.userValues[userValue.id] = userValue;
                this.env.registerUserValue(userValue);
            },
            unregisterUserValue: (userValue) => {
                delete this.userValues[userValue.id];
                this.env.unregisterUserValue(userValue);
            },
        });
    }
}

registry.category("snippet_widgets").add("WeRow", WeRow);

/**
 * TODO: @owl-options remove when done.
 * Build the correct DOM for a we-collapse element.
 *
 * @param {string} [title] - @see _buildElement
 * @param {Object} [options] - @see _buildElement
 * @param {HTMLElement[]} [options.childNodes]
 * @returns {HTMLElement}
 */
export function _buildCollapseElement(title, options) {
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

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

const NULL_ID = '__NULL__';

/**
 * Base class for components to be used in snippet options widgets to retrieve
 * user values.
 */
const UserValueWidget = Widget;

export class UserValue {
    static custom_events = {
        'user_value_update': '_onUserValueNotification',
    };

    /**
     * @constructor
     * @param {string} id
     * @param {Object} state
     * @param {Object} env
     * @param {SnippetOption} option
     * @param {Object} data
     */
    constructor(id, state, env, option, data) {
        this.id = id;
        this.option = option;
        this.env = env;
        // TODO: @owl-option maybe we should take the opportunity to remove this.
        this.$target = env.$target;
        /** @type {UserValue[]} */
        this._subValues = {};
        this.mounted = false;
        this.textContent = "";
        this._state = state;
        this._state.preview = false;
        this._state.active = false;
        this._state.show = true;
        this._data = data;
    }
    /**
     * Returns the value that is currently in the state. This allows components
     * to react to state changes, and is different than what a SnippetOption
     * would need.
     */
    get value() {
        return this._state.value;
    }

    set value(value) {
        this._state.value = value;
    }
    /**
     * Returns whether the component that posses this state should be visible
     * or not. Cannot be set directly, use {@link toggleVisibility} instead.
     */
    get show() {
        return this._state.show;
    }
    /**
     * Returns whether sub widgets should or shouldn't be shown. Typically in
     * the case of a list, we do not want to show all buttons at all time, so
     * instead they will only be shown when this value is true.
     *
     * @type {boolean}
     */
    get opened() {
        return this._state.opened;
    }
    /**
     * Gives the opportunity for values to prepare asynchronous content.
     * E.g. fetch external data.
     */
    async start() {
        this.started = true;
    }
    /**
     * @TODO: @owl-options: This should be moved into the component
     */
    async willStart() {
        await this._super(...arguments);
        if (this.options.dataAttributes.reload) {
            this.options.dataAttributes.noPreview = "true";
        }
    }
    /**
     * @TODO: @owl-options: This should be moved into the component
     */
    _makeDescriptive() {
        const $el = this._super(...arguments);
        const el = $el[0];
        _addTitleAndAllowedAttributes(el, this.title, this.options);
        this.containerEl = document.createElement('div');

        if (this.illustrationEl) {
            this.containerEl.appendChild(this.illustrationEl);
        }

        el.appendChild(this.containerEl);
        return $el;
    }
    /**
     * @TODO: @owl-options: This should be moved into the component
     */
    async old_start() {
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
    }
    /**
     * @TODO: @owl-options: This should be moved into the component
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
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Closes the widget (only meaningful for widgets that can be closed).
     */
    close() {
        if (!this._state.opened) {
            // Small optimization: it would normally not matter asking to
            // remove a class of an element if it does not already have it but
            // in this case we do more: we trigger_up an event and ask to close
            // all sub widgets. When we ask the editor to close all widgets...
            // it makes sense not letting every sub button of every select
            // trigger_up an event. This allows to avoid tens of thousands of
            // instructions being done at each click in the editor.
            return;
        }
        this.env.userValueWidgetClosing();
        this._state.opened = false;
        Object.values(this._subValues).forEach(widget => widget.close());
    }
    /**
     * Triggers a value change in non preview mode.
     * Should be overridden by Sub-classes to properly reflect what enabling
     * their component means.
     */
    enable() {
        this.notifyValueChange(false);
    }
    // TODO: @owl-options: rename this to findUserValue
    /**
     * @param {string} name
     * @returns {UserValueWidget|null}
     */
    findWidget(name) {
        for (const widget of Object.values(this._subValues)) {
            if (widget.getName() === name) {
                return widget;
            }
            const depWidget = widget.findWidget(name);
            if (depWidget) {
                return depWidget;
            }
        }
        return null;
    }
    /**
     * Focus the main focusable element of the widget.
     */
    focus() {
        const el = this._getFocusableElement();
        if (el) {
            el.focus();
        }
    }
    /**
     * Returns the value that the widget would hold if it was active, by default
     * the internal value it holds.
     *
     * @param {string} [methodName]
     * @returns {string}
     */
    getActiveValue(methodName) {
        return this.value;
    }
    /**
     * Returns the default value the widget holds when inactive, by default the
     * first "possible value".
     *
     * @param {string} [methodName]
     * @returns {string}
     */
    getDefaultValue(methodName) {
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        return possibleValues && possibleValues[0] || '';
    }
    /**
     * @returns {string[]}
     */
    getDependencies() {
        return this._dependencies;
    }
    /**
     * Returns the names of the option methods associated to the widget. Those
     * are loaded with @see loadMethodsData.
     *
     * @returns {string[]}
     */
    getMethodsNames() {
        return [...this._methodsNames.values()];
    }
    /**
     * Returns the option parameters associated to the widget (for a given
     * method name or not). Most are loaded with @see loadMethodsData.
     *
     * @param {string} [methodName]
     * @returns {Object}
     */
    getMethodsParams(methodName) {
        const params = Object.assign({}, this._methodsParams);
        if (methodName) {
            params.possibleValues = params.optionsPossibleValues[methodName] || [];
            params.activeValue = this.getActiveValue(methodName);
            params.defaultValue = this.getDefaultValue(methodName);
        }
        return params;
    }
    /**
     * @returns {string} empty string if no name is used by the widget
     */
    getName() {
        return this._methodsParams.name || '';
    }
    /**
     * Returns the user value that the widget currently holds. The value is a
     * string, this is the value that will be received in the option methods
     * of SnippetOptionWidget instances.
     *
     * @param {string} [methodName]
     * @returns {string}
     */
    getValue(methodName) {
        const isActive = this.isActive();
        if (!methodName || !this._methodsNames.has(methodName)) {
            return isActive ? 'true' : '';
        }
        if (isActive) {
            return this.getActiveValue(methodName);
        }
        return this.getDefaultValue(methodName);
    }
    /**
     * Returns whether or not the widget is active (holds a value).
     *
     * @returns {boolean}
     */
    isActive() {
        return this.value && this.value !== NULL_ID;
    }
    /**
     * Indicates if the widget can contain sub user value widgets or not.
     *
     * @returns {boolean}
     */
    isContainer() {
        return false;
    }
    /**
     * Indicates if the widget is being previewed or not: the user is
     * manipulating it. Base case: if an internal <input/> element is focused.
     *
     * @returns {boolean}
     */
    isPreviewed() {
        // const focusEl = document.activeElement;
        // TODO: @owl-options: implement this on input values
        // if (focusEl && focusEl.tagName === 'INPUT'
        //         && (this.el === focusEl || this.el.contains(focusEl))) {
        //     return true;
        // }
        return this._state.preview;
    }
    /**
     * Loads option method names and option method parameters.
     *
     * @param {string[]} validMethodNames
     * @param {Object} extraParams
     */
    loadMethodsData(validMethodNames, extraParams) {
        this._validMethodNames = validMethodNames;
        this._methodsNames = new Set();
        this._methodsParams = Object.assign({}, extraParams);
        this._methodsParams.optionsPossibleValues = {};
        this._dependencies = [];
        this._triggerWidgetsNames = [];
        this._triggerWidgetsValues = [];

        for (const key in this._data) {
            // Ignore values set to false or undefined but not empty strings.
            if (this._data[key] === false || this._data[key] === undefined) {
                continue;
            }

            const dataValue = this._data[key].trim();

            if (key === 'dependencies') {
                this._dependencies.push(...dataValue.split(/\s*,\s*/g));
            } else if (key === 'trigger') {
                this._triggerWidgetsNames.push(...dataValue.split(/\s*,\s*/g));
            } else if (key === 'triggerValue') {
                this._triggerWidgetsValues.push(...dataValue.split(/\s*,\s*/g));
            } else if (validMethodNames.includes(key)) {
                this._methodsNames.add(key);
                this._methodsParams.optionsPossibleValues[key] = dataValue.split(/\s*\|\s*/g);
            } else {
                this._methodsParams[key] = dataValue;
            }
        }

        // TODO: @owl-options Sort the method names or fix this.
        // Method names come from the widget's dataset whose keys' order cannot
        // be relied on. We explicitely sort them by alphabetical order allowing
        // consistent behavior, while relying on order for such methods should
        // not be done when possible (the methods should be independent from
        // each other when possible).
        //this._methodsNames.sort();
    }
    /**
     * @param {boolean} [previewMode=false]
     * @param {boolean} [isSimulatedEvent=false]
     */
    notifyValueChange(previewMode, isSimulatedEvent) {
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
        // @owl-options: Could we change this?
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
            data.prepare = () => this._state.preview = true;
        } else if (previewMode === 'reset') {
            data.prepare = () => this._state.preview = false;
        }

        this.userValueNotification(data);
    }
    /**
     * Opens the widget (only meaningful for widgets that can be opened).
     */
    open() {
        this.env.userValueWidgetOpening();
        this._state.opened = true;
    }
    /**
     * Adds the given userValue to the list of sub values (useful for container
     * components).
     *
     * @param {UserValue} userValue
     */
    registerUserValue(userValue) {
        this._subValues[userValue.id] = (userValue);
        const inheritedParams = Object.assign({}, this._methodsParams);
        inheritedParams.optionsPossibleValues = null;
        userValue.loadMethodsData(this._validMethodNames, inheritedParams);
        const subMethodsNames = userValue.getMethodsNames();
        const subMethodsParams = userValue.getMethodsParams();

        for (const methodName of subMethodsNames) {
            if (!this._methodsNames.has(methodName)) {
                this._methodsNames.add(methodName);
                this._methodsParams.optionsPossibleValues[methodName] = [];
            }
            for (const subPossibleValue of subMethodsParams.optionsPossibleValues[methodName]) {
                if (!this._methodsParams.optionsPossibleValues[methodName].includes(subPossibleValue)) {
                    this._methodsParams.optionsPossibleValues[methodName].push(subPossibleValue);
                }
            }
        }
    }
    /**
     * Removes the given userValue from the list of sub values.
     *
     * @param {UserValue} userValue
     */
    unregisterUserValue(userValue) {
        delete this._subValues[userValue.id];
    }
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
        this._state.preview = false;
        this.value = value;
    }
    /**
     * @param {boolean} show
     */
    toggleVisibility(show) {
        this._state.show = show;
        // let doFocus = false;
        // if (show) {
        //     const wasInvisible = this.el.classList.contains('d-none');
        //     doFocus = wasInvisible && this.el.dataset.requestFocus === "true";
        // }
        // this.el.classList.toggle('d-none', !show);
        // if (doFocus) {
        //     this.focus();
        // }
    }

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
    _getFocusableElement() {
        return null;
    }
    /**
     * Allows container widgets to add additional data if needed.
     *
     * @private
     * @param {Object} params
     */
    userValueNotification(params) {
        params.widget = this;

        if (!params.triggerWidgetsNames) {
            params.triggerWidgetsNames = [];
        }
        params.triggerWidgetsNames.push(...this._triggerWidgetsNames);

        if (!params.triggerWidgetsValues) {
            params.triggerWidgetsValues = [];
        }
        params.triggerWidgetsValues.push(...this._triggerWidgetsValues);
        this.env.userValueNotification(params);
    }
}

export class UserValueComponent extends Component {

    static props = {
        name: { type: String, optional: true },
        slots: { type: Object, optional: true },
        // Allow any prop as they will reference a method of SnippetOption
        "*": {},
    };

    static StateModel = UserValue;

    // This is an abstract component, it should not be used alone.
    static template = "";

    setup() {
        const id = uniqueId("userValue");
        const state = useState({});
        const stateParams = this.getStateParams();
        this.state = new this.constructor.StateModel(
            id,
            state,
            this.env,
            this.env.snippetOption,
            stateParams
        );
        if (this.props.multiSequence) {
            this.state.multiSequence = this.props.multiSequence;
        }

        this.env.registerUserValue(this.state);

        if (this.constructor.isContainer) {
            // If this component contains other UserValueComponents, they should
            // not register to the options, but to this Component's state instead, so
            // that this one's UserValue can handle their state, as they are
            // heavily dependent on the parent's state.
            useChildSubEnv({
                registerUserValue: (userValue) => {
                    this.state.registerUserValue(userValue);
                    if (this.env.isContained) {
                        this.env.registerUserValue(userValue);
                    }
                },
                unregisterUserValue: (userValue) => {
                    this.state.unregisterUserValue(userValue);
                },
                userValueNotification: (params) => {
                    this.state.userValueNotification(params);
                },
                isContained: true,
            });
        }

        onWillStart(async () => {
            if (this.props.img) {
                const src = this.props.img;
                if (src.split(".").pop() === "svg") {
                    this.svg = await buildSvgElement(src);
                } else {
                    this.img = this.props.img;
                }
            }
        });
        // Track the changes to the textContent slot so that parent widgets can
        // use it (e.g. WeSelect use the active value's textContent for its
        // toggler).
        this.textContentRef = useRef("text-content");
        useEffect(
            () => {
                const textContent = this.textContentRef.el?.textContent || "";
                if (textContent && textContent !== this.state.textContent) {
                    this.state.textContent = textContent;
                } else if (!textContent) {
                    const fakeImgEl = this.textContentRef.el?.querySelector('.o_we_fake_img_item');
                    if (fakeImgEl) {
                        this.state.fakeImg = markup(fakeImgEl.outerHTML);
                    }
                }
            },
            () => [this.textContentRef.el]
        );

        onWillDestroy(() => {
            this.env.unregisterUserValue(this.state);
        });
    }
    /**
     * Returns an object containing the classes defined in the props
     *
     * @returns {Object}
     */
    getPropsClass() {
        if (typeof this.props.class === "string") {
            return { [this.props.class]: true };
        }
        if (Array.isArray(this.props.class)) {
            const classes = this.props.class.join(" ");
            return { [classes]: this.props.class.length > 0 };
        }
        if (typeof this.props.class === "object") {
            return this.props.class;
        }
	}
    /**
     * Returns all the classes that should be applied on the root of the widget.
     *
     * @returns {Object}
     */
    getAllClasses() {
        return {
            "active": this.state.active,
            "o_we_preview": this.state.isPreviewed(),
            "d-none": !this.state.show,
            "o_we_widget_opened": this.state.opened,
            "o_we_icon_button": this.img || this.svg || this.props.icon,
            ...this.getPropsClass(),
        };
    }
    /**
     * Sets all props as data attributes to match with existing tours.
     * @TODO this should be removed or only shown when tours are actually 
     * activated. However, some SCSS styles are using attributes to style some
     * buttons (e.g. BackgroundShape).
     */
    getAllDataAttributes() {
        const dataAttributes = {};
        for (const key of Object.getOwnPropertyNames(this.state._data)) {
            const kebabName = key.replace(/([a-z])([A-Z])/g, "$1-$2").toLowerCase();
            dataAttributes[`data-${kebabName}`] = this.props[key];
        }
        return dataAttributes;
    }
    /**
     * Prepare the values that will be passed as parameters to the state.
     * 
     * @private
     * @return {Objectl}
     */
    getStateParams() {
        const propsCopy = { ...this.props };
        delete propsCopy.slots;
        delete propsCopy.multiSequence;
        return propsCopy;
    }
    /**
     * @private
     * @param {OdooEvent|Event}
     * @returns {boolean}
     */
    _handleNotifierEvent(ev) {
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
    }

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
    _onUserValueChange(ev) {
        if (this._handleNotifierEvent(ev)) {
            this.state.notifyValueChange(false);
        }
    }
    /**
     * Should be called when an user event on the widget indicates a value
     * preview.
     *
     * @private
     * @param {OdooEvent|Event} [ev]
     */
    _onUserValuePreview(ev) {
        if (this._handleNotifierEvent(ev)) {
            this.state.notifyValueChange(true);
        }
    }
    /**
     * Should be called when an user event on the widget indicates a value
     * reset.
     *
     * @private
     * @param {OdooEvent|Event} [ev]
     */
    _onUserValueReset(ev) {
        if (this._handleNotifierEvent(ev)) {
            this.state.notifyValueChange('reset');
        }
    }
}


class ButtonUserValue extends UserValue {
    /**
     * @override
     */
    async setValue(value, methodName) {
        await super.setValue(...arguments);
        let active = !!value;
        if (methodName) {
            if (!this._methodsNames.has(methodName)) {
                return;
            }
            active = (this.getActiveValue(methodName) === value);
        }
        this._state.active = active;
        // TODO: @owl-options: Some of this code is no longer used, it should
        // probably be removed in its own commit.
        // if (this.illustrationEl && this.activeImgEl) {
        //     this.illustrationEl.classList.toggle('d-none', active);
        //     this.activeImgEl.classList.toggle('d-none', !active);
        // }
        // this.el.classList.toggle('active', active);
    }

    get active() {
        return this._state.active;
    }
    /**
     * @override
     */
    getActiveValue(methodName) {
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        return possibleValues && possibleValues[possibleValues.length - 1] || '';
    }
    /**
     * @override
     */
    isActive() {
        return (this.isPreviewed() !== this._state.active);
    }
    /**
     * @override
     */
    loadMethodsData(validMethodNames) {
        super.loadMethodsData(...arguments);
        for (const methodName of this._methodsNames.values()) {
            const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
            if (possibleValues.length <= 1) {
                possibleValues.unshift('');
            }
        }
    }
}

export class WeButton extends UserValueComponent {
    static template = "web_editor.WeButton";
    static StateModel = ButtonUserValue;
    setup() {
        super.setup();
    }
    /**
     * @override
     */
    async willStart() {
        await this._super(...arguments);
        if (this.options.dataAttributes.activeImg) {
            // TODO: @owl-options: this is no longer used.
            this.activeImgEl = await _buildImgElement(this.options.dataAttributes.activeImg);
        }
    }
    /**
     * @override
     */
    _makeDescriptive() {
        const $el = this._super(...arguments);
        if (this.illustrationEl) {
            $el[0].classList.add('o_we_icon_button');
        }
        if (this.activeImgEl) {
            this.containerEl.appendChild(this.activeImgEl);
        }
        return $el;
    }
    /**
     * @override
     */
    start(parent, title, options) {
        if (this.options && this.options.childNodes) {
            this.options.childNodes.forEach(node => this.containerEl.appendChild(node));
        }

        return this._super(...arguments);
    }
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onButtonClick(ev) {
        if (!ev._innerButtonClicked) {
            this._onUserValueChange(ev);
        }
    }
    /**
     * @private
     */
    _onInnerButtonClick(ev) {
        // Cannot just stop propagation as the click needs to be propagated to
        // potential parent widgets for event delegation on those inner buttons.
        ev._innerButtonClicked = true;
    }
}
registry.category("snippet_widgets").add("WeButton", WeButton);

const ButtonUserValueWidget = Widget.extend({className: ''});
const CheckboxUserValueWidget = ButtonUserValueWidget.extend({});

class WeCheckbox extends WeButton {
    static template = "web_editor.WeCheckbox";
    static components = { WeTitle };

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    enable() {
        // TODO: @owl-options adapt
        this.$('we-checkbox').click();
    }

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
        return super._onButtonClick(...arguments);
    }
}
registry.category("snippet_widgets").add("WeCheckbox", WeCheckbox);

const BaseSelectionUserValueWidget = UserValueWidget.extend({});
class BaseSelectionUserValue extends UserValue {
    /**
     * @override
     */
    async start() {
        await super.start(...arguments);

        // this.menuEl = document.createElement('we-selection-items');
        // if (this.options && this.options.childNodes) {
        //     this.options.childNodes.forEach(node => {
        //         // Ensure to only put element nodes inside the selection menu
        //         // as there could be an :empty CSS rule to handle the case when
        //         // the menu is empty (so it should not contain any whitespace).
        //         if (node.nodeType === Node.ELEMENT_NODE) {
        //             this.menuEl.appendChild(node);
        //         }
        //     });
        // }
        // this.containerEl.appendChild(this.menuEl);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams(methodName) {
        const params = super.getMethodsParams(...arguments);
        const activeWidget = this._getActiveSubWidget();
        if (!activeWidget) {
            return params;
        }
        return Object.assign(activeWidget.getMethodsParams(...arguments), params);
    }
    /**
     * @override
     */
    getValue(methodName) {
        const activeWidget = this._getActiveSubWidget();
        if (activeWidget) {
            return activeWidget.getActiveValue(methodName);
        }
        return super.getValue(...arguments);
    }
    /**
     * @override
     */
    isContainer() {
        return true;
    }
    /**
     * @override
     */
    async setValue(value, methodName) {
        const subValues = Object.values(this._subValues);
        for (const widget of subValues) {
            await widget.setValue(NULL_ID, methodName);
        }
        for (const widget of subValues.reverse()) {
            await widget.setValue(value, methodName);
            if (widget.isActive()) {
                // Only one select item can be true at a time, we consider the
                // last one if multiple would be active.
                break;
            }
        }
        await super.setValue(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns {UserValue|undefined}
     */
    _getActiveSubWidget() {
        const previewedWidget = Object.values(this._subValues).find(value => value.isPreviewed());
        if (previewedWidget) {
            return previewedWidget;
        }
        return Object.values(this._subValues).find(value => value.isActive());
    }
}
export class SelectUserValue extends BaseSelectionUserValue {

    static PLACEHOLDER_TEXT = _t("None");

    constructor() {
        super(...arguments);
        this._state.toggler = {
            faIcon: false,
            imgSrc: false,
            textContent: this.constructor.PLACEHOLDER_TEXT,
        };
    }
    /**
     * Informations about the toggler element, to be used in the template.
     *
     * @type {Object}
     */
    get toggler() {
        return this._state.toggler;
    }
    /**
     * @override
     */
    async setValue(value, methodName) {
        await super.setValue(...arguments);
        // Re-initialising the toggler.
        const newToggler = {
            textContent: "",
            faIcon: false,
            imgSrc: false,
        };
        const activeWidget = Object.values(this._subValues).find(value => !value.isPreviewed() && value.isActive());
        if (activeWidget) {
            const params = activeWidget.getMethodsParams(methodName);
            // Check the param for svg on buttons
            const svgSrc = params.svgSrc; // useful to avoid searching text content in svg element
            const text = (params.selectLabel || (!svgSrc && activeWidget.textContent.trim()));
            const imgSrc = params.img;
            const icon = params.icon;
            if (text) {
                newToggler.textContent = text;
            } else if (icon) {
                newToggler.faIcon = icon;
            } else if (imgSrc) {
                newToggler.imgSrc = imgSrc;
            } else {
                // TODO: @owl-options: check this? See the "border-style" option
                // that appears when you add a border for an example. e.g.: on
                // Images Wall.
                if (activeWidget.fakeImg) {
                   newToggler.textContent = activeWidget.fakeImg;
                }
            }
        } else {
            newToggler.textContent = this.constructor.PLACEHOLDER_TEXT;
        }

        this._state.toggler = newToggler;
    }
    /**
     * @override
     */
    isPreviewed() {
        return super.isPreviewed() || this.opened;
    }
    /**
     * @override
     */
    enable() {
        if (!this.opened) {
            this.open();
        }
    }
}
const SelectUserValueWidget = BaseSelectionUserValueWidget.extend({});
export class WeSelect extends UserValueComponent {
    static isContainer = true;
    static template = "web_editor.WeSelect";
    static components = { Dropdown, WeTitle };
    static StateModel = SelectUserValue;
    static props = {
        ...UserValueComponent.props,
        title: { type: String, optional: true },
    }

    setup() {
        // Use this ref to adjust the dropdown's position upwards if not enough
        // space downwards.
        this.menuRef = useRef("menu");

        useEffect(
            (opened) => {
                if (opened) {
                    this._adjustDropdownPosition();
                }
                return () => {
                    const containerEl = this.menuRef.el?.closest(".o_we_user_value_widget");
                    containerEl.classList.remove("o_we_select_dropdown_up");
                };
            },
            () => [this.state.opened]
        );

        super.setup();
    }
    /**
     * @override
     */
    getStateParams() {
        const propsCopy = super.getStateParams();
        delete propsCopy.title;
        return propsCopy;
    }

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        if (this.options && this.options.valueEl) {
            this.containerEl.insertBefore(this.options.valueEl, this.menuEl);
        }

        this.menuEl.dataset.placeholderText = this.PLACEHOLDER_TEXT;

        this.menuTogglerEl = document.createElement('we-toggler');
        this.menuTogglerEl.dataset.placeholderText = this.PLACEHOLDER_TEXT;
        this.iconEl = this.illustrationEl || null;
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
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _shouldIgnoreClick(ev) {
        return !!ev.target.closest('[role="button"]');
    }
    /**
     * Decides whether the dropdown should be positioned below or above the
     * selector based on the available space.
     *
     * @private
     */
    _adjustDropdownPosition() {
        if (!this.state.opened) {
            return;
        }
        const customizePanelEl = this.menuRef.el?.closest(".o_we_customize_panel");
        if (!customizePanelEl) {
            return;
        }

        const containerEl = this.menuRef.el.closest(".o_we_user_value_widget");
        if (!containerEl) {
            return;
        }

        containerEl.classList.remove("o_we_select_dropdown_up");
        const customizePanelElCoords = customizePanelEl.getBoundingClientRect();
        let dropdownMenuElCoords = this.menuRef.el.getBoundingClientRect();

        // Adds a margin to prevent the dropdown from sticking to the edge of
        // the customize panel.
        const dropdownMenuMargin = 5;
        // If after opening, the dropdown list overflows the customization
        // panel at the bottom, opens the dropdown above the selector.
        if ((dropdownMenuElCoords.bottom + dropdownMenuMargin) > customizePanelElCoords.bottom) {
            containerEl.classList.add("o_we_select_dropdown_up");
            dropdownMenuElCoords = this.menuRef.el.getBoundingClientRect();
            // If there is no available space above it either, then we open
            // it below the selector.
            if (dropdownMenuElCoords.top < customizePanelElCoords.top) {
                containerEl.classList.remove("o_we_select_dropdown_up");
            }
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the select is clicked anywhere -> open/close it.
     *
     * @private
     */
    _onClick(ev) {
        if (this._shouldIgnoreClick(ev)) {
            return;
        }

        if (!this.state.opened) {
            this.state.open();
        } else {
            this.state.close();
        }
        const activeItem = this.menuRef.el?.querySelector(".active");
        if (activeItem) {
            this.menuRef.el.scrollTop = activeItem.offsetTop - (this.menuRef.el.offsetHeight / 2);
        }
    }
}
registry.category("snippet_widgets").add("WeSelect", WeSelect);

class WeButtonGroup extends UserValueComponent {
    static template = "web_editor.WeButtonGroup";
    static isContainer = true;
    static components = { WeTitle };
    static StateModel = BaseSelectionUserValue;
}

registry.category("snippet_widgets").add("WeButtonGroup", WeButtonGroup);

const ButtonGroupUserValueWidget = BaseSelectionUserValueWidget.extend({
    tagName: 'we-button-group',
});

const UnitUserValueWidget = UserValueWidget.extend({});
class UnitUserValue extends UserValue {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getActiveValue(methodName) {
        const activeValue = this._nextValue || super.getActiveValue(...arguments) || "";

        const params = this._methodsParams;
        if (!this._isNumeric()) {
            return activeValue;
        }
        // TODO find correct way to apply this
        if (params.saveUnit === undefined) {
            params.saveUnit = params.unit;
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
    }
    /**
     * @override
     * @param {boolean} [useInputUnit=false]
     */
    getDefaultValue(methodName, useInputUnit) {
        const defaultValue = super.getDefaultValue(...arguments);

        const params = this._methodsParams;
        if (!this._isNumeric()) {
            return defaultValue;
        }

        const unit = useInputUnit ? params.unit : params.saveUnit;
        const numValue = weUtils.convertValueToUnit(defaultValue || '0', unit, params.cssProperty, this.$target);
        if (isNaN(numValue)) {
            return defaultValue;
        }
        return `${this._floatToStr(numValue)}${unit}`;
    }
    /**
     * @override
     */
    isActive() {
        const isSuperActive = super.isActive(...arguments);
        if (!this._isNumeric()) {
            return isSuperActive;
        }
        return isSuperActive && (
            this._floatToStr(parseFloat(this.value)) !== '0'
            // Or is a composite value.
            || !!this.value.match(/\d+\s+\d+/)
        );
    }
    /**
     * @override
     */
    loadMethodsData() {
        super.loadMethodsData(...arguments);
        const params = this._methodsParams;
        const unit = params.unit || '';
        if (params.saveUnit === undefined) {
            params.saveUnit = unit;
        }
    }
    /**
     * @override
     */
    async setValue(value, methodName) {
        const params = this._methodsParams;
        if (this._isNumeric()) {
            value = value.split(' ').map(v => {
                const numValue = weUtils.convertValueToUnit(v, params.unit, params.cssProperty, this.$target);
                if (isNaN(numValue)) {
                    return ''; // Something not supported
                }
                return this._floatToStr(numValue);
            }).join(' ');
        }
        return super.setValue(value, methodName);
    }

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
    _floatToStr(value) {
        return `${parseFloat(value.toFixed(5))}`;
    }
    /**
     * Checks whether the widget contains a numeric value.
     *
     * @private
     * @returns {Boolean} true if the value is numeric, false otherwise.
     */
    _isNumeric() {
        const params = this._methodsParams;
        return !!params.unit;
    }
}

const InputUserValueWidget = UnitUserValueWidget.extend({});
class InputUserValue extends UnitUserValue {
    /**
     * @override
     */
    async setValue() {
        await super.setValue(...arguments);
        this._oldValue = this.value;
    }
    /**
     * @override
     */
    _isNumeric() {
        const isNumeric = super._isNumeric(...arguments);
        const params = this._methodsParams;
        return isNumeric || !!params.fakeUnit || !!params.step;
    }
}
export class WeInput extends UserValueComponent {
    static template = 'web_editor.WeInput';
    static props = { ...UserValueComponent.props,
        unit: { type: String, optional: true },
        step: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        // withUnit: { type: String, optional: true }, // ? boolean ?
        fakeUnit: { type: String, optional: true }, // ? boolean ?
        hideUnit: { type: String, optional: true }, // ? boolean ?
        extraClass: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        unit: "",
    };
    static components = { WeTitle };
    static StateModel = InputUserValue;

    setup() {
        super.setup();
        this.inputRef = useRef("input");
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    getAllClasses() {
        return {
            ...super.getAllClasses(),
            "o_we_large": (
                !this.props.unit && !this.props.fakeUnit
            ) || this.props.hideUnit,
        };
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getFocusableElement() {
        return this.inputRef.el;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onInputInput(ev) {
        // First record the input value as the new current value and bound it if
        // necessary (min / max params).
        this.state.value = this.inputRef.el?.value;

        const params = this.props;
        const hasMin = ('min' in params);
        const hasMax = ('max' in params);
        if (hasMin || hasMax) {
            // Bounding the value in [min, max] if specified.
            const boundedValue = this.state.value.split(/\s+/g).map(v => {
                let numValue = parseFloat(v);
                if (isNaN(numValue)) {
                    return hasMin ? params.min : v;
                } else {
                    numValue = hasMin ? Math.max(params.min, numValue) : numValue;
                    numValue = hasMax ? Math.min(numValue, params.max) : numValue;
                    return numValue;
                }
            }).join(" ");

            // If the bounded version is different from the value, forget about
            // the old value so that we properly update the UI in any case.
            this.state._oldValue = undefined;

            // Note: we do not change the input's value because we want the user
            // to be able to enter anything without it being auto-fixed. For
            // example, just emptying the input to enter new numbers: you don't
            // want the min value to pop up unexpectedly. The next UI update
            // will take care of showing the user that the value was bound.
            this.state.value = boundedValue;
        }

        // When the value changes as a result of a arrow up/down, the change
        // event is not called, unless a real user input has been triggered.
        // This event handler holds a variable for this in order to not call
        // `_onUserValueChange` two times. If the users only uses arrow up/down
        // it will be trigger on blur otherwise it will be triggered on change.
        if (!ev.detail || !ev.detail.keyUpOrDown) {
            this.changeEventWillBeTriggered = true;
        }
        this._onUserValuePreview(ev);
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onInputBlur(ev) {
        if (this.notifyValueChangeOnBlur && !this.changeEventWillBeTriggered) {
            // In case the input value has been modified with arrow up/down, the
            // change event is not triggered (except if there has been a natural
            // input event), so if the element doesn't trigger a preview, we
            // have to notify that the value changes now.
            this._onUserValueChange(ev);
            this.notifyValueChangeOnBlur = false;
        }
        this.changeEventWillBeTriggered = false;
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onInputKeydown(ev) {
        const params = this.props;
        if (!this.state._isNumeric()) {
            return;
        }
        switch (ev.key) {
            case "Enter":
                this._onUserValueChange(ev);
                break;
            case "ArrowUp":
            case "ArrowDown": {
                ev.preventDefault(); // Do not let it be handled as an hotkey.
                const input = ev.currentTarget;
                let parts = (input.value || input.placeholder).match(/-?\d+\.\d+|-?\d+/g);
                if (!parts) {
                    parts = [input.value || input.placeholder];
                }
                if (parts.length > 1 && !('min' in params)) {
                    // No negative for composite values.
                    params['min'] = 0;
                }
                const newValue = parts.map(part => {
                    let value = parseFloat(part);
                    if (isNaN(value)) {
                        value = 0.0;
                    }
                    let step = parseFloat(params.step);
                    if (isNaN(step)) {
                        step = 1.0;
                    }

                    const increasing = ev.key === "ArrowUp";
                    const hasMin = ('min' in params);
                    const hasMax = ('max' in params);

                    // If value already at min and trying to decrease, do nothing
                    if (!increasing && hasMin && Math.abs(value - params.min) < 0.001) {
                        return value;
                    }
                    // If value already at max and trying to increase, do nothing
                    if (increasing && hasMax && Math.abs(value - params.max) < 0.001) {
                        return value;
                    }

                    // If trying to decrease/increase near min/max, we still need to
                    // bound the produced value and immediately show the user.
                    value += (increasing ? step : -step);
                    value = hasMin ? Math.max(params.min, value) : value;
                    value = hasMax ? Math.min(value, params.max) : value;
                    return this.state._floatToStr(value);
                }).join(" ");
                if (newValue === (input.value || input.placeholder)) {
                    return;
                }
                input.value = newValue;

                // We need to know if the change event will be triggered or not.
                // Change is triggered if there has been a "natural" input event
                // from the user. Since we are triggering a "fake" input event,
                // we specify that the original event is a key up/down.
                input.dispatchEvent(new CustomEvent('input', {
                    bubbles: true,
                    cancelable: true,
                    detail: {keyUpOrDown: true}
                }));
                this.notifyValueChangeOnBlur = true;
                break;
            }
        }
    }
    /**
     * @override
     */
    _onUserValueChange() {
        if (this.state._oldValue !== this.state.value) {
            super._onUserValueChange(...arguments);
        }
    }
}
registry.category("snippet_widgets").add("WeInput", WeInput);

class MultiUserValue extends UserValue {

    get sortedValues() {
        if (!this._sortedValues) {
            this._sortedValues = Object.values(this._subValues);
            this._sortedValues.sort((a, b) => {
                return a.multiSequence - b.multiSequence;
            });
        }
        return this._sortedValues;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getValue(methodName) {
        const value = this.sortedValues.map(subValue => {
            return subValue.getValue(methodName);
        }).join(' ').trim();

        return value || super.getValue(...arguments);
    }
    /**
     * @override
     */
    async setValue(value, methodName) {
        // TODO: @owl-options avoid null
        value ||= "";
        let values = value.split(/\s*\|\s*/g);
        if (values.length === 1) {
            values = value.split(/\s+/g);
        }
        for (let i = 0; i < this.sortedValues.length - 1; i++) {
            await this.sortedValues[i].setValue(values.shift() || '', methodName);
        }
        await this.sortedValues[this.sortedValues.length - 1].setValue(values.join(' '), methodName);
    }
}

const MultiUserValueWidget = UserValueWidget.extend({});
class WeMulti extends UserValueComponent {
    static template = "web_editor.WeMulti";
    static isContainer = true;
    static StateModel = MultiUserValue;
    static components = { WeTitle };
}
registry.category("snippet_widgets").add("WeMulti", WeMulti);

export class ColorpickerUserValue extends SelectUserValue {
    /** 
     * The Color Combination value, which is a string ranging from 1 to 5
     *
     * @type {string}
     */
    get ccValue() {
        return this._state.ccValue;
    }
    set ccValue(value) {
        this._state.ccValue = value;
    }
    /**
     * A custom color value, selected through the color picker of the color
     * palette
     *
     * @type {string}
     */
    get customColorValue() {
        return this._state.cutomColorValue;
    }
    set customColorValue(value) {
        this._state.customColorValue = value;
    }
    /**
     * @override
     */
    getMethodsParams() {
        return Object.assign(super.getMethodsParams(...arguments), {
            colorNames: this.colorPaletteColorNames,
        });
    }
    /**
     * @override
     */
    getValue(methodName) {
        const isCCMethod = (this._methodsParams.withCombinations === methodName);
        let value = super.getValue(...arguments);
        if (isCCMethod) {
            value = this.ccValue;
        } else if (typeof this.customColorValue === 'string') {
            value = this.customColorValue;
        }

        // TODO strange there is some processing below for the normal value but
        // not for the preview value? To check in older stable versions as well.
        if (typeof this.previewColor === 'string') {
            return isCCMethod ? this.previewCC : this.previewColor;
        }

        if (value) {
            // TODO probably something to be done to handle gradients properly
            // in this code.
            const useCssColor = this._data.useCssColor;
            const cssCompatible = this._data.cssCompatible;
            if ((useCssColor || cssCompatible) && !isCSSColor(value)) {
                if (useCssColor) {
                    value = weUtils.getCSSVariableValue(value);
                } else {
                    value = `var(--${value})`;
                }
            }
        }
        return value;
    }
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
        await super.setValue(isCCMethod ? this.value : color, methodName, ...rest);
        if (isCCMethod) {
            this.ccValue = color;
        }
    }
    /**
     * @override
     */
    isActive() {
        return !!this.ccValue
            || !weUtils.areCssValuesEqual(this.value, 'rgba(0, 0, 0, 0)');
    }
    /**
     * @override
     */
    close() {
        super.close();
        if (this._state.customColorValue && this._state.customColorValue !== this._state.value) {
            this._state.value = this._state.customColorValue;
            this._state.customColorValue = false;
            this.notifyValueChange(false);
        }
    }
}

export class WeColorpicker extends WeSelect {
    static StateModel = ColorpickerUserValue;
    static template = "web_editor.WeColorpicker";
    static components = { ...WeSelect.components, ColorPalette };
    static isContainer = false;

    setup() {
        super.setup();
        this.getColorPickerTemplateService = useService("get_color_picker_template");
        onWillStart(async () => {
            // TODO: find a better way to do this.
            // The colorpicker widget is started before the ColorPalette component
            // is attached to the DOM (which only happens once the user opens the
            // picker). However, the colorNames are only set after the ColorPalette
            // has been mounted. Initializing the colorNames through a direct call
            // to the `getColorPickerTemplateService` so that the widget starts
            // with possible default values is thus necessary to avoid bugs on
            // `_computeWidgetState()`.
            const colorpickerTemplate = await this.getColorPickerTemplateService();
            this.state.colorPaletteColorNames = this._getColorNames(colorpickerTemplate);
        });
        this.colorPaletteColorNames = [];
        // Colorpalette Props.
        this.resetTabCount = 0;
        const options = {
            getCustomColors: () => {
                let result = [];
                if (this.env.getCustomColors) {
                    result = this.env.getCustomColors();
                }
                return result;
            },
            onCustomColorPicked: this._onCustomColorPicked.bind(this),
            onColorPicked: this._onColorPicked.bind(this),
            onColorHover: this._onColorHovered.bind(this),
            onColorLeave: this._onColorLeft.bind(this),
            onInputEnter: this._onEnterKey.bind(this),
        };
        if (this.props.excluded) {
            options.excluded = this.props.excluded.replace(/ /g, '').split(',');
        }
        if (this.props.opacity) {
            options.opacity = parseFloat(this.props.opacity);
        }
        if (this.props.withCombinations) {
            options.withCombinations = !!this.props.withCombinations;
        }
        if (this.props.withGradients) {
            options.withGradients = !!this.props.withGradients;
        }
        if (this.props.noTransparency) {
            options.noTransparency = !!this.props.noTransparency;
            options.excluded = [...(options.excluded || []), 'transparent_grayscale'];
        }
        if (this.props.selectedTab) {
            options.selectedTab = this.props.selectedTab;
        }
        options.getTemplate = this.getColorPickerTemplateService;
        this.options = options;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @override
     */
    isContainer() {
        return false;
    }
    /**
     * @override
     */
    isActive() {
        return !!this._ccValue
            || !weUtils.areCssValuesEqual(this._value, 'rgba(0, 0, 0, 0)');
    }
    getPreviewAttributes() {
        const classes = weUtils.computeColorClasses(this.colorPaletteColorNames);
        // this.colorPreviewEl.classList.remove(...classes);
        // this.colorPreviewEl.style.removeProperty('background-color');
        // this.colorPreviewEl.style.removeProperty('background-image');
        const prefix = this.props.colorPrefix || 'bg';
        const style = {
            "background-color": "",
            "background-image": "",
        };
        const attributes = {
            class: "",
            style: "",
        };
        if (this.state.ccValue) {
            style["background-color"] = `var(--we-cp-o-cc${this.state.ccValue}-${prefix.replace(/-/, '')})`;
            style["background-image"] = `var(--we-cp-o-cc${this.state.ccValue}-${prefix.replace(/-/, '')}-gradient)`;
        }
        if (this.state.value) {
            style["background-image"] = "none";
            if (isCSSColor(this.state.value)) {
                style["background-color"] = this.state.value;
            } else if (weUtils.isColorGradient(this.state.value)) {
                style["background-image"] = this.state.value;
            } else if (weUtils.EDITOR_COLOR_CSS_VARIABLES.includes(this.state.value)) {
                style["background-color"] = `var(--we-cp-${this.state.value}`;
            } else {
                // Checking if the className actually exists seems overkill but
                // it is actually needed to prevent a crash. As an example, if a
                // colorpicker widget is linked to a SnippetOption instance's
                // `selectStyle` method designed to handle the "border-color"
                // property of an element, the value received can be split if
                // the item uses different colors for its top/right/bottom/left
                // borders. For instance, you could receive "red blue" if the
                // item as red top and bottom borders and blue left and right
                // borders, in which case you would reach this `else` and try to
                // add the class "bg-red blue" which would crash because of the
                // space inside). In that case, we simply do not show any color.
                // We could choose to handle this split-value case specifically
                // but it was decided that this is enough for the moment.
                const className = `bg-${this.state.value}`;
                if (classes.includes(className)) {
                    attributes.class = className;
                }
            }
        }
        attributes.style = Object.entries(style).map(([k, v]) => `${k}: ${v}`).join("; ");
        // If the palette was already opened (e.g. modifying a gradient), the new DOM state must be
        // reflected in the palette, but the tab selection must not be impacted.
        // TODO: @owl-options this used to be part of setValue, now it isn't.
        // this.options.selectedCC = this.state.ccValue;
        // this.options.selectedColor = this.state.value;
        return attributes;
    }
    /**
     * @override
     */
    _shouldIgnoreClick(ev) {
        return ev.__isColorpickerClick || super._shouldIgnoreClick(...arguments);
    }
    /**
     * Browses the colorpicker XML template to return all possible values of
     * [data-color].
     *
     * @param {string} colorpickerTemplate
     * @returns {string[]}
     */
    _getColorNames(colorpickerTemplate) {
        // Init with the color combinations presets as these don't appear in
        // the template.
        const colorNames = ["1", "2", "3", "4", "5"];
        const template = new DOMParser().parseFromString(colorpickerTemplate, "text/html");
        template.querySelectorAll("button[data-color]:not(.o_custom_gradient_btn)").forEach(el => {
            const colorName = el.dataset.color;
            if (!weUtils.isColorGradient(colorName)) {
                colorNames.push(colorName);
            }
        });
        return colorNames;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a custom color is selected -> preview the color
     * and set the current value. Update of this value on close
     *
     * @private
     * @param {Object} params
     */
    _onCustomColorPicked(params) {
        this.state.customColorValue = params.color;
    }
    /**
     * Called when a color button is clicked -> confirms the preview.
     *
     * @private
     * @param {Object} params
     */
    _onColorPicked(params) {
        this.state.previewCC = false;
        this.state.previewColor = false;
        this.state.customColorValue = false;

        this.state.ccValue = params.ccValue;
        this.state.value = params.color;

        this._onUserValueChange();
    }
    /**
     * Called when a color button is entered -> previews the background color.
     *
     * @private
     * @param {Object} params
     */
    _onColorHovered(params) {
        this.state.previewCC = params.ccValue;
        this.state.previewColor = params.color;
        this._onUserValuePreview();
    }
    /**
     * Called when a color button is left -> cancels the preview.
     *
     * @private
     */
    _onColorLeft() {
        this.state.previewCC = false;
        this.state.previewColor = false;
        this._onUserValueReset();
    }
    /**
     * @private
     */
    _onEnterKey() {
        this.state.close();
    }
    /**
     * @override
     */
    _onClick() {
        super._onClick(...arguments);
        if (this.state.opened) {
            this.options.resetTabCount++;
        }
    }
}

registry.category("snippet_widgets").add("WeColorpicker", WeColorpicker);

const MediapickerUserValueWidget = UserValueWidget.extend({});
class MediapickerUserValue extends UserValue {
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
        el.src = this.value || "";
        // @TODO: @owl-options: review this line. Put it in the env maybe?
        const editableEl = this.option.$target[0].closest('.o_editable');
        this.env.services.dialog.add(MediaDialog, {
            noImages: !images,
            noVideos: !videos,
            noIcons: true,
            noDocuments: true,
            isForBgVideo: true,
            vimeoPreviewIds: ['528686125', '430330731', '509869821', '397142251', '763851966', '486931161',
                '499761556', '392935303', '728584384', '865314310', '511727912', '466830211'],
            'res_model': editableEl ? editableEl.dataset.oeModel : null,
            'res_id': editableEl ? editableEl.dataset.oeId : null,
            save,
            media: el,
        });
    }
    /**
     * Opens a dialog to select a new image and sets the new src
     */
    _editMedia() {
        // Need a dummy element for the media dialog to modify.
        const tagName = this._data.mediaType === "images" ? "img" : "iframe";
        const dummyEl = document.createElement(tagName);
        this._openDialog(dummyEl, {
            [this._data.mediaType]: true,
            save: (media) => {
                this.value = this._data.mediaType === "images"
                    ? media.getAttribute('src')
                    : media.querySelector(tagName).src;
                this.notifyValueChange(false);
        }});
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async setValue() {
        await super.setValue(...arguments);
        this._state.active = this.isActive();
    }
    /**
     * @override
     */
    enable() {
        this._editMedia();
    }
}

class WeMediapicker extends UserValueComponent {
    static template = "web_editor.WeMediapicker";
    static StateModel = MediapickerUserValue;
    static props = {
        ...UserValueComponent.props,
        mediaType: { type: String }, // One of "images", "videos"
        buttonStyle: { type: Boolean, optional: true },
    };
    static components = { WeTitle };

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getAllClasses() {
        return {
            ...super.getAllClasses(),
            "o_we_no_toggle o_we_bg_success": !this.props.buttonStyle,
        };
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the edit button is clicked.
     *
     * @private
     * @param {Event} ev
    */
    _onEditMedia(ev) {
        this.state._editMedia();
    }
}
registry.category("snippet_widgets").add("WeMediapicker", WeMediapicker);

const ImagepickerUserValueWidget = MediapickerUserValueWidget.extend({});
const VideopickerUserValueWidget = MediapickerUserValueWidget.extend({});

const DatetimePickerUserValueWidget = InputUserValueWidget.extend({});
class WeDatetime extends WeInput {
    static template = "web_editor.WeDatetime";
    static props = { ...WeInput.props,
        pickerType: { type: String, optional: true },
    };
    static defaultProps = {
        pickerType: "datetime",
    };
    /**
     * @override
     */
    setup() {
        super.setup();
        this.datetimePicker = useService("datetime_picker");
        onMounted(() => {
            this.picker = this.datetimePicker.create({
                target: this.inputRef.el,
                onChange: this._onDateTimePickerChange.bind(this),
                pickerProps: {
                    type: this.props.pickerType,
                    minDate: DateTime.fromObject({ year: 1000 }),
                    maxDate: DateTime.now().plus({ year: 200 }),
                    value: this.state.value,
                    rounding: 0,
                },
            });
            this.picker.enable();
        });

        useEffect(
            (value) => {
                let dateTime = null;
                if (value) {
                    dateTime = DateTime.fromSeconds(parseInt(value));
                    if (!dateTime.isValid) {
                        dateTime = DateTime.now();
                    }
                }
                this.picker.state.value = dateTime;
            },
            () => [this.state.value]
        );
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams() {
        return Object.assign(this._super(...arguments), {
            format: this.defaultFormat,
        });
    }
    /**
     * @override
     */
    isPreviewed() {
        return this._super(...arguments) || this.picker.isOpen;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onDateTimePickerChange(newDateTime) {
        if (!newDateTime || !newDateTime.isValid) {
            this.state.value = "";
        } else {
            this.state.value = newDateTime.toUnixInteger().toString();
        }
        this._onUserValuePreview();
    }
    /**
     * Handles the clear button of the datepicker.
     *
     * @private
     * @param {Event} ev
     */
    _onDateInputInput(ev) {
        if (!this.inputRef.el.value) {
            this.state.value = "";
            this._onUserValuePreview(ev);
        }
    }
}
registry.category("snippet_widgets").add("WeDatetime", WeDatetime);

const DatePickerUserValueWidget = DatetimePickerUserValueWidget.extend({});

const ListUserValueWidget = UserValueWidget.extend({});
class ListUserValue extends UserValue {
    constructor() {
        super(...arguments);
        this._state.listRecords = [];
        this._state.selected = [];

        if (this._data.availableRecords) {
            this.existingRecords = JSON.parse(this._data.availableRecords);
        } else {
            this.isCustom = this._data.notEditable !== "true";
        }
        if (this._data.defaults || this._data.hasDefault) {
            this.hasDefault = this._data.hasDefault || 'unique';
            this._state.selected = this._data.defaults ? JSON.parse(this._data.defaults) : [];
        }
    }
    /**
     * @type {Object[]}
     */
    get listRecords() {
        return this._state.listRecords;
    }
    set listRecords(value) {
        this._state.listRecords = value;
    }
    /**
     * @type {integer|string[]}
     */
    get selected() {
        return this._state.selected;
    }
    set selected(value) {
        this._state.selected = value;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getMethodsParams() {
        return Object.assign(super.getMethodsParams(...arguments), {
            records: this.existingRecords,
        });
    }
    /**
     * @override
     */
    setValue() {
        super.setValue(...arguments);
        const currentValues = this._state.value ? JSON.parse(this._state.value) : [];

        if (this.createUserValue) {
            const selectedIds = currentValues.map(({ id }) => id)
                .filter(id => typeof id === 'number');
            // Note: it's important to simplify the domain at its maximum as the
            // rpc using it are cached. Similar domain components should be
            // written the same way for the cache to work.
            this.createUserValue.options.domainComponents.selected = selectedIds.length ? ['id', 'not in', selectedIds] : null;
            this.createUserValue.setValue("");
            // Reset the search with an empty needle and the proper selected ids
            this.createUserValue._search("");
            // Reset the input value after creating a new record. The actual
            // input element's value is reset `_onClick` of the WeMany2one.
            this.createUserValue.createInputValue = "";
        }
        this.listRecords = [];
        this.selected = [];
        currentValues.forEach((value) => {
            if (typeof value === "object") {
                const record = this._updateListRecords(value);
                if (value.selected) {
                    this.selected.push(record.id);
                }
            } else {
                this.listRecords.push({ id: value, display_name: value });
                this.selected.push(value);
            }
        });
    }
    /**
     * @override
     */
    getValue(methodName) {
        if (this.createUserValue?.getMethodsNames().includes(methodName)) {
            return this.createUserValue.getValue(methodName);
        }
        return this._state.value;
    }
    /**
     * @override
     */
    registerUserValue(userValue) {
        if (userValue instanceof Many2oneUserValue && userValue._data.createUserValue) {
            this.createUserValue = userValue;
        }
        super.registerUserValue(userValue);
    }
    /**
     * @override
     */
    userValueNotification(params) {
        const { widget, previewMode, prepare } = params;
        if (widget && widget === this.createUserValue) {
            if (widget.options.createMethod && widget.getValue(widget.options.createMethod)) {
                return super.userValueNotification(...arguments);
            }
            if (previewMode) {
                return;
            }
            prepare();
            const recordData = JSON.parse(widget.getMethodsParams('addRecord').recordData);
            if (!this.listRecords.find((record) => record.id === recordData.id)) {
                this._updateListRecords(recordData);
                this._notifyCurrentState();
            }
        }
        return super.userValueNotification(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} newRecord
     */
    _updateListRecords(newRecord) {
        let id = newRecord.id;
        // Create an ID if there is none, and avoid duplicate IDs.
        if (
            !newRecord.id
            || this.listRecords.find((record) => record.id === this._toComparableId(newRecord.id))
        ) {
            id = uniqueId("list_record_");
        }
        const record = Object.assign({}, newRecord, {
            id: this._toComparableId(id),
            name: this._trimmed(newRecord.name),
            display_name: this._trimmed(newRecord.display_name) || this._data.defaultValue,
        });
        this.listRecords.push(record);
        return record;
    }
    /**
     * @param {string} str
     * @returns {string}
     */
    _trimmed(str) {
        if (typeof str !== "string") {
            return str;
        }
        return str.trim().replace(/\s+/g, " ");
    }
    /**
     * Cast ids to the right type (number or string) to compare them between
     * record / state / DOM.
     *
     * @private
     * @param {string|number} id
     * @returns {string|number}
     */
    _toComparableId(id) {
        if (typeof id === "string") {
            id = this._trimmed(id);
            return /^-?[0-9]{1,15}$/.test(id) ? parseInt(id) : id;
        }
        return id;
    }
}

class WeList extends UserValueComponent {
    static template = "web_editor.WeList";
    static StateModel = ListUserValue;
    static props = {
        ...UserValueComponent.props,
        availableRecords: { type: String, optional: true },
        hasDefault: { type: String, optional: true },
        inputType: { type: String, optional: true },
        defaults: { type: String, optional: true },
        defaultValue: { type: String, optional: true },
        addItemTitle: { type: String, optional: true },
        unsortable: { type: String, optional: true },
        notEditable: { type: String, optional: true },
        allowEmpty: { type: String, optional: true },
        newElementsNotToggleable: { type: String, optional: true },
        renderOnInputBlur: { type: String, optional: true },
    };
    static defaultProps = {
        inputType: "text",
        defaultValue: _t("Item"),
        addItemTitle: _t("Add"),
    };
    static isContainer = true;
    static components = { WeTitle };

    setup() {
        super.setup();
        this.tableRef = useRef("table");

        this._makeListItemsSortable();
        this.state._notifyCurrentState = this._notifyCurrentState.bind(this);

        useEffect(
            () => {
                if (this.scrollToLast) {
                    // Scroll to the new list element.
                    this.tableRef.el.querySelector('tr:last-child')
                        .scrollIntoView({behavior: 'smooth', block: 'nearest'});
                    this.scrollToLast = false;
                }
            },
            () => [this.state.listRecords.length]
        );
    }

    //------------------------------------------------------------------
    // PRIVATE
    //------------------------------------------------------------------

    /**
     * @override
     */
    _getFocusableElement() {
        return this.tableRef.el.querySelector("input");
    }
    /**
     * @private
     */
    _makeListItemsSortable() {
        if (this.props.unsortable === "true") {
            return;
        }
        useSortable({
            ref: this.tableRef,
            elements: "tr",
            followingElementClasses: ["opacity-50"],
            handle: ".o_we_drag_handle",
            onDrop: ({ element, next }) => {
                const id = this.state._toComparableId(element.querySelector("input").name);
                const recordIdx = this.state.listRecords.findIndex((rec) => rec.id === id);
                const record = this.state.listRecords.splice(recordIdx, 1)[0];
                const insertIdx = next
                    ? this.state.listRecords.findIndex((rec) =>
                        rec.id === this.state._toComparableId(next.querySelector("input").name)
                    ) : this.state.listRecords.length;
                this.state.listRecords.splice(insertIdx, 0, record);
                this._notifyCurrentState();
            },
            applyChangeOnDrop: true,
        });
    }
    /**
     * @private
     * @param {Boolean} [preview]
     */
    _notifyCurrentState(preview = false) {
        if (this.state.hasDefault) {
            this.state.listRecords.forEach((v) => {
                const id = this.state._toComparableId(v.id);
                // Elements not toggleable are considered as always selected.
                v.selected = this.state.selected.includes(id) || v.notToggleable;
            });
        }

        this.state.value = JSON.stringify(this.state.listRecords);
        if (preview) {
            this._onUserValuePreview();
        } else {
            this._onUserValueChange();
        }
    }
    /**
     * Maps listRecord properties to data-attributes.
     *
     * @private
     * @param {Object} listRecord
     * @returns {Object}
     */
    getInputDataAtts(listRecord) {
        return Object.entries(listRecord).reduce((obj, entry) => {
            if (["display_name", "id", "placeholder"].includes(entry[0])) {
                return obj;
            }
            obj[`data-${camelToKebab(entry[0])}`] = entry[1];
            return obj;
        }, {});
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick(ev) {
        if (!this.state.opened) {
            this.state.open();
        } else {
            this.state.close();
        }
    }
    /**
     * @private
     */
    _onAddCustomItemClick() {
        const recordData = {};
        if (this.props.newElementsNotToggleable === "true") {
            recordData.notToggleable = true;
        }
        this.state._updateListRecords(recordData);
        this._notifyCurrentState();
        this.scrollToLast = true;
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onAddExistingItemClick(ev) {
        const record = this.state.existingRecords.find((record) => {
            return record.id === this.state._toComparableId(ev.currentTarget.dataset.addOption);
        });
        this.state._updateListRecords(record);
        this._notifyCurrentState();
        this.scrollToLast = true;
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onAddItemCheckboxClick(ev) {
        const recordId = this.state._toComparableId(ev.currentTarget.dataset.select);
        const isActive = this.state.selected.includes(recordId);
        if (this.props.hasDefault === 'unique') {
            this.state.selected = [];
        }
        if (isActive) {
            this.state.selected.splice(this.state.selected.indexOf(recordId), 1);
        } else {
            this.state.selected.push(recordId);
        }
        this._notifyCurrentState();
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onListItemBlurInput(ev) {
        const preview = ev.type === 'input';
        if (preview || !this.tableRef.el.contains(ev.relatedTarget) || this.props.renderOnInputBlur === "true") {
            // We call the function below only if the element that recovers the
            // focus after this blur is not an element of the we-list or if it
            // is an input event (preview). This allows to use the TAB key to go
            // from one input to another in the list. This behavior can be
            // cancelled if the widget has reloadOnInputBlur = "true" in its
            // props.
            const recordToUpdate = this.state.listRecords.find((rec) =>
                rec.id === this.state._toComparableId(ev.currentTarget.name)
            );
            recordToUpdate.display_name = ev.currentTarget.value;
            const timeSinceMousedown = ev.timeStamp - this.mousedownTime;
            if (timeSinceMousedown < 500) {
                // Without this "setTimeOut", "click" events are not triggered when
                // clicking directly on a "we-button" of the "we-list" without first
                // focusing out the input.
                setTimeout(() => {
                    this._notifyCurrentState(preview);
                }, 500);
            } else {
                this._notifyCurrentState(preview);
            }
        }
    }
    /**
     * @private
     */
    _onWeListMousedown(ev) {
        this.mousedownTime = ev.timeStamp;
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onRemoveItemClick(ev) {
        const minElements = this.props.allowEmpty ? 0 : 1;
        if (this.state.listRecords.length > minElements) {
            const removeId = this.state._toComparableId(ev.currentTarget.dataset.removeOption);
            const recordIdx = this.state.listRecords.findIndex((record) => record.id === removeId);
            if (recordIdx >= 0) {
                this.state.listRecords.splice(recordIdx, 1);
            }
            if (this.state.hasDefault) {
                const selectedIdx = this.state.selected.indexOf(removeId);
                if (selectedIdx >= 0) {
                    this.state.selected.splice(selectedIdx, 1);
                }
            }
            this._notifyCurrentState();
        }
    }
}
registry.category("snippet_widgets").add("WeList", WeList);

class RangeUserValue extends UnitUserValue {
    constructor() {
        super(...arguments);
        this._state.max = undefined;
        this._state.displayValue = false;
    }
    /**
     * @type {number}
     */
    get max() {
        return this._state.max;
    }
    set max(value) {
        this._state.max = value;
    }
    /**
     * @type {string|number}
     */
    get displayValue() {
        return this._state.displayValue;
    }
    set displayValue(value) {
        this._state.displayValue = value;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    loadMethodsData(validMethodNames) {
        super.loadMethodsData(...arguments);
        for (const methodName of this._methodsNames) {
            const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
            if (possibleValues.length > 1) {
                this.max = possibleValues.length - 1;
                break;
            }
        }
    }
    /**
     * @override
     */
    async setValue(value, methodName) {
        await super.setValue(value, methodName);
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        const inputValue = possibleValues.length > 1 ? possibleValues.indexOf(value) : this.value;
        if (this._data.displayRangeValue) {
            this._computeDisplayValue(inputValue);
        }
    }
    /**
     * @override
     */
    getValue(methodName) {
        const value = super.getValue(...arguments);
        const possibleValues = this._methodsParams.optionsPossibleValues[methodName];
        return possibleValues.length > 1 ? possibleValues[+value] : value;
    }
    /**
     * @private
     * @param {string} inputValue 
     */
    _computeDisplayValue(inputValue) {
        if (this.toRatio) {
            const inputValueAsNumber = Number(inputValue);
            const ratio = inputValueAsNumber >= 0 ? 1 + inputValueAsNumber : 1 / (1 - inputValueAsNumber);
            this.displayValue = `${ratio.toFixed(2)}x`;
        } else if (this._data.displayRangeValueUnit) {
            this.displayValue = inputValue + this._data.displayRangeValueUnit;
        } else {
            this.displayValue = inputValue;
        }
    }
}

const RangeUserValueWidget = UnitUserValueWidget.extend({});
class WeRange extends WeInput {
    static template = "web_editor.WeRange";
    static StateModel = RangeUserValue;
    static props = {
        ...WeInput.props,
        min: { type: String, optional: true },
        max: { type: String, optional: true },
        step: { type: String, optional: true },
        toRatio: { type: String, optional: true },
        displayRangeValue: { type: String, optional: true },
    };
    static defaultProps = {
        min: "0",
        max: "100",
        step: "1",
        toRatio: "",
        displayRangeValue: "",
        unit: "",
    };
    setup() {
        this._onInputChange = debounce(this._onInputChange, 100);
        super.setup();
        this.state.toRatio = this.props.toRatio;
        if (Number(this.props.min) > Number(this.props.max)) {
            this.state.max = this.props.min;
            this.min = this.props.max;
            this.inverted = true;
        } else {
            this.min = this.props.min;
            this.state.max ||= this.props.max;
            this.inverted = false;
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInputChange(ev) {
        this.state.value = ev.target.value;
        this._onUserValueChange(ev);
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onInputInput(ev) {
        this.state.value = ev.target.value;
        if (this.props.displayRangeValue) {
            this.state._computeDisplayValue(this.state.value);
        }
        this._onUserValuePreview(ev);
    }
}
registry.category("snippet_widgets").add("WeRange", WeRange);

class WeSelectPager extends WeSelect {

    static template = "web_editor.WeSelectPager";
    /**
     * @override
     */
    setup() {
        super.setup();
        this.__onScroll = useThrottleForAnimation(this._onScroll);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * We never try to adjust the position for selection with pagers as they
     * are fullscreen.
     *
     * @override
     */
    _adjustDropdownPosition() {
        return;
    }
    /**
     * @override
     */
    _shouldIgnoreClick(ev) {
        return !!ev.target.closest('.o_pager_nav') || super._shouldIgnoreClick(...arguments);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Scrolls to the requested section.
     *
     * @private
     */
    _onClickScrollPage(ev) {
        const navButtonEl = ev.target.closest("[data-scroll-to]");
        if (!navButtonEl) {
            return;
        }
        const attribute = navButtonEl.dataset.scrollTo;
        const destinationOffset = this.menuRef.el.querySelector('.' + attribute).offsetTop;

        const pagerNavEl = this.menuRef.el.querySelector(".o_pager_nav");
        const pagerContainerEl = this.menuRef.el.querySelector(".o_pager_container");
        pagerContainerEl.scrollTop = destinationOffset - pagerNavEl.offsetHeight;
    }
    /**
     * @private
     */
    _onClickCloseMenu(ev) {
        this.state.close();
    }
    /**
     * @private
     */
    _onScroll(ev) {
        const pagerContainerEl = this.menuRef.el.querySelector(".o_pager_container");
        const pagerContainerHeight = pagerContainerEl.getBoundingClientRect().height;
        // The threshold for when a menu element is defined as 'active' is half
        // of the container's height. This has a drawback as if a section
        // is too small it might never get `active` if it's the last section.
        const threshold = pagerContainerEl.scrollTop + (pagerContainerHeight / 2);
        const anchorElements = this.menuRef.el.querySelectorAll('[data-scroll-to]');
        for (const anchorEl of anchorElements) {
            const destination = anchorEl.getAttribute('data-scroll-to');
            const sectionEl = this.menuRef.el.querySelector(`.${destination}`);
            const nextSectionEl = sectionEl.nextElementSibling;
            anchorEl.classList.toggle('active', sectionEl.offsetTop < threshold &&
            (!nextSectionEl || nextSectionEl.offsetTop > threshold));
        }
    }
}
registry.category("snippet_widgets").add("WeSelectPager", WeSelectPager);

const Many2oneUserValueWidget = SelectUserValueWidget.extend({});

export class Many2oneUserValue extends SelectUserValue {
    // Props that will be read into `this.options` on setup and not
    // transfered to inner buttons.
    // `domain` is the static part of the domain used in searches, not
    // depending on already selected ids and other filters.
    static configProps = [
        "model", "fields", "limit", "domain",
        "callWith", "createMethod", "filterInModel", "filterInField", "nullText",
        "defaultMessage",
    ];

    constructor() {
        super(...arguments);
        this.orm = serviceCached(this.env.services.orm);
        this._state.records = [];
        this._state.hasMore = false;

        this.displayNameCache = {};
        this.options = Object.assign({}, this._data, {
            limit: '5',
            fields: '[]',
            domain: '[]',
            callWith: 'id',
            dataAttributes: {},
        });
        this._updateOptions(this._data);
        this.options.domainComponents = {};

        this.constructorPatch();
    }
    constructorPatch() {}
    /**
     * @type {Object[]}
     */
    get records() {
        return this._state.records;
    }
    set records(value) {
        this._state.records = value;
    }
    /**
     * @type {boolean}
     */
    get hasMore() {
        return this._state.hasMore;
    }

    /**
     * @override
     */
    async setValue(value, methodName) {
        await super.setValue(...arguments);
        if (this._state.toggler.textContent === this.constructor.PLACEHOLDER_TEXT.toString()) {
            // The currently selected value is not present in the search, need to read
            // its display name.
            if (value !== '') {
                // FIXME: value may not be an id if callWith is specified!
                this._state.toggler.textContent = await this._getDisplayName(parseInt(value));
            } else {
                this._state.toggler.textContent = this.options.defaultMessage || _t("Choose a record...");
            }
        }
    }
    /**
     * @override
     */
    getValue(methodName) {
        if (methodName === this.options.createMethod && this.createInputValue) {
            return this.createInputValue;
        }
        return super.getValue(...arguments);
    }
    /**
     * @override
     */
    registerUserValue(userValue) {
        // Get a reference to the createButton and make sure it is always
        // inactive.
        if (this._data.createMethod) {
            if (
                !this.createButton
                && userValue instanceof ButtonUserValue
                && userValue._data[this._data.createMethod] !== undefined
            ) {
                this.createButton = userValue;
                this.createButton.isActive = () => false;
            }
        }
        super.registerUserValue(userValue);
    }
    /**
     * @override
     */
    close() {
        super.close(...arguments);
        this._search("");
    }
    /**
     * Updates the domain with defined inclusive filter to make sure that only
     * records that are linked to specific records are retrieved.
     * Filtering-in is configured with
     *   * a `filterInModel` attribute, the linked model
     *   * a `filterInField` attribute, field of the linked model holding
     *   allowed values for this widget
     *
     * @param {integer[]} linkedRecordsIds
     * @returns {Promise}
     */
    async setFilterInDomainIds(linkedRecordsIds) {
        const allowedIds = new Set();
        if (linkedRecordsIds) {
            const parentRecordsData = await this.orm.searchRead(
                this.options.filterInModel,
                [['id', 'in', linkedRecordsIds]],
                [this.options.filterInField]
            );
            parentRecordsData.forEach(record => {
                record[this.options.filterInField].forEach(item => allowedIds.add(item));
            });
        }
        if (allowedIds.size) {
            this.options.domainComponents.filterInModel = ['id', 'in', [...allowedIds]];
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _updateOptions(props) {
        for (const prop in props) {
            // TODO: @owl-options: remove undefined props in UserValue directly?
            if (props[prop] === undefined) {
                continue;
            }
            if (this.constructor.configProps.includes(prop)) {
                this.options[prop] = props[prop];
            } else {
                this.options.dataAttributes[prop] = props[prop];
            }
        }
        this.options.limit = parseInt(this.options.limit);
        if (typeof this.options.fields === "string") {
            this.options.fields = JSON.parse(this.options.fields);
        }
        if (!this.options.fields.includes('display_name')) {
            this.options.fields.push('display_name');
        }
        if (typeof this.options.domain === "string") {
            this.options.domain = JSON.parse(this.options.domain);
        }
        this.options.nullText = this.$target[0].dataset.nullText ||
            JSON.parse(this.$target[0].dataset.oeContactOptions || '{}')['null_text'];
    }
    /**
     * Searches the database for corresponding records and updates the dropdown
     *
     * @private
     */
    async _search(needle) {
        const recTuples = await this.orm.call(this.options.model, "name_search", [], {
            name: needle,
            args: (await this._getSearchDomain()).concat(
                Object.values(this.options.domainComponents).filter(item => item !== null)
            ),
            operator: "ilike",
            limit: this.options.limit + 1,
        });
        const records = await this.orm.read(
            this.options.model,
            recTuples.map(([id, _name]) => id),
            this.options.fields
        );

        if (this.options.nullText &&
                this.options.nullText.toLowerCase().includes(needle.toLowerCase())) {
            // Beware of RPC cache.
            if (!records.length || records[0].id) {
                records.unshift({id: 0, name: this.options.nullText, display_name: this.options.nullText});
            }
        }
        records.forEach(record => {
            this.displayNameCache[record.id] = record.display_name;
        });

        this.records = records.slice(0, this.options.limit);
        this._state.hasMore = records.length > this.options.limit;

        if (this.options.nullText && !this.getValue()) {
            this.setValue(0);
        }
    }
    /**
     * Returns the domain to use for the search.
     *
     * @private
     */
    async _getSearchDomain() {
        return this.options.domain;
    }
    /**
     * Returns the display name for a given record.
     *
     * @private
     */
    async _getDisplayName(recordId) {
        if (!this.displayNameCache.hasOwnProperty(recordId)) {
            this.displayNameCache[recordId] = (await this.orm.read(this.options.model, [recordId], ['display_name']))[0].display_name;
        }
        return this.displayNameCache[recordId];
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    userValueNotification(params) {
        const { widget } = params;
        if (widget && widget === this.createButton && !params.previewMode) {
            // When the create button is clicked, make sure the state value
            // matches the value of the input element because it might have been
            // removed after closing the dropdown.
            if (this.displayedValue && !this.createInputValue) {
                this.createInputValue = this.displayedValue;
                delete this.displayedValue;
            }
            // Prevent creating a record if the input is empty.
            if (!this.createInputValue) {
                return;
            }
        }
        if (widget !== this.createButton && this.createInputValue) {
            // Remove the createInputValue if something else than the
            // createButton was clicked or hovered, so that it doesn't create a
            // record. We reset it after the value handling.
            this.displayedValue = this.createInputValue;
            this.createInputValue = "";
        }
        super.userValueNotification(...arguments);
        // Reset the createInputValue after value handling, only with
        // previewMode === true or 'reset'.
        if (this.displayedValue && params.previewMode) {
            this.createInputValue = this.displayedValue;
            delete this.displayedValue;
        }
    }
}

class WeMany2one extends WeSelect {
    static template = "web_editor.WeMany2one";
    static StateModel = Many2oneUserValue;
    static components = { ...WeSelect.components, WeRow, WeInput, WeButton };
    static configProps = {
        model: { type: String },
        domain: { type: String, optional: true },
        fields: { type: String, optional: true },
        limit: { type: String, optional: true },
        callWith: { type: String, optional: true },
        createMethod: { type: String, optional: true },
        filterInModel: { type: String, optional: true },
        filterInField: { type: String, optional: true },
        nullText: { type: String, optional: true },
        defaultMessage: { type: String, optional: true },
    };
    static props = {
        ...WeSelect.props,
        ...this.configProps,
    };

    setup() {
        super.setup();
        const keepLast = new KeepLast();
        this.afterSearch = [];

        onWillStart(async () => {
            await this.state._search("");
        });

        onWillUpdateProps(async (nextProps) => {
            this.state._updateOptions(nextProps);
            // Make sure the update is reflected in the prefetched records.
            await this.state._search("");
        });

        useEffect(
            () => {
                // Load methodsData for WeButtons generated from
                // this.state.records.
                if (this.state._methodsNames) {
                    Object.values(this.state._subValues).forEach(widget => {
                        if (widget instanceof ButtonUserValue && widget._data.recordData) {
                            widget.loadMethodsData([...this.state._methodsNames]);
                        }
                    });
                    if (this.state.value !== undefined) {
                        this.state._methodsNames.forEach(async (methodName) =>
                            await keepLast.add(this.state.setValue(this.state.value, methodName))
                        );
                    }
                }
                this.waitingForSearch = false;
                this.afterSearch.forEach(cb => cb());
                this.afterSearch = [];
            },
            () => [this.state.records]
        );
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    getAllClasses() {
        return {
            ...super.getAllClasses(),
            "position-static": this.props.createUserValue,
        };
    }
    /**
     * Copy over the props from the main element, and default the value
     * to the callWith field of the record so that if it's a method, it will
     * be called with that value
     *
     * @param {Object} record
     * @returns {Object}
     */
    getButtonProps(record) {
        const buttonProps = Object.assign({}, this.state.options.dataAttributes);
        Object.keys(buttonProps).forEach((key) => {
            buttonProps[key] = buttonProps[key] || record[this.state.options.callWith].toString();
        });
        buttonProps.recordData = JSON.stringify(record);
        return buttonProps;
    }

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
        if (ev.target.closest("we-button")) {
            this.menuRef.el.querySelector(".o_we_m2o_search input").value = "";
        }
        // Reset the input value when creating a new record. The state value is
        // reset on `setValue` of the ListUserValue.
        if (ev.target.closest(".o_we_m2o_create") && ev.target.closest("we-button")) {
            this.menuRef.el.querySelector(".o_we_m2o_create input").value = "";
        }
        return super._onClick(...arguments);
    }
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
        this.searchIntent = setTimeout(async () => {
            await this.state._search(ev.target.value);
        }, 500);
    }
    /**
     * Selects the first option when pressing enter in the search input.
     *
     * @private
     */
    _onSearchKeydown(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        const action = () => {
            const firstButton = this.menuRef.el.querySelector(':scope > we-button');
            if (firstButton) {
                firstButton.click();
            }
        };
        if (this.waitingForSearch) {
            this.afterSearch.push(action);
        } else {
            action();
        }
    }
    /**
     * Focuses the search input when clicking on the "Search more..." button.
     *
     * @private
     */
    _onSearchMoreClick(ev) {
        this.menuRef.el.querySelector(".o_we_m2o_search input").focus();
    }
    /**
     * @private
     */
    _onCreateInputInput(ev) {
        this.state.createInputValue = ev.currentTarget.value;
    }
}
registry.category("snippet_widgets").add("WeMany2one", WeMany2one);


const Many2manyUserValueWidget = UserValueWidget.extend({});

class Many2manyUserValue extends UserValue {
    static configProps = ['model', 'recordId', 'm2oField', 'createMethod', 'fakem2m', 'filterIn'];

    constructor() {
        super(...arguments);
        this._state.m2oProps = {};

        for (const prop in this._data) {
            if (
                !this.constructor.configProps.includes(prop)
                && Many2oneUserValue.configProps.includes(prop)
            ) {
                this.m2oProps[prop] = this._data[prop];
            }
        }

        this.filterIn = this._data.filterIn !== undefined;
        if (this.filterIn) {
            // Transfer filter-in values to child m2o.
            this.m2oProps.filterInModel = this._data.model;
            this.m2oProps.filterInField = this._data.m2oField;
        }
    }
    get m2oProps() {
        return this._state.m2oProps;
    }
    set m2oProps(value) {
        this._state.m2oProps = value;
    }

    /**
     * Only allow to fetch/select records which are linked (via `m2oField`) to the
     * specified records.
     *
     * @param {integer[]} linkedRecordsIds
     * @returns {Promise}
     * @see Many2oneUserValue.setFilterInDomainIds
     */
    async setFilterInDomainIds(linkedRecordsIds) {
        if (this.filterIn) {
            return this.listUserValue.createUserValue.setFilterInDomainIds(linkedRecordsIds);
        }
    }
    /**
     * @override
     */
    loadMethodsData(validMethodNames, ...rest) {
        // TODO: check that addRecord is still needed.
        super.loadMethodsData(['addRecord', ...validMethodNames], ...rest);
    }
    /**
     * @override
     */
    setValue(value, methodName) {
        if (methodName === this._data.createMethod) {
            return this.listUserValue?.createUserValue.setValue(value, methodName);
        }
        if (!value) {
            // TODO: why do we need this.
            value = this.value;
        }
        super.setValue(value, methodName);
        this.listUserValue?.setValue(this.value);
    }
    /**
     * @override
     */
    getValue(methodName) {
        return this.listUserValue.getValue(methodName);
    }
    /**
     * @override
     */
    registerUserValue(userValue) {
        if (!this.listUserValue && userValue instanceof ListUserValue) {
            this.listUserValue = userValue;
        }
        super.registerUserValue(userValue);
        this._methodsNames.delete("addRecord");
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    userValueNotification(params) {
        const { widget, previewMode } = params;
        if (!widget) {
            return super.userValueNotification(...arguments);
        }
        if (widget === this.listUserValue) {
            this.value = widget.value;
            this.notifyValueChange(previewMode);
        }
    }
}

class WeMany2many extends UserValueComponent {
    static isContainer = true;
    static template = "web_editor.WeMany2many";
    static StateModel = Many2manyUserValue;
    static components = { WeList, WeMany2one, WeTitle };
    static configProps = {
        // "model" and "createMethod" are already part of the WeMany2one props.
        fakem2m: { type: String, optional: true },
        filterIn: { type: String, optional: true },
        m2oField: { type: String, optional: true },
        recordId: { type: String, optional: true },
    };
    static props = {
        ...UserValueComponent.props,
        ...WeMany2one.configProps,
        ...this.configProps,
    };

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.field = useService("field");

        onWillStart(async () => {
            let m2oModel;
            // If the widget does not have a real m2m field in the database
            // We do not need to fetch anything from the DB
            if (this.props.fakem2m) {
                m2oModel = this.props.model;
            } else {
                const { model, recordId, m2oField } = this.props;
                const [record] = await this.orm.read(model, [parseInt(recordId)], [m2oField]);
                const selectedRecordIds = record[m2oField];
                // TODO: handle no record
                const modelData = await this.field.loadFields(model, { fieldNames: [m2oField] });
                m2oModel = modelData[m2oField].relation;

                const selectedRecords = await this.orm.read(m2oModel, selectedRecordIds, ['display_name']);
                this.state.value = JSON.stringify(selectedRecords);
            }

            Object.assign(this.state.m2oProps, {
                model: m2oModel,
                addRecord: '',
                createMethod: this.props.createMethod,
            });
        });
    }
}
registry.category("snippet_widgets").add("WeMany2many", WeMany2many);

const userValueWidgetsRegistry = {
    'we-button': ButtonUserValueWidget,
    'we-checkbox': CheckboxUserValueWidget,
    'we-select': SelectUserValueWidget,
    'we-button-group': ButtonGroupUserValueWidget,
    'we-input': InputUserValueWidget,
    'we-multi': MultiUserValueWidget,
    'we-datetimepicker': DatetimePickerUserValueWidget,
    'we-datepicker': DatePickerUserValueWidget,
    'we-list': ListUserValueWidget,
    'we-imagepicker': ImagepickerUserValueWidget,
    'we-videopicker': VideopickerUserValueWidget,
    'we-range': RangeUserValueWidget,
    'we-many2one': Many2oneUserValueWidget,
    'we-many2many': Many2manyUserValueWidget,
};

/**
 * This component is responsible for rendering the widgets. Once it's mounted
 * it means all "UserValue" states have been created, and the templates are
 * accessible. So it notifies the SnippetsMenu that the initial "updateUI" is
 * ready to be done.
 * @TODO @owl-options: If an option renders a widget **after** the initial
 * onMounted, the SnippetsMenu will not have a computed state for its widgets.
 * It should therefore ask for a new updateUI. This should probably be improved.
 * To discuss.
 */
export class SnippetOptionComponent extends Component {

    static template = "web_editor.SnippetOptionComponent";

    static props = {
        snippetOption: Object,
        onOptionMounted: Function,
    };

    setup() {
        this.renderContext = useState(this.props.snippetOption.instance.renderContext);
        // When a component is mounted or unmounted, the state of other
        // components might be impacted. (i.e. dependencies behaving 
        // differently when a component is in the DOM or when it isn't)
        this.updateUI = false;

        useSubEnv({
            snippetOption: this.props.snippetOption.instance,
            userValueNotification: this.props.snippetOption.instance.onUserValueUpdate,
            registerUserValue: (userValue) => {
                this.updateUI = true;
                return this.props.snippetOption.instance.registerUserValue(userValue);
            },
            unregisterUserValue: (userValue) => {
                this.updateUI = true;
                return this.props.snippetOption.instance.unregisterUserValue(userValue);
            },
            renderContext: this.renderContext,
            registerLayoutElement: (layoutElement) => {
                return this.props.snippetOption.instance.registerLayoutElement(layoutElement);
            },
            $target: this.props.snippetOption.instance.$target,
        });

        onMounted(() => {
            this.props.onOptionMounted();
            this.updateUI = false;
        });

        onPatched(() => {
            if (this.updateUI) {
                this.updateUI = false;
                this.props.onOptionMounted();
            }
        });
    }
}
/**
 * Handles a set of options for one snippet. The registry returned by this
 * module contains the names of the specialized SnippetOptionWidget which can be
 * referenced thanks to the data-js key in the web_editor options template.
 */
export class SnippetOption {
    static events = {
        'click .o_we_collapse_toggler': '_onCollapseTogglerClick',
    };
    static custom_events = {
        'user_value_update': '_onUserValueUpdate',
        'user_value_widget_critical': '_onUserValueWidgetCritical',
    };
    /**
     * Indicates if the option should be displayed in the button group at the
     * top of the options panel, next to the clone/remove button.
     *
     * @type {boolean}
     */
    static isTopOption = false;
    /**
     * Indicates if the option should be the first one displayed in the button
     * group at the top of the options panel, next to the clone/remove button.
     *
     * @type {boolean}
     */
    static isTopFirstOption = false;
    /**
     * Forces the target to not be possible to remove. It will also hide the
     * clone button.
     *
     * @type {boolean}
     */
    static forceNoDeleteButton = false;
    /**
     * The option needs the handles overlay to be displayed on the snippet.
     *
     * @type {boolean}
     */
    static displayOverlayOptions = false;
    /**
     * Forces the target to be duplicable.
     *
     * @type {boolean}
     */
    static forceDuplicateButton = false;

    /**
     * The option `$el` is supposed to be the associated DOM UI element.
     * The option controls another DOM element: the snippet it
     * customizes, which can be found at `$target`. Access to the whole edition
     * overlay is possible with `$overlay` (this is not recommended though).
     *
     * @constructor
     */
    constructor({ editor, $target, $overlay, data, options, callbacks }) {

        this.env = options.env;
        this.$target = $target;
        this.$overlay = $overlay;
        this.data = data;
        this.options = options;
        // TODO: @owl-options better name or do it differently? It's to replace
        // what was previously done by trigger_up's.
        this.callbacks = callbacks;

        this.className = 'snippet-option-' + this.data.optionName;

        this.ownerDocument = this.$target[0].ownerDocument;

        /** @type {UserValue[]} */
        this._userValues = {};
        this._layoutElements = [];
        this._userValueWidgets = [];
        this._actionQueues = new Map();

        this.dialog = this.env.services.dialog;
        // Passed as props to components so bind it here, that way
        // it will always have the same reference.
        this.onUserValueUpdate = this._onUserValueUpdate.bind(this);

        this.constructorPatch();
    }
    /**
     * To be patched.
     */
    constructorPatch() {}
    /**
     * Called after the constructor. Allows the option to do async stuff
     * before the widgets are mounted.
     */
    async willStart() {
        const context = await this._getRenderContext();
        this.renderContext = reactive({...context});
    }
    destroy() {}
    /**
     * @override
     */
    renderElement() {
        this.el.appendChild(this.uiFragment);
        this.uiFragment = null;
    }
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * (the first time, this follows the call to the @see start method).
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    async onFocus() {}
    /**
     * Called when the parent edition overlay is covering the associated snippet
     * for the first time, when it is a new snippet dropped from the d&d snippet
     * menu. Note: this is called after the start and onFocus methods.
     *
     * @abstract
     * @param {Object} options
     * @param {boolean} options.isCurrent
     *        true if the main element has been built (so not when a child of
     *        the main element has been built).
     * @returns {Promise|undefined}
     */
    async onBuilt(options) {}
    /**
     * Called when the parent edition overlay is removed from the associated
     * snippet (another snippet enters edition for example).
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    async onBlur() {}
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
    onClone(options) {}
    /**
     * Called when the associated snippet is moved to another DOM location.
     *
     * @abstract
     */
    onMove() {}
    /**
     * Called when the associated snippet is about to be removed from the DOM.
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    async onRemove() {}
    /**
     * Called when the target is shown, only meaningful if the target was hidden
     * at some point (typically used for 'invisible' snippets).
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    async onTargetShow() {}
    /**
     * Called when the target is hidden (typically used for 'invisible'
     * snippets).
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    async onTargetHide() {}
    /**
     * Called when the template which contains the associated snippet is about
     * to be saved.
     *
     * @abstract
     * @return {Promise|undefined}
     */
    async cleanForSave() {}
    /**
     * Called when the associated snippet UI needs to be cleaned (e.g. from
     * visual effects like previews).
     * TODO this function will replace `cleanForSave` in the future.
     *
     * @abstract
     * @return {Promise|undefined}
     */
    async cleanUI() {}
    /**
     * Adds the given widget to the known list of user value widgets
     *
     * @param {UserValue} userValue
     */
    registerUserValue(userValue) {
        this._userValues[userValue.id] = (userValue);
        userValue.loadMethodsData(this.getMethodsNames());
    }
    /**
     * Removes the give user value to the known list of user values.
     *
     * @param {UserValue} userValue
     */
    unregisterUserValue(userValue) {
        delete this._userValues[userValue.id];
    }
    /**
     * Register a layout element to hide them if no component is visible
     * within it.
     * @params {Object} layoutElement
     */
    registerLayoutElement(layoutElement) {
        this._layoutElements.push(layoutElement);
    }

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
    selectClass(previewMode, widgetValue, params) {
        for (const classNames of params.possibleValues) {
            if (classNames) {
                this.$target[0].classList.remove(...classNames.trim().split(/\s+/g));
            }
        }
        if (widgetValue) {
            this.$target[0].classList.add(...widgetValue.trim().split(/\s+/g));
        }
    }
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
    selectDataAttribute(previewMode, widgetValue, params) {
        const value = this._selectAttributeHelper(widgetValue, params);
        this.$target[0].dataset[params.attributeName] = value;
    }
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
    selectAttribute(previewMode, widgetValue, params) {
        const value = this._selectAttributeHelper(widgetValue, params);
        if (value) {
            this.$target[0].setAttribute(params.attributeName, value);
        } else {
            this.$target[0].removeAttribute(params.attributeName);
        }
    }
    /**
     * Default option method which allows to select a value and set it on the
     * associated snippet as a property. The name of the property is
     * given by the propertyName parameter.
     *
     * @param {boolean} previewMode - @see this.selectClass
     * @param {string} widgetValue
     * @param {Object} params
     */
    selectProperty(previewMode, widgetValue, params) {
        if (!params.propertyName) {
            throw new Error('Property name missing');
        }
        const value = this._selectValueHelper(widgetValue, params);
        this.$target[0][params.propertyName] = value;
    }
    /**
     * Default option method which allows to select a value and set it on the
     * associated snippet as a css style. The name of the css property is
     * given by the cssProperty parameter.
     *
     * @param {boolean} previewMode - @see this.selectClass
     * @param {string} widgetValue
     * @param {Object} params
     * @param {string} [params.forceStyle] if undefined, the method will not
     *      set the inline style (and thus even remove it) if the item would
     *      already have the given style without it (thanks to a CSS rule for
     *      example). If defined (as a string), it acts as the "priority" param
     *      of @see CSSStyleDeclaration.setProperty: it should be 'important' to
     *      set the style as important or '' otherwise. Note that if forceStyle
     *      is undefined, the style is set as important only if required to have
     *      an effect.
     * @returns {Promise|undefined}
     */
    async selectStyle(previewMode, widgetValue, params) {
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
            this.$target[0].style.setProperty('background-image', '');
            if (!widgetValue || widgetValue === 'false') {
                // If no background-color is being set and there is an image,
                // combine it with the current color combination's gradient.
                const styleBgImageParts = backgroundImageCssToParts(styles['background-image']);
                bgImageParts.gradient = styleBgImageParts.gradient;
            }
            const combined = backgroundImagePartsToCss(bgImageParts);
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
        const applyAllCSS = (values) => {
            for (let i = cssProps.length - 1; i > 0; i--) {
                hasUserValue = applyCSS.call(this, cssProps[i], values.pop(), styles) || hasUserValue;
            }
            hasUserValue = applyCSS.call(this, cssProps[0], values.join(' '), styles) || hasUserValue;
        }

        applyAllCSS([...values]);

        function applyCSS(cssProp, cssValue, styles) {
            if (typeof params.forceStyle !== 'undefined') {
                this.$target[0].style.setProperty(cssProp, cssValue, params.forceStyle);
                return true;
            }

            if (!weUtils.areCssValuesEqual(styles.getPropertyValue(cssProp), cssValue, cssProp, this.$target[0])) {
                this.$target[0].style.setProperty(cssProp, cssValue);
                // If change had no effect then make it important.
                if (!params.preventImportant && !weUtils.areCssValuesEqual(
                        styles.getPropertyValue(cssProp), cssValue, cssProp, this.$target[0])) {
                    this.$target[0].style.setProperty(cssProp, cssValue, 'important');
                }
                return true;
            }
            return false;
        }

        if (params.extraClass) {
            this.$target.toggleClass(params.extraClass, hasUserValue);
            if (hasUserValue) {
                // Might have changed because of the class.
                for (const cssProp of cssProps) {
                    this.$target[0].style.removeProperty(cssProp);
                }
                applyAllCSS(values);
            }
        }

        _restoreTransitions();
    }
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
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override the helper method to search inside the $target element instead
     * of the UI item element.
     *
     * @override
     */
    $() {
        return this.$target.find.apply(this.$target, arguments);
    }
    /**
     * Closes all user value widgets.
     */
    closeWidgets() {
        Object.values(this._userValues).forEach(widget => widget.close());
    }
    /**
     * @param {string} name
     * @returns {UserValueWidget|null}
     */
    findWidget(name) {
        for (const widget of Object.values(this._userValues)) {
            if (widget.getName() === name) {
                return widget;
            }
            const depWidget = widget.findWidget(name);
            if (depWidget) {
                return depWidget;
            }
        }
        return null;
    }
    /**
     * Sometimes, options may need to notify other options, even in parent
     * editors. This can be done thanks to the 'option_update' event, which
     * will then be handled by this function.
     *
     * @param {string} name - an identifier for a type of update
     * @param {*} data
     */
    notify(name, data) {
        // We prefer to avoid refactoring this notify mechanism to make it
        // asynchronous because the upcoming conversion to owl might remove it.
        if (name === 'target') {
            this.setTarget(data);
        }
    }
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
    setTarget($target) {
        this.$target = $target;
    }
    getMethodsNames() {
        // TODO: @owl-options either add all possible method or find a way to compute it.
        function getMethods(obj) {
            if (!obj || obj === Object) {
                return [];
            }
            const properties = Object.getOwnPropertyNames(obj);
            const methods = properties.filter(name => typeof obj[name] === "function");
            return [...methods, ...getMethods(Object.getPrototypeOf(obj))];
        }
        return getMethods(this);
    }
    /**
     * Updates the UI. For widget update, @see _computeWidgetState.
     *
     * @param {boolean} [noVisibility=false]
     *     If true, only update widget values and their UI, not their visibility
     *     -> @see updateUIVisibility for toggling visibility only
     * @param {boolean} [assetsChanged=false]
     *     If true, widgets might prefer to _rerenderXML instead of calling
     *     this super implementation
     * @returns {Promise}
     */
    async updateUI({noVisibility, assetsChanged} = {}) {
        // For each widget, for each of their option method, notify to the
        // widget the current value they should hold according to the $target's
        // current state, related for that method.
        const useValueStates = Object.values(this._userValues);
        const proms = useValueStates.map(async (userValue) => {
            if (!userValue.started) {
                await userValue.start();
            }
            // Update widget value (for each method)
            const methodsNames = userValue.getMethodsNames();
            for (const methodName of methodsNames) {
                const params = userValue.getMethodsParams(methodName);

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
                await userValue.setValue(normalizedValue, methodName);
            }
        });
        await Promise.all(proms);

        if (!noVisibility) {
            await this.updateUIVisibility();
        }
    }
    /**
     * Updates the UI visibility - @see _computeVisibility. For widget update,
     * @see _computeWidgetVisibility.
     *
     * @returns {Promise}
     */
    async updateUIVisibility() {
        const proms = Object.values(this._userValues).map(async userValue => {
            const params = userValue.getMethodsParams();

            let obj = this;
            if (params.applyTo) {
                const $firstSubTarget = this.$(params.applyTo).eq(0);
                if (!$firstSubTarget.length) {
                    userValue.toggleVisibility(false);
                    return;
                }
                obj = createPropertyProxy(this, '$target', $firstSubTarget);
            }

            // Make sure to check the visibility of all sub-widgets. For
            // simplicity and efficiency, those will be checked with main
            // widgets params.
            const allSubValues = [userValue];
            let i = 0;
            while (i < allSubValues.length) {
                allSubValues.push(...Object.values(allSubValues[i]._subValues));
                i++;
            }
            const proms = allSubValues.map(async userValue => {
                const show = await this._computeWidgetVisibility.call(obj, userValue.getName(), params);
                if (!show) {
                    userValue.toggleVisibility(false);
                    return;
                }

                const dependencies = userValue.getDependencies();

                if (dependencies.length === 1 && dependencies[0] === 'fake') {
                    userValue.toggleVisibility(false);
                    return;
                }

                const dependenciesData = [];
                dependencies.forEach(depName => {
                    const toBeActive = (depName[0] !== '!');
                    if (!toBeActive) {
                        depName = depName.substr(1);
                    }

                    const userValue = this._requestUserValueWidgets(depName, true)[0];
                    if (userValue) {
                        dependenciesData.push({
                            userValue: userValue,
                            toBeActive: toBeActive,
                        });
                    }
                });
                const dependenciesOK = !dependenciesData.length || dependenciesData.some(depData => {
                    return (depData.userValue.isActive() === depData.toBeActive);
                });

                userValue.toggleVisibility(dependenciesOK);
            });
            return Promise.all(proms);
        });

        this.renderContext.showUI = await this._computeVisibility();

        await Promise.all(proms);

        for (const layout of this._layoutElements) {
            const shouldShow = Object.values(layout.userValues)
                .some(uv => uv.show);
            layout.state.show = shouldShow;
        }

        // TODO: @owl-options, layout should probably be hidden in template.
        // Hide layouting elements which contains only hidden widgets
        // TODO improve this, this is hackish to rely on DOM structure here.
        // Layouting elements should be handled as widgets or other.

        return !this.displayOverlayOptions && this.renderContext.showUI;
    }

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
    }
    /**
     * @private
     * @param {UserValueWidget[]} widgets
     * @returns {Promise<boolean|string>}
     */
    async _checkIfWidgetsUpdateNeedReload(widgets) {
        return false;
    }
    /**
     * @private
     * @returns {Promise<boolean>|boolean}
     */
    async _computeVisibility() {
        return true;
    }
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
    async _computeWidgetState(methodName, params) {
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

                const styles = window.getComputedStyle(this.$target[0]);
                const cssProps = weUtils.CSS_SHORTHANDS[params.cssProperty] || [params.cssProperty];
                const borderWidthCssProps = weUtils.CSS_SHORTHANDS['border-width'];
                const cssValues = cssProps.map(cssProp => {
                    let value = styles.getPropertyValue(cssProp).trim();
                    if (cssProp === 'box-shadow') {
                        const inset = value.includes('inset');
                        let values = value.replace(/,\s/g, ',').replace('inset', '').trim().split(/\s+/g);
                        const color = values.find(s => !s.match(/^\d/));
                        values = values.join(' ').replace(color, '').trim();
                        value = `${color} ${values}${inset ? ' inset' : ''}`;
                    }
                    if (borderWidthCssProps.includes(cssProp) && value.endsWith('px')) {
                        // Rounding value up avoids zoom-in issues.
                        // Zoom-out issues are not an expected use case.
                        value = `${Math.ceil(parseFloat(value))}px`;
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

                let value = cssValues.join(' ');
                if (params.withGradients && params.cssProperty === 'background-color') {
                    // Check if there is a gradient, in that case this is the
                    // value to be returned, we normally do not allow color and
                    // gradient at the same time (the option would remove one
                    // if editing the other).
                    const parts = backgroundImageCssToParts(styles['background-image']);
                    if (parts.gradient) {
                        value = parts.gradient;
                    }
                }

                this.$target[0].classList.remove('o_we_force_no_transition');

                if (params.cssProperty === 'background-color' && params.withCombinations) {
                    if (usedCC) {
                        const ccValue = weUtils.getCSSVariableValue(`o-cc${usedCC}-bg-gradient`).trim().replaceAll("'", '')
                            || weUtils.getCSSVariableValue(`o-cc${usedCC}-bg`).trim();
                        if (weUtils.areCssValuesEqual(value, ccValue)) {
                            // Prevent to consider that a color is used as CC
                            // override in case that color is the same as the
                            // one used in that CC.
                            return '';
                        }
                    } else {
                        const rgba = convertCSSColorToRgba(value);
                        if (rgba && rgba.opacity < 0.001) {
                            // Prevent to consider a transparent color is
                            // applied as background unless it is to override a
                            // CC. Simply allows to add a CC on a transparent
                            // snippet in the first place.
                            return '';
                        }
                    }
                }
                // When the default color is the target's "currentColor", the
                // value should be handled correctly by the option.
                if (value === "currentColor") {
                    return styles.color;
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
    }
    /**
     * @private
     * @param {string} widgetName
     * @param {Object} params
     * @returns {Promise<boolean>|boolean}
     */
    async _computeWidgetVisibility(widgetName, params) {
        return true;
    }
    /**
     * @private
     * @param {HTMLElement} el
     * @returns {Object}
     */
    _extraInfoFromDescriptionElement(el) {
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
    }
    /**
     * @private
     * @param {*}
     * @returns {string}
     */
    _normalizeWidgetValue(value) {
        value = `${value}`.trim(); // Force to a trimmed string
        value = normalizeCSSColor(value); // If is a css color, normalize it
        return value;
    }
    /**
     * Allows options to share a context to their template / components.
     *
     * @private
     * @returns {Promise}
     */
    async _getRenderContext() {
        return {};
    }
    /**
     * @private
     * @param {...string} widgetNames
     * @param {boolean} [allowParentOption=false]
     * @returns {UserValueWidget[]}
     */
    _requestUserValueWidgets(...args) {
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
            widget = this.callbacks.requestUserValue({
                name: widgetName,
                allowParentOption: allowParentOption,
            });
            if (widget) {
                widgets.push(widget);
            }
        }
        return widgets;
    }
    /**
     * @private
     * @param {function<Promise<jQuery>>} [callback]
     * @returns {Promise}
     */
    async _rerenderXML(callback) {
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
    }
    /**
     * Activates the option associated to the given DOM element.
     *
     * @private
     * @param {boolean|string} previewMode
     *        - truthy if the option is enabled for preview or if leaving it (in
     *          that second case, the value is 'reset')
     *        - false if the option should be activated for good
     * @param {UserValue} widget - the widget which triggered the option change
     * @returns {Promise}
     */
    async _select(previewMode, widget) {
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
                const proms = Array.from($applyTo).map((subTargetEl) => {
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
    }
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
    }
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
    }
    /**
     * @private
     * @param {HTMLElement} collapseEl
     * @param {boolean|undefined} [show]
     */
    _toggleCollapseEl(collapseEl, show) {
        collapseEl.classList.toggle('active', show);
        collapseEl.querySelector('we-toggler.o_we_collapse_toggler').classList.toggle('active', show);
    }

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
    }
    /**
     * Called when a widget notifies a preview/change/reset.
     *
     * @private
     * @param {Event} ev
     */
    async _onUserValueUpdate(params) {
        const widget = params.widget;
        const previewMode = params.previewMode;

        // First check if the updated widget or any of the widgets it triggers
        // will require a reload or a confirmation choice by the user. If it is
        // the case, warn the user and potentially ask if he agrees to save its
        // current changes. If not, just do nothing.
        let requiresReload = false;
        if (!params.previewMode && !params.isSimulatedEvent) {
            const linkedWidgets = this._requestUserValueWidgets(...params.triggerWidgetsNames);
            const widgets = [params.widget].concat(linkedWidgets);

            const warnMessage = await this._checkIfWidgetsUpdateNeedWarning(widgets);
            if (warnMessage) {
                const okWarning = await new Promise(resolve => {
                    this.dialog.add(ConfirmationDialog, {
                        body: warnMessage,
                        confirm: () => resolve(true),
                        cancel: () => resolve(false),
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
        const shouldRecordUndo = (!previewMode && !params.isSimulatedEvent);
        if (shouldRecordUndo) {
            this.options.wysiwyg.odooEditor.unbreakableStepUnactive();
        }
        // TODO: @owl-options make it go through props + params.
        // const useLoaderOnOptionPanel = ev.target.el.dataset.loaderOnOptionPanel;
        const useLoaderOnOptionPanel = false;
        this.options.snippetEditionRequest({exec: async () => {
            // If some previous snippet edition in the mutex removed the target from
            // the DOM, the widget can be destroyed, in that case the edition request
            // is now useless and can be discarded.
            // if (this.isDestroyed()) {
            //     return;
            // }
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

            if (params.prepare) {
                // Why must this be done before checking noPreview ?
                params.prepare();
            }

            if (previewMode && (widget.getMethodsParams().noPreview)) {
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

            if (previewMode || requiresReload) {
                return;
            }

            await new Promise(resolve => setTimeout(() => {
                // Will update the UI of the correct widgets for all options
                // related to the same $target/editor
                this.options.optionUpdate().then(resolve);
            // Set timeout needed so that the user event which triggered the
            // option can bubble first.
            }));
        }, optionsLoader: useLoaderOnOptionPanel});

        // TODO: @owl-options is this still needed?
        if (params.isSimulatedEvent) {
            // If the user value update was simulated through a trigger, we
            // prevent triggering further widgets. This could be allowed at some
            // point but does not work correctly in complex website cases (see
            // customizeWebsite).
            return;
        }

        // TODO: @owl-options support triggerWidgets.
        // Check linked widgets: force their value and simulate a notification
        // It is possible that we don't have the widget, we continue because a
        // reload might be needed. For example, change template header without
        // being on a website.page (e.g: /shop).
        const linkedWidgets = this._requestUserValueWidgets(...params.triggerWidgetsNames);
        let i = 0;
        const triggerWidgetsValues = params.triggerWidgetsValues;
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
            this.env.requestSave({
                reloadEditor: true,
                optionSelector: this.data.selector,
                url: this.data.reload,
            });
        }
    }
    /**
     * @private
     */
    _onUserValueWidgetCritical() {
        this.trigger_up('remove_snippet', {
            $snippet: this.$target,
        });
    }
}


// class TestOption extends SnippetOption {
//     constructor() {
//         super(...arguments);
//         this.orm = serviceCached(this.env, "orm");
//         this.listItems = ["Test1", "Test2", "Test3"];
//         // M2O
//         this.pageId = "";
//         this.newPage = {};
//         // M2m
//         this.allGroupsByID = {};
//         this.groupIDs = [];

//         this.fetchGroups();
//     }
//     async fetchGroups() {
//         const groups = await this.orm.searchRead(
//             "res.groups",
//             [],
//             ["id", "name", "display_name"]
//         );
//         for (const group of groups) {
//             this.allGroupsByID[group.id] = group;
//         }
//     }

//     renderListItems(previewMode, widgetValue, params) {
//         this.listItems = JSON.parse(widgetValue);
//     }

//     setPageTemplate(previewMode, widgetValue, params) {
//         this.pageId = widgetValue;
//     }
//     createPage(previewMode, widgetValue, params) {
//         if (!widgetValue) {
//             return;
//         }
//         this.newPage = {
//             'id': Math.floor(Math.random() * 8) + 1,
//             'name': widgetValue,
//             'display_name': widgetValue,
//         };
//         this.pageId = this.newPage.id.toString();
//     }

//     setGroups(previewMode, widgetValue, params) {
//         this.groupIDs = JSON.parse(widgetValue).map(group => group.id);
//     }
//     createGroup(previewMode, widgetValue, params) {
//         if (!widgetValue) {
//             return;
//         }
//         const existing = Object.values(this.allGroupsByID).some(group => {
//             // A group is already existing only if it was already defined (i.e.
//             // id is a number) or if it appears in the current list of groups.
//             return group.name.toLowerCase() === widgetValue.toLowerCase()
//                 && (typeof(group.id) === 'number' || this.groupIDs.includes(group.id));
//         });
//         if (existing) {
//             return;
//         }
//         const newGroupID = uniqueId("new_group_");
//         this.allGroupsByID[newGroupID] = {
//             'id': newGroupID,
//             'name': widgetValue,
//             'display_name': widgetValue,
//         };
//         this.groupIDs.push(newGroupID);
//     }

//     _computeWidgetState(methodName, params) {
//         if (methodName === "renderListItems") {
//             return JSON.stringify(this.listItems);
//         } else if (methodName === "setPageTemplate") {
//             return this.pageId;
//         } else if (methodName === "setGroups") {
//             return JSON.stringify(this.groupIDs.map(id => this.allGroupsByID[id]));
//         }
//         return super._computeWidgetState(...arguments);
//     }
// }
// TODO: @owl-options remove this or include it in some tests?
//registerOption("test_option", {
//    Class: TestOption,
//    template: "web_editor.TestSnippetOption",
//    selector: "section",
//});

const legacyRegistry = {};

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

legacyRegistry.sizing = SnippetOptionWidget.extend({
    displayOverlayOptions: true,

    /**
     * @override
     */
    start: function () {
        const self = this;
        const def = this._super.apply(this, arguments);
        let isMobile = weUtils.isMobileView(this.$target[0]);

        this.$handles = this.$overlay.find('.o_handle');

        let resizeValues = this._getSize();
        this.$handles.on('mousedown', function (ev) {
            const mousedownTime = ev.timeStamp;
            ev.preventDefault();
            isMobile = weUtils.isMobileView(self.$target[0]);

            // First update size values as some element sizes may not have been
            // initialized on option start (hidden slides, etc)
            resizeValues = self._getSize();
            const $handle = $(ev.currentTarget);

            let compass = false;
            let XY = false;
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
            } else if ($handle.hasClass('nw')) {
                compass = 'nw';
                XY = 'YX';
            } else if ($handle.hasClass('ne')) {
                compass = 'ne';
                XY = 'YX';
            } else if ($handle.hasClass('sw')) {
                compass = 'sw';
                XY = 'YX';
            } else if ($handle.hasClass('se')) {
                compass = 'se';
                XY = 'YX';
            }

            // Don't call the normal resize methods if we are in a grid and
            // vice-versa.
            const isGrid = Object.keys(resizeValues).length === 4;
            const isGridHandle = $handle[0].classList.contains('o_grid_handle');
            if (isGrid && !isGridHandle || !isGrid && isGridHandle) {
                return;
            }

            let resizeVal;
            if (compass.length > 1) {
                resizeVal = [resizeValues[compass[0]], resizeValues[compass[1]]];
            } else {
                resizeVal = [resizeValues[compass]];
            }

            if (resizeVal.some(rV => !rV)) {
                return;
            }

            // Locking the mutex during the resize. Started here to avoid
            // empty returns.
            let resizeResolve;
            const prom = new Promise(resolve => resizeResolve = () => resolve());
            self.trigger_up("snippet_edition_request", { exec: () => {
                self.trigger_up("disable_loading_effect");
                return prom;
            }});

            // If we are in grid mode, add a background grid and place it in
            // front of the other elements.
            const rowEl = self.$target[0].parentNode;
            let backgroundGridEl;
            if (rowEl.classList.contains("o_grid_mode") && !isMobile) {
                self.options.wysiwyg.odooEditor.observerUnactive('displayBackgroundGrid');
                backgroundGridEl = gridUtils._addBackgroundGrid(rowEl, 0);
                gridUtils._setElementToMaxZindex(backgroundGridEl, rowEl);
                self.options.wysiwyg.odooEditor.observerActive('displayBackgroundGrid');
            }

            // For loop to handle the cases where it is ne, nw, se or sw. Since
            // there are two directions, we compute for both directions and we
            // store the values in an array.
            const directions = [];
            for (const [i, resize] of resizeVal.entries()) {
                const props = {};
                let current = 0;
                const cssProperty = resize[2];
                const cssPropertyValue = parseInt(self.$target.css(cssProperty));
                resize[0].forEach((val, key) => {
                    if (self.$target.hasClass(val)) {
                        current = key;
                    } else if (resize[1][key] === cssPropertyValue) {
                        current = key;
                    }
                });

                props.resize = resize;
                props.current = current;
                props.begin = current;
                props.beginClass = self.$target.attr('class');
                props.regClass = new RegExp('\\s*' + resize[0][current].replace(/[-]*[0-9]+/, '[-]*[0-9]+'), 'g');
                props.xy = ev['page' + XY[i]];
                props.XY = XY[i];
                props.compass = compass[i];

                directions.push(props);
            }

            self.options.wysiwyg.odooEditor.automaticStepUnactive('resizing');

            const cursor = $handle.css('cursor') + '-important';
            const $iframeWindow = $(this.ownerDocument.defaultView);
            $iframeWindow[0].document.body.classList.add(cursor);
            self.$overlay.removeClass('o_handlers_idle');

            const iframeWindowMouseMove = function (ev) {
                ev.preventDefault();

                let changeTotal = false;
                for (const dir of directions) {
                    // dd is the number of pixels by which the mouse moved,
                    // compared to the initial position of the handle.
                    const dd = ev['page' + dir.XY] - dir.xy + dir.resize[1][dir.begin];
                    const next = dir.current + (dir.current + 1 === dir.resize[1].length ? 0 : 1);
                    const prev = dir.current ? (dir.current - 1) : 0;

                    let change = false;
                    // If the mouse moved to the right/down by at least 2/3 of
                    // the space between the previous and the next steps, the
                    // handle is snapped to the next step and the class is
                    // replaced by the one matching this step.
                    if (dd > (2 * dir.resize[1][next] + dir.resize[1][dir.current]) / 3) {
                        self.$target.attr('class', (self.$target.attr('class') || '').replace(dir.regClass, ''));
                        self.$target.addClass(dir.resize[0][next]);
                        dir.current = next;
                        change = true;
                    }
                    // Same as above but to the left/up.
                    if (prev !== dir.current && dd < (2 * dir.resize[1][prev] + dir.resize[1][dir.current]) / 3) {
                        self.$target.attr('class', (self.$target.attr('class') || '').replace(dir.regClass, ''));
                        self.$target.addClass(dir.resize[0][prev]);
                        dir.current = prev;
                        change = true;
                    }

                    if (change) {
                        self._onResize(dir.compass, dir.beginClass, dir.current);
                    }

                    changeTotal = changeTotal || change;
                }

                if (changeTotal) {
                    self.trigger_up('cover_update');
                    $handle.addClass('o_active');
                }
            };
            const iframeWindowMouseUp = function (ev) {
                $iframeWindow.off("mousemove", iframeWindowMouseMove);
                $iframeWindow.off("mouseup", iframeWindowMouseUp);
                $iframeWindow[0].document.body.classList.remove(cursor);
                self.$overlay.addClass('o_handlers_idle');
                $handle.removeClass('o_active');

                // If we are in grid mode, removes the background grid.
                // Also sync the col-* class with the g-col-* class so the
                // toggle to normal mode and the mobile view are well done.
                if (rowEl.classList.contains("o_grid_mode") && !isMobile) {
                    self.options.wysiwyg.odooEditor.observerUnactive('displayBackgroundGrid');
                    backgroundGridEl.remove();
                    self.options.wysiwyg.odooEditor.observerActive('displayBackgroundGrid');
                    gridUtils._resizeGrid(rowEl);

                    const colClass = [...self.$target[0].classList].find(c => /^col-/.test(c));
                    const gColClass = [...self.$target[0].classList].find(c => /^g-col-/.test(c));
                    self.$target[0].classList.remove(colClass);
                    self.$target[0].classList.add(gColClass.substring(2));
                }

                self.options.wysiwyg.odooEditor.automaticStepActive('resizing');

                // Freeing the mutex once the resizing is done.
                resizeResolve();
                self.trigger_up("enable_loading_effect");

                // Check whether there has been a resizing.
                if (directions.every(dir => dir.begin === dir.current)) {
                    const mouseupTime = ev.timeStamp;
                    // Mouse held duration in milliseconds.
                    const mouseHeldDuration = mouseupTime - mousedownTime;
                    // If no resizing happened and if the mouse was pressed less
                    // than 500 ms, we assume that the user wanted to click on
                    // the element behind the handle.
                    if (mouseHeldDuration < 500) {
                        // Find the first element behind the overlay.
                        const sameCoordinatesEls = self.ownerDocument
                            .elementsFromPoint(ev.pageX, ev.pageY);
                        const toBeClickedEl = sameCoordinatesEls
                            .find(el => !el.closest("#oe_manipulators"));
                        if (toBeClickedEl) {
                            toBeClickedEl.click();
                        }
                    }
                    return;
                }

                setTimeout(function () {
                    self.options.wysiwyg.odooEditor.historyStep();

                    self.trigger_up("snippet_edition_request", { exec: async () => {
                        await new Promise(resolve => {
                            self.trigger_up("snippet_option_update", { onSuccess: () => resolve() });
                        });
                    }});
                }, 0);
            };
            $iframeWindow.on("mousemove", iframeWindowMouseMove);
            $iframeWindow.on("mouseup", iframeWindowMouseUp);
        });

        for (const [key, value] of Object.entries(resizeValues)) {
            this.$handles.filter('.' + key).toggleClass('readonly', !value);
        }
        if (!isMobile && this.$target[0].classList.contains("o_grid_item")) {
            this.$handles.filter('.o_grid_handle').toggleClass('readonly', false);
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        this._updateSizingHandles();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    setTarget: function () {
        this._super(...arguments);
        // TODO master: _onResize should not be called here, need to check if
        // updateUI is called when the target is changed
        this._onResize();
    },
    /**
     * @override
     */
    async updateUIVisibility() {
        await this._super(...arguments);

        const isMobileView = weUtils.isMobileView(this.$target[0]);
        const isGridOn = this.$target[0].classList.contains("o_grid_item");
        const isGrid = !isMobileView && isGridOn;
        if (this.$target[0].parentNode && this.$target[0].parentNode.classList.contains('row')) {
            // Hiding/showing the correct resize handles if we are in grid mode
            // or not.
            for (const handleEl of this.$handles) {
                const isGridHandle = handleEl.classList.contains('o_grid_handle');
                handleEl.classList.toggle('d-none', isGrid ^ isGridHandle);
                // Disabling the vertical resize if we are in mobile view.
                const isVerticalSizing = handleEl.matches('.n, .s');
                handleEl.classList.toggle("readonly", isMobileView && isVerticalSizing && isGridOn);
            }

            // Hiding the move handle in mobile view so we can't drag the
            // columns.
            const moveHandleEl = this.$overlay[0].querySelector('.o_move_handle');
            moveHandleEl.classList.toggle('d-none', isMobileView);

            // Show/hide the buttons to send back/front a grid item.
            const bringFrontBackEls = this.$overlay[0].querySelectorAll('.o_front_back');
            bringFrontBackEls.forEach(button => button.classList.toggle("d-none", !isGrid));
        }
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
        this._updateSizingHandles();
        this._notifyResizeChange();
    },
    /**
     * @private
     */
    _updateSizingHandles: function () {
        var self = this;

        // Adapt the resize handles according to the classes and dimensions
        var resizeValues = this._getSize();
        var $handles = this.$overlay.find('.o_handle');
        for (const [direction, resizeValue] of Object.entries(resizeValues)) {
            var classes = resizeValue[0];
            var values = resizeValue[1];
            var cssProperty = resizeValue[2];

            var $handle = $handles.filter('.' + direction);

            var current = 0;
            var cssPropertyValue = parseInt(self.$target.css(cssProperty));
            classes.forEach((className, key) => {
                if (self.$target.hasClass(className)) {
                    current = key;
                } else if (values[key] === cssPropertyValue) {
                    current = key;
                }
            });

            $handle.toggleClass('o_handle_start', current === 0);
            $handle.toggleClass('o_handle_end', current === classes.length - 1);
        }

        // Adapt the handles to fit top and bottom sizes
        this.$overlay.find('.o_handle:not(.o_grid_handle)').filter(".n, .s").toArray().forEach(handle => {
            var $handle = $(handle);
            var direction = $handle.hasClass('n') ? 'top' : 'bottom';
            $handle.outerHeight(self.$target.css('padding-' + direction));
        });
    },
    /**
     * @override
     */
    async _notifyResizeChange() {
        this.$target.trigger('content_changed');
    },
});

/**
 * Handles the edition of padding-top and padding-bottom.
 */
legacyRegistry['sizing_y'] = legacyRegistry.sizing.extend({

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
legacyRegistry['sizing_x'] = legacyRegistry.sizing.extend({
    /**
     * @override
     */
    onClone: function (options) {
        this._super.apply(this, arguments);
        // Below condition is added to remove offset of target element only
        // and not its children to avoid design alteration of a container/block.
        if (options.isCurrent) {
            const targetClassList = this.$target[0].classList;
            const offsetClasses = [...targetClassList]
                .filter(cls => cls.match(/^offset-(lg-)?([0-9]{1,2})$/));
            targetClassList.remove(...offsetClasses);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getSize: function () {
        const isMobileView = weUtils.isMobileView(this.$target[0]);
        const resolutionModifier = isMobileView ? "" : "lg-";
        var width = this.$target.closest('.row').width();
        var gridE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        var gridW = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
        this.grid = {
            e: [
                gridE.map(v => (`col-${resolutionModifier}${v}`)),
                gridE.map(v => width / 12 * v),
                "width",
            ],
            w: [
                gridW.map(v => (`offset-${resolutionModifier}${v}`)),
                gridW.map(v => width / 12 * v),
                "margin-left",
            ],
        };
        return this.grid;
    },
    /**
     * @override
     */
    _onResize: function (compass, beginClass, current) {
        const targetEl = this.$target[0];
        const isMobileView = weUtils.isMobileView(targetEl);
        const resolutionModifier = isMobileView ? "" : "lg-";

        if (compass === 'w' || compass === 'e') {
            // (?!\S): following char cannot be a non-space character
            const offsetRegex = new RegExp(`(?:^|\\s+)offset-${resolutionModifier}(\\d{1,2})(?!\\S)`);
            const colRegex = new RegExp(`(?:^|\\s+)col-${resolutionModifier}(\\d{1,2})(?!\\S)`);

            const beginOffset = Number(beginClass.match(offsetRegex)?.[1] || 0);

            if (compass === 'w') {
                // don't change the right border position when we change the offset (replace col size)
                const beginCol = Number(beginClass.match(colRegex)?.[1] || 12);
                let offset = Number(this.grid.w[0][current].match(offsetRegex)?.[1] || 0);
                if (offset < 0) {
                    offset = 0;
                }
                let colSize = beginCol - (offset - beginOffset);
                if (colSize <= 0) {
                    colSize = 1;
                    offset = beginOffset + beginCol - 1;
                }
                const offsetColRegex = new RegExp(`${offsetRegex.source}|${colRegex.source}`, "g");
                targetEl.className = targetEl.className.replace(offsetColRegex, "");
                targetEl.classList.add(`col-${resolutionModifier}${colSize > 12 ? 12 : colSize}`);

                if (offset > 0) {
                    targetEl.classList.add(`offset-${resolutionModifier}${offset}`);
                }
                if (isMobileView && offset === 0) {
                    targetEl.classList.remove("offset-lg-0");
                } else if ((isMobileView && offset > 0 &&
                        !targetEl.className.match(/(^|\s+)offset-lg-\d{1,2}(?!\S)/)) ||
                        (!isMobileView && offset === 0 &&
                        targetEl.className.match(/(^|\s+)offset-\d{1,2}(?!\S)/))) {
                    targetEl.classList.add("offset-lg-0");
                }
            } else if (beginOffset > 0) {
                const endCol = Number(this.grid.e[0][current].match(colRegex)?.[1] || 0);
                // Avoids overflowing the grid to the right if the
                // column size + the offset exceeds 12.
                if ((endCol + beginOffset) > 12) {
                    targetEl.className = targetEl.className.replace(colRegex, "");
                    targetEl.classList.add(`col-${resolutionModifier}${12 - beginOffset}`);
                }
            }
        }
        this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    async _notifyResizeChange() {
        this.trigger_up('option_update', {
            optionName: 'StepsConnector',
            name: 'change_column_size',
        });
        this._super.apply(this, arguments);
    },
});

/**
 * Handles the sizing in grid mode: edition of grid-{column|row}-{start|end}.
 */
legacyRegistry['sizing_grid'] = legacyRegistry.sizing.extend({
    /**
     * @override
     */
    _getSize() {
        const rowEl = this.$target.closest('.row')[0];
        const gridProp = gridUtils._getGridProperties(rowEl);

        const rowStart = this.$target[0].style.gridRowStart;
        const rowEnd = parseInt(this.$target[0].style.gridRowEnd);
        const columnStart = this.$target[0].style.gridColumnStart;
        const columnEnd = this.$target[0].style.gridColumnEnd;

        const gridN = [];
        const gridS = [];
        for (let i = 1; i < rowEnd + 12; i++) {
            gridN.push(i);
            gridS.push(i + 1);
        }
        const gridW = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
        const gridE = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13];

        this.grid = {
            n: [gridN.map(v => ('g-height-' + (rowEnd - v))), gridN.map(v => ((gridProp.rowSize + gridProp.rowGap) * (v - 1))), 'grid-row-start'],
            s: [gridS.map(v => ('g-height-' + (v - rowStart))), gridS.map(v => ((gridProp.rowSize + gridProp.rowGap) * (v - 1))), 'grid-row-end'],
            w: [gridW.map(v => ('g-col-lg-' + (columnEnd - v))), gridW.map(v => ((gridProp.columnSize + gridProp.columnGap) * (v - 1))), 'grid-column-start'],
            e: [gridE.map(v => ('g-col-lg-' + (v - columnStart))), gridE.map(v => ((gridProp.columnSize + gridProp.columnGap) * (v - 1))), 'grid-column-end'],
        };

        return this.grid;
    },
    /**
     * @override
     */
    _onResize(compass, beginClass, current) {
        if (compass === 'n') {
            const rowEnd = parseInt(this.$target[0].style.gridRowEnd);
            if (current < 0) {
                this.$target[0].style.gridRowStart = 1;
            } else if (current + 1 >= rowEnd) {
                this.$target[0].style.gridRowStart = rowEnd - 1;
            } else {
                this.$target[0].style.gridRowStart = current + 1;
            }
        } else if (compass === 's') {
            const rowStart = parseInt(this.$target[0].style.gridRowStart);
            const rowEnd = parseInt(this.$target[0].style.gridRowEnd);
            if (current + 2 <= rowStart) {
                this.$target[0].style.gridRowEnd = rowStart + 1;
            } else {
                this.$target[0].style.gridRowEnd = current + 2;
            }

            // Updating the grid height.
            const rowEl = this.$target[0].parentNode;
            const rowCount = parseInt(rowEl.dataset.rowCount);
            const backgroundGridEl = rowEl.querySelector('.o_we_background_grid');
            const backgroundGridRowEnd = parseInt(backgroundGridEl.style.gridRowEnd);
            let rowMove = 0;
            if (this.$target[0].style.gridRowEnd > rowEnd && this.$target[0].style.gridRowEnd > rowCount + 1) {
                rowMove = this.$target[0].style.gridRowEnd - rowEnd;
            } else if (this.$target[0].style.gridRowEnd < rowEnd && this.$target[0].style.gridRowEnd >= rowCount + 1) {
                rowMove = this.$target[0].style.gridRowEnd - rowEnd;
            }
            backgroundGridEl.style.gridRowEnd = backgroundGridRowEnd + rowMove;
        } else if (compass === 'w') {
            const columnEnd = parseInt(this.$target[0].style.gridColumnEnd);
            if (current < 0) {
                this.$target[0].style.gridColumnStart = 1;
            } else if (current + 1 >= columnEnd) {
                this.$target[0].style.gridColumnStart = columnEnd - 1;
            } else {
                this.$target[0].style.gridColumnStart = current + 1;
            }
        } else if (compass === 'e') {
            const columnStart = parseInt(this.$target[0].style.gridColumnStart);
            if (current + 2 > 13) {
                this.$target[0].style.gridColumnEnd = 13;
            } else if (current + 2 <= columnStart) {
                this.$target[0].style.gridColumnEnd = columnStart + 1;
            } else {
                this.$target[0].style.gridColumnEnd = current + 2;
            }
        }

        if (compass === 'n' || compass === 's') {
            const numberRows = this.$target[0].style.gridRowEnd - this.$target[0].style.gridRowStart;
            this.$target.attr('class', this.$target.attr('class').replace(/\s*(g-height-)([0-9-]+)/g, ''));
            this.$target.addClass('g-height-' + numberRows);
        }

        if (compass === 'w' || compass === 'e') {
            const numberColumns = this.$target[0].style.gridColumnEnd - this.$target[0].style.gridColumnStart;
            this.$target.attr('class', this.$target.attr('class').replace(/\s*(g-col-lg-)([0-9-]+)/g, ''));
            this.$target.addClass('g-col-lg-' + numberColumns);
        }
    },
});

/**
 * Controls box properties.
 */
legacyRegistry.Box = SnippetOptionWidget.extend({

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



export class LayoutColumn extends ColumnLayoutMixin(SnippetOption) {
    /**
     * @override
     */
    cleanUI() {
        this._removeGridPreview();
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the number of columns.
     *
     * @see this.selectClass for parameters
     */
    async selectCount(previewMode, widgetValue, params) {
        // Make sure the "Custom" option is read-only.
        if (widgetValue === "custom") {
            return;
        }
        const previousNbColumns = this.$('> .row').children().length;
        let $row = this.$('> .row');
        if (!$row.length) {
            const restoreCursor = preserveCursor(this.$target[0].ownerDocument);
            resetOuids(this.$target[0]);
            $row = this.$target.contents().wrapAll($('<div class="row"><div class="col-lg-12"/></div>')).parent().parent();
            restoreCursor();
        }

        const nbColumns = parseInt(widgetValue);
        await this._updateColumnCount($row[0], (nbColumns || 1));
        // Yield UI thread to wait for event to bubble before activate_snippet is called.
        // In this case this lets the select handle the click event before we switch snippet.
        // TODO: make this more generic in activate_snippet event handler.
        await new Promise(resolve => setTimeout(resolve));
        if (nbColumns === 0) {
            const restoreCursor = preserveCursor(this.$target[0].ownerDocument);
            resetOuids($row[0]);
            $row.contents().unwrap().contents().unwrap();
            restoreCursor();
            this.env.activateSnippet(this.$target);
        } else if (previousNbColumns === 0) {
            this.env.activateSnippet(this.$('> .row').children().first());
        }
        // TODO: @owl-options
        // this.trigger_up('option_update', {
        //     optionName: 'StepsConnector',
        //     name: 'change_columns',
        // });
    }
    /**
     * Changes the layout (columns or grid).
     *
     * @see this.selectClass for parameters
     */
    async selectLayout(previewMode, widgetValue, params) {
        if (widgetValue === "grid") {
            const rowEl = this.$target[0].querySelector('.row');
            if (!rowEl || !rowEl.classList.contains('o_grid_mode')) { // Prevent toggling grid mode twice.
                gridUtils._toggleGridMode(this.$target[0]);
                this.env.activateSnippet(this.$target);
            }
        } else {
            // Toggle normal mode only if grid mode was activated (as it's in
            // normal mode by default).
            const rowEl = this.$target[0].querySelector('.row');
            if (rowEl && rowEl.classList.contains('o_grid_mode')) {
                this._toggleNormalMode(rowEl);
                this.env.activateSnippet(this.$target);
            }
        }
        // TODO: @owl-options
        // this.trigger_up('option_update', {
        //     optionName: 'StepsConnector',
        //     name: 'change_columns',
        // });
    }
    /**
     * Adds an image, some text or a button in the grid.
     *
     * @see this.selectClass for parameters
     */
    async addElement(previewMode, widgetValue, params) {
        const rowEl = this.$target[0].querySelector('.row');
        const elementType = widgetValue;

        // If it has been less than 15 seconds that we have added an element,
        // shift the new element right and down by one cell. Otherwise, put it
        // on the top left corner.
        const currentTime = new Date().getTime();
        if (this.lastAddTime && (currentTime - this.lastAddTime) / 1000 < 15) {
            this.lastStartPosition = [this.lastStartPosition[0] + 1, this.lastStartPosition[1] + 1];
        } else {
            this.lastStartPosition = [1, 1]; // [rowStart, columnStart]
        }
        this.lastAddTime = currentTime;

        // Create the new column.
        const newColumnEl = document.createElement('div');
        newColumnEl.classList.add('o_grid_item');
        let numberColumns, numberRows;
        let imageLoadedPromise;

        if (elementType === 'image') {
            // Set the columns properties.
            newColumnEl.classList.add('col-lg-6', 'g-col-lg-6', 'g-height-6', 'o_grid_item_image');
            numberColumns = 6;
            numberRows = 6;

            // Choose an image with the media dialog.
            let isImageSaved = false;
            await new Promise(resolve => {
                this.env.services.dialog.add(MediaDialog, {
                    onlyImages: true,
                    save: imageEl => {
                        isImageSaved = true;
                        imageLoadedPromise = new Promise(resolve => {
                            imageEl.addEventListener("load", () => resolve(), {once: true});
                        });
                        // Adds the image to the new column.
                        newColumnEl.appendChild(imageEl);
                    },
                }, {
                    onClose: () => resolve()
                });
            });
            if (!isImageSaved) {
                // Revert the current step to exclude the step saved when the
                // media dialog closed.
                this.options.wysiwyg.odooEditor.historyRevertCurrentStep();
                return;
            }
        } else if (elementType === 'text') {
            newColumnEl.classList.add('col-lg-4', 'g-col-lg-4', 'g-height-2');
            numberColumns = 4;
            numberRows = 2;

            // Create default text content.
            const pEl = document.createElement('p');
            pEl.classList.add('o_default_snippet_text');
            pEl.textContent = _t("Write something...");

            newColumnEl.appendChild(pEl);
        } else if (elementType === 'button') {
            newColumnEl.classList.add('col-lg-2', 'g-col-lg-2', 'g-height-1');
            numberColumns = 2;
            numberRows = 1;

            // Create default button.
            const aEl = document.createElement('a');
            aEl.href = '#';
            aEl.classList.add('mb-2', 'btn', 'btn-primary');
            aEl.textContent = "Button";

            newColumnEl.appendChild(aEl);
        }
        // Place the column in the grid.
        const rowStart = this.lastStartPosition[0];
        let columnStart = this.lastStartPosition[1];
        if (columnStart + numberColumns > 13) {
            columnStart = 1;
            this.lastStartPosition[1] = columnStart;
        }
        newColumnEl.style.gridArea = `${rowStart} / ${columnStart} / ${rowStart + numberRows} / ${columnStart + numberColumns}`;

        // Setting the z-index to the maximum of the grid.
        gridUtils._setElementToMaxZindex(newColumnEl, rowEl);

        // Add the new column and update the grid height.
        rowEl.appendChild(newColumnEl);
        gridUtils._resizeGrid(rowEl);

        // Scroll to the new column if more than half of it is hidden (= out of
        // the viewport or hidden by an other element).
        if (elementType === "image") {
            // If an image was added, wait for it to be loaded before scrolling.
            await imageLoadedPromise;
        }
        const newColumnPosition = newColumnEl.getBoundingClientRect();
        const middleX = (newColumnPosition.left + newColumnPosition.right) / 2;
        const middleY = (newColumnPosition.top + newColumnPosition.bottom) / 2;
        const sameCoordinatesEl = this.ownerDocument.elementFromPoint(middleX, middleY);
        if (!sameCoordinatesEl || !newColumnEl.contains(sameCoordinatesEl)) {
            newColumnEl.scrollIntoView({behavior: "smooth", block: "center"});
        }
        this.env.activateSnippet($(newColumnEl));
    }
    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        await super.selectStyle(previewMode, widgetValue, params);

        const rowEl = this.$target[0];
        const isMobileView = weUtils.isMobileView(rowEl);
        if (["row-gap", "column-gap"].includes(params.cssProperty) && !isMobileView) {
            // Reset the animation.
            this._removeGridPreview();
            void rowEl.offsetWidth; // Trigger a DOM reflow.

            // Add an animated grid preview.
            this.options.wysiwyg.odooEditor.observerUnactive("addGridPreview");
            this.gridPreviewEl = gridUtils._addBackgroundGrid(rowEl, 0);
            this.gridPreviewEl.classList.add("o_we_grid_preview");
            gridUtils._setElementToMaxZindex(this.gridPreviewEl, rowEl);
            this.options.wysiwyg.odooEditor.observerActive("addGridPreview");
            this.removeGridPreview = this._removeGridPreview.bind(this);
            rowEl.addEventListener("animationend", this.removeGridPreview);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'selectCount') {
            const isMobile = this._isMobile();
            const columnEls = this.$target[0].querySelector(":scope > .row")?.children;
            return this._getNbColumns(columnEls, isMobile);
        } else if (methodName === 'selectLayout') {
            const rowEl = this.$target[0].querySelector('.row');
            if (rowEl && rowEl.classList.contains('o_grid_mode')) {
                return "grid";
            } else {
                return 'normal';
            }
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'zero_cols_opt') {
            // Note: "s_allow_columns" indicates containers which may have
            // bare content (without columns) and are allowed to have columns.
            // By extension, we only show the "None" option on elements that
            // were marked as such as they were allowed to have bare content in
            // the first place.
            return this.$target.is('.s_allow_columns');
        } else if (widgetName === "column_count_opt") {
            // Hide the selectCount widget if the `s_nb_column_fixed` class is
            // on the row.
            return !this.$target[0].querySelector(":scope > .row.s_nb_column_fixed");
        } else if (widgetName === "custom_cols_opt") {
            // Show "Custom" if the user altered the columns in some way (i.e.
            // by adding offsets or resizing a column). This is only shown as
            // an indication, but shouldn't be selectable.
            const isMobile = this._isMobile();
            return this.$target[0].querySelector(":scope > .row") &&
                this._areColsCustomized(this.$target[0].querySelector(":scope > .row").children,
                isMobile);
        }
        return super._computeVisibility(...arguments);
    }
    /**
     * If the number of columns requested is greater than the number of items,
     * adds new columns which are clones of the last one. If there are less
     * columns than the number of items, reorganizes the elements on the right
     * amount of rows.
     *
     * @private
     * @param {HTMLElement} rowEl - the row in which to update the columns
     * @param {integer} nbColumns - the number of columns requested
     */
    async _updateColumnCount(rowEl, nbColumns) {
        const isMobile = this._isMobile();
        // The number of elements per row before the update.
        const prevNbColumns = this._getNbColumns(rowEl.children, isMobile);

        if (nbColumns === prevNbColumns) {
            return;
        }
        this._resizeColumns(rowEl.children, nbColumns);

        const itemsDelta = nbColumns - rowEl.children.length;
        if (itemsDelta > 0) {
            const newItems = [];
            for (let i = 0; i < itemsDelta; i++) {
                const lastEl = rowEl.lastElementChild;
                newItems.push(new Promise(resolve => {
                    this.env.cloneSnippet($(lastEl)).then(resolve);
                }));
            }
            await Promise.all(newItems);
        }

        this.callbacks.cover();
    }
    /**
     * Resizes the columns for the mobile or desktop view.
     *
     * @private
     * @param {HTMLCollection} columnEls - the elements to resize
     * @param {integer} nbColumns - the number of wanted columns
     */
    _resizeColumns(columnEls, nbColumns) {
        const isMobile = this._isMobile();
        const itemSize = Math.floor(12 / nbColumns) || 1;
        const firstItem = this._getFirstItem(columnEls, isMobile);
        const firstItemOffset = Math.floor((12 - itemSize * nbColumns) / 2);

        const resolutionModifier = isMobile ? "" : "-lg";
        const replacingRegex =
            // (?!\S): following char cannot be a non-space character
            new RegExp(`(?:^|\\s+)(col|offset)${resolutionModifier}(-\\d{1,2})?(?!\\S)`, "g");

        for (const columnEl of columnEls) {
            columnEl.className = columnEl.className.replace(replacingRegex, "");
            columnEl.classList.add(`col${resolutionModifier}-${itemSize}`);

            if (firstItemOffset && columnEl === firstItem) {
                columnEl.classList.add(`offset${resolutionModifier}-${firstItemOffset}`);
            }
            const hasMobileOffset = columnEl.className.match(/(^|\s+)offset-\d{1,2}(?!\S)/);
            const hasDesktopOffset = columnEl.className.match(/(^|\s+)offset-lg-[1-9][0-1]?(?!\S)/);
            columnEl.classList.toggle("offset-lg-0", hasMobileOffset && !hasDesktopOffset);
        }
    }
    /**
     * Toggles the normal mode.
     *
     * @private
     * @param {Element} rowEl
     */
    async _toggleNormalMode(rowEl) {
        // Removing the grid class
        rowEl.classList.remove('o_grid_mode');
        const columnEls = rowEl.children;
        // Removing the grid previews (if any).
        await this.env.cleanUI(this.$target[0].closest("section"))

        for (const columnEl of columnEls) {
            // Reloading the images.
            gridUtils._reloadLazyImages(columnEl);
            // Removing the grid properties.
            gridUtils._convertToNormalColumn(columnEl);
        }
        // Removing the grid properties.
        delete rowEl.dataset.rowCount;
        // Kept for compatibility.
        rowEl.style.removeProperty('--grid-item-padding-x');
        rowEl.style.removeProperty('--grid-item-padding-y');
        rowEl.style.removeProperty("gap");
    }
    /**
     * Removes the grid preview that was added when changing the grid gaps.
     *
     * @private
     */
    _removeGridPreview() {
        this.options.wysiwyg.odooEditor.observerUnactive("removeGridPreview");
        this.$target[0].removeEventListener("animationend", this.removeGridPreview);
        if (this.gridPreviewEl) {
            this.gridPreviewEl.remove();
            delete this.gridPreviewEl;
        }
        delete this.removeGridPreview;
        this.options.wysiwyg.odooEditor.observerActive("removeGridPreview");
    }
    /**
     * @returns {boolean}
     */
    _isMobile() {
        return weUtils.isMobileView(this.$target[0]);
    }
}

legacyRegistry.GridColumns = SnippetOptionWidget.extend({
    /**
     * @override
     */
    cleanUI() {
        // Remove the padding highlights.
        this._removePaddingPreview();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectStyle(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (["--grid-item-padding-y", "--grid-item-padding-x"].includes(params.cssProperty)) {
            // Reset the animation.
            this._removePaddingPreview();
            void this.$target[0].offsetWidth; // Trigger a DOM reflow.

            // Highlight the padding when changing it, by adding a pseudo-
            // element with an animated colored border inside the grid item.
            this.options.wysiwyg.odooEditor.observerUnactive("addPaddingPreview");
            this.$target[0].classList.add("o_we_padding_highlight");
            this.options.wysiwyg.odooEditor.observerActive("addPaddingPreview");
            this.removePaddingPreview = this._removePaddingPreview.bind(this);
            this.$target[0].addEventListener("animationend", this.removePaddingPreview);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (["grid_padding_y_opt", "grid_padding_x_opt"].includes(widgetName)) {
            return this.$target[0].parentElement.classList.contains("o_grid_mode");
        }
        return this._super(...arguments);
    },
    /**
     * Removes the padding highlights that were added when changing the grid
     * item padding.
     *
     * @private
     */
    _removePaddingPreview() {
        this.options.wysiwyg.odooEditor.observerUnactive("removePaddingPreview");
        this.$target[0].removeEventListener("animationend", this.removePaddingPreview);
        this.$target[0].classList.remove("o_we_padding_highlight");
        delete this.removePaddingPreview;
        this.options.wysiwyg.odooEditor.observerActive("removePaddingPreview");
    },
});

legacyRegistry.vAlignment = SnippetOptionWidget.extend({
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const value = await this._super(...arguments);
        if (methodName === 'selectClass' && !value) {
            // If there is no `align-items-` class on the row, then the `align-
            // items-stretch` class is selected, because the behaviors are
            // equivalent in both situations.
            return 'align-items-stretch';
        }
        return value;
    },
});

/**
 * Allows snippets to be moved before the preceding element or after the following.
 */
legacyRegistry.SnippetMove = SnippetOptionWidget.extend(ColumnLayoutUtils, {
    displayOverlayOptions: true,

    /**
     * @override
     */
    start: function () {
        var $buttons = this.$el.find('we-button');
        var $overlayArea = this.$overlay.find('.o_overlay_move_options');
        // Putting the arrows side by side.
        $overlayArea.prepend($buttons[1]);
        $overlayArea.prepend($buttons[0]);

        // Needed for compatibility (with already dropped snippets).
        // If the target is a column, check if all the columns are either mobile
        // ordered or not. If they are not consistent, then we remove the mobile
        // order classes from all of them, to avoid issues.
        const parentEl = this.$target[0].parentElement;
        if (parentEl.classList.contains("row")) {
            const columnEls = [...parentEl.children];
            const orderedColumnEls = columnEls.filter(el => el.style.order);
            if (orderedColumnEls.length && orderedColumnEls.length !== columnEls.length) {
                this._removeMobileOrders(orderedColumnEls);
            }
        }

        return this._super(...arguments);
    },
    /**
     * @override
     */
    onClone(options) {
        this._super.apply(this, arguments);
        const mobileOrder = this.$target[0].style.order;
        // If the order has been adapted on mobile, it must be different
        // for each clone.
        if (options.isCurrent && mobileOrder) {
            const siblingEls = this.$target[0].parentElement.children;
            const cloneEls = [...siblingEls].filter(el => el.style.order === mobileOrder);
            // For cases in which multiple clones are made at the same time, we
            // change the order for all clones at once. (e.g.: it happens when
            // increasing the columns count.) This makes sure the clones get a
            // mobile order in line with their DOM order.
            cloneEls.forEach((el, i) => {
                if (i > 0) {
                    el.style.order = siblingEls.length - cloneEls.length + i;
                }
            });
        }
    },
    /**
     * @override
     */
    onMove() {
        this._super.apply(this, arguments);
        // Remove all the mobile order classes after a drag and drop.
        this._removeMobileOrders(this.$target[0].parentElement.children);
    },
    /**
     * @override
     */
    onRemove() {
        this._super.apply(this, arguments);
        const targetMobileOrder = this.$target[0].style.order;
        // If the order has been adapted on mobile, the gap created by the
        // removed snippet must be filled in.
        if (targetMobileOrder) {
            const targetOrder = parseInt(targetMobileOrder);
            this._fillRemovedItemGap(this.$target[0].parentElement, targetOrder);
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
        const isMobile = this._isMobile();
        const isNavItem = this.$target[0].classList.contains('nav-item');
        const $tabPane = isNavItem ? $(this.$target.find('.nav-link')[0].hash) : null;
        const moveLeftOrRight = ["move_left_opt", "move_right_opt"].includes(params.name);

        let siblingEls, mobileOrder;
        if (moveLeftOrRight) {
            siblingEls = this.$target[0].parentElement.children;
            mobileOrder = !!this.$target[0].style.order;
        }
        if (moveLeftOrRight && isMobile && !isNavItem) {
            if (!mobileOrder) {
                this._addMobileOrders(siblingEls);
            }
            this._swapMobileOrders(widgetValue, siblingEls);
        } else {
            switch (widgetValue) {
                case "prev": {
                    // Consider only visible elements.
                    let prevEl = this.$target[0].previousElementSibling;
                    while (prevEl && window.getComputedStyle(prevEl).display === "none") {
                        prevEl = prevEl.previousElementSibling;
                    }
                    prevEl?.insertAdjacentElement("beforebegin", this.$target[0]);
                    if (isNavItem) {
                        $tabPane.prev().before($tabPane);
                    }
                    break;
                }
                case "next": {
                    // Consider only visible elements.
                    let nextEl = this.$target[0].nextElementSibling;
                    while (nextEl && window.getComputedStyle(nextEl).display === "none") {
                        nextEl = nextEl.nextElementSibling;
                    }
                    nextEl?.insertAdjacentElement("afterend", this.$target[0]);
                    if (isNavItem) {
                        $tabPane.next().after($tabPane);
                    }
                    break;
                }
            }
            if (mobileOrder) {
                this._removeMobileOrders(siblingEls);
            }
        }
        if (!this.$target.is(this.data.noScroll)
                && (params.name === 'move_up_opt' || params.name === 'move_down_opt')) {
            const mainScrollingEl = $().getScrollingElement()[0];
            const elTop = this.$target[0].getBoundingClientRect().top;
            const heightDiff = mainScrollingEl.offsetHeight - this.$target[0].offsetHeight;
            const bottomHidden = heightDiff < elTop;
            const hidden = elTop < 0 || bottomHidden;
            if (hidden) {
                scrollTo(this.$target[0], {
                    extraOffset: 50,
                    forcedOffset: bottomHidden ? heightDiff - 50 : undefined,
                    easing: 'linear',
                    duration: 500,
                });
            }
        }
        this.trigger_up('option_update', {
            optionName: 'StepsConnector',
            name: 'move_snippet',
        });
        // Update the "Invisible Elements" panel as the order of invisible
        // snippets could have changed on the page.
        this.trigger_up("update_invisible_dom");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        const moveUpOrLeft = widgetName === "move_up_opt" || widgetName === "move_left_opt";
        const moveDownOrRight = widgetName === "move_down_opt" || widgetName === "move_right_opt";
        const moveLeftOrRight = widgetName === "move_left_opt" || widgetName === "move_right_opt";

        if (moveUpOrLeft || moveDownOrRight) {
            // The arrows are not displayed if the target is in a grid and if
            // not in mobile view.
            const isMobileView = weUtils.isMobileView(this.$target[0]);
            if (!isMobileView && this.$target[0].classList.contains("o_grid_item")) {
                return false;
            }
            // On mobile, items' reordering is independent from desktop inside
            // a snippet (left or right), not at a higher level (up or down).
            if (moveLeftOrRight && isMobileView) {
                const targetMobileOrder = this.$target[0].style.order;
                if (targetMobileOrder) {
                    const siblingEls = this.$target[0].parentElement.children;
                    const orderModifier = widgetName === "move_left_opt" ? -1 : 1;
                    let delta = 0;
                    while (true) {
                        delta += orderModifier;
                        const nextOrder = parseInt(targetMobileOrder) + delta;
                        const siblingEl = [...siblingEls].find(el => el.style.order === nextOrder.toString());
                        if (!siblingEl) {
                            break;
                        }
                        if (window.getComputedStyle(siblingEl).display === "none") {
                            continue;
                        }
                        return true;
                    }
                    return false;
                }
            }
            // Consider only visible elements.
            const direction = moveUpOrLeft ? "previousElementSibling" : "nextElementSibling";
            let siblingEl = this.$target[0][direction];
            while (siblingEl && window.getComputedStyle(siblingEl).display === "none") {
                siblingEl = siblingEl[direction];
            }
            return !!siblingEl;
        }
        return this._super(...arguments);
    },
    /**
     * Swaps the mobile orders.
     *
     * @param {string} widgetValue
     * @param {HTMLCollection} siblingEls
     */
    _swapMobileOrders(widgetValue, siblingEls) {
        const targetMobileOrder = this.$target[0].style.order;
        const orderModifier = widgetValue === "prev" ? -1 : 1;
        let delta = 0;
        while (true) {
            delta += orderModifier;
            const newOrder = parseInt(targetMobileOrder) + delta;
            const comparedEl = [...siblingEls].find(el => el.style.order === newOrder.toString());
            if (window.getComputedStyle(comparedEl).display === "none") {
                continue;
            }
            this.$target[0].style.order = newOrder;
            comparedEl.style.order = targetMobileOrder;
            break;
        }
    },
    /**
     * @returns {Boolean}
     */
    _isMobile() {
        return false;
    },
});

/**
 * Allows for media to be replaced.
 */
legacyRegistry.ReplaceMedia = SnippetOptionWidget.extend({
    init: function () {
        this._super(...arguments);
        this._activateLinkTool = this._activateLinkTool.bind(this);
        this._deactivateLinkTool = this._deactivateLinkTool.bind(this);
    },

    /**
     * @override
     */
    onFocus() {
        this.options.wysiwyg.odooEditor.addEventListener('activate_image_link_tool', this._activateLinkTool);
        this.options.wysiwyg.odooEditor.addEventListener('deactivate_image_link_tool', this._deactivateLinkTool);
        // When we start editing an image, rerender the UI to ensure the
        // we-select that suggests the anchors is in a consistent state.
        this.rerender = true;
    },
    /**
     * @override
     */
    onBlur() {
        this.options.wysiwyg.odooEditor.removeEventListener('activate_image_link_tool', this._activateLinkTool);
        this.options.wysiwyg.odooEditor.removeEventListener('deactivate_image_link_tool', this._deactivateLinkTool);
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
        // open mediaDialog and replace the media.
        await this.options.wysiwyg.openMediaDialog({ node:this.$target[0] });
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
            // TODO Remove when bug fixed in Chrome.
            if (this.$target[0].getBoundingClientRect().width === 0) {
                // Chrome lost lazy-loaded image => Force Chrome to display image.
                const src = this.$target[0].src;
                this.$target[0].src = '';
                this.$target[0].src = src;
            }
        } else {
            const fragment = document.createDocumentFragment();
            fragment.append(...parentEl.childNodes);
            parentEl.replaceWith(fragment);
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
            this.$target.trigger('href_changed');
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
        this.$target.trigger('href_changed');
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
     * @private
     */
    _deactivateLinkTool() {
        const parentEl = this.$target[0].parentNode;
        if (parentEl.tagName === 'A') {
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
export class ImageHandlerOption extends SnippetOption {
    /**
     * @override
     */
    async willStart() {
        await this._initializeImage();
        return super.willStart(...arguments);
    }
    /**
     * @override
     *
     */
    async start() {
        // TODO: @owl-options This is currently not called
        await this._super(...arguments);
        // Perform the loading of the image info synchronously in order to
        // avoid an intermediate rendering of the Blocks tab during the
        // loadImageInfo RPC that obtains the file size.
        // This does not update the target.
        await this._applyOptions(false);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        await super.updateUI(...arguments);

        if (this._filesize === undefined) {
            await this._applyOptions(false);
        }

        this._relocateWeightEl();
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    selectFormat(previewMode, widgetValue, params) {
        const values = widgetValue.split(' ');
        const image = this._getImg();
        image.dataset.resizeWidth = values[0];
        if (image.dataset.shape) {
            // If the image has a shape, modify its originalMimetype attribute.
            image.dataset.originalMimetype = values[1];
        } else {
            // If the image does not have a shape, modify its mimetype
            // attribute.
            image.dataset.mimetype = values[1];
        }
        return this._applyOptions();
    }
    /**
     * @see this.selectClass for parameters
     */
    async setQuality(previewMode, widgetValue, params) {
        if (previewMode) {
            return;
        }
        this._getImg().dataset.quality = widgetValue;
        return this._applyOptions();
    }
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
    }
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
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeVisibility() {
        const src = this._getImg().getAttribute('src');
        return src && src !== '/';
    }
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
            case 'selectFormat':
                return img.naturalWidth + ' ' + this._getImageMimetype(img);
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
        return super._computeWidgetState(...arguments);
    }
    /**
     * @abstract
     */
    _relocateWeightEl() {}
    /**
     * @override
     */
    async _getRenderContext() {
        const context = await super._getRenderContext();
        const img = this._getImg();
        if (!this.originalSrc || !this._isImageSupportedForProcessing(img)) {
            return context;
        }
        context.availableFormats = await this._computeAvailableFormats();
        context.noQuality = !['image/jpeg', 'image/webp'].includes(this._getImageMimetype(img));

        return context;
    }
    /**
     * Returns a list of valid formats for a given image or an empty list if
     * there is no mimetypeBeforeConversion data attribute on the image.
     *
     * @private
     */
    async _computeAvailableFormats() {
        if (!this.mimetypeBeforeConversion) {
            return [];
        }
        const img = this._getImg();
        const original = await loadImage(this.originalSrc);
        const maxWidth = img.dataset.width ? img.naturalWidth : original.naturalWidth;
        const optimizedWidth = Math.min(maxWidth, this._computeMaxDisplayWidth());
        this.optimizedWidth = optimizedWidth;
        const widths = {
            128: ['128px', 'image/webp'],
            256: ['256px', 'image/webp'],
            512: ['512px', 'image/webp'],
            1024: ['1024px', 'image/webp'],
            1920: ['1920px', 'image/webp'],
        };
        widths[img.naturalWidth] = [_t("%spx", img.naturalWidth), 'image/webp'];
        widths[optimizedWidth] = [_t("%spx (Suggested)", optimizedWidth), 'image/webp'];
        const mimetypeBeforeConversion = img.dataset.mimetypeBeforeConversion;
        widths[maxWidth] = [_t("%spx (Original)", maxWidth), mimetypeBeforeConversion];
        if (mimetypeBeforeConversion !== "image/webp") {
            // Avoid a key collision by subtracting 0.1 - putting the webp
            // above the original format one of the same size.
            widths[maxWidth - 0.1] = [_t("%spx", maxWidth), 'image/webp'];
        }
        return Object.entries(widths)
            .filter(([width]) => width <= maxWidth)
            .sort(([v1], [v2]) => v1 - v2);
    }
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
        // Do not apply modifications if there is no original src, since it is
        // needed for it.
        if (!img.dataset.originalSrc) {
            delete img.dataset.mimetype;
            return;
        }
        const dataURL = await applyModifications(img, {mimetype: this._getImageMimetype(img)});
        this._filesize = getDataURLBinarySize(dataURL) / 1024;

        if (update) {
            img.classList.add('o_modified_image_to_save');
            const loadedImg = await loadImage(dataURL, img);
            this._applyImage(loadedImg);
            // Also apply to carousel thumbnail if applicable.
            weUtils.forwardToThumbnail(img);
            return loadedImg;
        }
        return img;
    }
    /**
     * Loads the image's attachment info.
     *
     * @private
     */
    async _loadImageInfo(attachmentSrc = '') {
        const img = this._getImg();
        await loadImageInfo(img, attachmentSrc);
        if (!img.dataset.originalId) {
            this.originalId = null;
            this.originalSrc = null;
            return;
        }
        this.originalId = img.dataset.originalId;
        this.originalSrc = img.dataset.originalSrc;
        this.mimetypeBeforeConversion = img.dataset.mimetypeBeforeConversion;
    }
    /**
     * Sets the image's width to its suggested size.
     *
     * @private
     */
    async _autoOptimizeImage() {
        await this._loadImageInfo();
        const newContext = await this._getRenderContext();
        Object.assign(this.renderContext, newContext);
        const img = this._getImg();
        if (!['image/gif', 'image/svg+xml'].includes(img.dataset.mimetype)) {
            // Convert to recommended format and width.
            img.dataset.mimetype = 'image/webp';
            img.dataset.resizeWidth = this.optimizedWidth;
        } else if (img.dataset.shape && img.dataset.originalMimetype !== "image/gif") {
            img.dataset.originalMimetype = "image/webp";
            img.dataset.resizeWidth = this.optimizedWidth;
        }
        await this._applyOptions();
        await this.updateUI();
    }
    /**
     * Returns the image that is currently being modified.
     *
     * @private
     * @abstract
     * @returns {HTMLImageElement} the image to use for modifications
     */
    _getImg() {}
    /**
     * Computes the image's maximum display width.
     *
     * @private
     * @abstract
     * @returns {Int} the maximum width at which the image can be displayed
     */
    _computeMaxDisplayWidth() {}
    /**
     * Use the processed image when it's needed in the DOM.
     *
     * @private
     * @abstract
     * @param {HTMLImageElement} img
     */
    _applyImage(img) {}
    /**
     * @private
     * @param {HTMLImageElement} img
     * @returns {String} The right mimetype used to apply options on image.
     */
    _getImageMimetype(img) {
        return img.dataset.mimetype;
    }
    /**
     * @private
     */
    async _initializeImage() {
        return this._loadImageInfo();
    }
     /**
     * @private
     * @param {HTMLImageElement} img
     * @param {Boolean} [strict=false]
     * @returns {Boolean}
     */
    _isImageSupportedForProcessing(img, strict = false) {
        return isImageSupportedForProcessing(this._getImageMimetype(img), strict);
    }
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === "format_select_opt" && !this.mimetypeBeforeConversion) {
            return false;
        }
        if (this._isImageProcessingWidget(widgetName, params)) {
            const img = this._getImg();
            return this._isImageSupportedForProcessing(img, true);
        }
        return isImageSupportedForStyle(this._getImg());
    }
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
            || widgetName === 'format_select_opt';
    }
}

/**
 * @param {Element} containerEl
 * @param {boolean} labelIsDimension - Optional display imgsize attribute instead of animated
 * @returns {Element}
 */
const _addAnimatedShapeLabel = function addAnimatedShapeLabel(containerEl, labelIsDimension = false) {
    const labelEl = document.createElement('span');
    labelEl.classList.add('o_we_shape_animated_label');
    let labelStr = _t("Animated");
    const spanEl = document.createElement('span');
    if (labelIsDimension) {
        const dimensionIcon = document.createElement('i');
        labelStr = containerEl.dataset.imgSize;
        dimensionIcon.classList.add('fa', 'fa-expand');
        labelEl.append(dimensionIcon);
        spanEl.textContent = labelStr;
    } else {
        labelEl.textContent = labelStr[0];
        spanEl.textContent = labelStr.substr(1);
    }
    labelEl.appendChild(spanEl);
    containerEl.classList.add('position-relative');
    containerEl.appendChild(labelEl);
    return labelEl;
};

/**
 * Controls image width and quality.
 */

legacyRegistry.ImageTools = {
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
     * Toggles the ratio of the image between 0:0 (no crop) and 1:1, in order to
     * make it appear squared when needed (with `data-unstretch=true` shapes).
     *
     * @see this.selectClass for parameters
     */
    async removeStretch(previewMode, widgetValue, params) {
        this.options.wysiwyg.odooEditor.historyPauseSteps();
        this.trigger_up("disable_loading_effect");
        // Preserve the cursor to be able to replace the image afterwards.
        const restoreCursor = preserveCursor(this.$target[0].ownerDocument);
        const img = this._getImg();
        const document = this.el.ownerDocument;
        const imageCropWrapperElement = document.createElement("div");
        imageCropWrapperElement.classList.add("d-none"); // Hiding the cropper.
        document.body.append(imageCropWrapperElement);
        const imageCropWrapper = await attachComponent(this, imageCropWrapperElement, ImageCrop, {
            activeOnStart: true,
            media: img,
            mimetype: this._getImageMimetype(img),
        });
        await imageCropWrapper.component.mountedPromise;
        if (widgetValue) {
            await imageCropWrapper.component.reset();
        } else {
            await imageCropWrapper.component.cropSquare(false);
            if (isGif(this._getImageMimetype(img))) {
                img.dataset[img.dataset.shape ? "originalMimetype" : "mimetype"] = "image/png";
            }
        }
        await this._reapplyCurrentShape();
        imageCropWrapper.destroy();
        imageCropWrapperElement.remove();
        restoreCursor();
        this.trigger_up("enable_loading_effect");
        if (!widgetValue) {
            this._onImageCropped();
        }
        this.options.wysiwyg.odooEditor.historyUnpauseSteps();
    },
    /**
     * Displays the image cropping tools
     *
     * @see this.selectClass for parameters
     */
    async crop() {
        this.trigger_up('disable_loading_effect');
        const img = this._getImg();
        const document = this.$el[0].ownerDocument;
        const imageCropWrapperElement = document.createElement('div');
        document.body.append(imageCropWrapperElement);
        const imageCropWrapper = await attachComponent(this, imageCropWrapperElement, ImageCrop, {
            activeOnStart: true,
            media: img,
            mimetype: this._getImageMimetype(img),
        });

        await new Promise(resolve => {
            this.$target.one('image_cropper_destroyed', async () => {
                if (isGif(this._getImageMimetype(img))) {
                    img.dataset[img.dataset.shape ? 'originalMimetype' : 'mimetype'] = 'image/png';
                }
                await this._reapplyCurrentShape();
                resolve();
            });
        });
        imageCropWrapperElement.remove();
        imageCropWrapper.destroy();
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
        const destroyTransfo = () => {
            this.$target.transfo('destroy');
            $(document).off('mousedown', mousedown);
            window.document.removeEventListener('keydown', keydown);
        }
        const mousedown = mousedownEvent => {
            if (!$(mousedownEvent.target).closest('.transfo-container').length) {
                destroyTransfo();
                // Restore animation css properties potentially affected by the
                // jQuery transfo plugin.
                this.$target[0].style.animationPlayState = playState;
                this.$target[0].style.transition = transition;
            }
        };
        $(document).on('mousedown', mousedown);
        const keydown = keydownEvent => {
            if (keydownEvent.key === 'Escape') {
                keydownEvent.stopImmediatePropagation();
                destroyTransfo();
            }
        };
        window.document.addEventListener('keydown', keydown);

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

        // Mount the ImageCrop to call the reset method. As we need the state of
        // the component to be mounted before calling reset, mount it
        // temporarily into the body.
        const imageCropWrapperElement = document.createElement('div');
        imageCropWrapperElement.classList.add("d-none"); // Hiding the cropper.
        document.body.append(imageCropWrapperElement);
        const imageCropWrapper = await attachComponent(this, imageCropWrapperElement, ImageCrop, {
            activeOnStart: true,
            media: img,
            mimetype: this._getImageMimetype(img),
        });
        await imageCropWrapper.component.mountedPromise;
        await imageCropWrapper.component.reset();
        imageCropWrapper.destroy();
        imageCropWrapperElement.remove();

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
        this.trigger_up("disable_loading_effect");
        const img = this._getImg();
        let clonedImgEl;

        // If the shape needs the image to be square (1:1 ratio) and if not
        // already the case, crop the image before applying the shape.
        const isCropRequired = params.unstretch;
        if ((isCropRequired && img.dataset.aspectRatio !== "1/1" && previewMode !== "reset")
                || this.hasCroppedPreview) {
            // Preserve the cursor to be able to replace the image afterwards.
            const restoreCursor = preserveCursor(this.$target[0].ownerDocument);
            // Replace the image by its clone to avoid flickering.
            clonedImgEl = img.cloneNode(true);
            img.insertAdjacentElement("afterend", clonedImgEl);
            img.classList.add("d-none");

            const document = this.el.ownerDocument;
            const imageCropWrapperElement = document.createElement("div");
            imageCropWrapperElement.classList.add("d-none"); // Hiding the cropper.
            document.body.append(imageCropWrapperElement);
            const imageCropWrapper = await attachComponent(this, imageCropWrapperElement, ImageCrop, {
                activeOnStart: true,
                media: img,
                mimetype: this._getImageMimetype(img),
            });
            await imageCropWrapper.component.mountedPromise;
            await imageCropWrapper.component.cropSquare(previewMode);
            if (previewMode === false) {
                if (isGif(this._getImageMimetype(img))) {
                    img.dataset[img.dataset.shape ? "originalMimetype" : "mimetype"] = "image/png";
                }
                this.isImageCropped = true;
            }
            await this._reapplyCurrentShape();
            imageCropWrapper.destroy();
            imageCropWrapperElement.remove();

            restoreCursor();

            if (previewMode === true) {
                this.hasCroppedPreview = true;
            } else {
                delete this.hasCroppedPreview;
            }
        }
        // Re-rendering the options after selecting a "cropping" shape.
        if (this.isImageCropped && previewMode === "reset") {
            delete this.isImageCropped;
            this._onImageCropped();
        }

        const saveData = previewMode === false;
        if (img.dataset.hoverEffect && !widgetValue) {
            // When a shape is removed and there is a hover effect on the
            // image, we then place the "Square" shape as the default because a
            // shape is required for the hover effects to work.
            const shapeImgSquareWidget = this._requestUserValueWidgets("shape_img_square_opt")[0];
            widgetValue = shapeImgSquareWidget.getActiveValue("setImgShape");
        }
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
                // When the user selects a shape, we remove the data attributes
                // that are not compatible with this shape.
                if (saveData) {
                    if (!this._isTransformableShape()) {
                        delete img.dataset.shapeFlip;
                        delete img.dataset.shapeRotate;
                    }
                    if (!this._canHaveHoverEffect()) {
                        delete img.dataset.hoverEffect;
                        delete img.dataset.hoverEffectColor;
                        delete img.dataset.hoverEffectStrokeWidth;
                        delete img.dataset.hoverEffectIntensity;
                        img.classList.remove("o_animate_on_hover");
                    }
                    if (!this._isAnimatedShape()) {
                        delete img.dataset.shapeAnimationSpeed;
                    }
                }
            }
        } else {
            // Re-applying the modifications and deleting the shapes
            img.src = await applyModifications(img, {mimetype: this._getImageMimetype(img)});
            delete img.dataset.shape;
            delete img.dataset.shapeColors;
            delete img.dataset.fileName;
            delete img.dataset.shapeFlip;
            delete img.dataset.shapeRotate;
            delete img.dataset.shapeAnimationSpeed;
            if (saveData) {
                img.dataset.mimetype = img.dataset.originalMimetype;
                delete img.dataset.originalMimetype;
            }
            // Also apply to carousel thumbnail if applicable.
            weUtils.forwardToThumbnail(img);
        }
        img.classList.add('o_modified_image_to_save');
        // Remove the image clone, if any.
        if (clonedImgEl) {
            clonedImgEl.remove();
            img.classList.remove("d-none");
        }
        this.trigger_up("enable_loading_effect");
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
    /**
     * Flips the image shape horizontally.
     *
     * @see this.selectClass for parameters
     */
    async setImgShapeFlipX(previewMode, widgetValue, params) {
        await this._setImgShapeFlip("x");
    },
    /**
     * Flips the image shape vertically.
     *
     * @see this.selectClass for parameters
     */
    async setImgShapeFlipY(previewMode, widgetValue, params) {
        await this._setImgShapeFlip("y");
    },
    /**
     * Rotates the image shape 90 degrees to the left.
     *
     * @see this.selectClass for parameters
     */
    async setImgShapeRotateLeft(previewMode, widgetValue, params) {
        await this._setImgShapeRotate(-90);
    },
    /**
     * Rotates the image shape 90 degrees to the right.
     *
     * @see this.selectClass for parameters
     */
    async setImgShapeRotateRight(previewMode, widgetValue, params) {
        await this._setImgShapeRotate(90);
    },
    /**
     * Sets the hover effects of the image shape.
     *
     * @see this.selectClass for parameters
     */
    async setImgShapeHoverEffect(previewMode, widgetValue, params) {
        const imgEl = this._getImg();
        if (previewMode !== "reset") {
            this.prevHoverEffectColor = imgEl.dataset.hoverEffectColor;
            this.prevHoverEffectIntensity = imgEl.dataset.hoverEffectIntensity;
            this.prevHoverEffectStrokeWidth = imgEl.dataset.hoverEffectStrokeWidth;
        }
        delete imgEl.dataset.hoverEffectColor;
        delete imgEl.dataset.hoverEffectIntensity;
        delete imgEl.dataset.hoverEffectStrokeWidth;
        if (previewMode === true) {
            if (params.name === "hover_effect_overlay_opt") {
                imgEl.dataset.hoverEffectColor = this._getCSSColorValue("black-25");
            } else if (params.name === "hover_effect_outline_opt") {
                imgEl.dataset.hoverEffectColor = this._getCSSColorValue("primary");
                imgEl.dataset.hoverEffectStrokeWidth = 10;
            } else {
                imgEl.dataset.hoverEffectIntensity = 20;
                if (params.name !== "hover_effect_mirror_blur_opt") {
                    imgEl.dataset.hoverEffectColor = "rgba(0, 0, 0, 0)";
                }
            }
        } else {
            if (this.prevHoverEffectColor) {
                imgEl.dataset.hoverEffectColor = this.prevHoverEffectColor;
            }
            if (this.prevHoverEffectIntensity) {
                imgEl.dataset.hoverEffectIntensity = this.prevHoverEffectIntensity;
            }
            if (this.prevHoverEffectStrokeWidth) {
                imgEl.dataset.hoverEffectStrokeWidth = this.prevHoverEffectStrokeWidth;
            }
        }
        await this._reapplyCurrentShape();
        // When the hover effects are first activated from the "animationMode"
        // function of the "WebsiteAnimate" class, the history was paused to
        // avoid recording intermediate steps. That's why we unpause it here.
        if (this.firstHoverEffect) {
            this.options.wysiwyg.odooEditor.historyUnpauseSteps();
            delete this.firstHoverEffect;
        }
    },
    /**
     * @see this.selectClass for parameters
     */
    async selectDataAttribute(previewMode, widgetValue, params) {
        await this._super(...arguments);
        if (["shapeAnimationSpeed", "hoverEffectIntensity", "hoverEffectStrokeWidth"].includes(params.attributeName)) {
            await this._reapplyCurrentShape();
        }
    },
    /**
     * Sets the color of hover effects.
     *
     * @see this.selectClass for parameters
     */
    async setHoverEffectColor(previewMode, widgetValue, params) {
        const img = this._getImg();
        let defaultColor = "rgba(0, 0, 0, 0)";
        if (img.dataset.hoverEffect === "overlay") {
            defaultColor = "black-25";
        } else if (img.dataset.hoverEffect === "outline") {
            defaultColor = "primary";
        }
        img.dataset.hoverEffectColor = this._getCSSColorValue(widgetValue || defaultColor);
        await this._reapplyCurrentShape();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name) {
        if (name === "enable_hover_effect") {
            this.trigger_up("snippet_edition_request", {exec: () => {
                // Add the "square" shape to the image if it has no shape
                // because the "hover effects" need a shape to work.
                const imgEl = this._getImg();
                const shapeName = imgEl.dataset.shape?.split("/")[2];
                if (!shapeName) {
                    const shapeImgSquareWidget = this._requestUserValueWidgets("shape_img_square_opt")[0];
                    shapeImgSquareWidget.enable();
                    shapeImgSquareWidget.getParent().close(); // FIXME remove this ugly hack asap
                }
                // Add the "Overlay" hover effect to the shape.
                this.firstHoverEffect = true;
                const hoverEffectOverlayWidget = this._requestUserValueWidgets("hover_effect_overlay_opt")[0];
                hoverEffectOverlayWidget.enable();
                hoverEffectOverlayWidget.getParent().close(); // FIXME remove this ugly hack asap
            }});
        } else if (name === "disable_hover_effect") {
            this._disableHoverEffect();
        } else {
            this._super(...arguments);
        }
    },
    /**
     * @override
     */
    async updateUI() {
        await this._super(...arguments);
        // Adapts the colorpicker label according to the selected "On Hover"
        // animation.
        const hoverEffectName = this.$target[0].dataset.hoverEffect;
        if (hoverEffectName) {
            const hoverEffectColorWidget = this.findWidget("hover_effect_color_opt");
            const needToAdaptLabel = ["image_zoom_in", "image_zoom_out", "dolly_zoom"].includes(hoverEffectName);
            const labelEl = hoverEffectColorWidget.el.querySelector("we-title");
            if (!this._originalHoverEffectColorLabel) {
                this._originalHoverEffectColorLabel = labelEl.textContent;
            }
            labelEl.textContent = needToAdaptLabel
                ? _t("Overlay")
                : this._originalHoverEffectColorLabel;
        }
        // Move the "hover effects" options to the 'websiteAnimate' options.
        const hoverEffectsOptionsEl = this.$el[0].querySelector("#o_hover_effects_options");
        const animationEffectWidget = this._requestUserValueWidgets("animation_effect_opt")[0];
        if (hoverEffectsOptionsEl && animationEffectWidget) {
            animationEffectWidget.getParent().$el[0].append(hoverEffectsOptionsEl);
        }
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
            const shapeURL = `/${encodeURIComponent(module)}/static/image_shapes/${encodeURIComponent(directory)}/${encodeURIComponent(fileName)}.svg`;
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
        // Also apply to carousel thumbnail if applicable.
        weUtils.forwardToThumbnail(img);
    },
    /**
     * Replace animation durations in SVG and CSS with modified values.
     *
     * This function takes a ratio and an SVG string containing animations. It 
     * uses regular expressions to find and replace the duration values in both
     * CSS animation rules and SVG duration attributes based on the provided
     * ratio.
     *
     * @param {number} speed The speed used to calculate the new animation
     *                       durations. If speed is 0.0, the original
     *                       durations are preserved.
     * @param {string} svg The SVG string containing animations.
     * @returns {string} The modified SVG string with updated animation 
     *                   durations.
     */
    _replaceAnimationDuration(speed, svg) {
        const ratio = (speed >= 0.0 ? 1.0 + speed : 1.0 / (1.0 - speed)).toFixed(3);
        // Callback for CSS 'animation' and 'animation-duration' declarations
        function callbackCssAnimationRule(match, declaration, value, unit, separator) {
            value = parseFloat(value) / (ratio ? ratio : 1);
            return `${declaration}${value}${unit}${separator}`;
        }

        // Callback function for handling the 'dur' SVG attribute timecount
        // value in accordance with the SMIL animation specification (e.g., 4s,
        // 2ms). If no unit is provided, seconds are implied.
        function callbackSvgDurTimecountVal(match, attribute_name, value, unit) {
            value = parseFloat(value) / (ratio ? ratio : 1);
            return `${attribute_name}${value}${unit ? unit : 's'}"`
        }

        // Applying regex substitutions to modify animation speed in the 'svg'
        // variable.
        svg = svg.replace(CSS_ANIMATION_RULE_REGEX, callbackCssAnimationRule);
        svg = svg.replace(SVG_DUR_TIMECOUNT_VAL_REGEX, callbackSvgDurTimecountVal);
        if (CSS_ANIMATION_RATIO_REGEX.test(svg)) {
            // Replace the CSS --animation_ratio variable for future purpose.
            svg = svg.replace(CSS_ANIMATION_RATIO_REGEX, `--animation_ratio: ${ratio};`);
        } else {
            // Add the style tag with the root variable --animation ratio for 
            // future purpose.
            const regex = /<svg .*>/m;
            const subst = `$&\n\t<style>\n\t\t:root { \n\t\t\t--animation_ratio: ${ratio};\n\t\t}\n\t</style>`;
            svg = svg.replace(regex, subst);
        }
        return svg;
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
        let needToRefreshPublicWidgets = false;
        let hasHoverEffect = false;

        // Add shape animations on hover.
        if (img.dataset.hoverEffect && this._canHaveHoverEffect()) {
            // The "ImageShapeHoverEffet" public widget needs to restart
            // (e.g. image replacement).
            needToRefreshPublicWidgets = true;
            hasHoverEffect = true;
        }

        const dataURL = await this.computeShape(svgText, img);

        let clonedImgEl = null;
        if (hasHoverEffect) {
            // This is useful during hover effects previews. Without this, in
            // Chrome, the 'mouse out' animation is triggered very briefly when
            // previewMode === 'reset' (when transitioning from one hover effect
            // to another), causing a visual glitch. To avoid this, we hide the
            // image with its clone when the source is set.
            clonedImgEl = img.cloneNode(true);
            this.options.wysiwyg.odooEditor.observerUnactive("addClonedImgForHoverEffectPreview");
            img.classList.add("d-none");
            img.insertAdjacentElement("afterend", clonedImgEl);
            this.options.wysiwyg.odooEditor.observerActive("addClonedImgForHoverEffectPreview");
        }
        const loadedImg = await loadImage(dataURL, img);
        if (hasHoverEffect) {
            this.options.wysiwyg.odooEditor.observerUnactive("removeClonedImgForHoverEffectPreview");
            clonedImgEl.remove();
            img.classList.remove("d-none");
            this.options.wysiwyg.odooEditor.observerActive("removeClonedImgForHoverEffectPreview");
        }
        if (needToRefreshPublicWidgets) {
            await this._refreshPublicWidgets();
        }
        return loadedImg;
    },
    /**
     * Sets the image in the supplied SVG and replace the src with a dataURL
     *
     * @param {string} svgText svg text file
     * @param img JQuery image
     * @returns {Promise} resolved once the svg is properly loaded
     * in the document
     */
    async computeShape(svgText, img) {
        const initialImageWidth = img.naturalWidth;

        // Apply the right animation speed if there is an animated shape.
        const shapeAnimationSpeed = Number(img.dataset.shapeAnimationSpeed) || 0;
        if (shapeAnimationSpeed) {
            svgText = this._replaceAnimationDuration(shapeAnimationSpeed, svgText);
        }

        const svg = new DOMParser().parseFromString(svgText, 'image/svg+xml').documentElement;

        // Modifies the SVG according to the "flip" or/and "rotate" options.
        const shapeFlip = img.dataset.shapeFlip || "";
        const shapeRotate = img.dataset.shapeRotate || 0;
        if ((shapeFlip || shapeRotate) && this._isTransformableShape()) {
            let shapeTransformValues = [];
            if (shapeFlip) { // Possible values => "x", "y", "xy"
                shapeTransformValues.push(`scale${shapeFlip === "x" ? "X" : shapeFlip === "y" ? "Y" : ""}(-1)`);
            }
            if (shapeRotate) { // Possible values => "90", "180", "270"
                shapeTransformValues.push(`rotate(${shapeRotate}deg)`);
            }
            // "transform-origin: center;" does not work on "#filterPath". But
            // since its dimension is 1px * 1px the following solution works.
            const transformOrigin = "transform-origin: 0.5px 0.5px;";
            // Applies the transformation values to the path used to create a
            // mask over the SVG image.
            svg.querySelector("#filterPath").setAttribute("style", `transform: ${shapeTransformValues.join(" ")}; ${transformOrigin}`);
        }

        // Add shape animations on hover.
        if (img.dataset.hoverEffect && this._canHaveHoverEffect()) {
            this._addImageShapeHoverEffect(svg, img);
        }

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
        svg.querySelectorAll("image").forEach(image => {
            image.setAttribute("xlink:href", imgDataURL);
        });
        // Force natural width & height (note: loading the original image is
        // needed for Safari where natural width & height of SVG does not return
        // the correct values).
        const originalImage = await loadImage(imgDataURL);
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
        return dataURL;
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
            return Math.round(clamp(displayWidth, mdContainerInnerWidth, this.MAX_SUGGESTED_WIDTH));
        // If the image is displayed in a container-fluid, it might also get
        // bigger on smaller screens. The same way, we suggest the width of the
        // current image unless it is smaller than the max size of the container
        // on the md breakpoint (which is the LG breakpoint since the container
        // fluid is full-width).
        } else if (img.closest('.container-fluid')) {
            const lgBp = parseFloat(computedStyles.getPropertyValue('--breakpoint-lg')) || 992;
            const mdContainerFluidMaxInnerWidth = lgBp - gutterWidth;
            return Math.round(clamp(displayWidth, mdContainerFluidMaxInnerWidth, this.MAX_SUGGESTED_WIDTH));
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
            const shapeColors = img.dataset.shapeColors;
            if (!shapeName || !shapeColors) {
                return false;
            }
            const colors = img.dataset.shapeColors.split(';');
            return colors[parseInt(params.colorId)];
        }
        if (widgetName === "shape_anim_speed_opt") {
            return this._isAnimatedShape();
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
        if (["img_shape_transform_flip_x_opt", "img_shape_transform_flip_y_opt",
            "img_shape_transform_rotate_x_opt", "img_shape_transform_rotate_y_opt"].includes(params.name)) {
            return this._isTransformableShape();
        }
        if (widgetName === "hover_effect_none_opt") {
            // The hover effects are removed with the "WebsiteAnimate" animation
            // selector so this option should not be visible.
            return false;
        }
        if (params.optionsPossibleValues.setImgShapeHoverEffect) {
            const imgEl = this._getImg();
            return imgEl.classList.contains("o_animate_on_hover") && this._canHaveHoverEffect();
        }
        // If "Description" or "Tooltip" options.
        if (["alt", "title"].includes(params.attributeName)) {
            return isImageSupportedForStyle(this._getImg());
        }
        // The "Square" shape is only used for hover effects. It is
        // automatically set when there is an hover effect and no shape is
        // chosen by the user. This shape is always hidden in the shape select.
        if (widgetName === "shape_img_square_opt") {
            return false;
        }
        if (widgetName === "remove_img_shape_opt") {
            // Do not show the "remove shape" button when the "square" shape is
            // enable. The "square" shape is only enable when there is a hover
            // effect and it is always hidden in the shape select.
            const shapeImgSquareWidget = this._requestUserValueWidgets("shape_img_square_opt")[0];
            return !shapeImgSquareWidget.isActive();
        }
        if (widgetName === "toggle_stretch_opt") {
            return this._isCropRequired();
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
            case 'setImgShapeFlipX': {
                const imgEl = this._getImg();
                return imgEl.dataset.shapeFlip?.includes("x") || "";
            }
            case 'setImgShapeFlipY': {
                const imgEl = this._getImg();
                return imgEl.dataset.shapeFlip?.includes("y") || "";
            }
            case 'setHoverEffectColor': {
                const imgEl = this._getImg();
                return imgEl.dataset.hoverEffectColor || "";
            }
            case "removeStretch": {
                const imgEl = this._getImg();
                return imgEl.dataset.aspectRatio !== "1/1";
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
            image.src = `/${encodeURIComponent(moduleName)}/static/image_shapes/${encodeURIComponent(directory)}/${encodeURIComponent(shapeName)}.svg`;
            $(btn).prepend(image);

            if (btn.dataset.animated) {
                _addAnimatedShapeLabel(btn);
            } else if (btn.dataset.imgSize) {
                _addAnimatedShapeLabel(btn, true);
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
        if (!color || isCSSColor(color)) {
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
        const _super = this._super.bind(this);
        let img = this._getImg();

        // Check first if the `src` and eventual `data-original-src` attributes
        // are correct (i.e. the await are not rejected), as they may have been
        // wrongly hardcoded in some templates.
        let checkedAttribute = 'src';
        try {
            await loadImage(img.src);
            if (img.dataset.originalSrc) {
                checkedAttribute = 'originalSrc';
                await loadImage(img.dataset.originalSrc);
            }
        } catch {
            if (checkedAttribute === 'src') {
                // If `src` does not exist, replace the image by a placeholder.
                Object.keys(img.dataset).forEach(key => delete img.dataset[key]);
                img.dataset.mimetype = 'image/png';
                const newSrc = '/web/image/web.image_placeholder';
                img = await loadImage(newSrc, img);
                return this._loadImageInfo(newSrc);
            } else {
                // If `data-original-src` does not exist, remove the `data-
                // original-*` attributes (they will be set correctly afterwards
                // in `_loadImageInfo`).
                delete img.dataset.originalId;
                delete img.dataset.originalSrc;
                delete img.dataset.originalMimetype;
            }
        }

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
            return this._loadImageInfo(`/web/image/${encodeURIComponent(match)}`);
        }
        return _super(...arguments);
    },
    /**
     * @override
     * @private
     */
    async _loadImageInfo() {
        await this._super(...arguments);
        const img = this._getImg();
        if (img.dataset.shape) {
            if (img.dataset.mimetype !== "image/svg+xml") {
                img.dataset.originalMimetype = img.dataset.mimetype;
            }
            if (!this._isImageSupportedForProcessing(img)) {
                delete img.dataset.shape;
                delete img.dataset.shapeColors;
                delete img.dataset.fileName;
                delete img.dataset.originalMimetype;
                delete img.dataset.shapeFlip;
                delete img.dataset.shapeRotate;
                delete img.dataset.hoverEffect;
                delete img.dataset.hoverEffectColor;
                delete img.dataset.hoverEffectStrokeWidth;
                delete img.dataset.hoverEffectIntensity;
                img.classList.remove("o_animate_on_hover");
                delete img.dataset.shapeAnimationSpeed;
                return;
            }
            if (img.dataset.mimetype !== "image/svg+xml") {
                // Image data-mimetype should be changed to SVG since
                // loadImageInfo() will set the original attachment mimetype on
                // it.
                img.dataset.mimetype = "image/svg+xml";
            }
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
            img.classList.add("o_modified_image_to_save");
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
    /**
     * Flips the image shape (vertically or/and horizontally).
     *
     * @private
     * @param {string} flipValue image shape flip value
     */
    async _setImgShapeFlip(flipValue) {
        const imgEl = this._getImg();
        const currentFlipValue = imgEl.dataset.shapeFlip || "";
        const newFlipValue = currentFlipValue.includes(flipValue)
            ? currentFlipValue.replace(flipValue, "")
            : currentFlipValue + flipValue;
        if (newFlipValue) {
            imgEl.dataset.shapeFlip = newFlipValue === "yx" ? "xy" : newFlipValue;
        } else {
            delete imgEl.dataset.shapeFlip;
        }
        await this._applyShapeAndColors(true, imgEl.dataset.shapeColors?.split(";"));
        imgEl.classList.add("o_modified_image_to_save");
    },
    /**
     * Rotates the image shape 90 degrees.
     *
     * @private
     * @param {integer} rotation rotation value
     */
    async _setImgShapeRotate(rotation) {
        const imgEl = this._getImg();
        const currentRotateValue = parseInt(imgEl.dataset.shapeRotate) || 0;
        const newRotateValue = (currentRotateValue + rotation + 360) % 360;
        if (newRotateValue) {
            imgEl.dataset.shapeRotate = newRotateValue;
        } else {
            delete imgEl.dataset.shapeRotate;
        }
        await this._applyShapeAndColors(true, imgEl.dataset.shapeColors?.split(";"));
        imgEl.classList.add("o_modified_image_to_save");
    },
    /**
     * Checks if the shape is in the "devices" category.
     *
     * @private
     * @returns {boolean}
     */
    _isDeviceShape() {
        const imgEl = this._getImg();
        const shapeName = imgEl.dataset.shape;
        if (!shapeName) {
            return false;
        }
        const shapeCategory = imgEl.dataset.shape.split("/")[1];
        return shapeCategory === "devices";
    },
    /**
     * Checks if the shape is transformable.
     *
     * @private
     * @returns {boolean}
     */
    _isTransformableShape() {
        const shapeImgWidget = this._requestUserValueWidgets("shape_img_opt")[0];
        return (shapeImgWidget && !shapeImgWidget.getMethodsParams().noTransform) && !this._isDeviceShape();
    },
    /**
     * Checks if the shape is in animated.
     *
     * @private
     * @returns {boolean}
     */
    _isAnimatedShape() {
        const shapeImgWidget = this._requestUserValueWidgets("shape_img_opt")[0];
        return shapeImgWidget?.getMethodsParams().animated;
    },
    /**
     * Checks if squaring of image is required before application of shape.
     *
     * @private
     * @returns {boolean}
     */
    _isCropRequired() {
        const shapeImgWidget = this._requestUserValueWidgets("shape_img_opt")[0];
        return shapeImgWidget?.getMethodsParams().unstretch;
    },
    /**
     * Checks if the shape can have a hover effect.
     *
     * @private
     * @returns {boolean}
     */
    _canHaveHoverEffect() {
        return !this._isDeviceShape() && !this._isAnimatedShape() && this._isImageSupportedForShapes();
    },
    /**
     * Adds hover effect to the SVG.
     *
     * @private
     * @param {HTMLElement} svgEl
     * @param {HTMLImageElement} [img] img element
     */
    async _addImageShapeHoverEffect(svgEl, img) {
        let rgba = null;
        let rbg = null;
        let opacity = null;
        // Add the required parts for the hover effects to the SVG.
        const hoverEffectName = img.dataset.hoverEffect;
        if (!this.hoverEffectsSvg) {
            this.hoverEffectsSvg = await this._getHoverEffects();
        }
        const hoverEffectEls = this.hoverEffectsSvg.querySelectorAll(`#${hoverEffectName} > *`);
        hoverEffectEls.forEach(hoverEffectEl => {
            svgEl.appendChild(hoverEffectEl.cloneNode(true));
        });
        // Modifies the svg according to the chosen hover effect and the value
        // of the options.
        const animateEl = svgEl.querySelector("animate");
        const animateTransformEls = svgEl.querySelectorAll("animateTransform");
        const animateElValues = animateEl?.getAttribute("values");
        let animateTransformElValues = animateTransformEls[0]?.getAttribute("values");
        if (img.dataset.hoverEffectColor) {
            rgba = convertCSSColorToRgba(img.dataset.hoverEffectColor);
            rbg = `rgb(${rgba.red},${rgba.green},${rgba.blue})`;
            opacity = rgba.opacity / 100;
            if (!["outline", "image_mirror_blur"].includes(hoverEffectName)) {
                svgEl.querySelector('[fill="hover_effect_color"]').setAttribute("fill", rbg);
                animateEl.setAttribute("values", animateElValues.replace("hover_effect_opacity", opacity));
            }
        }
        switch (hoverEffectName) {
            case "outline": {
                svgEl.querySelector('[stroke="hover_effect_color"]').setAttribute("stroke", rbg);
                svgEl.querySelector('[stroke-opacity="hover_effect_opacity"]').setAttribute("stroke-opacity", opacity);
                // The stroke width needs to be multiplied by two because half
                // of the stroke is invisible since it is centered on the path.
                const strokeWidth = parseInt(img.dataset.hoverEffectStrokeWidth) * 2;
                animateEl.setAttribute("values", animateElValues.replace("hover_effect_stroke_width", strokeWidth));
                break;
            }
            case "image_zoom_in":
            case "image_zoom_out":
            case "dolly_zoom": {
                const imageEl = svgEl.querySelector("image");
                const clipPathEl = svgEl.querySelector("#clip-path");
                imageEl.setAttribute("id", "shapeImage");
                // Modify the SVG so that the clip-path is not zoomed when the
                // image is zoomed.
                imageEl.setAttribute("style", "transform-origin: center; width: 100%; height: 100%");
                imageEl.setAttribute("preserveAspectRatio", "none");
                svgEl.setAttribute("viewBox", "0 0 1 1");
                svgEl.setAttribute("preserveAspectRatio", "none");
                clipPathEl.setAttribute("clipPathUnits", "userSpaceOnUse");
                const clipPathValue = imageEl.getAttribute("clip-path");
                imageEl.removeAttribute("clip-path");
                const gEl = document.createElementNS("http://www.w3.org/2000/svg", "g");
                gEl.setAttribute("clip-path", clipPathValue);
                imageEl.parentNode.replaceChild(gEl, imageEl);
                gEl.appendChild(imageEl);
                let zoomValue = 1.01 + parseInt(img.dataset.hoverEffectIntensity) / 200;
                animateTransformEls[0].setAttribute("values", animateTransformElValues.replace("hover_effect_zoom", zoomValue));
                if (hoverEffectName === "image_zoom_out") {
                    // Set zoom intensity for the image.
                    const styleAttr = svgEl.querySelector("style");
                    styleAttr.textContent = styleAttr.textContent.replace("hover_effect_zoom", zoomValue);
                }
                if (hoverEffectName === "dolly_zoom") {
                    clipPathEl.setAttribute("style", "transform-origin: center;");
                    // Set zoom intensity for clip-path and overlay.
                    zoomValue = 0.99 - parseInt(img.dataset.hoverEffectIntensity) / 2000;
                    animateTransformEls.forEach((animateTransformEl, index) => {
                        if (index > 0) {
                            animateTransformElValues = animateTransformEl.getAttribute("values");
                            animateTransformEl.setAttribute("values", animateTransformElValues.replace("hover_effect_zoom", zoomValue));
                        }
                    });
                }
                break;
            }
            case "image_mirror_blur": {
                const imageEl = svgEl.querySelector("image");
                imageEl.setAttribute('id', 'shapeImage');
                imageEl.setAttribute('style', 'transform-origin: center;');
                const imageMirrorEl = imageEl.cloneNode();
                imageMirrorEl.setAttribute("id", 'shapeImageMirror');
                imageMirrorEl.setAttribute("filter", "url(#blurFilter)");
                imageEl.insertAdjacentElement("beforebegin", imageMirrorEl);
                const zoomValue = 0.99 - parseInt(img.dataset.hoverEffectIntensity) / 200;
                animateTransformEls[0].setAttribute("values", animateTransformElValues.replace("hover_effect_zoom", zoomValue));
                break;
            }
        }
    },
    /**
     * Gets the hover effects list.
     *
     * @private
     * @returns {HTMLElement}
     */
    _getHoverEffects() {
        const hoverEffectsURL = "/website/static/src/svg/hover_effects.svg";
        return fetch(hoverEffectsURL)
            .then(response => response.text())
            .then(text => {
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(text, "text/xml");
                return xmlDoc.getElementsByTagName("svg")[0];
            });
    },
    /**
     * Disables the hover effect on the image.
     *
     * @private
     */
    async _disableHoverEffect() {
        const imgEl = this._getImg();
        const shapeName = imgEl.dataset.shape?.split("/")[2];
        delete imgEl.dataset.hoverEffect;
        delete imgEl.dataset.hoverEffectColor;
        delete imgEl.dataset.hoverEffectStrokeWidth;
        delete imgEl.dataset.hoverEffectIntensity;
        await this._applyOptions();
        // If "Square" shape, remove it, it doesn't make sense to keep it
        // without hover effect.
        if (shapeName === "geo_square") {
            this._requestUserValueWidgets("remove_img_shape_opt")[0].enable();
        }
    },
    /**
     * @override
     */
    async _select(previewMode, widget) {
        await this._super(...arguments);
        // This is a special case where we need to override the "_select"
        // function in order to trigger mouse events for hover effects on the
        // images when previewing the options. This is done here because if it
        // was done in one of the widget methods, the animation would be
        // canceled when "_refreshPublicWidgets" is executed in the "_super"
        if (widget.$el[0].closest("#o_hover_effects_options")) {
            const hasSetImgShapeHoverEffectMethod = widget.getMethodsNames().includes("setImgShapeHoverEffect");
            // We trigger the animation when preview mode is "false", except for
            // the "setImgShapeHoverEffect" option, where we trigger it when
            // preview mode is "true".
            if (previewMode === hasSetImgShapeHoverEffectMethod) {
                this.$target[0].dispatchEvent(new Event("mouseover"));
                this.hoverTimeoutId = setTimeout(() => {
                    this.$target[0].dispatchEvent(new Event("mouseout"));
                }, 700);
            } else if (previewMode === "reset") {
                clearTimeout(this.hoverTimeoutId);
            }
        }
    },
    /**
     * Checks if a shape can be applied on the target.
     *
     * @private
     * @returns {boolean}
     */
    _isImageSupportedForShapes() {
        const imgEl = this._getImg();
        return imgEl.dataset.originalId && this._isImageSupportedForProcessing(imgEl);
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
};

/**
 * Controls background image width and quality.
 */
export class BackgroundOptimize extends ImageHandlerOption {
    /**
     * @override
     */
    async willStart() {
        this.$target.on('background_changed.BackgroundOptimize', this._onBackgroundChanged.bind(this));
        return super.willStart(...arguments);
    }
    /**
     * @override
     */
    cleanForSave() {
        this.$target.off('.BackgroundOptimize');
        return super.cleanForSave(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getImg() {
        return this.img;
    }
    /**
     * @override
     */
    _computeMaxDisplayWidth() {
        return 1920;
    }
    /**
     * Initializes this.img to an image with the background image url as src.
     *
     * @override
     */
    async _loadImageInfo() {
        this.img = new Image();
        // In the case of a parallax, the background of the snippet is actually
        // set on a child <span> and should be focused here. This is necessary
        // because, at this point, the $target has not yet been updated in the
        // notify() method ("option_update" event), although the event is
        // properly fired from the parallax.
        const targetEl = this.$target[0].classList.contains("oe_img_bg")
            ? this.$target[0] : this.$target[0].querySelector(":scope > .s_parallax_bg.oe_img_bg");
        if (targetEl) {
            Object.entries(targetEl.dataset).filter(([key]) =>
                isBackgroundImageAttribute(key)).forEach(([key, value]) => {
                this.img.dataset[key] = value;
            });
            const src = getBgImageURL(targetEl);
            // Don't set the src if not relative (ie, not local image: cannot be
            // modified)
            this.img.src = src.startsWith("/") ? src : "";
        }
        return await super._loadImageInfo(...arguments);
    }
    /**
     * @override
     */
    _relocateWeightEl() {
        this.callbacks.notifyOptions({
           optionNames: ['BackgroundImage'],
           name: 'add_size_indicator',
           data: this._filesize,
       });
    }
    /**
     * @override
     */
    _applyImage(img) {
        const parts = backgroundImageCssToParts(this.$target.css('background-image'));
        parts.url = `url('${img.getAttribute('src')}')`;
        const combined = backgroundImagePartsToCss(parts);
        this.$target.css('background-image', combined);
        // Apply modification on the DOM HTML element that is currently being
        // modified.
        this.$target[0].classList.add("o_modified_image_to_save");
        // First delete the data attributes relative to the image background
        // from the target as a data attribute could have been be removed (ex:
        // glFilter).
        for (const attribute in this.$target[0].dataset) {
            if (isBackgroundImageAttribute(attribute)) {
                delete this.$target[0].dataset[attribute];
            }
        }
        Object.entries(img.dataset).forEach(([key, value]) => {
            this.$target[0].dataset[key] = value;
        });
        this.$target[0].dataset.bgSrc = img.getAttribute("src");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Reloads image data when the background is changed.
     *
     * @private
     */
    async _onBackgroundChanged(ev, previewMode) {
        ev.stopPropagation();
        if (!previewMode) {
            this.env.snippetEditionRequest(async () => {
                await this._autoOptimizeImage();
            });
        }
    }
}

export class BackgroundToggler extends SnippetOption {

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
            const bgImageOpt = bgImageWidget.option;
            return bgImageOpt.background(false, '', bgImageWidget.getMethodsParams('background'));
        } else {
            // TODO: use trigger instead of el.click when possible
            this._requestUserValueWidgets('bg_image_opt')[0].enable();
        }
    }
    /**
     * Toggles background shape on or off.
     *
     * @see this.selectClass for parameters
     */
    toggleBgShape(previewMode, widgetValue, params) {
        const [shapeWidget] = this._requestUserValueWidgets('bg_shape_opt');
        const shapeOption = shapeWidget.option;
        // TODO: open select after shape was selected?
        // TODO: use setWidgetValue instead of calling shapeOption method directly when possible
        return shapeOption._toggleShape();
    }
    /**
     * Sets a color filter.
     *
     * @see this.selectClass for parameters
     */
    async selectFilterColor(previewMode, widgetValue, params) {
        // Find the filter element.
        let filterEl = this.$target[0].querySelector(':scope > .o_we_bg_filter');

        // If the filter would be transparent, remove it / don't create it.
        const rgba = widgetValue && convertCSSColorToRgba(widgetValue);
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
    }

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
                const bgImageOpt = bgImageWidget.option;
                return !!bgImageOpt._computeWidgetState('background', bgImageWidget.getMethodsParams('background'));
            }
            case 'toggleBgShape': {
                const [shapeWidget] = this._requestUserValueWidgets('bg_shape_opt');
                const shapeOption = shapeWidget.option;
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
        return super._computeWidgetState(...arguments);
    }
    /**
     * @private
     */
    _getLastPreFilterLayerElement() {
        return null;
    }
}

/**
 * Handles the edition of snippet's background image.
 */
export class BackgroundImage extends SnippetOption {
    /**
     * @override
     */
    willStart() {
        this.__customImageSrc = getBgImageURL(this.$target[0]);
        return super.willStart(...arguments);
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Handles a background change.
     *
     * @see this.selectClass for parameters
     */
    async background(previewMode, widgetValue, params) {
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
    }
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
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name, data) {
        if (name === 'add_size_indicator') {
            this.renderContext.filesize = data && `${data.toFixed(1)} kb` || undefined;
        } else {
            super.notify(...arguments);
        }
    }
    /**
     * @override
     */
    setTarget() {
        // When we change the target of this option we need to transfer the
        // background-image and the dataset information relative to this image
        // from the old target to the new one.
        const oldBgURL = getBgImageURL(this.$target);
        const isModifiedImage = this.$target[0].classList.contains("o_modified_image_to_save");
        const filteredOldDataset = Object.entries(this.$target[0].dataset).filter(([key]) => {
            return isBackgroundImageAttribute(key);
        });
        // Delete the dataset information relative to the background-image of
        // the old target.
        filteredOldDataset.forEach(([key]) => {
            delete this.$target[0].dataset[key];
        });
        // It is important to delete ".o_modified_image_to_save" from the old
        // target as its image source will be deleted.
        this.$target[0].classList.remove("o_modified_image_to_save");
        this._setBackground('');
        super.setTarget(...arguments);
        if (oldBgURL) {
            this._setBackground(oldBgURL);
            filteredOldDataset.forEach(([key, value]) => {
                this.$target[0].dataset[key] = value;
            });
            this.$target[0].classList.toggle("o_modified_image_to_save", isModifiedImage);
        }

        // TODO should be automatic for all options as equal to the start method
        this.__customImageSrc = getBgImageURL(this.$target[0]);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'background':
                return getBgImageURL(this.$target[0]);
            case 'dynamicColor':
                return new URL(getBgImageURL(this.$target[0]), window.location.origin).searchParams.get(params.colorName);
        }
        return super._computeWidgetState(...arguments);
    }
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
        return super._computeWidgetVisibility(...arguments);
    }
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
            this.$target[0].classList.remove(
                "oe_img_bg",
                "o_bg_img_center",
                "o_modified_image_to_save",
            );
        }
        const combined = backgroundImagePartsToCss(parts);
        // We use selectStyle so that if when a background image is removed the
        // remaining image matches the o_cc's gradient background, it can be
        // removed too.
        this.selectStyle(false, combined, {
            cssProperty: 'background-image',
        });
    }
}

/**
 * Handles background shapes.
 */
export class BackgroundShape extends SnippetOption {
    constructor() {
        super(...arguments);
        this.debugRow = true;
    }
    /**
     * @override
     */
    async updateUI({assetsChanged} = {}) {
        if (this.rerender || assetsChanged) {
            this.rerender = false;
            const newContext = await this._getRenderContext();
            Object.assign(this.renderContext, newContext);
        }
        return super.updateUI(this, arguments);
    }
    /**
     * @override
     */
    onBuilt() {
        // Flip classes should no longer be used but are still present in some
        // theme snippets.
        if (this.$target[0].querySelector('.o_we_flip_x, .o_we_flip_y')) {
            this._handlePreviewState(false, () => {
                return {flip: this._getShapeData().flip};
            });
        }
    }

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
            return {
                shape: widgetValue,
                colors: this._getImplicitColors(widgetValue, this._getShapeData().colors),
                flip: [],
                animated: params.animated,
                shapeAnimationSpeed: this._getShapeData().shapeAnimationSpeed,
            };
        });
    }
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
    }
    /**
     * Flips the shape on its x axis.
     *
     * @see this.selectClass for params
     */
    flipX(previewMode, widgetValue, params) {
        this._flipShape(previewMode, 'x');
    }
    /**
     * Flips the shape on its y axis.
     *
     * @see this.selectClass for params
     */
    flipY(previewMode, widgetValue, params) {
        this._flipShape(previewMode, 'y');
    }
    /**
     * Shows/Hides the shape on mobile.
     *
     * @see this.selectClass for params
     */
    showOnMobile(previewMode, widgetValue, params) {
        this._handlePreviewState(previewMode, () => {
            return {showOnMobile: !this._getShapeData().showOnMobile};
        });
    }
    /**
     * Sets the speed of the animation of a background shape.
     *
     * @see this.selectClass for params
     */
    setBgShapeAnimationSpeed(previewMode, widgetValue, params) {
        this._handlePreviewState(previewMode, () => {
            return { shapeAnimationSpeed: widgetValue };
        });
    }

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
            case 'showOnMobile': {
                return this._getShapeData().showOnMobile;
            }
            case "setBgShapeAnimationSpeed": {
                return this._getShapeData().shapeAnimationSpeed;
            }
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === "bg_shape_anim_speed_opt") {
            const bgShapeWidget = this._requestUserValueWidgets("bg_shape_opt")[0];
            return bgShapeWidget.getMethodsParams().animated === "true";
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * @override
     */
    async _getRenderContext() {
        const context = await super._getRenderContext();
        const colorPickers = Object.keys(this._getDefaultColors());

        // Inventory shape URLs per class.
        const style = window.getComputedStyle(this.$target[0]);
        const palette = [1, 2, 3, 4, 5].map(n => style.getPropertyValue(`--o-cc${n}-bg`)).join();
        if (palette !== this._lastShapePalette) {
            this._lastShapePalette = palette;
            this._shapeBackgroundImagePerClass = {};
            for (const styleSheet of this.$target[0].ownerDocument.styleSheets) {
                if (styleSheet.href && new URL(styleSheet.href).host !== location.host) {
                    // In some browsers, if a stylesheet is loaded from a different domain
                    // accessing cssRules results in a SecurityError.
                    continue;
                }
                for (const rule of [...styleSheet.cssRules]) {
                    if (rule.selectorText && rule.selectorText.startsWith(".o_we_shape.")) {
                        this._shapeBackgroundImagePerClass[rule.selectorText] = rule.style.backgroundImage;
                    }
                }
            }
            context._shapeBackgroundImagePerClass = this._shapeBackgroundImagePerClass;
        }
        context.colorPickers = colorPickers;
        return context;
    }
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
    }
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
            this._removeShapeEl(shapeContainer);
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
    }
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
    }
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
        const {shape, colors, flip = [], animated = 'false', showOnMobile, shapeAnimationSpeed} = json ? JSON.parse(json) : {};
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

        shapeContainer.classList.toggle('o_we_animated', animated === 'true');
        if (colors || flip.length || parseFloat(shapeAnimationSpeed) !== 0) {
            // Custom colors/flip/speed, overwrite shape that is set by the class
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
        shapeContainer.classList.toggle('o_shape_show_mobile', !!showOnMobile);
        if (previewMode === false) {
            this.prevShapeContainer = shapeContainer.cloneNode(true);
            this.prevShape = target.dataset.oeShapeData;
        }
    }
    /**
     * @private
     * @param {HTMLElement} shapeEl
     */
    _removeShapeEl(shapeEl) {
        shapeEl.remove();
    }
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
    }
    /**
     * @private
     */
    _getLastPreShapeLayerElement() {
        const $filterEl = this.$target.find('> .o_we_bg_filter');
        if ($filterEl.length) {
            return $filterEl[0];
        }
        return null;
    }
    /**
     * Returns the src of the shape corresponding to the current parameters.
     *
     * @private
     */
    _getShapeSrc() {
        const { shape, colors, flip, shapeAnimationSpeed } = this._getShapeData();
        if (!shape) {
            return '';
        }
        const searchParams = Object.entries(colors)
            .map(([colorName, colorValue]) => {
                const encodedCol = encodeURIComponent(colorValue);
                return `${colorName}=${encodedCol}`;
            });
        if (flip.length) {
            searchParams.push(`flip=${encodeURIComponent(flip.sort().join(''))}`);
        }
        if (Number(shapeAnimationSpeed)) {
            searchParams.push(`shapeAnimationSpeed=${encodeURIComponent(shapeAnimationSpeed)}`);
        }
        return `/web_editor/shape/${encodeURIComponent(shape)}.svg?${searchParams.join('&')}`;
    }
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
            showOnMobile: false,
            shapeAnimationSpeed: "0",
        };
        const json = target.dataset.oeShapeData;
        return json ? Object.assign(defaultData, JSON.parse(json.replace(/'/g, '"'))) : defaultData;
    }
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
    }
    /**
     * Returns the default colors for the a shape in the selector.
     *
     * @private
     * @param {String} shapeId identifier of the shape
     */
    _getShapeDefaultColors(shapeId) {
        const shapeClassName = `o_we_shape.${shapeId.replace(new RegExp('/', 'g'), '_')}`;
        const shapeSrc = getBgImageURL(this.renderContext._shapeBackgroundImagePerClass[shapeClassName]);
        const url = new URL(shapeSrc, window.location.origin);
        return Object.fromEntries(url.searchParams.entries());
    }
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
        return pick(colors, ...defaultKeys);
    }
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
            const params = shapeWidget.getMethodsParams("shape");
            const possibleShapes = params.possibleValues;
            let shapeToSelect;
            if (previousSibling) {
                const previousShape = this._getShapeData(previousSibling).shape;
                shapeToSelect = possibleShapes.find((shape, i) => {
                    return possibleShapes[i - 1] === previousShape;
                });
            }
            // If there is no previous sibling, if the previous sibling had the
            // last shape selected or if the previous shape could not be found
            // in the possible shapes, default to the first shape. ([0] being no
            // shapes selected.)
            if (!shapeToSelect) {
                shapeToSelect = possibleShapes[1];
            }
            // Only show on mobile by default if toggled from mobile view
            const showOnMobile = weUtils.isMobileView(this.$target[0]);
            this.options.snippetEditionRequest({exec: () => {
                // options for shape will only be available after _toggleShape() returned
                this._requestUserValueWidgets('bg_shape_opt')[0].open();
            }});
            this._createShapeContainer(shapeToSelect);
            return this._handlePreviewState(false, () => (
                {
                    shape: shapeToSelect,
                    colors: this._getImplicitColors(shapeToSelect),
                    showOnMobile,
                }
            ));
        }
    }
}

export class WeShapeBtn extends Component {
    static template = "web_editor.WeShapeBtn";
    static components = { WeButton };
    static props = {
        shape: String,
        selectLabel: String,
        animated: { type: Boolean, optional: true },
    };
    setup() {
        this.renderContext = useState(this.env.renderContext);
    }
}

registry.category("snippet_widgets").add("WeShapeBtn", WeShapeBtn);

export class BackgroundShapePosition extends SnippetOptionComponent {
    static template = "web_editor.BackgroundShape";
}

/**
 * Handles the edition of snippets' background image position.
 */
class BackgroundPosition extends SnippetOption {
    /**
     * @override
     */
    willStart() {
        this._initOverlay();
        $(window).on('resize.bgposition', () => this._dimensionOverlay());
        return super.willStart();
    }
    /**
     * @override
     */
    cleanUI() {
        this._toggleBgOverlay(false);
        $(window).off('.bgposition');
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /*
     * Sets the background type (cover/repeat pattern).
     *
     * @see this.selectClass for params
     */
    backgroundType(previewMode, widgetValue, params) {
        this.$target.toggleClass('o_bg_img_opt_repeat', widgetValue === 'repeat-pattern');
        this.$target.css('background-position', '');
        this.$target.css('background-size', widgetValue !== 'repeat-pattern' ? '' : '100px');
    }
    /**
     * Saves current background position and enables overlay.
     *
     * @see this.selectClass for params
     */
    async backgroundPositionOverlay(previewMode, widgetValue, params) {
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
            await scrollTo(this.$target[0], { behavior: "smooth", offset: 50 });
        }
        this._toggleBgOverlay(true);
    }
    /**
     * @override
     */
    selectStyle(previewMode, widgetValue, params) {
        if (params.cssProperty === 'background-size'
                && !this.$target.hasClass('o_bg_img_opt_repeat')) {
            // Disable the option when the image is in cover mode, otherwise
            // the background-size: auto style may be forced.
            return;
        }
        this._super(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeVisibility() {
        return super._computeVisibility && !!getBgImageURL(this.$target[0]);
    }
    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'backgroundType') {
            return this.$target.css('background-repeat') === 'repeat' ? 'repeat-pattern' : 'cover';
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * Initializes the overlay, binds events to the buttons, inserts it in
     * the DOM.
     *
     * @private
     */
    _initOverlay() {
        this.$backgroundOverlay = $(renderToElement('web_editor.background_position_overlay'));
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
    }
    /**
     * Sets the overlay in the right place so that the draggable background
     * renders over the target, and size the background item like the target.
     *
     * @private
     */
    _dimensionOverlay() {
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
    }
    /**
     * Toggles the overlay's display and renders a background clone inside of it.
     *
     * @private
     * @param {boolean} activate toggle the overlay on (true) or off (false)
     */
    _toggleBgOverlay(activate) {
        if (!this.$backgroundOverlay || this.$backgroundOverlay.is('.oe_active') === activate) {
            return;
        }

        if (!activate) {
            this.$backgroundOverlay.removeClass('oe_active');
            this.env.unblockPreviewOverlays();
            this.env.activateSnippet(this.$target);

            $(document).off('click.bgposition');
            if (this.$bgDragger) {
                this.$bgDragger.tooltip('dispose');
            }
            return;
        }

        this.env.hideOverlay();
        this.env.activateSnippet(this.$target, true);
        this.env.blockPreviewOverlays();

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
    }
    /**
     * Returns the difference between the target's size and the background's
     * rendered size. Background position values in % are a percentage of this.
     *
     * @private
     */
    _getBackgroundDelta() {
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
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Drags the overlay's background image, copied to target on "Apply".
     *
     * @private
     */
    _onDragBackgroundStart(ev) {
        ev.preventDefault();
        this.$bgDragger.addClass('o_we_grabbing');
        const $document = $(this.$target[0].ownerDocument);
        $document.on('mousemove.bgposition', this._onDragBackgroundMove.bind(this));
        $document.one('mouseup', () => {
            this.$bgDragger.removeClass('o_we_grabbing');
            $document.off('mousemove.bgposition');
        });
    }
    /**
     * Drags the overlay's background image, copied to target on "Apply".
     *
     * @private
     */
    _onDragBackgroundMove(ev) {
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
    }
    /**
     * Deactivates the overlay if the user clicks outside of it.
     *
     * @private
     */
    _onDocumentClicked(ev) {
        if (!$(ev.target).closest('.o_we_background_position_overlay').length) {
            this._toggleBgOverlay(false);
        }
    }
}

/**
 * Marks color levels of any element that may get or has a color classes. This
 * is done for the specific main colorpicker option so that those are marked on
 * snippet drop (so that base snippet definition do not need to care about that)
 * and on first focus (for compatibility).
 */
export class ColoredLevelBackground extends BackgroundToggler {
    /**
     * @override
     */
    start() {
        this._markColorLevel();
        return this._super(...arguments);
    }
    /**
     * @override
     */
    onBuilt() {
        this._markColorLevel();
    }

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
    _markColorLevel() {
        this.options.wysiwyg.odooEditor.observerUnactive('_markColorLevel');
        this.$target.addClass('o_colored_level');
        this.options.wysiwyg.odooEditor.observerActive('_markColorLevel');
    }
}

class ContainerWidth extends SnippetOption {
    /**
     * @override
     */
    cleanForSave() {
        this.$target.removeClass('o_container_preview');
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async selectClass(previewMode, widgetValue, params) {
        await super.selectClass(...arguments);
        if (previewMode === 'reset') {
            this.$target.removeClass('o_container_preview');
        } else if (previewMode) {
            this.$target.addClass('o_container_preview');
        }
        // TODO: @owl-options implement option_update
        // this.trigger_up('option_update', {
        //     optionName: 'StepsConnector',
        //     name: 'change_container_width',
        // });
    }
}

registerOption("container_width", {
    Class: ContainerWidth,
    template: "web_editor.container_width",
    selector: "section, .s_carousel .carousel-item, s_quotes_carousel .carousel-item",
    exclude: "[data-snippet] :not(.oe_structure) > [data-snippet]",
    target: "> .container, > .container-fluid, > .o_container_small",
});

/**
 * Allows to replace a text value with the name of a database record.
 * @todo replace this mechanism with real backend m2o field ?
 */
legacyRegistry.many2one = SnippetOptionWidget.extend({
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     */
    async willStart() {
        const {oeMany2oneModel, oeMany2oneId} = this.$target[0].dataset;
        this.fields = ['name', 'display_name'];
        return Promise.all([
            this._super(...arguments),
            this.orm.read(oeMany2oneModel, [parseInt(oeMany2oneId)], this.fields).then(([initialRecord]) => {
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
        const [{name: modelName}] = await this.orm.searchRead("ir.model", [['model', '=', model]], ['name']);
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
                    const html = await this.orm.call(
                        "ir.qweb.field.contact",
                        "get_record_to_html",
                        [[contactId]],
                        {options: JSON.parse(node.dataset.oeContactOptions)}
                    );
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
legacyRegistry.VersionControl = SnippetOptionWidget.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Replaces an outdated snippet by its new version.
     */
    async replaceSnippet() {
        // Getting the new block version.
        let newBlockEl;
        this.trigger_up("find_snippet_template", {
            snippet: this.$target[0],
            callback: (snippet) => {
                newBlockEl = snippet.baseBody.cloneNode(true);
            },
        });
        // Replacing the block.
        this.options.wysiwyg.odooEditor.historyPauseSteps();
        this.$target[0].classList.add("d-none"); // Hiding the block to replace it smoothly.
        this.$target[0].insertAdjacentElement("beforebegin", newBlockEl);
        // Initializing the new block as if it was dropped: the mutex needs to
        // be free for that so we wait for it first.
        this.options.wysiwyg.waitForEmptyMutexAction().then(async () => {
            await new Promise((resolve) => {
                this.options.wysiwyg.snippetsMenuBus.trigger("CALL_POST_SNIPPET_DROP", {
                    $snippet: $(newBlockEl),
                    onSuccess: resolve,
                });
            });
            await new Promise(resolve => {
                this.trigger_up("remove_snippet",
                    {$snippet: this.$target, onSuccess: resolve, shouldRecordUndo: false}
                );
            });
            this.options.wysiwyg.odooEditor.historyUnpauseSteps();
            newBlockEl.classList.remove("oe_snippet_body");
            this.options.wysiwyg.odooEditor.historyStep();
        });
    },
    /**
     * Allows to still access the options of an outdated block, despite the
     * warning.
     */
    discardAlert() {
        const alertEl = this.$el[0].querySelector("we-alert");
        const optionsSectionEl = this.$overlay.data("$optionsSection")[0];
        alertEl.remove();
        optionsSectionEl.classList.remove("o_we_outdated_block_options");
        // Preventing the alert to reappear at each render.
        controlledSnippets.add(this.$target[0].dataset.snippet);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        const snippetName = this.$target[0].dataset.snippet;
        // Do not display the alert if it was previously discarded.
        if (controlledSnippets.has(snippetName)) {
            return;
        }
        this.trigger_up("get_snippet_versions", {
            snippetName: snippetName,
            onSuccess: snippetVersions => {
                const isUpToDate = snippetVersions && ["vjs", "vcss", "vxml"].every(key => this.$target[0].dataset[key] === snippetVersions[key]);
                if (!isUpToDate) {
                    uiFragment.prepend(renderToElement("web_editor.outdated_block_message"));
                    // Hide the other options, to only have the alert displayed.
                    const optionsSectionEl = this.$overlay.data("$optionsSection")[0];
                    optionsSectionEl.classList.add("o_we_outdated_block_options");
                }
            },
        });
    },
});

/**
 * Handle the save of a snippet as a template that can be reused later
 */
legacyRegistry.SnippetSave = SnippetOptionWidget.extend({
    isTopOption: true,

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @see this.selectClass for parameters
     */
    saveSnippet: function (previewMode, widgetValue, params) {
        return new Promise(resolve => {
            this.dialog.add(ConfirmationDialog, {
                body: _t("To save a snippet, we need to save all your previous modifications and reload the page."),
                cancel: () => resolve(false),
                confirmLabel: _t("Save and Reload"),
                confirm: () => {
                    let targetCopyEl = null;
                    const isButton = this.$target[0].matches("a.btn");
                    const snippetKey = !isButton ? this.$target[0].dataset.snippet : "s_button";
                    let thumbnailURL;
                    this.trigger_up('snippet_thumbnail_url_request', {
                        key: snippetKey,
                        onSuccess: url => thumbnailURL = url,
                    });
                    let context;
                    this.trigger_up('context_get', {
                        callback: ctx => context = ctx,
                    });
                    if (this.$target[0].matches("[data-snippet=s_popup]")) {
                        // Do not "cleanForSave" the popup before copying the
                        // HTML, otherwise the popup will be saved invisible and
                        // therefore not visible in the "add snippet" dialog.
                        targetCopyEl = this.$target[0].cloneNode(true);
                    }
                    this.trigger_up('request_save', {
                        reloadEditor: true,
                        invalidateSnippetCache: true,
                        onSuccess: async () => {
                            const defaultSnippetName = !isButton
                                ? _t("Custom %s", this.data.snippetName)
                                : _t("Custom Button");
                            targetCopyEl = targetCopyEl || this.$target[0].cloneNode(true);
                            targetCopyEl.classList.add('s_custom_snippet');
                            delete targetCopyEl.dataset.name;
                            if (isButton) {
                                targetCopyEl.classList.remove("mb-2");
                                targetCopyEl.classList.add("o_snippet_drop_in_only", "s_custom_button");
                            }
                            // By the time onSuccess is called after request_save, the
                            // current widget has been destroyed and is orphaned, so this._rpc
                            // will not work as it can't trigger_up. For this reason, we need
                            // to bypass the service provider and use the global RPC directly

                            // Get editable parent TODO find proper method to get it directly
                            let editableParentEl;
                            for (const parentEl of this.options.getContentEditableAreas()) {
                                if (parentEl.contains(this.$target[0])) {
                                    editableParentEl = parentEl;
                                    break;
                                }
                            }
                            context['model'] = editableParentEl.dataset.oeModel;
                            context['field'] = editableParentEl.dataset.oeField;
                            context['resId'] = editableParentEl.dataset.oeId;
                            await rpc(`/web/dataset/call_kw/ir.ui.view/save_snippet`, {
                                model: "ir.ui.view",
                                method: "save_snippet",
                                args: [],
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
                },
            });
        });
    },
});

/**
 * Handles the dynamic colors for dynamic SVGs.
 */
legacyRegistry.DynamicSvg = SnippetOptionWidget.extend({
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
legacyRegistry.MultipleItems = SnippetOptionWidget.extend({

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

legacyRegistry.SelectTemplate = SnippetOptionWidget.extend({
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
        this.orm = this.bindService("orm");
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
            this._templates[xmlid] = await this.orm.call(
                "ir.ui.view",
                "render_public_asset",
                [`${xmlid}`, {}],
                { context: this.options.context }
            );
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

/*
 * Abstract option to be extended by the Carousel and gallery options (through
 * the "CarouselHandler" option) that handles all the common parts (reordering
 * of elements).
 */
legacyRegistry.GalleryHandler = SnippetOptionWidget.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Handles reordering of items.
     *
     * @override
     */
    notify(name, data) {
        this._super(...arguments);
        if (name === "reorder_items") {
            const itemsEls = this._getItemsGallery();
            const oldPosition = itemsEls.indexOf(data.itemEl);
            if (oldPosition === 0 && data.position === "prev") {
                data.position = "last";
            } else if (oldPosition === itemsEls.length - 1 && data.position === "next") {
                data.position = "first";
            }
            itemsEls.splice(oldPosition, 1);
            switch (data.position) {
                case "first":
                    itemsEls.unshift(data.itemEl);
                    break;
                case "prev":
                    itemsEls.splice(Math.max(oldPosition - 1, 0), 0, data.itemEl);
                    break;
                case "next":
                    itemsEls.splice(oldPosition + 1, 0, data.itemEl);
                    break;
                case "last":
                    itemsEls.push(data.itemEl);
                    break;
            }
            this._reorderItems(itemsEls, itemsEls.indexOf(data.itemEl));
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Called to get the items of the gallery sorted by index if any (see
     * gallery option) or by the order on the DOM otherwise.
     *
     * @abstract
     * @returns {HTMLElement[]}
     */
    _getItemsGallery() {},
    /**
     * Called to reorder the items of the gallery.
     *
     * @abstract
     * @param {HTMLElement[]} itemsEls - the items to reorder.
     * @param {integer} newItemPosition - the new position of the moved items.
     */
    _reorderItems(itemsEls, newItemPosition) {},
});

/*
 * Abstract option to be extended by the Carousel and gallery options that
 * handles the update of the carousel indicator.
 */
legacyRegistry.CarouselHandler = legacyRegistry.GalleryHandler.extend({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Update the carousel indicator.
     *
     * @private
     * @param {integer} position - the position of the indicator to activate on
     * the carousel.
     */
    _updateIndicatorAndActivateSnippet(position) {
        const carouselEl = this.$target[0].classList.contains("carousel") ? this.$target[0]
            : this.$target[0].querySelector(".carousel");
        carouselEl.classList.remove("slide");
        $(carouselEl).carousel(position);
        for (const indicatorEl of this.$target[0].querySelectorAll(".carousel-indicators li")) {
            indicatorEl.classList.remove("active");
        }
        this.$target[0].querySelector(`.carousel-indicators li[data-bs-slide-to="${position}"]`)
                    .classList.add("active");
        this.trigger_up("activate_snippet", {
            $snippet: $(this.$target[0].querySelector(".carousel-item.active img")),
            ifInactiveOptions: true,
        });
        carouselEl.classList.add("slide");
    },
});

export function registerBackgroundOptions(name, options, getTemplateName = () => null) {
    registerOption(`${name}-bgToggler`, {
        Class: (
            options.withColors
            && options.withColorCombinations
            && ColoredLevelBackground
        ) || BackgroundToggler,
        template: getTemplateName("toggler") || "web_editor.snippet_options_background_options",
        ...options
    }, { sequence: 25 });
    if (options.withImages) {
        registerOption(`${name}-bgImg`, {
            Class: BackgroundImage,
            template: getTemplateName("img") || "web_editor.BackgroundImage",
            ...options
        }, { sequence: 27 });
        registerOption(`${name}-bgPosition`, {
            Class: BackgroundPosition,
            template: getTemplateName("position") || "web_editor.BackgroundPosition",
            ...options,
        }, { sequence: 29 });
        registerOption(`${name}-bgOptimize`, {
            Class: BackgroundOptimize,
            template: getTemplateName("optimize") || "web_editor.snippet_options_image_optimization_widgets",
            indent: true,
            ...options,
        }, { sequence: 31 });
        registerOption(`${name}-filter`, {
            Class: options.withColors && options.withColorCombinations && ColoredLevelBackground || BackgroundToggler,
            template: getTemplateName("filter") || "web_editor.BackgroundFilter",
            ...options,
        }, { sequence: 33 });
        registerOption(`${name}-shape`, {
            Class: BackgroundShape,
            template: getTemplateName("shape") || "web_editor.BackgroundShapes",
            ...options,
        }, { sequence: 35 });
    }
}

