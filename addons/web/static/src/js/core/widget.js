odoo.define('web.Widget', function (require) {
"use strict";

var core = require('web.core');

var mixins = core.mixins;

/**
 * Base class for all visual components. Provides a lot of functionalities helpful
 * for the management of a part of the DOM.
 *
 * Widget handles:
 * - Rendering with QWeb.
 * - Life-cycle management and parenting (when a parent is destroyed, all its children are
 *     destroyed too).
 * - Insertion in DOM.
 *
 * Guide to create implementations of the Widget class:
 * ==============================================
 *
 * Here is a sample child class:
 *
 * MyWidget = openerp.base.Widget.extend({
 *     // the name of the QWeb template to use for rendering
 *     template: "MyQWebTemplate",
 *
 *     init: function(parent) {
 *         this._super(parent);
 *         // stuff that you want to init before the rendering
 *     },
 *     start: function() {
 *         // stuff you want to make after the rendering, `this.$el` holds a correct value
 *         this.$(".my_button").click(/* an example of event binding * /);
 *
 *         // if you have some asynchronous operations, it's a good idea to return
 *         // a promise in start()
 *         var promise = this.rpc(...);
 *         return promise;
 *     }
 * });
 *
 * Now this class can simply be used with the following syntax:
 *
 * var my_widget = new MyWidget(this);
 * my_widget.appendTo($(".some-div"));
 *
 * With these two lines, the MyWidget instance was inited, rendered, it was inserted into the
 * DOM inside the ".some-div" div and its events were binded.
 *
 * And of course, when you don't need that widget anymore, just do:
 *
 * my_widget.destroy();
 *
 * That will kill the widget in a clean way and erase its content from the dom.
 */


var Widget = core.Class.extend(mixins.PropertiesMixin, mixins.ServicesMixin, {
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
     * @type string
     */
    template: null,
    /**
     * Constructs the widget and sets its parent if a parent is given.
     *
     * @constructs openerp.Widget
     *
     * @param {openerp.Widget} parent Binds the current instance to the given Widget instance.
     * When that widget is destroyed by calling destroy(), the current instance will be
     * destroyed too. Can be null.
     */
    init: function (parent) {
        mixins.PropertiesMixin.init.call(this);
        this.setParent(parent);
        // Bind on_/do_* methods to this
        // We might remove this automatic binding in the future
        for (var name in this) {
            if(typeof(this[name]) == "function") {
                if((/^on_|^do_/).test(name)) {
                    this[name] = _.bind(this[name], this);
                }
            }
        }
        // FIXME: this should not be
        this.setElement(this._make_descriptive());
    },
    /**
     * Method called between init and start. Performs asynchronous calls required by start.
     *
     * This method should return a Deferred which is resolved when start can be executed.
     *
     * @return {jQuery.Deferred}
     */
    willStart: function () {
        return $.when();
    },
    /**
     * Destroys the current widget, also destroys all its children before destroying itself.
     */
    destroy: function () {
        _.each(this.getChildren(), function (el) {
            el.destroy();
        });
        if(this.$el) {
            this.$el.remove();
        }
        mixins.PropertiesMixin.destroy.call(this);
    },
    /**
     * Renders the current widget and appends it to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    appendTo: function (target) {
        var self = this;
        return this.__widgetRenderAndInsert(function (t) {
            self.$el.appendTo(t);
        }, target);
    },
    /**
     * Renders the current widget and prepends it to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    prependTo: function (target) {
        var self = this;
        return this.__widgetRenderAndInsert(function (t) {
            self.$el.prependTo(t);
        }, target);
    },
    /**
     * Renders the current widget and inserts it after to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    insertAfter: function (target) {
        var self = this;
        return this.__widgetRenderAndInsert(function (t) {
            self.$el.insertAfter(t);
        }, target);
    },
    /**
     * Renders the current widget and inserts it before to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    insertBefore: function (target) {
        var self = this;
        return this.__widgetRenderAndInsert(function (t) {
            self.$el.insertBefore(t);
        }, target);
    },
    /**
     * Attach the current widget to a dom element
     *
     * @param target A jQuery object or a Widget instance.
     */
    attachTo: function (target) {
        var self = this;
        this.setElement(target.$el || target);
        return this.willStart().then(function () {
            return self.start();
        });
    },
    /**
     * Renders the current widget and replaces the given jQuery object.
     *
     * @param target A jQuery object or a Widget instance.
     */
    replace: function (target) {
        return this.__widgetRenderAndInsert(_.bind(function (t) {
            this.$el.replaceAll(t);
        }, this), target);
    },
    __widgetRenderAndInsert: function (insertion, target) {
        var self = this;
        return this.willStart().then(function () {
            self.renderElement();
            insertion(target);
            return self.start();
        });
    },
    /**
     * Method called after rendering. Mostly used to bind actions, perform asynchronous
     * calls, etc...
     *
     * By convention, this method should return an object that can be passed to $.when()
     * to inform the caller when this widget has been initialized.
     *
     * @returns {jQuery.Deferred or any}
     */
    start: function () {
        return $.when();
    },
    /**
     * Renders the element. The default implementation renders the widget using QWeb,
     * `this.template` must be defined. The context given to QWeb contains the "widget"
     * key that references `this`.
     */
    renderElement: function () {
        var $el;
        if (this.template) {
            $el = $(core.qweb.render(this.template, {widget: this}).trim());
        } else {
            $el = this._make_descriptive();
        }
        this.replaceElement($el);
    },
    /**
     * Re-sets the widget's root element and replaces the old root element
     * (if any) by the new one in the DOM.
     *
     * @param {HTMLElement | jQuery} $el
     * @returns {*} this
     */
    replaceElement: function ($el) {
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
     * Re-sets the widget's root element (el/$el/$el).
     *
     * Includes:
     * * re-delegating events
     * * re-binding sub-elements
     * * if the widget already had a root element, replacing the pre-existing
     *   element in the DOM
     *
     * @param {HTMLElement | jQuery} element new root element for the widget
     * @return {*} this
     */
    setElement: function (element) {
        // NB: completely useless, as WidgetMixin#init creates a $el
        // always
        if (this.$el) {
            this.undelegateEvents();
        }

        this.$el = (element instanceof $) ? element : $(element);
        this.el = this.$el[0];

        this.delegateEvents();

        return this;
    },
    /**
     * Utility function to build small DOM elements.
     *
     * @param {String} tagName name of the DOM element to create
     * @param {Object} [attributes] map of DOM attributes to set on the element
     * @param {String} [content] HTML content to set on the element
     * @return {Element}
     */
    make: function (tagName, attributes, content) {
        var el = document.createElement(tagName);
        if (!_.isEmpty(attributes)) {
            $(el).attr(attributes);
        }
        if (content) {
            $(el).html(content);
        }
        return el;
    },
    /**
     * Makes a potential root element from the declarative builder of the
     * widget
     *
     * @return {jQuery}
     * @private
     */
    _make_descriptive: function () {
        var attrs = _.extend({}, this.attributes || {});
        if (this.id) { attrs.id = this.id; }
        if (this.className) { attrs['class'] = this.className; }
        return $(this.make(this.tagName, attrs));
    },
    delegateEvents: function () {
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
    undelegateEvents: function () {
        this.$el.off('.widget_events');
    },
    /**
     * Shortcut for ``this.$el.find(selector)``
     *
     * @param {String} selector CSS selector, rooted in $el
     * @returns {jQuery} selector match
     */
    $: function (selector) {
        if (selector === undefined)
            return this.$el;
        return this.$el.find(selector);
    },
    /**
     * Displays the widget
     */
    do_show: function () {
        this.$el.removeClass('o_hidden');
    },
    /**
     * Hides the widget
     */
    do_hide: function () {
        this.$el.addClass('o_hidden');
    },
    /**
     * Displays or hides the widget
     * @param {Boolean} [display] use true to show the widget or false to hide it
     */
    do_toggle: function (display) {
        if (_.isBoolean(display)) {
            display ? this.do_show() : this.do_hide();
        } else {
            this.$el.hasClass('o_hidden') ? this.do_show() : this.do_hide();
        }
    },
});

return Widget;

});
