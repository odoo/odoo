/**
 * Provides a way to start JS code for public contents.
 */

import dom from '@web/core/dom';
import Class from "@web/legacy/js/core/class";
import mixins from "@web/legacy/js/core/mixins";
import ServicesMixin from "@web/legacy/js/core/service_mixins";
import { loadBundle, loadCSS, loadJS } from '@web/core/assets';
import { renderToElement } from "@web/core/utils/render";
import { makeAsyncHandler, makeButtonHandler } from "@web/legacy/js/core/minimal_dom";

/**
 * Base class for all visual components. Provides a lot of functions helpful
 * for the management of a part of the DOM.
 *
 * Widget handles:
 *
 * - Rendering with QWeb.
 * - Life-cycle management and parenting (when a parent is destroyed, all its
 *   children are destroyed too).
 * - Insertion in DOM.
 *
 * **Guide to create implementations of the Widget class**
 *
 * Here is a sample child class::
 *
 *     var MyWidget = Widget.extend({
 *         // the name of the QWeb template to use for rendering
 *         template: "MyQWebTemplate",
 *
 *         init: function (parent) {
 *             this._super(parent);
 *             // stuff that you want to init before the rendering
 *         },
 *         willStart: function () {
 *             // async work that need to be done before the widget is ready
 *             // this method should return a promise
 *         },
 *         start: function() {
 *             // stuff you want to make after the rendering, `this.el` holds a correct value
 *             this.el.querySelector(".my_button").click(/* an example of event binding * /);
 *
 *             // if you have some asynchronous operations, it's a good idea to return
 *             // a promise in start(). Note that this is quite rare, and if you
 *             // need to fetch some data, this should probably be done in the
 *             // willStart method
 *             var promise = this._rpc(...);
 *             return promise;
 *         }
 *     });
 *
 * Now this class can simply be used with the following syntax::
 *
 *     var myWidget = new MyWidget(this);
 *     myWidget.appendTo(document.querySelector(".some-div"));
 *
 * With these two lines, the MyWidget instance was initialized, rendered,
 * inserted into the DOM inside the ``.some-div`` div and its events were
 * bound.
 *
 * This class can also be initialized and started on an existing DOM element
 * using the `selector` property. See below for more documentation.
 *
 * And of course, when you don't need that widget anymore, just do::
 *
 *     myWidget.destroy();
 *
 * That will kill the widget in a clean way and erase its content from the dom.
 *
 * This class also provides a way for executing code once a website DOM element
 * is loaded in the dom.
 * @see PublicWidget.selector
 */
export const PublicWidget = Class.extend(mixins.PropertiesMixin, ServicesMixin, {
    // Backbone-ish API
    tagName: 'div',
    id: null,
    className: null,
    attributes: {},
    /**
     * The name of the QWeb template that will be used for rendering. Must be
     * redefined in subclasses or the default render() method can not be used.
     *
     * @type {null|string}
     */
    template: null,
    /**
     * List of paths to css files that need to be loaded before the widget can
     * be rendered. This will not induce loading anything that has already been
     * loaded.
     *
     * @type {null|string[]}
     */
    cssLibs: null,
    /**
     * List of paths to js files that need to be loaded before the widget can
     * be rendered. This will not induce loading anything that has already been
     * loaded.
     *
     * @type {null|string[]}
     */
    jsLibs: null,
    /**
     * List of xmlID that need to be loaded before the widget can be rendered.
     * The content css (link file or style tag) and js (file or inline) of the
     * assets are loaded.
     * This will not induce loading anything that has already been
     * loaded.
     *
     * @type {null|string[]}
     */
    assetLibs: null,
    /**
     * The selector attribute, if defined, allows to automatically create an
     * instance of this widget on page load for each DOM element which matches
     * this selector. The `PublicWidget.el` element will then be that
     * particular DOM element. This should be the main way of instantiating
     * `PublicWidget` elements.
     *
     * @todo do not make this part of the Widget but rather an info to give when
     * registering the widget.
     */
    selector: false,
    /**
     * Extension of @see Widget.events
     *
     * A description of the event handlers to bind/delegate once the widget
     * has been rendered::
     *
     *   'click .hello .world': 'async _onHelloWorldClick',
     *     _^_      _^_           _^_        _^_
     *      |        |             |          |
     *      |  (Optional) HTML   |  Handler method name
     *      |  delegate selector   |
     *      |                      |_ (Optional) space separated options
     *      |                          * async: use the automatic system
     *      |_ Event name with           making handlers promise-ready (see
     *         potential HTML          makeButtonHandler, makeAsyncHandler)
     *         namespaces
     *
     * Note: the values may be replaced by a function declaration. This is
     * however a deprecated behavior.
     *
     * @type {Object}
     */
    events: {},

    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} [options]
     */
    init: function (parent, options) {
        mixins.PropertiesMixin.init.call(this);
        this.setParent(parent);
        this.options = options || {};
    },
    /**
     * Method called between @see init and @see start. Performs asynchronous
     * calls required by the rendering and the start method.
     *
     * This method should return a Promise which is resolved when start can be
     * executed.
     *
     * @returns {Promise}
     */
    willStart: function () {
        var proms = [];
        if (this.jsLibs || this.cssLibs || this.assetLibs) {
            var assetsPromise = Promise.all([
                ...(this.cssLibs || []).map(loadCSS),
                ...(this.jsLibs || []).map(loadJS),
            ]);
            for (const bundleName of this.assetLibs || []) {
                if (typeof bundleName === "string") {
                    assetsPromise = assetsPromise.then(() => {
                        return loadBundle(bundleName);
                    });
                } else {
                    assetsPromise = assetsPromise.then(() => {
                        return Promise.all([...bundleName.map(loadBundle)]);
                    })
                }
            }
            proms.push(assetsPromise);
        }
        return Promise.all(proms);
    },
    /**
     * Method called after rendering. Mostly used to bind actions, perform
     * asynchronous calls, etc...
     *
     * By convention, this method should return an object that can be passed to
     * Promise.resolve() to inform the caller when this widget has been initialized.
     *
     * Note that, for historic reasons, many widgets still do work in the start
     * method that would be more suited to the willStart method.
     *
     * @returns {Promise}
     */
    start: function () {
        return Promise.resolve();
    },
    /**
     * Destroys the widget and basically restores the target to the state it
     * was before the start method was called (unlike standard widget, the
     * associated el DOM is not removed, if this was instantiated thanks to the
     * selector property).
     */
    destroy: function () {
        mixins.PropertiesMixin.destroy.call(this);
        this._undelegateEvents();
        // If not done with a selector, then
        // remove the elements added to the DOM.
        if (!this.selector && this.el) {
            this.el.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Renders the current widget and appends it to the given jQuery object.
     *
     * @param {HTMLElement} targetEl
     * @returns {Promise}
     */
    appendTo: function (targetEl) {
        // TO-remove : backward compatibility targetEl can be a jQuery object
        targetEl = targetEl instanceof jQuery ? targetEl[0] : targetEl;
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.append(self.el);
        }, targetEl);
    },
    /**
     * Attach the current widget to a dom element
     *
     * @param {HTMLElement} targetEl
     * @returns {Promise}
     */
    attachTo: function (targetEl) {
        // TO-remove : backward compatibility targetEl can be a jQuery object
        targetEl = targetEl instanceof jQuery ? targetEl[0] : targetEl;
        var self = this;
        this.setElement(targetEl.el || targetEl);
        return this.willStart().then(function () {
            if (self.__parentedDestroyed) {
                return;
            }
            return self.start();
        });
    },
    /**
     * Renders the current widget and inserts it after to the given jQuery
     * object.
     *
     * @param {HTMLElement} targetEl
     * @returns {Promise}
     */
    insertAfter: function (targetEl) {
        // Ensure targetEl is not a jQuery object for backward compatibility
        targetEl = targetEl instanceof jQuery ? targetEl[0] : targetEl;
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.parentNode.insertBefore(self.el, t.nextSibling);
        }, targetEl);
    },
    /**
     * Renders the current widget and inserts it before to the given jQuery
     * object.
     *
     * @param {HTMLElement} targetEl
     * @returns {Promise}
     */
    insertBefore: function (targetEl) {
        // Ensure targetEl is not a jQuery object for backward compatibility
        targetEl = targetEl instanceof jQuery ? targetEl[0] : targetEl;
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.parentNode.insertBefore(self.el, t);
        }, targetEl);
    },
    /**
     * Renders the current widget and prepends it to the given jQuery object.
     *
     * @param {HTMLElement} targetEl
     * @returns {Promise}
     */
    prependTo: function (targetEl) {
        // Ensure targetEl is not a jQuery object for backward compatibility
        targetEl = targetEl instanceof jQuery ? targetEl[0] : targetEl;
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.prepend(self.el);
        }, targetEl);
    },
    /**
     * Renders the element. The default implementation renders the widget using
     * QWeb, `this.template` must be defined. The context given to QWeb contains
     * the "widget" key that references `this`.
     */
    renderElement: function () {
        let el;
        if (this.template) {
            el = renderToElement(this.template, { widget: this });
        } else {
            el = this._makeDescriptive();
        }
        this._replaceElement(el);
    },
    /**
     * Renders the current widget and replaces the given jQuery object.
     *
     * @param targetEl A HTMLElement or a Widget instance.
     * @returns {Promise}
     */
    replace: function (targetEl) {
        const self = this;
        return this._widgetRenderAndInsert((t) => {
            t.replaceWith(self.el);
        }, targetEl);
    },
    /**
     * Re-sets the widget's root element (el/$el/$el).
     *
     * Includes:
     *
     * * re-delegating events
     * * re-binding sub-elements
     * * if the widget already had a root element, replacing the pre-existing
     *   element in the DOM
     *
     * @param {HTMLElement | jQuery} element new root element for the widget
     * @return {Widget} this
     */
    setElement: function (element) {
        if (this.el) {
            this._undelegateEvents();
        }

        // Note: Kept for backward compatibility, we will remove it in future
        this.$el = (element instanceof $) ? element : $(element);
        // Note this.el can also be selector (case found when i click course in website)
        // To-do use querySeletor in place of $(element)[0] while removing jQuery
        this.el =
            element instanceof $
                ? element[0]
                : this.el instanceof Element
                ? this.el
                : $(element)[0];

        this._delegateEvents();

        if (this.selector) {
            // Note: Kept for backward compatibility, we will remove it in future
            this.$target = this.$el;
            this.target = this.el;
        }

        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    // Note: Kept for backward compatibility, we will remove it in future when all public Widget uses this.el
    /**
     * Helper method, for ``this.$el.find(selector)``
     *
     * @private
     * @param {string} selector CSS selector, rooted in $el
     * @returns {jQuery} selector match
     */
    $: function (selector) {
        if (selector === undefined) {
            return this.$el;
        }
        return this.$el.find(selector);
    },
    /**
     * @see this.events
     * @override
     */
    _delegateEvents: function () {
        var self = this;

        const _delegateEvent = (method, key) => {
            var match = /^(\S+)(\s+(.*))?$/.exec(key);
            var event = match[1];
            var selector = match[3];

            event += '.widget_events';
            if (!selector) {
                self.el.on(event, method);
            } else {
                self.el.on(event, selector, method);
            }
        };
        Object.entries(this.events || {}).forEach(([event, method]) => {
            // If the method is a function, use the default Widget system
            if (typeof method !== 'string') {
                _delegateEvent(self.proxy(method), event);
                return;
            }
            // If the method is only a function name without options, use the
            // default Widget system
            var methodOptions = method.split(' ');
            if (methodOptions.length <= 1) {
                _delegateEvent(self.proxy(method), event);
                return;
            }
            // If the method has no meaningful options, use the default Widget
            // system
            var isAsync = methodOptions.includes('async');
            if (!isAsync) {
                _delegateEvent(self.proxy(method), event);
                return;
            }

            method = self.proxy(methodOptions[methodOptions.length - 1]);
            if (String(event).startsWith("click")) {
                // Protect click handler to be called multiple times by
                // mistake by the user and add a visual disabling effect
                // for buttons.
                method = makeButtonHandler(method);
            } else {
                // Protect all handlers to be recalled while the previous
                // async handler call is not finished.
                method = makeAsyncHandler(method);
            }
            _delegateEvent(method, event);
        });
    },
    /**
     * @private
     * @param {boolean} [extra=false]
     * @param {Object} [extraContext]
     * @returns {Object}
     */
    _getContext: function (extra, extraContext) {
        var context;
        this.trigger_up('context_get', {
            extra: extra || false,
            context: extraContext,
            callback: function (ctx) {
                context = ctx;
            },
        });
        return context;
    },
    /**
     * Makes a potential root element from the declarative builder of the
     * widget
     *
     * @private
     * @return {HTMLElement}
     */
    _makeDescriptive: function () {
        var attrs = Object.assign({}, this.attributes || {});
        if (this.id) {
            attrs.id = this.id;
        }
        if (this.className) {
            attrs['class'] = this.className;
        }
        const el = document.createElement(this.tagName);
        if (Object.keys(attrs || {}).length > 0) {
            for (const key in attrs) {
                el.setAttribute(key, attrs[key]);
            }
        }
        return el;
    },
    /**
     * Re-sets the widget's root element and replaces the old root element
     * (if any) by the new one in the DOM.
     *
     * @private
     * @param {HTMLElement} el
     * @returns {Widget} this instance, so it can be chained
     */
    _replaceElement: function (el) {
        var oldel = this.el;
        this.setElement(el);
        if (oldel && !(oldel === this.el)) {
            if (oldel) {
                const divEl = document.createElement('div');
                divEl.append(oldel);
                oldel.parentNode.replaceWith(this.el);
            } else {
                oldel.replaceWith(this.el);
            }
        }
        return this;
    },
    /**
     * Remove all handlers registered on this.el
     *
     * @private
     */
    _undelegateEvents: function () {
        this.el?.off(".widget_events");
    },
    /**
     * Render the widget.  This is a private method, and should really never be
     * called by anyone (except this widget).  It assumes that the widget was
     * not willStarted yet.
     *
     * @private
     * @param {function} insertion
     * @param {HTMLElement} targetEl
     * @returns {Promise}
     */
    _widgetRenderAndInsert: function (insertion, targetEl) {
        var self = this;
        return this.willStart().then(function () {
            if (self.__parentedDestroyed) {
                return;
            }
            self.renderElement();
            insertion(targetEl);
            return self.start();
        });
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * Specialized Widget which automatically instantiates child widgets to attach
 * to internal DOM elements once it is started. The widgets to instantiate are
 * known thanks to a linked registry which contains info about the widget
 * classes and jQuery selectors to use to find the elements to attach them to.
 *
 * @todo Merge with 'PublicWidget' ?
 */
var RootWidget = PublicWidget.extend({
    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._widgets = [];
    },
    /**
     * @override
     * @see _attachComponents
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];

        defs.push(this._attachComponents());
        this._getRegistry().addEventListener("UPDATE", ({ detail }) => {
            const { operation, value } = detail;
            if (operation === "add") {
                this._attachComponent(value);
            }
        });

        return Promise.all(defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiates a child widget according to the given registry data.
     *
     * @private
     * @param {Object} childInfo
     * @param {function} childInfo.Widget - the widget class to instantiate
     * @param {string} childInfo.selector
     *        the jQuery selector to use to find the internal DOM element which
     *        needs to be attached to the instantiated widget
     * @param {HTMLElement} [fromEl] - only check DOM elements which are descendant of
     *                         the given one. If not given, use this.el.
     * @returns {Deferred}
     */
    _attachComponent: function (childInfo, fromEl) {
        var self = this;
        var elements = dom.cssFind(fromEl || this.el, childInfo.selector);
        var defs = Array.from(elements).map((element) => {
            var w = new childInfo.Widget(self);
            self._widgets.push(w);
            return w.attachTo(element);
        });
        return Promise.all(defs);
    },
    /**
     * Instantiates the child widgets that need to be according to the linked
     * registry.
     *
     * @private
     * @param {HTMLElement} [fromEl] - only check DOM elements which are descendant of
     *                         the given one. If not given, use this.$el.
     * @returns {Deferred}
     */
    _attachComponents: function (fromEl) {
        // TODO: MSH: Need to convert to VanillaJS
        var self = this;
        var childInfos = this._getRegistry().getAll();
        var defs = childInfos.map((childInfo) => {
            return self._attachComponent(childInfo, fromEl);
        });
        return Promise.all(defs);
    },
    /**
     * Returns the `RootWidgetRegistry` instance that is linked to this
     * `RootWidget` instance.
     *
     * @abstract
     * @private
     * @returns {RootWidgetRegistry}
     */
    _getRegistry: function () {},
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * The registry object contains the list of widgets that should be instantiated
 * thanks to their selector property if any.
 */
var registry = {};

export default {
    RootWidget: RootWidget,
    Widget: PublicWidget,
    registry: registry,
};
