// @ts-check

/** @module @web/legacy/js/public/public_widget - Legacy widget framework for public pages with parent-child lifecycle and DOM event handling */

import { Component } from "@odoo/owl";
import Class from "@web/legacy/js/core/class";
import { loadBundle, loadCSS, loadJS } from "@web/core/assets";
import { SERVICES_METADATA } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import {
    makeAsyncHandler,
    makeButtonHandler,
} from "@web/legacy/js/public/minimal_dom";

/**
 * Mixin to structure objects' life-cycles following a parent-children
 * relationship. Each object can a have a parent and multiple children.
 * When an object is destroyed, all its children are destroyed too releasing
 * any resource they could have reserved before.
 *
 * @name ParentedMixin
 * @mixin
 */
const ParentedMixin = {
    __parentedMixin: true,

    init: function () {
        this.__parentedDestroyed = false;
        this.__parentedChildren = [];
        this.__parentedParent = null;
    },
    /**
     * Set the parent of the current object. When calling this method, the
     * parent will also be informed and will return the current object
     * when its getChildren() method is called. If the current object did
     * already have a parent, it is unregistered before, which means the
     * previous parent will not return the current object anymore when its
     * getChildren() method is called.
     */
    setParent(parent) {
        if (this.getParent()) {
            if (this.getParent().__parentedMixin) {
                const children = this.getParent().getChildren();
                this.getParent().__parentedChildren = children.filter(
                    (child) => child.el !== this.el,
                );
            }
        }
        this.__parentedParent = parent;
        if (parent && parent.__parentedMixin) {
            parent.__parentedChildren.push(this);
        }
    },
    /**
     * Return the current parent of the object (or null).
     */
    getParent() {
        return this.__parentedParent;
    },
    /**
     * Return a list of the children of the current object.
     */
    getChildren() {
        return [...this.__parentedChildren];
    },
    /**
     * Returns true if destroy() was called on the current object.
     */
    isDestroyed() {
        return this.__parentedDestroyed;
    },
    /**
     * Releases any resource the instance could have reserved.
     */
    destroy() {
        this.getChildren().forEach(function (child) {
            child.destroy();
        });
        this.setParent(undefined);
        this.__parentedDestroyed = true;
    },
};

function OdooEvent(target, name, data) {
    this.target = target;
    this.name = name;
    this.data = Object.create(null);
    Object.assign(this.data, data);
    this.stopped = false;
}
OdooEvent.prototype.stopPropagation = function () {
    this.stopped = true;
};
OdooEvent.prototype.is_stopped = function () {
    return this.stopped;
};

/**
 * Do not ever use it directly, use EventDispatcherMixin instead. This class
 * just handles the dispatching of events, it is not meant to be extended, nor
 * used directly. All integration with parenting and automatic unregistration of
 * events is done in EventDispatcherMixin.
 *
 * Copyright notice for the following Class and its uses:
 *
 * (c) 2010-2012 Jeremy Ashkenas, DocumentCloud Inc.
 * Backbone may be freely distributed under the MIT license.
 * For all details and documentation:
 * http://backbonejs.org
 *
 * See the debian/copyright file for the text of the MIT license.
 */
class Events {
    on(events, callback, context) {
        let ev;
        events = events.split(/\s+/);
        const calls = this._callbacks || (this._callbacks = {});
        while ((ev = events.shift())) {
            const list = calls[ev] || (calls[ev] = {});
            const tail = list.tail || (list.tail = list.next = {});
            tail.callback = callback;
            tail.context = context;
            list.tail = tail.next = {};
        }
        return this;
    }
    off(events, callback, context) {
        let ev, calls, node;
        if (!events) {
            delete this._callbacks;
        } else if ((calls = this._callbacks)) {
            events = events.split(/\s+/);
            while ((ev = events.shift())) {
                node = calls[ev];
                delete calls[ev];
                if (!callback || !node) {
                    continue;
                }
                while ((node = node.next) && node.next) {
                    if (
                        node.callback === callback &&
                        (!context || node.context === context)
                    ) {
                        continue;
                    }
                    this.on(ev, node.callback, node.context);
                }
            }
        }
        return this;
    }
    callbackList() {
        const lst = [];
        for (const [eventName, el] of Object.entries(this._callbacks || {})) {
            let node = el;
            while ((node = node.next) && node.next) {
                lst.push([eventName, node.callback, node.context]);
            }
        }
        return lst;
    }
    /* eslint-disable prefer-const -- legacy Backbone event system, pervasive mutation */
    trigger(events) {
        let event, node, calls, tail, args, all, rest;
        if (!(calls = this._callbacks)) {
            return this;
        }
        all = calls.all;
        (events = events.split(/\s+/)).push(null);
        // Save references to the current heads & tails.
        while ((event = events.shift())) {
            if (all) {
                events.push({
                    next: all.next,
                    tail: all.tail,
                    event: event,
                });
            }
            if (!(node = calls[event])) {
                continue;
            }
            events.push({
                next: node.next,
                tail: node.tail,
            });
        }
        rest = Array.prototype.slice.call(arguments, 1);
        while ((node = events.pop())) {
            tail = node.tail;
            args = node.event ? [node.event].concat(rest) : rest;
            while ((node = node.next) !== tail) {
                node.callback.apply(node.context || this, args);
            }
        }
        return this;
    }
    /* eslint-enable prefer-const */
}

/**
 * Mixin containing an event system. Events are also registered by specifying
 * the target object (the object which will receive the event when raised). Both
 * the event-emitting object and the target object store or reference to each
 * other. This is used to correctly remove all reference to the event handler
 * when any of the object is destroyed (when the destroy() method from
 * ParentedMixin is called). Removing those references is necessary to avoid
 * memory leak and phantom events (events which are raised and sent to a
 * previously destroyed object).
 *
 * @name EventDispatcherMixin
 * @mixin
 */
const EventDispatcherMixin = Object.assign({}, ParentedMixin, {
    __eventDispatcherMixin: true,
    custom_events: {},

    /** @this {any} */
    init() {
        ParentedMixin.init.call(this);
        this.__edispatcherEvents = new Events();
        this.__edispatcherRegisteredEvents = [];
        this._delegateCustomEvents();
    },
    /**
     * Proxies a method of the object, in order to keep the right ``this`` on
     * method invocations.
     *
     * This method is similar to ``Function.prototype.bind``, and
     * even more so to ``jQuery.proxy`` with a fundamental difference: its
     * resolution of the method being called is lazy, meaning it will use the
     * method as it is when the proxy is called, not when the proxy is created.
     *
     * Other methods will fix the bound method to what it is when creating the
     * binding/proxy, which is fine in most javascript code but problematic in
     * Odoo where developers may want to replace existing callbacks with theirs.
     *
     * The semantics of this precisely replace closing over the method call.
     *
     * @param {String|Function} method function or name of the method to invoke
     * @returns {Function} proxied method
     */
    proxy(method) {
        const self = this;
        return function () {
            const fn = typeof method === "string" ? self[method] : method;
            if (fn === void 0) {
                throw new Error(
                    "Couldn't find method '" + method + "' in widget " + self,
                );
            }
            return fn.apply(self, arguments);
        };
    },
    _delegateCustomEvents() {
        if (Object.keys(this.custom_events || {}).length === 0) {
            return;
        }
        for (const key in this.custom_events) {
            if (!Object.hasOwn(this.custom_events, key)) {
                continue;
            }

            const method = this.proxy(this.custom_events[key]);
            this.on(key, this, method);
        }
    },
    /** @this {any} */
    on(events, dest, func) {
        const self = this;
        if (typeof func !== "function") {
            throw new Error("Event handler must be a function.");
        }
        events = events.split(/\s+/);
        events.forEach((eventName) => {
            self.__edispatcherEvents.on(eventName, func, dest);
            if (dest && dest.__eventDispatcherMixin) {
                dest.__edispatcherRegisteredEvents.push({
                    name: eventName,
                    func: func,
                    source: self,
                });
            }
        });
        return this;
    },
    /** @this {any} */
    off(events, dest, func) {
        const self = this;
        events = events.split(/\s+/);
        events.forEach((eventName) => {
            self.__edispatcherEvents.off(eventName, func, dest);
            if (dest && dest.__eventDispatcherMixin) {
                dest.__edispatcherRegisteredEvents =
                    dest.__edispatcherRegisteredEvents.filter((el) => {
                        return !(
                            el.name === eventName &&
                            el.func === func &&
                            el.source === self
                        );
                    });
            }
        });
        return this;
    },
    /** @this {any} */
    trigger() {
        this.__edispatcherEvents.trigger.apply(
            this.__edispatcherEvents,
            arguments,
        );
        return this;
    },
    /** @this {any} */
    trigger_up: function (name, info) {
        const event = new OdooEvent(this, name, info);
        //console.info('event: ', name, info);
        this._trigger_up(event);
        return event;
    },
    /** @this {any} */
    _trigger_up: function (event) {
        let parent;
        this.__edispatcherEvents.trigger(event.name, event);
        if (!event.is_stopped() && (parent = this.getParent())) {
            parent._trigger_up(event);
        }
    },
    /** @this {any} */
    destroy() {
        const self = this;
        this.__edispatcherRegisteredEvents.forEach((event) => {
            event.source.__edispatcherEvents.off(event.name, event.func, self);
        });
        this.__edispatcherRegisteredEvents = [];
        this.__edispatcherEvents.callbackList().forEach(
            ((cal) => {
                this.off(cal[0], cal[2], cal[1]);
            }).bind(this),
        );
        this.__edispatcherEvents.off();
        ParentedMixin.destroy.call(this);
    },
});

function protectMethod(widget, fn) {
    return function (...args) {
        return new Promise((resolve, reject) => {
            Promise.resolve(fn.call(this, ...args))
                .then((result) => {
                    if (!widget.isDestroyed()) {
                        resolve(result);
                    }
                })
                .catch((reason) => {
                    if (!widget.isDestroyed()) {
                        reject(reason);
                    }
                });
        });
    };
}

const ServicesMixin = {
    bindService: function (serviceName) {
        const { services } = /** @type {any} */ (Component).env;
        const service = services[serviceName];
        if (!service) {
            throw new Error(`Service ${serviceName} is not available`);
        }
        if (serviceName in SERVICES_METADATA) {
            if (service instanceof Function) {
                return protectMethod(this, service);
            } else {
                const methods = SERVICES_METADATA[serviceName];
                const result = Object.create(service);
                for (const method of methods) {
                    result[method] = protectMethod(this, service[method]);
                }
                return result;
            }
        }
        return service;
    },
    /**
     * @param  {string} service
     * @param  {string} method
     * @return {any} result of the service called
     */
    call: function (service, method) {
        const args = Array.prototype.slice.call(arguments, 2);
        let result;
        this.trigger_up("call_service", {
            service: service,
            method: method,
            args: args,
            callback: function (r) {
                result = r;
            },
        });
        return result;
    },
};

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
 *             this.el.querySelector(".my_button").addEventListener("click", ...);
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
 *     myWidget.appendTo(someElement);
 *
 * With these two lines, the MyWidget instance was initialized, rendered,
 * inserted into the DOM inside the target element and its events were bound.
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
export const PublicWidget = Class.extend(EventDispatcherMixin, ServicesMixin, {
    // Backbone-ish API
    tagName: "div",
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
     * instance of this widget on page load for each DOM element according to
     * this selector. The `PublicWidget.el` element will then be that
     * particular DOM element. This should be the main way of instantiating
     * `PublicWidget` elements.
     *
     * The value can either be a string in which case it is considered as a
     * `querySelectorAll` selector to match, or a function expecting to return
     * all DOM elements to consider, which are inside the element received as
     * parameter of the function (or that element itself).
     *
     * @see selectorHas
     *
     * @todo do not make this part of the Widget but rather an info to give when
     * registering the widget.
     *
     * @type {string|function|false}
     */
    selector: false,
    /**
     * The `selectorHas` attribute, if defined, allows to filter elements found
     * through the `selector` attribute by only considering those which contain
     * at least an element which matches this `selectorHas` selector.
     *
     * Note that this is the equivalent of setting up a `selector` using the
     * `:has` pseudo-selector but that pseudo-selector is known to not be fully
     * supported in all browsers. To prevent useless crashes, using this
     * `selectorHas` attribute should be preferred.
     *
     * @type {string|false}
     */
    selectorHas: false,
    /**
     * Extension of @see Widget.events
     *
     * A description of the event handlers to bind/delegate once the widget
     * has been rendered::
     *
     *   'click .hello .world': 'async _onHelloWorldClick',
     *     _^_      _^_           _^_        _^_
     *      |        |             |          |
     *      |  (Optional) delegate |  Handler method name
     *      |  selector            |
     *      |                      |_ (Optional) space separated options
     *      |                          * async: use the automatic system
     *      |_ Event name                making handlers promise-ready (see
     *                                  makeButtonHandler, makeAsyncHandler)
     *
     * Note: the values may be replaced by a function declaration. This is
     * however a deprecated behavior.
     *
     * @type {Object}
     */
    events: {},

    /**
     * @constructor
     * @this {any}
     * @param {Object} parent
     * @param {Object} [options]
     */
    init: function (parent, options) {
        EventDispatcherMixin.init.call(this);
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
        const proms = [];
        if (this.jsLibs || this.cssLibs || this.assetLibs) {
            let assetsPromise = Promise.all([
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
                    });
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
        EventDispatcherMixin.destroy.call(this);
        if (this.el) {
            this._undelegateEvents();

            // If not done with a selector (attached to existing DOM), then
            // remove the elements added to the DOM.
            if (!this.selector) {
                this.el.remove();
            }
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Renders the current widget and appends it to the given element.
     *
     * @param {HTMLElement} target
     * @returns {Promise}
     */
    appendTo: function (target) {
        const self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.append(self.el);
        }, target);
    },
    /**
     * Attach the current widget to a dom element.
     *
     * @param {HTMLElement} target
     * @returns {Promise}
     */
    attachTo: function (target) {
        const self = this;
        this.setElement(/** @type {any} */ (target).el || target);
        return this.willStart().then(function () {
            if (self.__parentedDestroyed) {
                return;
            }
            return self.start();
        });
    },
    /**
     * Renders the current widget and inserts it after the given element.
     *
     * @param {HTMLElement} target
     * @returns {Promise}
     */
    insertAfter: function (target) {
        const self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.after(self.el);
        }, target);
    },
    /**
     * Renders the current widget and inserts it before the given element.
     *
     * @param {HTMLElement} target
     * @returns {Promise}
     */
    insertBefore: function (target) {
        const self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.before(self.el);
        }, target);
    },
    /**
     * Renders the current widget and prepends it to the given element.
     *
     * @param {HTMLElement} target
     * @returns {Promise}
     */
    prependTo: function (target) {
        const self = this;
        return this._widgetRenderAndInsert(function (t) {
            t.prepend(self.el);
        }, target);
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
     * Renders the current widget and replaces the given element.
     *
     * @param {HTMLElement} target
     * @returns {Promise}
     */
    replace: function (target) {
        return this._widgetRenderAndInsert((t) => {
            t.replaceWith(this.el);
        }, target);
    },
    /**
     * Re-sets the widget's root element (el).
     *
     * Includes:
     *
     * * re-delegating events
     * * re-binding sub-elements
     * * if the widget already had a root element, replacing the pre-existing
     *   element in the DOM
     *
     * @param {HTMLElement | Document | Node} element new root element for the widget
     * @returns {any} this
     */
    setElement: function (element) {
        if (this.el) {
            this._undelegateEvents();
        }

        if (element instanceof HTMLElement || element instanceof Document) {
            this.el = element;
        } else if (element && element.nodeType) {
            // Other node types (DocumentFragment, etc.)
            this.el = element;
        } else {
            this.el = element;
        }

        // Legacy compat: some subclasses still reference $el
        this.$el = this.el;

        this._delegateEvents();

        if (this.selector) {
            this.$target = this.el;
            this.target = this.el;
        }

        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Helper method, for ``this.el.querySelectorAll(selector)``
     *
     * @private
     * @param {string} selector CSS selector, rooted in el
     * @returns {NodeList|HTMLElement} selector match
     */
    $: function (selector) {
        if (selector === undefined) {
            return this.el;
        }
        if (this.el.querySelectorAll) {
            return this.el.querySelectorAll(selector);
        }
        return /** @type {NodeListOf<Element>} */ (/** @type {unknown} */ ([]));
    },
    /**
     * @see events
     * @override
     */
    _delegateEvents: function () {
        const self = this;
        // Create a new AbortController for this round of event delegation
        this.__eventAC = new AbortController();
        const signal = this.__eventAC.signal;

        const _delegateEvent = (method, key) => {
            const match = /^(\S+)(\s+(.*))?$/.exec(key);
            const event = match[1];
            const selector = match[3];

            // Strip jQuery-style namespaces (e.g. "click.widget_events" → "click")
            const eventName = event.split(".")[0];

            if (!selector) {
                self.el.addEventListener(eventName, method, { signal });
            } else {
                // Delegate: listen on root, filter by selector
                self.el.addEventListener(
                    eventName,
                    function (e) {
                        const delegateTarget = e.target.closest(selector);
                        if (
                            delegateTarget &&
                            self.el.contains(delegateTarget)
                        ) {
                            // Set delegateTarget for compat with code expecting it
                            Object.defineProperty(e, "currentTarget", {
                                value: delegateTarget,
                                configurable: true,
                            });
                            method.call(delegateTarget, e);
                        }
                    },
                    { signal },
                );
            }
        };
        Object.entries(this.events || {}).forEach(([event, method]) => {
            // If the method is a function, use the default Widget system
            if (typeof method !== "string") {
                _delegateEvent(self.proxy(method), event);
                return;
            }
            // If the method is only a function name without options, use the
            // default Widget system
            const methodOptions = method.split(" ");
            if (methodOptions.length <= 1) {
                _delegateEvent(self.proxy(method), event);
                return;
            }
            // If the method has no meaningful options, use the default Widget
            // system
            const isAsync = methodOptions.includes("async");
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
        let context;
        this.trigger_up("context_get", {
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
     * widget.
     *
     * @private
     * @return {HTMLElement}
     */
    _makeDescriptive: function () {
        const attrs = Object.assign({}, this.attributes || {});
        if (this.id) {
            attrs.id = this.id;
        }
        if (this.className) {
            attrs["class"] = this.className;
        }
        const el = document.createElement(this.tagName);
        for (const [key, value] of Object.entries(attrs)) {
            el.setAttribute(key, value);
        }
        return el;
    },
    /**
     * Re-sets the widget's root element and replaces the old root element
     * (if any) by the new one in the DOM.
     *
     * @private
     * @param {HTMLElement} el
     * @returns {any} this instance, so it can be chained
     */
    _replaceElement: function (el) {
        const oldEl = this.el;
        this.setElement(el);
        if (oldEl && oldEl !== this.el) {
            oldEl.replaceWith(this.el);
        }
        return this;
    },
    /**
     * Remove all handlers registered on this.el
     *
     * @private
     */
    _undelegateEvents: function () {
        if (this.__eventAC) {
            this.__eventAC.abort();
            this.__eventAC = null;
        }
    },
    /**
     * Render the widget.  This is a private method, and should really never be
     * called by anyone (except this widget).  It assumes that the widget was
     * not willStarted yet.
     *
     * @private
     * @param {function} insertion
     * @param {HTMLElement} target
     * @returns {Promise}
     */
    _widgetRenderAndInsert: function (insertion, target) {
        const self = this;
        return this.willStart().then(function () {
            if (self.__parentedDestroyed) {
                return;
            }
            self.renderElement();
            insertion(target);
            return self.start();
        });
    },
});

//::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

/**
 * The registry object contains the list of widgets that should be instantiated
 * thanks to their selector property if any.
 */
const registry = {};

export default {
    Widget: PublicWidget,
    registry: registry,

    ParentedMixin: ParentedMixin,
    EventDispatcherMixin: EventDispatcherMixin,
    ServicesMixin: ServicesMixin,
};
