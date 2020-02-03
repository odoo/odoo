odoo.define('web.Widget', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var mixins = require('web.mixins');
var ServicesMixin = require('web.ServicesMixin');

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
 * And of course, when you don't need that widget anymore, just do::
 *
 *     myWidget.destroy();
 *
 * That will kill the widget in a clean way and erase its content from the dom.
 */

var Widget = core.Class.extend(mixins.PropertiesMixin, ServicesMixin, {
    // Backbone-ish API
    tagName: 'div',
    id: null,
    className: null,
    attributes: {},
    events: {},
    /**
     * The name of the QWeb template that will be used for rendering. Must be
     * redefined in subclasses or the default render() method can not be used.
     *
     * @type {null|string}
     */
    template: null,
    /**
     * List of paths to xml files that need to be loaded before the widget can
     * be rendered. This will not induce loading anything that has already been
     * loaded.
     *
     * @type {null|string[]}
     */
    xmlDependencies: null,
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
     * Constructs the widget and sets its parent if a parent is given.
     *
     * @param {Widget|null} parent Binds the current instance to the given Widget
     *   instance. When that widget is destroyed by calling destroy(), the
     *   current instance will be destroyed too. Can be null.
     */
    init: function (parent) {
        mixins.PropertiesMixin.init.call(this);
        this.setParent(parent);
        // Bind on_/do_* methods to this
        // We might remove this automatic binding in the future
        for (var name in this) {
            if(typeof(this[name]) === "function") {
                if((/^on_|^do_/).test(name)) {
                    this[name] = this[name].bind(this);
                }
            }
        }
    },
    /**
     * Method called between @see init and @see start. Performs asynchronous
     * calls required by the rendering and the start method.
     *
     * This method should return a Promose which is resolved when start can be
     * executed.
     *
     * @returns {Promise}
     */
    willStart: function () {
        var proms = [];
        if (this.xmlDependencies) {
            proms.push.apply(proms, _.map(this.xmlDependencies, function (xmlPath) {
                return ajax.loadXML(xmlPath, core.qweb);
            }));
        }
        if (this.jsLibs || this.cssLibs || this.assetLibs) {
            proms.push(this._loadLibs(this));
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
     * Destroys the current widget, also destroys all its children before
     * destroying itself.
     */
    destroy: function () {
        mixins.PropertiesMixin.destroy.call(this);
        if (this.$el) {
            this.$el.remove();
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
     * Hides the widget
     */
    do_hide: function () {
        this.$el.addClass('o_hidden');
    },
    /**
     * Displays the widget
     */
    do_show: function () {
        this.$el.removeClass('o_hidden');
    },
    /**
     * Displays or hides the widget
     * @param {boolean} [display] use true to show the widget or false to hide it
     */
    do_toggle: function (display) {
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            this.$el.hasClass('o_hidden') ? this.do_show() : this.do_hide();
        }
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
            $el = $(core.qweb.render(this.template, {widget: this}).trim());
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
        return this._widgetRenderAndInsert(_.bind(function (t) {
            this.$el.replaceAll(t);
        }, this), target);
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
     * Attach event handlers for events described in the 'events' key
     *
     * @private
     */
    _delegateEvents: function () {
        var events = this.events;
        if (_.isEmpty(events)) { return; }

        for(var key in events) {
            if (!events.hasOwnProperty(key)) { continue; }

            var method = this.proxy(events[key]);

            var match = /^(\S+)(\s+(.*))?$/.exec(key);
            var event = match[1];
            var selector = match[3];

            event += '.widget_events';
            if (!selector) {
                this.$el.on(event, method);
            } else {
                this.$el.on(event, selector, method);
            }
        }
    },
    /**
     * Makes a potential root element from the declarative builder of the
     * widget
     *
     * @private
     * @return {jQuery}
     */
    _makeDescriptive: function () {
        var attrs = _.extend({}, this.attributes || {});
        if (this.id) {
            attrs.id = this.id;
        }
        if (this.className) {
            attrs['class'] = this.className;
        }
        var $el = $(document.createElement(this.tagName));
        if (!_.isEmpty(attrs)) {
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

return Widget;

});
