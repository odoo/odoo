/** @odoo-module */

/**
 * Provides a way to start JS code for public contents.
 */

import dom from '@web/legacy/js/core/dom';
import Class from "@web/legacy/js/core/class";
import mixins from "@web/legacy/js/core/mixins";
import ServicesMixin from "@web/legacy/js/core/service_mixins";
import { loadBundle } from '@web/core/assets';
import { renderToElement } from "@web/core/utils/render";

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
 *             // stuff you want to make after the rendering, `this.$el` holds a correct value
 *             this.$(".my_button").click(/* an example of event binding * /);
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
 *     myWidget.appendTo($(".some-div"));
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
     * this selector. The `PublicWidget.$el / el` element will then be that
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
     *      |  (Optional) jQuery   |  Handler method name
     *      |  delegate selector   |
     *      |                      |_ (Optional) space separated options
     *      |                          * async: use the automatic system
     *      |_ Event name with           making handlers promise-ready (see
     *         potential jQuery          makeButtonHandler, makeAsyncHandler)
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
            proms.push(loadBundle(this));
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
     * associated $el DOM is not removed, if this was instantiated thanks to the
     * selector property).
     */
    destroy: function () {
        mixins.PropertiesMixin.destroy.call(this);
        if (this.$el) {
            this._undelegateEvents();

            // If not done with a selector (attached to existing DOM), then
            // remove the elements added to the DOM.
            if (!this.selector) {
                this.$el.remove();
            }
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Renders the current widget and appends it to the given jQuery object.
     *
     * @param {jQuery} target
     * @returns {Promise}
     */
    appendTo: function (target) {
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            self.$el.appendTo(t);
        }, target);
    },
    /**
     * Attach the current widget to a dom element
     *
     * @param {jQuery} target
     * @returns {Promise}
     */
    attachTo: function (target) {
        var self = this;
        this.setElement(target.$el || target);
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
     * @param {jQuery} target
     * @returns {Promise}
     */
    insertAfter: function (target) {
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            self.$el.insertAfter(t);
        }, target);
    },
    /**
     * Renders the current widget and inserts it before to the given jQuery
     * object.
     *
     * @param {jQuery} target
     * @returns {Promise}
     */
    insertBefore: function (target) {
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            self.$el.insertBefore(t);
        }, target);
    },
    /**
     * Renders the current widget and prepends it to the given jQuery object.
     *
     * @param {jQuery} target
     * @returns {Promise}
     */
    prependTo: function (target) {
        var self = this;
        return this._widgetRenderAndInsert(function (t) {
            self.$el.prependTo(t);
        }, target);
    },
    /**
     * Renders the element. The default implementation renders the widget using
     * QWeb, `this.template` must be defined. The context given to QWeb contains
     * the "widget" key that references `this`.
     */
    renderElement: function () {
        var $el;
        if (this.template) {
            $el = $(renderToElement(this.template, {widget: this}));
        } else {
            $el = this._makeDescriptive();
        }
        this._replaceElement($el);
    },
    /**
     * Renders the current widget and replaces the given jQuery object.
     *
     * @param target A jQuery object or a Widget instance.
     * @returns {Promise}
     */
    replace: function (target) {
        return this._widgetRenderAndInsert((t) => {
            this.$el.replaceAll(t);
        }, target);
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
        if (this.$el) {
            this._undelegateEvents();
        }

        this.$el = (element instanceof $) ? element : $(element);
        this.el = this.$el[0];

        this._delegateEvents();

        if (this.selector) {
            this.$target = this.$el;
            this.target = this.el;
        }

        return this;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
                self.$el.on(event, method);
            } else {
                self.$el.on(event, selector, method);
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
                method = dom.makeButtonHandler(method);
            } else {
                // Protect all handlers to be recalled while the previous
                // async handler call is not finished.
                method = dom.makeAsyncHandler(method);
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
     * @return {jQuery}
     */
    _makeDescriptive: function () {
        var attrs = Object.assign({}, this.attributes || {});
        if (this.id) {
            attrs.id = this.id;
        }
        if (this.className) {
            attrs['class'] = this.className;
        }
        var $el = $(document.createElement(this.tagName));
        if (Object.keys(attrs || {}).length > 0) {
            $el.attr(attrs);
        }
        return $el;
    },
    /**
     * Re-sets the widget's root element and replaces the old root element
     * (if any) by the new one in the DOM.
     *
     * @private
     * @param {HTMLElement | jQuery} $el
     * @returns {Widget} this instance, so it can be chained
     */
    _replaceElement: function ($el) {
        var $oldel = this.$el;
        this.setElement($el);
        if ($oldel && !$oldel.is(this.$el)) {
            if ($oldel.length > 1) {
                $oldel.wrapAll('<div/>');
                $oldel.parent().replaceWith(this.$el);
            } else {
                $oldel.replaceWith(this.$el);
            }
        }
        return this;
    },
    /**
     * Remove all handlers registered on this.$el
     *
     * @private
     */
    _undelegateEvents: function () {
        this.$el.off('.widget_events');
    },
    /**
     * Render the widget.  This is a private method, and should really never be
     * called by anyone (except this widget).  It assumes that the widget was
     * not willStarted yet.
     *
     * @private
     * @param {function: jQuery -> any} insertion
     * @param {jQuery} target
     * @returns {Promise}
     */
    _widgetRenderAndInsert: function (insertion, target) {
        var self = this;
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
     * @param {jQuery} [$from] - only check DOM elements which are descendant of
     *                         the given one. If not given, use this.$el.
     * @returns {Deferred}
     */
    _attachComponent: function (childInfo, $from) {
        var self = this;
        var $elements = dom.cssFind($from || this.$el, childInfo.selector);
        var defs = Array.from($elements).map((element) => {
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
     * @param {jQuery} [$from] - only check DOM elements which are descendant of
     *                         the given one. If not given, use this.$el.
     * @returns {Deferred}
     */
    _attachComponents: function ($from) {
        var self = this;
        var childInfos = this._getRegistry().getAll();
        var defs = childInfos.map((childInfo) => {
            return self._attachComponent(childInfo, $from);
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
