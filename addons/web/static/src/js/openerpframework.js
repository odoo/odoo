/*
 * Copyright (c) 2012, OpenERP S.A.
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this
 *    list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
 * ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

 /*
    The only dependencies of this file are underscore >= 1.3.1, jQuery >= 1.8.3 and
    QWeb >= 1.0.0 . No dependencies shall be added.

    This file must compile in EcmaScript 3 and work in IE7.
 */

(function() {
/* jshint es3: true */
"use strict";

function declare($, _, QWeb2) {
var openerp = {};

/**
 * Improved John Resig's inheritance, based on:
 *
 * Simple JavaScript Inheritance
 * By John Resig http://ejohn.org/
 * MIT Licensed.
 *
 * Adds "include()"
 *
 * Defines The Class object. That object can be used to define and inherit classes using
 * the extend() method.
 *
 * Example:
 *
 * var Person = openerp.Class.extend({
 *  init: function(isDancing){
 *     this.dancing = isDancing;
 *   },
 *   dance: function(){
 *     return this.dancing;
 *   }
 * });
 *
 * The init() method act as a constructor. This class can be instancied this way:
 *
 * var person = new Person(true);
 * person.dance();
 *
 * The Person class can also be extended again:
 *
 * var Ninja = Person.extend({
 *   init: function(){
 *     this._super( false );
 *   },
 *   dance: function(){
 *     // Call the inherited version of dance()
 *     return this._super();
 *   },
 *   swingSword: function(){
 *     return true;
 *   }
 * });
 *
 * When extending a class, each re-defined method can use this._super() to call the previous
 * implementation of that method.
 */
(function() {
    var initializing = false,
        fnTest = /xyz/.test(function(){xyz();}) ? /\b_super\b/ : /.*/;
    // The web Class implementation (does nothing)
    openerp.Class = function(){};

    /**
     * Subclass an existing class
     *
     * @param {Object} prop class-level properties (class attributes and instance methods) to set on the new class
     */
    openerp.Class.extend = function() {
        var _super = this.prototype;
        // Support mixins arguments
        var args = _.toArray(arguments);
        args.unshift({});
        var prop = _.extend.apply(_,args);

        // Instantiate a web class (but only create the instance,
        // don't run the init constructor)
        initializing = true;
        var This = this;
        var prototype = new This();
        initializing = false;

        // Copy the properties over onto the new prototype
        _.each(prop, function(val, name) {
            // Check if we're overwriting an existing function
            prototype[name] = typeof prop[name] == "function" &&
                              fnTest.test(prop[name]) ?
                    (function(name, fn) {
                        return function() {
                            var tmp = this._super;

                            // Add a new ._super() method that is the same
                            // method but on the super-class
                            this._super = _super[name];

                            // The method only need to be bound temporarily, so
                            // we remove it when we're done executing
                            var ret = fn.apply(this, arguments);
                            this._super = tmp;

                            return ret;
                        };
                    })(name, prop[name]) :
                    prop[name];
        });

        // The dummy class constructor
        function Class() {
            if(this.constructor !== openerp.Class){
                throw new Error("You can only instanciate objects with the 'new' operator");
            }
            // All construction is actually done in the init method
            this._super = null;
            if (!initializing && this.init) {
                var ret = this.init.apply(this, arguments);
                if (ret) { return ret; }
            }
            return this;
        }
        Class.include = function (properties) {
            _.each(properties, function(val, name) {
                if (typeof properties[name] !== 'function'
                        || !fnTest.test(properties[name])) {
                    prototype[name] = properties[name];
                } else if (typeof prototype[name] === 'function'
                           && prototype.hasOwnProperty(name)) {
                    prototype[name] = (function (name, fn, previous) {
                        return function () {
                            var tmp = this._super;
                            this._super = previous;
                            var ret = fn.apply(this, arguments);
                            this._super = tmp;
                            return ret;
                        };
                    })(name, properties[name], prototype[name]);
                } else if (typeof _super[name] === 'function') {
                    prototype[name] = (function (name, fn) {
                        return function () {
                            var tmp = this._super;
                            this._super = _super[name];
                            var ret = fn.apply(this, arguments);
                            this._super = tmp;
                            return ret;
                        };
                    })(name, properties[name]);
                }
            });
        };

        // Populate our constructed prototype object
        Class.prototype = prototype;

        // Enforce the constructor to be what we expect
        Class.constructor = Class;

        // And make this class extendable
        Class.extend = this.extend;

        return Class;
    };
})();

// Mixins

/**
 * Mixin to structure objects' life-cycles folowing a parent-children
 * relationship. Each object can a have a parent and multiple children.
 * When an object is destroyed, all its children are destroyed too releasing
 * any resource they could have reserved before.
 */
openerp.ParentedMixin = {
    __parentedMixin : true,
    init: function() {
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
    setParent : function(parent) {
        if (this.getParent()) {
            if (this.getParent().__parentedMixin) {
                this.getParent().__parentedChildren = _.without(this
                        .getParent().getChildren(), this);
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
    getParent : function() {
        return this.__parentedParent;
    },
    /**
     * Return a list of the children of the current object.
     */
    getChildren : function() {
        return _.clone(this.__parentedChildren);
    },
    /**
     * Returns true if destroy() was called on the current object.
     */
    isDestroyed : function() {
        return this.__parentedDestroyed;
    },
    /**
        Utility method to only execute asynchronous actions if the current
        object has not been destroyed.

        @param {$.Deferred} promise The promise representing the asynchronous
                                    action.
        @param {bool} [reject=false] If true, the returned promise will be
                                     rejected with no arguments if the current
                                     object is destroyed. If false, the
                                     returned promise will never be resolved
                                     or rejected.
        @returns {$.Deferred} A promise that will mirror the given promise if
                              everything goes fine but will either be rejected
                              with no arguments or never resolved if the
                              current object is destroyed.
    */
    alive: function(promise, reject) {
        var self = this;
        return $.Deferred(function (def) {
            promise.then(function () {
                if (!self.isDestroyed()) {
                    def.resolve.apply(def, arguments);
                }
            }, function () {
                if (!self.isDestroyed()) {
                    def.reject.apply(def, arguments);
                }
            }).always(function () {
                if (reject) {
                    // noop if def already resolved or rejected
                    def.reject();
                }
                // otherwise leave promise in limbo
            });
        }).promise();
    },
    /**
     * Inform the object it should destroy itself, releasing any
     * resource it could have reserved.
     */
    destroy : function() {
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        this.setParent(undefined);
        this.__parentedDestroyed = true;
    },
    /**
     * Find the closest ancestor matching predicate
     */
    findAncestor: function (predicate) {
        var ancestor = this;
        while (!(predicate(ancestor)) && ancestor && ancestor.getParent) {
            ancestor = ancestor.getParent();
        }
        return ancestor;
    },
};

/**
 * Backbone's events. Do not ever use it directly, use EventDispatcherMixin instead.
 *
 * This class just handle the dispatching of events, it is not meant to be extended,
 * nor used directly. All integration with parenting and automatic unregistration of
 * events is done in EventDispatcherMixin.
 *
 * Copyright notice for the following Class:
 *
 * (c) 2010-2012 Jeremy Ashkenas, DocumentCloud Inc.
 * Backbone may be freely distributed under the MIT license.
 * For all details and documentation:
 * http://backbonejs.org
 *
 */
var Events = openerp.Class.extend({
    on : function(events, callback, context) {
        var ev;
        events = events.split(/\s+/);
        var calls = this._callbacks || (this._callbacks = {});
        while ((ev = events.shift())) {
            var list = calls[ev] || (calls[ev] = {});
            var tail = list.tail || (list.tail = list.next = {});
            tail.callback = callback;
            tail.context = context;
            list.tail = tail.next = {};
        }
        return this;
    },

    off : function(events, callback, context) {
        var ev, calls, node;
        if (!events) {
            delete this._callbacks;
        } else if ((calls = this._callbacks)) {
            events = events.split(/\s+/);
            while ((ev = events.shift())) {
                node = calls[ev];
                delete calls[ev];
                if (!callback || !node)
                    continue;
                while ((node = node.next) && node.next) {
                    if (node.callback === callback
                            && (!context || node.context === context))
                        continue;
                    this.on(ev, node.callback, node.context);
                }
            }
        }
        return this;
    },

    callbackList: function() {
        var lst = [];
        _.each(this._callbacks || {}, function(el, eventName) {
            var node = el;
            while ((node = node.next) && node.next) {
                lst.push([eventName, node.callback, node.context]);
            }
        });
        return lst;
    },

    trigger : function(events) {
        var event, node, calls, tail, args, all, rest;
        if (!(calls = this._callbacks))
            return this;
        all = calls['all'];
        (events = events.split(/\s+/)).push(null);
        // Save references to the current heads & tails.
        while ((event = events.shift())) {
            if (all)
                events.push({
                    next : all.next,
                    tail : all.tail,
                    event : event
                });
            if (!(node = calls[event]))
                continue;
            events.push({
                next : node.next,
                tail : node.tail
            });
        }
        rest = Array.prototype.slice.call(arguments, 1);
        while ((node = events.pop())) {
            tail = node.tail;
            args = node.event ? [ node.event ].concat(rest) : rest;
            while ((node = node.next) !== tail) {
                node.callback.apply(node.context || this, args);
            }
        }
        return this;
    }
});

/**
    Mixin containing an event system. Events are also registered by specifying the target object
    (the object which will receive the event when it is raised). Both the event-emitting object
    and the target object store or reference to each other. This is used to correctly remove all
    reference to the event handler when any of the object is destroyed (when the destroy() method
    from ParentedMixin is called). Removing those references is necessary to avoid memory leak
    and phantom events (events which are raised and sent to a previously destroyed object).
*/
openerp.EventDispatcherMixin = _.extend({}, openerp.ParentedMixin, {
    __eventDispatcherMixin: true,
    init: function() {
        openerp.ParentedMixin.init.call(this);
        this.__edispatcherEvents = new Events();
        this.__edispatcherRegisteredEvents = [];
    },
    on: function(events, dest, func) {
        var self = this;
        if (!(func instanceof Function)) {
            throw new Error("Event handler must be a function.");
        }
        events = events.split(/\s+/);
        _.each(events, function(eventName) {
            self.__edispatcherEvents.on(eventName, func, dest);
            if (dest && dest.__eventDispatcherMixin) {
                dest.__edispatcherRegisteredEvents.push({name: eventName, func: func, source: self});
            }
        });
        return this;
    },
    off: function(events, dest, func) {
        var self = this;
        events = events.split(/\s+/);
        _.each(events, function(eventName) {
            self.__edispatcherEvents.off(eventName, func, dest);
            if (dest && dest.__eventDispatcherMixin) {
                dest.__edispatcherRegisteredEvents = _.filter(dest.__edispatcherRegisteredEvents, function(el) {
                    return !(el.name === eventName && el.func === func && el.source === self);
                });
            }
        });
        return this;
    },
    trigger: function(events) {
        this.__edispatcherEvents.trigger.apply(this.__edispatcherEvents, arguments);
        return this;
    },
    destroy: function() {
        var self = this;
        _.each(this.__edispatcherRegisteredEvents, function(event) {
            event.source.__edispatcherEvents.off(event.name, event.func, self);
        });
        this.__edispatcherRegisteredEvents = [];
        _.each(this.__edispatcherEvents.callbackList(), function(cal) {
            this.off(cal[0], cal[2], cal[1]);
        }, this);
        this.__edispatcherEvents.off();
        openerp.ParentedMixin.destroy.call(this);
    }
});

openerp.PropertiesMixin = _.extend({}, openerp.EventDispatcherMixin, {
    init: function() {
        openerp.EventDispatcherMixin.init.call(this);
        this.__getterSetterInternalMap = {};
    },
    set: function(arg1, arg2, arg3) {
        var map;
        var options;
        if (typeof arg1 === "string") {
            map = {};
            map[arg1] = arg2;
            options = arg3 || {};
        } else {
            map = arg1;
            options = arg2 || {};
        }
        var self = this;
        var changed = false;
        _.each(map, function(val, key) {
            var tmp = self.__getterSetterInternalMap[key];
            if (tmp === val)
                return;
            changed = true;
            self.__getterSetterInternalMap[key] = val;
            if (! options.silent)
                self.trigger("change:" + key, self, {
                    oldValue: tmp,
                    newValue: val
                });
        });
        if (changed)
            self.trigger("change", self);
    },
    get: function(key) {
        return this.__getterSetterInternalMap[key];
    }
});

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
 *         this.$el.find(".my_button").click(/* an example of event binding * /);
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
openerp.Widget = openerp.Class.extend(openerp.PropertiesMixin, {
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
    init: function(parent) {
        openerp.PropertiesMixin.init.call(this);
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
     * Destroys the current widget, also destroys all its children before destroying itself.
     */
    destroy: function() {
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        if(this.$el) {
            this.$el.remove();
        }
        openerp.PropertiesMixin.destroy.call(this);
    },
    /**
     * Renders the current widget and appends it to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    appendTo: function(target) {
        var self = this;
        return this.__widgetRenderAndInsert(function(t) {
            self.$el.appendTo(t);
        }, target);
    },
    /**
     * Renders the current widget and prepends it to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    prependTo: function(target) {
        var self = this;
        return this.__widgetRenderAndInsert(function(t) {
            self.$el.prependTo(t);
        }, target);
    },
    /**
     * Renders the current widget and inserts it after to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    insertAfter: function(target) {
        var self = this;
        return this.__widgetRenderAndInsert(function(t) {
            self.$el.insertAfter(t);
        }, target);
    },
    /**
     * Renders the current widget and inserts it before to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    insertBefore: function(target) {
        var self = this;
        return this.__widgetRenderAndInsert(function(t) {
            self.$el.insertBefore(t);
        }, target);
    },
    /**
     * Renders the current widget and replaces the given jQuery object.
     *
     * @param target A jQuery object or a Widget instance.
     */
    replace: function(target) {
        return this.__widgetRenderAndInsert(_.bind(function(t) {
            this.$el.replaceAll(t);
        }, this), target);
    },
    __widgetRenderAndInsert: function(insertion, target) {
        this.renderElement();
        insertion(target);
        return this.start();
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
    start: function() {
        return $.when();
    },
    /**
     * Renders the element. The default implementation renders the widget using QWeb,
     * `this.template` must be defined. The context given to QWeb contains the "widget"
     * key that references `this`.
     */
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(openerp.qweb.render(this.template, {widget: this}).trim());
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
            $oldel.replaceWith(this.$el);
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
    $: function(selector) {
        if (selector === undefined)
            return this.$el;
        return this.$el.find(selector);
    },
    /**
     * Proxies a method of the object, in order to keep the right ``this`` on
     * method invocations.
     *
     * This method is similar to ``Function.prototype.bind`` or ``_.bind``, and
     * even more so to ``jQuery.proxy`` with a fundamental difference: its
     * resolution of the method being called is lazy, meaning it will use the
     * method as it is when the proxy is called, not when the proxy is created.
     *
     * Other methods will fix the bound method to what it is when creating the
     * binding/proxy, which is fine in most javascript code but problematic in
     * OpenERP Web where developers may want to replace existing callbacks with
     * theirs.
     *
     * The semantics of this precisely replace closing over the method call.
     *
     * @param {String|Function} method function or name of the method to invoke
     * @returns {Function} proxied method
     */
    proxy: function (method) {
        var self = this;
        return function () {
            var fn = (typeof method === 'string') ? self[method] : method;
            return fn.apply(self, arguments);
        };
    }
});

var genericJsonRpc = function(fct_name, params, fct) {
    var data = {
        jsonrpc: "2.0",
        method: fct_name,
        params: params,
        id: Math.floor(Math.random() * 1000 * 1000 * 1000)
    };
    var xhr = fct(data);
    var result = xhr.pipe(function(result) {
        if (result.error !== undefined) {
            console.error("Server application error", result.error);
            return $.Deferred().reject("server", result.error);
        } else {
            return result.result;
        }
    }, function() {
        //console.error("JsonRPC communication error", _.toArray(arguments));
        var def = $.Deferred();
        return def.reject.apply(def, ["communication"].concat(_.toArray(arguments)));
    });
    // FIXME: jsonp?
    result.abort = function () { xhr.abort && xhr.abort(); };
    return result;
};

/**
 * Replacer function for JSON.stringify, serializes Date objects to UTC
 * datetime in the OpenERP Server format.
 *
 * However, if a serialized value has a toJSON method that method is called
 * *before* the replacer is invoked. Date#toJSON exists, and thus the value
 * passed to the replacer is a string, the original Date has to be fetched
 * on the parent object (which is provided as the replacer's context).
 *
 * @param {String} k
 * @param {Object} v
 * @returns {Object}
 */
function date_to_utc(k, v) {
    var value = this[k];
    if (!(value instanceof Date)) { return v; }

    return openerp.datetime_to_str(value);
}

openerp.jsonRpc = function(url, fct_name, params, settings) {
    return genericJsonRpc(fct_name, params, function(data) {
        return $.ajax(url, _.extend({}, settings, {
            url: url,
            dataType: 'json',
            type: 'POST',
            data: JSON.stringify(data, date_to_utc),
            contentType: 'application/json'
        }));
    });
};

openerp.jsonpRpc = function(url, fct_name, params, settings) {
    settings = settings || {};
    return genericJsonRpc(fct_name, params, function(data) {
        var payload_str = JSON.stringify(data, date_to_utc);
        var payload_url = $.param({r:payload_str});
        var force2step = settings.force2step || false;
        delete settings.force2step;
        var session_id = settings.session_id || null;
        delete settings.session_id;
        if (payload_url.length < 2000 && ! force2step) {
            return $.ajax(url, _.extend({}, settings, {
                url: url,
                dataType: 'jsonp',
                jsonp: 'jsonp',
                type: 'GET',
                cache: false,
                data: {r: payload_str, session_id: session_id}
            }));
        } else {
            var args = {session_id: session_id, id: data.id};
            var ifid = _.uniqueId('oe_rpc_iframe');
            var html = "<iframe src='javascript:false;' name='" + ifid + "' id='" + ifid + "' style='display:none'></iframe>";
            var $iframe = $(html);
            var nurl = 'jsonp=1&' + $.param(args);
            nurl = url.indexOf("?") !== -1 ? url + "&" + nurl : url + "?" + nurl;
            var $form = $('<form>')
                        .attr('method', 'POST')
                        .attr('target', ifid)
                        .attr('enctype', "multipart/form-data")
                        .attr('action', nurl)
                        .append($('<input type="hidden" name="r" />').attr('value', payload_str))
                        .hide()
                        .appendTo($('body'));
            var cleanUp = function() {
                if ($iframe) {
                    $iframe.unbind("load").remove();
                }
                $form.remove();
            };
            var deferred = $.Deferred();
            // the first bind is fired up when the iframe is added to the DOM
            $iframe.bind('load', function() {
                // the second bind is fired up when the result of the form submission is received
                $iframe.unbind('load').bind('load', function() {
                    $.ajax({
                        url: url,
                        dataType: 'jsonp',
                        jsonp: 'jsonp',
                        type: 'GET',
                        cache: false,
                        data: {session_id: session_id, id: data.id}
                    }).always(function() {
                        cleanUp();
                    }).done(function() {
                        deferred.resolve.apply(deferred, arguments);
                    }).fail(function() {
                        deferred.reject.apply(deferred, arguments);
                    });
                });
                // now that the iframe can receive data, we fill and submit the form
                $form.submit();
            });
            // append the iframe to the DOM (will trigger the first load)
            $form.after($iframe);
            if (settings.timeout) {
                realSetTimeout(function() {
                    deferred.reject({});
                }, settings.timeout);
            }
            return deferred;
        }
    });
};

openerp.loadCSS = function (url) {
    if (!$('link[href="' + url + '"]').length) {
        $('head').append($('<link>', {
            'href': url,
            'rel': 'stylesheet',
            'type': 'text/css'
        }));
    }
};
openerp.loadJS = function (url) {
    var def = $.Deferred();
    if ($('script[src="' + url + '"]').length) {
        def.resolve();
    } else {
        var script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = url;
        script.onload = script.onreadystatechange = function() {
            if ((script.readyState && script.readyState != "loaded" && script.readyState != "complete") || script.onload_done) {
                return;
            }
            script.onload_done = true;
            def.resolve(url);
        };
        script.onerror = function () {
            console.error("Error loading file", script.src);
            def.reject(url);
        };
        var head = document.head || document.getElementsByTagName('head')[0];
        head.appendChild(script);
    }
    return def;
};
openerp.loadBundle = function (name) {
    return $.when(
        openerp.loadCSS('/web/css/' + name),
        openerp.loadJS('/web/js/' + name)
    );
};

var realSetTimeout = function(fct, millis) {
    var finished = new Date().getTime() + millis;
    var wait = function() {
        var current = new Date().getTime();
        if (current < finished) {
            setTimeout(wait, finished - current);
        } else {
            fct();
        }
    };
    setTimeout(wait, millis);
};

openerp.Session = openerp.Class.extend(openerp.PropertiesMixin, {
    triggers: {
        'request': 'Request sent',
        'response': 'Response received',
        'response_failed': 'HTTP Error response or timeout received',
        'error': 'The received response is an JSON-RPC error'
    },
    /**
    @constructs openerp.Session
    
    @param parent The parent of the newly created object.
    @param {String} origin Url of the OpenERP server to contact with this session object
    or `null` if the server to contact is the origin server.
    @param {Dict} options A dictionary that can contain the following options:
        
        * "override_session": Default to false. If true, the current session object will
          not try to re-use a previously created session id stored in a cookie.
        * "session_id": Default to null. If specified, the specified session_id will be used
          by this session object. Specifying this option automatically implies that the option
          "override_session" is set to true.
     */
    init: function(parent, origin, options) {
        openerp.PropertiesMixin.init.call(this, parent);
        options = options || {};
        this.server = null;
        this.session_id = options.session_id || null;
        this.override_session = options.override_session || !!options.session_id || false;
        this.avoid_recursion = false;
        this.use_cors = options.use_cors || false;
        this.setup(origin);
    },
    setup: function(origin) {
        // must be able to customize server
        var window_origin = location.protocol + "//" + location.host;
        origin = origin ? origin.replace( /\/+$/, '') : window_origin;
        if (!_.isUndefined(this.origin) && this.origin !== origin)
            throw new Error('Session already bound to ' + this.origin);
        else
            this.origin = origin;
        this.prefix = this.origin;
        this.server = this.origin; // keep chs happy
        this.origin_server = this.origin === window_origin;
    },
    /**
     * (re)loads the content of a session: db name, username, user id, session
     * context and status of the support contract
     *
     * @returns {$.Deferred} deferred indicating the session is done reloading
     */
    session_reload: function () {
        var self = this;
        return self.rpc("/web/session/get_session_info", {}).then(function(result) {
            delete result.session_id;
            _.extend(self, result);
        });
    },
    /**
     * The session is validated either by login or by restoration of a previous session
     */
    session_authenticate: function(db, login, password) {
        var self = this;
        var params = {db: db, login: login, password: password};
        return this.rpc("/web/session/authenticate", params).then(function(result) {
            if (!result.uid) {
                return $.Deferred().reject();
            }
            delete result.session_id;
            _.extend(self, result);
        });
    },
    check_session_id: function() {
        var self = this;
        if (this.avoid_recursion || self.use_cors)
            return $.when();
        if (this.session_id)
            return $.when(); // we already have the session id
        if (this.override_session || ! this.origin_server) {
            // If we don't use the origin server we consider we should always create a new session.
            // Even if some browsers could support cookies when using jsonp that behavior is
            // not consistent and the browser creators are tending to removing that feature.
            this.avoid_recursion = true;
            return this.rpc("/gen_session_id", {}).then(function(result) {
                self.session_id = result;
            }).always(function() {
                self.avoid_recursion = false;
            });
        } else {
            // normal use case, just use the cookie
            self.session_id = openerp.get_cookie("session_id");
            return $.when();
        }
    },
    /**
     * Executes an RPC call, registering the provided callbacks.
     *
     * Registers a default error callback if none is provided, and handles
     * setting the correct session id and session context in the parameter
     * objects
     *
     * @param {String} url RPC endpoint
     * @param {Object} params call parameters
     * @param {Object} options additional options for rpc call
     * @param {Function} success_callback function to execute on RPC call success
     * @param {Function} error_callback function to execute on RPC call failure
     * @returns {jQuery.Deferred} jquery-provided ajax deferred
     */
    rpc: function(url, params, options) {
        var self = this;
        options = _.clone(options || {});
        var shadow = options.shadow || false;
        delete options.shadow;

        return self.check_session_id().then(function() {
            // TODO: remove
            if (! _.isString(url)) {
                _.extend(options, url);
                url = url.url;
            }
            // TODO correct handling of timeouts
            if (! shadow)
                self.trigger('request');
            var fct;
            if (self.origin_server) {
                fct = openerp.jsonRpc;
                if (self.override_session) {
                    options.headers = _.extend({}, options.headers, {
                        "X-Openerp-Session-Id": self.override_session ? self.session_id || '' : ''
                    });
                }
            } else if (self.use_cors) {
                fct = openerp.jsonRpc;
                url = self.url(url, null);
                options.session_id = self.session_id || '';
                if (self.override_session) {
                    options.headers = _.extend({}, options.headers, {
                        "X-Openerp-Session-Id": self.override_session ? self.session_id || '' : ''
                    });
                }
            } else {
                fct = openerp.jsonpRpc;
                url = self.url(url, null);
                options.session_id = self.session_id || '';
            }
            var p = fct(url, "call", params, options);
            p = p.then(function (result) {
                if (! shadow)
                    self.trigger('response');
                return result;
            }, function(type, error, textStatus, errorThrown) {
                if (type === "server") {
                    if (! shadow)
                        self.trigger('response');
                    if (error.code === 100) {
                        self.uid = false;
                    }
                    return $.Deferred().reject(error, $.Event());
                } else {
                    if (! shadow)
                        self.trigger('response_failed');
                    var nerror = {
                        code: -32098,
                        message: "XmlHttpRequestError " + errorThrown,
                        data: {type: "xhr"+textStatus, debug: error.responseText, objects: [error, errorThrown] }
                    };
                    return $.Deferred().reject(nerror, $.Event());
                }
            });
            return p.fail(function() { // Allow deferred user to disable rpc_error call in fail
                p.fail(function(error, event) {
                    if (!event.isDefaultPrevented()) {
                        self.trigger('error', error, event);
                    }
                });
            });
        });
    },
    url: function(path, params) {
        params = _.extend(params || {});
        if (this.override_session || (! this.origin_server))
            params.session_id = this.session_id;
        var qs = $.param(params);
        if (qs.length > 0)
            qs = "?" + qs;
        var prefix = _.any(['http://', 'https://', '//'], function(el) {
            return path.length >= el.length && path.slice(0, el.length) === el;
        }) ? '' : this.prefix; 
        return prefix + path + qs;
    },
    model: function(model_name) {
        return new openerp.Model(this, model_name);
    }
});

openerp.Model = openerp.Class.extend({
    /**
    new openerp.Model([session,] model_name)

    @constructs instance.Model
    @extends instance.Class
    
    @param {openerp.Session} [session] The session object used to communicate with
    the server.
    @param {String} model_name name of the OpenERP model this object is bound to
    @param {Object} [context]
    @param {Array} [domain]
    */
    init: function () {
        var session, model_name;
        var args = _.toArray(arguments);
        args.reverse();
        session = args.pop();
        if (session && ! (session instanceof openerp.Session)) {
            model_name = session;
            session = null;
        } else {
            model_name = args.pop();
        }

        this.name = model_name;
        this._session = session;
    },
    session: function() {
        if (! this._session)
            throw new Error("Not session specified");
        return this._session;
    },
    /**
     * Call a method (over RPC) on the bound OpenERP model.
     *
     * @param {String} method name of the method to call
     * @param {Array} [args] positional arguments
     * @param {Object} [kwargs] keyword arguments
     * @param {Object} [options] additional options for the rpc() method
     * @returns {jQuery.Deferred<>} call result
     */
    call: function (method, args, kwargs, options) {
        args = args || [];
        kwargs = kwargs || {};
        if (!_.isArray(args)) {
            // call(method, kwargs)
            kwargs = args;
            args = [];
        }
        var call_kw = '/web/dataset/call_kw/' + this.name + '/' + method;
        return this.session().rpc(call_kw, {
            model: this.name,
            method: method,
            args: args,
            kwargs: kwargs
        }, options);
    }
});

/** OpenERP Translations */
openerp.TranslationDataBase = openerp.Class.extend(/** @lends instance.TranslationDataBase# */{
    /**
     * @constructs instance.TranslationDataBase
     * @extends instance.Class
     */
    init: function() {
        this.db = {};
        this.parameters = {"direction": 'ltr',
                        "date_format": '%m/%d/%Y',
                        "time_format": '%H:%M:%S',
                        "grouping": [],
                        "decimal_point": ".",
                        "thousands_sep": ","};
    },
    set_bundle: function(translation_bundle) {
        var self = this;
        this.db = {};
        var modules = _.keys(translation_bundle.modules);
        modules.sort();
        if (_.include(modules, "web")) {
            modules = ["web"].concat(_.without(modules, "web"));
        }
        _.each(modules, function(name) {
            self.add_module_translation(translation_bundle.modules[name]);
        });
        if (translation_bundle.lang_parameters) {
            this.parameters = translation_bundle.lang_parameters;
        }
    },
    add_module_translation: function(mod) {
        var self = this;
        _.each(mod.messages, function(message) {
            self.db[message.id] = message.string;
        });
    },
    build_translation_function: function() {
        var self = this;
        var fcnt = function(str) {
            var tmp = self.get(str);
            return tmp === undefined ? str : tmp;
        };
        fcnt.database = this;
        return fcnt;
    },
    get: function(key) {
        return this.db[key];
    },
    /**
        Loads the translations from an OpenERP server.

        @param {openerp.Session} session The session object to contact the server.
        @param {Array} [modules] The list of modules to load the translation. If not specified,
        it will default to all the modules installed in the current database.
        @param {Object} [lang] lang The language. If not specified it will default to the language
        of the current user.
        @returns {jQuery.Deferred}
    */
    load_translations: function(session, modules, lang) {
        var self = this;
        return session.rpc('/web/webclient/translations', {
            "mods": modules || null,
            "lang": lang || null
        }).done(function(trans) {
            self.set_bundle(trans);
        });
    }
});

openerp._t = new openerp.TranslationDataBase().build_translation_function();

openerp.get_cookie = function(c_name) {
    var cookies = document.cookie ? document.cookie.split('; ') : [];
    for (var i = 0, l = cookies.length; i < l; i++) {
        var parts = cookies[i].split('=');
        var name = parts.shift();
        var cookie = parts.join('=');

        if (c_name && c_name === name) {
            return cookie;
        }
    }
    return "";
};

openerp.qweb = new QWeb2.Engine();

openerp.qweb.default_dict = {
    '_' : _,
    'JSON': JSON,
    '_t' : openerp._t
};

openerp.Mutex = openerp.Class.extend({
    init: function() {
        this.def = $.Deferred().resolve();
    },
    exec: function(action) {
        var current = this.def;
        var next = this.def = $.Deferred();
        return current.then(function() {
            return $.when(action()).always(function() {
                next.resolve();
            });
        });
    }
});

/**
 * Converts a string to a Date javascript object using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35.832').
 * 
 * The time zone is assumed to be UTC (standard for OpenERP 6.1)
 * and will be converted to the browser's time zone.
 * 
 * @param {String} str A string representing a datetime.
 * @returns {Date}
 */
openerp.str_to_datetime = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d(?:\.(\d+))?)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid datetime");
    }
    var tmp = new Date(2000,0,1);
    tmp.setUTCMonth(1970);
    tmp.setUTCMonth(0);
    tmp.setUTCDate(1);
    tmp.setUTCFullYear(parseFloat(res[1]));
    tmp.setUTCMonth(parseFloat(res[2]) - 1);
    tmp.setUTCDate(parseFloat(res[3]));
    tmp.setUTCHours(parseFloat(res[4]));
    tmp.setUTCMinutes(parseFloat(res[5]));
    tmp.setUTCSeconds(parseFloat(res[6]));
    tmp.setUTCSeconds(parseFloat(res[6]));
    tmp.setUTCMilliseconds(parseFloat(rpad((res[7] || "").slice(0, 3), 3)));
    return tmp;
};

/**
 * Converts a string to a Date javascript object using OpenERP's
 * date string format (exemple: '2011-12-01').
 * 
 * As a date is not subject to time zones, we assume it should be
 * represented as a Date javascript object at 00:00:00 in the
 * time zone of the browser.
 * 
 * @param {String} str A string representing a date.
 * @returns {Date}
 */
openerp.str_to_date = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid date");
    }
    var tmp = new Date(2000,0,1);
    tmp.setFullYear(parseFloat(res[1]));
    tmp.setMonth(parseFloat(res[2]) - 1);
    tmp.setDate(parseFloat(res[3]));
    tmp.setHours(0);
    tmp.setMinutes(0);
    tmp.setSeconds(0);
    return tmp;
};

/**
 * Converts a string to a Date javascript object using OpenERP's
 * time string format (exemple: '15:12:35').
 * 
 * The OpenERP times are supposed to always be naive times. We assume it is
 * represented using a javascript Date with a date 1 of January 1970 and a
 * time corresponding to the meant time in the browser's time zone.
 * 
 * @param {String} str A string representing a time.
 * @returns {Date}
 */
openerp.str_to_time = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d):(\d\d):(\d\d(?:\.(\d+))?)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid time");
    }
    var tmp = new Date();
    tmp.setFullYear(1970);
    tmp.setMonth(0);
    tmp.setDate(1);
    tmp.setHours(parseFloat(res[1]));
    tmp.setMinutes(parseFloat(res[2]));
    tmp.setSeconds(parseFloat(res[3]));
    tmp.setMilliseconds(parseFloat(rpad((res[4] || "").slice(0, 3), 3)));
    return tmp;
};

/*
 * Left-pad provided arg 1 with zeroes until reaching size provided by second
 * argument.
 *
 * @param {Number|String} str value to pad
 * @param {Number} size size to reach on the final padded value
 * @returns {String} padded string
 */
var lpad = function(str, size) {
    str = "" + str;
    return new Array(size - str.length + 1).join('0') + str;
};

var rpad = function(str, size) {
    str = "" + str;
    return str + new Array(size - str.length + 1).join('0');
};

/**
 * Converts a Date javascript object to a string using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35').
 * 
 * The time zone of the Date object is assumed to be the one of the
 * browser and it will be converted to UTC (standard for OpenERP 6.1).
 * 
 * @param {Date} obj
 * @returns {String} A string representing a datetime.
 */
openerp.datetime_to_str = function(obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getUTCFullYear(),4) + "-" + lpad(obj.getUTCMonth() + 1,2) + "-"
         + lpad(obj.getUTCDate(),2) + " " + lpad(obj.getUTCHours(),2) + ":"
         + lpad(obj.getUTCMinutes(),2) + ":" + lpad(obj.getUTCSeconds(),2);
};

/**
 * Converts a Date javascript object to a string using OpenERP's
 * date string format (exemple: '2011-12-01').
 * 
 * As a date is not subject to time zones, we assume it should be
 * represented as a Date javascript object at 00:00:00 in the
 * time zone of the browser.
 * 
 * @param {Date} obj
 * @returns {String} A string representing a date.
 */
openerp.date_to_str = function(obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getFullYear(),4) + "-" + lpad(obj.getMonth() + 1,2) + "-"
         + lpad(obj.getDate(),2);
};

/**
 * Converts a Date javascript object to a string using OpenERP's
 * time string format (exemple: '15:12:35').
 * 
 * The OpenERP times are supposed to always be naive times. We assume it is
 * represented using a javascript Date with a date 1 of January 1970 and a
 * time corresponding to the meant time in the browser's time zone.
 * 
 * @param {Date} obj
 * @returns {String} A string representing a time.
 */
openerp.time_to_str = function(obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getHours(),2) + ":" + lpad(obj.getMinutes(),2) + ":"
         + lpad(obj.getSeconds(),2);
};

// jQuery custom plugins
jQuery.expr[":"].Contains = jQuery.expr.createPseudo(function(arg) {
    return function( elem ) {
        return jQuery(elem).text().toUpperCase().indexOf(arg.toUpperCase()) >= 0;
    };
});

openerp.declare = declare;

return openerp;
}

if (typeof(define) !== "undefined") { // amd
    define(["jquery", "underscore", "qweb2"], declare);
} else {
    window.openerp = declare($, _, QWeb2);
}

})();
