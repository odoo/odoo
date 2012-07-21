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

openerp.web.corelib = function(instance) {

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
 * var Person = instance.web.Class.extend({
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
        fnTest = /xyz/.test(function(){xyz;}) ? /\b_super\b/ : /.*/;
    // The web Class implementation (does nothing)
    instance.web.Class = function(){};

    /**
     * Subclass an existing class
     *
     * @param {Object} prop class-level properties (class attributes and instance methods) to set on the new class
     */
    instance.web.Class.extend = function() {
        var _super = this.prototype;
        // Support mixins arguments
        var args = _.toArray(arguments);
        args.unshift({});
        var prop = _.extend.apply(_,args);

        // Instantiate a web class (but only create the instance,
        // don't run the init constructor)
        initializing = true;
        var prototype = new this();
        initializing = false;

        // Copy the properties over onto the new prototype
        for (var name in prop) {
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
        }

        // The dummy class constructor
        function Class() {
            // All construction is actually done in the init method
            if (!initializing && this.init) {
                var ret = this.init.apply(this, arguments);
                if (ret) { return ret; }
            }
            return this;
        }
        Class.include = function (properties) {
            for (var name in properties) {
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
                        }
                    })(name, properties[name], prototype[name]);
                } else if (typeof _super[name] === 'function') {
                    prototype[name] = (function (name, fn) {
                        return function () {
                            var tmp = this._super;
                            this._super = _super[name];
                            var ret = fn.apply(this, arguments);
                            this._super = tmp;
                            return ret;
                        }
                    })(name, properties[name]);
                }
            }
        };

        // Populate our constructed prototype object
        Class.prototype = prototype;

        // Enforce the constructor to be what we expect
        Class.constructor = Class;

        // And make this class extendable
        Class.extend = arguments.callee;

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
instance.web.ParentedMixin = {
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
     * Inform the object it should destroy itself, releasing any
     * resource it could have reserved.
     */
    destroy : function() {
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        this.setParent(undefined);
        this.__parentedDestroyed = true;
    }
};

/**
 * Backbone's events. Do not ever use it directly, use EventDispatcherMixin instead.
 *
 * (c) 2010-2012 Jeremy Ashkenas, DocumentCloud Inc.
 * Backbone may be freely distributed under the MIT license.
 * For all details and documentation:
 * http://backbonejs.org
 * 
 * This class just handle the dispatching of events, it is not meant to be extended,
 * nor used directly. All integration with parenting and automatic unregistration of
 * events is done in EventDispatcherMixin.
 *
 */
var Events = instance.web.Class.extend({
    on : function(events, callback, context) {
        var ev;
        events = events.split(/\s+/);
        var calls = this._callbacks || (this._callbacks = {});
        while (ev = events.shift()) {
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
        } else if (calls = this._callbacks) {
            events = events.split(/\s+/);
            while (ev = events.shift()) {
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

    trigger : function(events) {
        var event, node, calls, tail, args, all, rest;
        if (!(calls = this._callbacks))
            return this;
        all = calls['all'];
        (events = events.split(/\s+/)).push(null);
        // Save references to the current heads & tails.
        while (event = events.shift()) {
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
        while (node = events.pop()) {
            tail = node.tail;
            args = node.event ? [ node.event ].concat(rest) : rest;
            while ((node = node.next) !== tail) {
                node.callback.apply(node.context || this, args);
            }
        }
        return this;
    }
});
// end of Jeremy Ashkenas' code

instance.web.EventDispatcherMixin = _.extend({}, instance.web.ParentedMixin, {
    __eventDispatcherMixin: true,
    init: function() {
        instance.web.ParentedMixin.init.call(this);
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
        if(!this.__edispatcherEvents) {
            debugger;
        }
        this.__edispatcherEvents.off();
        instance.web.ParentedMixin.destroy.call(this);
    }
});

instance.web.PropertiesMixin = _.extend({}, instance.web.EventDispatcherMixin, {
    init: function() {
        instance.web.EventDispatcherMixin.init.call(this);
        this.__getterSetterInternalMap = {};
    },
    set: function(map) {
        var self = this;
        var changed = false;
        _.each(map, function(val, key) {
            var tmp = self.__getterSetterInternalMap[key];
            if (tmp === val)
                return;
            changed = true;
            self.__getterSetterInternalMap[key] = val;
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

instance.web.CallbackEnabledMixin = _.extend({}, instance.web.PropertiesMixin, {
    init: function() {
        instance.web.PropertiesMixin.init.call(this);
        var self = this;
        var callback_maker = function(obj, name, method) {
            var callback = function() {
                var args = Array.prototype.slice.call(arguments);
                self.trigger.apply(self, [name].concat(args));
                var r;
                for(var i = 0; i < callback.callback_chain.length; i++)  {
                    var c = callback.callback_chain[i];
                    if(c.unique) {
                        callback.callback_chain.splice(i, 1);
                        i -= 1;
                    }
                    var result = c.callback.apply(c.self, c.args.concat(args));
                    if (c.callback === method) {
                        // return the result of the original method
                        r = result;
                    }
                    // TODO special value to stop the chain
                    // instance.web.callback_stop
                }
                return r;
            };
            callback.callback_chain = [];
            callback.add = function(f) {
                if(typeof(f) == 'function') {
                    f = { callback: f, args: Array.prototype.slice.call(arguments, 1) };
                }
                f.self = f.self || null;
                f.args = f.args || [];
                f.unique = !!f.unique;
                if(f.position == 'last') {
                    callback.callback_chain.push(f);
                } else {
                    callback.callback_chain.unshift(f);
                }
                return callback;
            };
            callback.add_first = function(f) {
                return callback.add.apply(null,arguments);
            };
            callback.add_last = function(f) {
                return callback.add({
                    callback: f,
                    args: Array.prototype.slice.call(arguments, 1),
                    position: "last"
                });
            };
            callback.remove = function(f) {
                callback.callback_chain = _.difference(callback.callback_chain, _.filter(callback.callback_chain, function(el) {
                    return el.callback === f;
                }));
                return callback;
            };

            return callback.add({
                callback: method,
                self:obj,
                args:Array.prototype.slice.call(arguments, 3)
            });
        };
        // Transform on_/do_* methods into callbacks
        for (var name in this) {
            if(typeof(this[name]) == "function") {
                this[name].debug_name = name;
                if((/^on_|^do_/).test(name)) {
                    this[name] = callback_maker(this, name, this[name]);
                }
            }
        }
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
        }
    }
});

instance.web.WidgetMixin = _.extend({},instance.web.CallbackEnabledMixin, {
    /**
     * Constructs the widget and sets its parent if a parent is given.
     *
     * @constructs instance.web.Widget
     * @extends instance.web.CallbackEnabled
     *
     * @param {instance.web.Widget} parent Binds the current instance to the given Widget instance.
     * When that widget is destroyed by calling destroy(), the current instance will be
     * destroyed too. Can be null.
     */
    init: function(parent) {
        instance.web.CallbackEnabledMixin.init.call(this);
        this.setParent(parent);
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
        instance.web.PropertiesMixin.destroy.call(this);
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
     * This is the method to implement to render the Widget.
     */
    renderElement: function() {
    },
    /**
     * Method called after rendering. Mostly used to bind actions, perform asynchronous
     * calls, etc...
     *
     * By convention, the method should return a promise to inform the caller when
     * this widget has been initialized.
     *
     * @returns {jQuery.Deferred}
     */
    start: function() {
        return $.when();
    }
});

// Classes

instance.web.CallbackEnabled = instance.web.Class.extend(instance.web.CallbackEnabledMixin, {
    init: function() {
        instance.web.CallbackEnabledMixin.init.call(this);
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
 * MyWidget = instance.base.Widget.extend({
 *     // the name of the QWeb template to use for rendering
 *     template: "MyQWebTemplate",
 *
 *     init: function(parent) {
 *         this._super(parent);
 *         // stuff that you want to init before the rendering
 *     },
 *     start: function() {
 *         // stuff you want to make after the rendering, `this.$element` holds a correct value
 *         this.$element.find(".my_button").click(/* an example of event binding * /);
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
instance.web.Widget = instance.web.Class.extend(instance.web.WidgetMixin, {
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
     * @constructs instance.web.Widget
     * @extends instance.web.CallbackEnabled
     *
     * @param {instance.web.Widget} parent Binds the current instance to the given Widget instance.
     * When that widget is destroyed by calling destroy(), the current instance will be
     * destroyed too. Can be null.
     */
    init: function(parent) {
        instance.web.WidgetMixin.init.call(this,parent);
        this.session = instance.connection;
    },
    /**
     * Renders the element. The default implementation renders the widget using QWeb,
     * `this.template` must be defined. The context given to QWeb contains the "widget"
     * key that references `this`.
     */
    renderElement: function() {
        var $el;
        if (this.template) {
            $el = $(_.str.trim(instance.web.qweb.render(
                this.template, {widget: this})));
        } else {
            var attrs = _.extend({}, this.attributes || {});
            if (this.id) { attrs.id = this.id; }
            if (this.className) { attrs['class'] = this.className; }
            $el = $(this.make(this.tagName, attrs));
        }
        var $oldel = this.$el;
        this.setElement($el);
        if ($oldel && !$oldel.is(this.$el)) {
            $oldel.replaceWith(this.$el);
        }
    },

    /**
     * Re-sets the widget's root element (el/$el/$element).
     *
     * Includes:
     * * re-delegating events
     * * re-binding sub-elements
     * * if the widget already had a root element, replacing the pre-existing
     *   element in the DOM
     *
     * @param {HTMLElement | jQuery} element new root element for the widget
     * @return {*}
     */
    setElement: function (element) {
        if (this.$el) {
            this.undelegateEvents();
        }

        this.$element = this.$el = (element instanceof $) ? element : $(element);
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
    delegateEvents: function () {
        var events = this.events;
        if (_.isEmpty(events)) { return; }

        for(var key in events) {
            if (!events.hasOwnProperty(key)) { continue; }

            var method = this.proxy(events[key]);

            var match = /^(\S+)(\s+(.*))?$/.exec(key);
            var event = match[1];
            var selector = match[3];

            event += '.delegated-events';
            if (!selector) {
                this.$el.on(event, method);
            } else {
                this.$el.on(event, selector, method);
            }
        }
    },
    undelegateEvents: function () {
        this.$el.off('.delegated-events');
    },
    /**
     * Shortcut for ``this.$el.find(selector)``
     *
     * @param {String} selector CSS selector, rooted in $el
     * @returns {jQuery} selector match
     */
    $: function(selector) {
        return this.$el.find(selector);
    },
    /**
     * Informs the action manager to do an action. This supposes that
     * the action manager can be found amongst the ancestors of the current widget.
     * If that's not the case this method will simply return `false`.
     */
    do_action: function(action, on_finished) {
        if (this.getParent()) {
            return this.getParent().do_action(action, on_finished);
        }
        return false;
    },
    do_notify: function() {
        if (this.getParent()) {
            return this.getParent().do_notify.apply(this,arguments);
        }
        return false;
    },
    do_warn: function() {
        if (this.getParent()) {
            return this.getParent().do_warn.apply(this,arguments);
        }
        return false;
    },
    rpc: function(url, data, success, error) {
        var def = $.Deferred().then(success, error);
        var self = this;
        instance.connection.rpc(url, data). then(function() {
            if (!self.isDestroyed())
                def.resolve.apply(def, arguments);
        }, function() {
            if (!self.isDestroyed())
                def.reject.apply(def, arguments);
        });
        return def.promise();
    }
});

instance.web.Registry = instance.web.Class.extend({
    /**
     * Stores a mapping of arbitrary key (strings) to object paths (as strings
     * as well).
     *
     * Resolves those paths at query time in order to always fetch the correct
     * object, even if those objects have been overloaded/replaced after the
     * registry was created.
     *
     * An object path is simply a dotted name from the instance root to the
     * object pointed to (e.g. ``"instance.web.Session"`` for an OpenERP
     * connection object).
     *
     * @constructs instance.web.Registry
     * @param {Object} mapping a mapping of keys to object-paths
     */
    init: function (mapping) {
        this.parent = null;
        this.map = mapping || {};
    },
    /**
     * Retrieves the object matching the provided key string.
     *
     * @param {String} key the key to fetch the object for
     * @param {Boolean} [silent_error=false] returns undefined if the key or object is not found, rather than throwing an exception
     * @returns {Class} the stored class, to initialize or null if not found
     */
    get_object: function (key, silent_error) {
        var path_string = this.map[key];
        if (path_string === undefined) {
            if (this.parent) {
                return this.parent.get_object(key, silent_error);
            }
            if (silent_error) { return void 'nooo'; }
            return null;
        }

        var object_match = instance;
        var path = path_string.split('.');
        // ignore first section
        for(var i=1; i<path.length; ++i) {
            object_match = object_match[path[i]];

            if (object_match === undefined) {
                if (silent_error) { return void 'noooooo'; }
                return null;
            }
        }
        return object_match;
    },
    /**
     * Checks if the registry contains an object mapping for this key.
     *
     * @param {String} key key to look for
     */
    contains: function (key) {
        if (key === undefined) { return false; }
        if (key in this.map) {
            return true
        }
        if (this.parent) {
            return this.parent.contains(key);
        }
        return false;
    },
    /**
     * Tries a number of keys, and returns the first object matching one of
     * the keys.
     *
     * @param {Array} keys a sequence of keys to fetch the object for
     * @returns {Class} the first class found matching an object
     */
    get_any: function (keys) {
        for (var i=0; i<keys.length; ++i) {
            var key = keys[i];
            if (!this.contains(key)) {
                continue;
            }

            return this.get_object(key);
        }
        return null;
    },
    /**
     * Adds a new key and value to the registry.
     *
     * This method can be chained.
     *
     * @param {String} key
     * @param {String} object_path fully qualified dotted object path
     * @returns {instance.web.Registry} itself
     */
    add: function (key, object_path) {
        this.map[key] = object_path;
        return this;
    },
    /**
     * Creates and returns a copy of the current mapping, with the provided
     * mapping argument added in (replacing existing keys if needed)
     *
     * Parent and child remain linked, a new key in the parent (which is not
     * overwritten by the child) will appear in the child.
     *
     * @param {Object} [mapping={}] a mapping of keys to object-paths
     */
    extend: function (mapping) {
        var child = new instance.web.Registry(mapping);
        child.parent = this;
        return child;
    },
    /**
     * @deprecated use Registry#extend
     */
    clone: function (mapping) {
        console.warn('Registry#clone is deprecated, use Registry#extend');
        return this.extend(mapping);
    }
});

instance.web.JsonRPC = instance.web.CallbackEnabled.extend({
    /**
     * @constructs instance.web.JsonRPC
     * @extends instance.web.CallbackEnabled
     *
     * @param {String} [server] JSON-RPC endpoint hostname
     * @param {String} [port] JSON-RPC endpoint port
     */
    init: function() {
        this._super();
        this.server = null;
        this.debug = ($.deparam($.param.querystring()).debug != undefined);
    },
    setup: function(origin) {
        var window_origin = location.protocol+"//"+location.host, self=this;
        this.origin = origin ? _.str.rtrim(origin,'/') : window_origin;
        this.prefix = this.origin;
        this.server = this.origin; // keep chs happy
        this.rpc_function = (this.origin == window_origin) ? this.rpc_json : this.rpc_jsonp;
    },
    test_eval_get_context: function () {
        var asJS = function (arg) {
            if (arg instanceof py.object) {
                return arg.toJSON();
            }
            return arg;
        };

        var datetime = new py.object();
        datetime.datetime = new py.type(function datetime() {
            throw new Error('datetime.datetime not implemented');
        });
        var date = datetime.date = new py.type(function date(y, m, d) {
            if (y instanceof Array) {
                d = y[2];
                m = y[1];
                y = y[0];
            }
            this.year = asJS(y);
            this.month = asJS(m);
            this.day = asJS(d);
        }, py.object, {
            strftime: function (args) {
                var f = asJS(args[0]), self = this;
                return new py.str(f.replace(/%([A-Za-z])/g, function (m, c) {
                    switch (c) {
                    case 'Y': return self.year;
                    case 'm': return _.str.sprintf('%02d', self.month);
                    case 'd': return _.str.sprintf('%02d', self.day);
                    }
                    throw new Error('ValueError: No known conversion for ' + m);
                }));
            }
        });
        date.__getattribute__ = function (name) {
            if (name === 'today') {
                return date.today;
            }
            throw new Error("AttributeError: object 'date' has no attribute '" + name +"'");
        };
        date.today = new py.def(function () {
            var d = new Date();
            return new date(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate());
        });
        datetime.time = new py.type(function time() {
            throw new Error('datetime.time not implemented');
        });

        var time = new py.object();
        time.strftime = new py.def(function (args) {
            return date.today.__call__().strftime(args);
        });

        var relativedelta = new py.type(function relativedelta(args, kwargs) {
            if (!_.isEmpty(args)) {
                throw new Error('Extraction of relative deltas from existing datetimes not supported');
            }
            this.ops = kwargs;
        }, py.object, {
            __add__: function (other) {
                if (!(other instanceof datetime.date)) {
                    return py.NotImplemented;
                }
                // TODO: test this whole mess
                var year = asJS(this.ops.year) || asJS(other.year);
                if (asJS(this.ops.years)) {
                    year += asJS(this.ops.years);
                }

                var month = asJS(this.ops.month) || asJS(other.month);
                if (asJS(this.ops.months)) {
                    month += asJS(this.ops.months);
                    // FIXME: no divmod in JS?
                    while (month < 1) {
                        year -= 1;
                        month += 12;
                    }
                    while (month > 12) {
                        year += 1;
                        month -= 12;
                    }
                }

                var lastMonthDay = new Date(year, month, 0).getDate();
                var day = asJS(this.ops.day) || asJS(other.day);
                if (day > lastMonthDay) { day = lastMonthDay; }
                var days_offset = ((asJS(this.ops.weeks) || 0) * 7) + (asJS(this.ops.days) || 0);
                if (days_offset) {
                    day = new Date(year, month-1, day + days_offset).getDate();
                }
                // TODO: leapdays?
                // TODO: hours, minutes, seconds? Not used in XML domains
                // TODO: weekday?
                return new datetime.date(year, month, day);
            },
            __radd__: function (other) {
                return this.__add__(other);
            },

            __sub__: function (other) {
                if (!(other instanceof datetime.date)) {
                    return py.NotImplemented;
                }
                // TODO: test this whole mess
                var year = asJS(this.ops.year) || asJS(other.year);
                if (asJS(this.ops.years)) {
                    year -= asJS(this.ops.years);
                }

                var month = asJS(this.ops.month) || asJS(other.month);
                if (asJS(this.ops.months)) {
                    month -= asJS(this.ops.months);
                    // FIXME: no divmod in JS?
                    while (month < 1) {
                        year -= 1;
                        month += 12;
                    }
                    while (month > 12) {
                        year += 1;
                        month -= 12;
                    }
                }

                var lastMonthDay = new Date(year, month, 0).getDate();
                var day = asJS(this.ops.day) || asJS(other.day);
                if (day > lastMonthDay) { day = lastMonthDay; }
                var days_offset = ((asJS(this.ops.weeks) || 0) * 7) + (asJS(this.ops.days) || 0);
                if (days_offset) {
                    day = new Date(year, month-1, day - days_offset).getDate();
                }
                // TODO: leapdays?
                // TODO: hours, minutes, seconds? Not used in XML domains
                // TODO: weekday?
                return new datetime.date(year, month, day);
            },
            __rsub__: function (other) {
                return this.__sub__(other);
            }
        });

        return {
            uid: new py.float(this.uid),
            datetime: datetime,
            time: time,
            relativedelta: relativedelta
        };
    },
    /**
     * FIXME: Huge testing hack, especially the evaluation context, rewrite + test for real before switching
     */
    test_eval: function (source, expected) {
        var match_template = '<ul>' +
                '<li>Source: %(source)s</li>' +
                '<li>Local: %(local)s</li>' +
                '<li>Remote: %(remote)s</li>' +
            '</ul>',
            fail_template = '<ul>' +
                '<li>Error: %(error)s</li>' +
                '<li>Source: %(source)s</li>' +
            '</ul>';
        try {
            // see Session.eval_context in Python
            var ctx = this.test_eval_contexts(
                ([this.context] || []).concat(source.contexts));
            if (!_.isEqual(ctx, expected.context)) {
                instance.webclient.notification.warn('Context mismatch, report to xmo',
                    _.str.sprintf(match_template, {
                        source: JSON.stringify(source.contexts),
                        local: JSON.stringify(ctx),
                        remote: JSON.stringify(expected.context)
                    }), true);
            }
        } catch (e) {
            instance.webclient.notification.warn('Context fail, report to xmo',
                _.str.sprintf(fail_template, {
                    error: e.message,
                    source: JSON.stringify(source.contexts)
                }), true);
        }

        try {
            var dom = this.test_eval_domains(source.domains, this.test_eval_get_context());
            if (!_.isEqual(dom, expected.domain)) {
                instance.webclient.notification.warn('Domains mismatch, report to xmo',
                    _.str.sprintf(match_template, {
                        source: JSON.stringify(source.domains),
                        local: JSON.stringify(dom),
                        remote: JSON.stringify(expected.domain)
                    }), true);
            }
        } catch (e) {
            instance.webclient.notification.warn('Domain fail, report to xmo',
                _.str.sprintf(fail_template, {
                    error: e.message,
                    source: JSON.stringify(source.domains)
                }), true);
        }

        try {
            var groups = this.test_eval_groupby(source.group_by_seq);
            if (!_.isEqual(groups, expected.group_by)) {
                instance.webclient.notification.warn('GroupBy mismatch, report to xmo',
                    _.str.sprintf(match_template, {
                        source: JSON.stringify(source.group_by_seq),
                        local: JSON.stringify(groups),
                        remote: JSON.stringify(expected.group_by)
                    }), true);
            }
        } catch (e) {
            instance.webclient.notification.warn('GroupBy fail, report to xmo',
                _.str.sprintf(fail_template, {
                    error: e.message,
                    source: JSON.stringify(source.group_by_seq)
                }), true);
        }
    },
    test_eval_contexts: function (contexts, evaluation_context) {
        evaluation_context = evaluation_context || {};
        var self = this;
        return _(contexts).reduce(function (result_context, ctx) {
            // __eval_context evaluations can lead to some of `contexts`'s
            // values being null, skip them as well as empty contexts
            if (_.isEmpty(ctx)) { return result_context; }
            var evaluated = ctx;
            switch(ctx.__ref) {
            case 'context':
                evaluated = py.eval(ctx.__debug, evaluation_context);
                break;
            case 'compound_context':
                var eval_context = self.test_eval_contexts([ctx.__eval_context]);
                evaluated = self.test_eval_contexts(
                    ctx.__contexts, _.extend({}, evaluation_context, eval_context));
                break;
            }
            // add newly evaluated context to evaluation context for following
            // siblings
            _.extend(evaluation_context, evaluated);
            return _.extend(result_context, evaluated);
        }, _.extend({}, this.user_context));
    },
    test_eval_domains: function (domains, evaluation_context) {
        var result_domain = [], self = this;
        _(domains).each(function (dom) {
            switch(dom.__ref) {
            case 'domain':
                result_domain.push.apply(
                    result_domain, py.eval(dom.__debug, evaluation_context));
                break;
            case 'compound_domain':
                var eval_context = self.test_eval_contexts([dom.__eval_context]);
                result_domain.push.apply(
                    result_domain, self.test_eval_domains(
                        dom.__domains, _.extend(
                            {}, evaluation_context, eval_context)));
                break;
            default:
                result_domain.push.apply(
                    result_domain, dom);
            }
        });
        return result_domain;
    },
    test_eval_groupby: function (contexts) {
        var result_group = [], self = this;
        _(contexts).each(function (ctx) {
            var group;
            switch(ctx.__ref) {
            case 'context':
                group = py.eval(ctx.__debug).group_by;
                break;
            case 'compound_context':
                group = self.test_eval_contexts(
                    ctx.__contexts, ctx.__eval_context).group_by;
                break;
            default:
                group = ctx.group_by
            }
            if (!group) { return; }
            if (typeof group === 'string') {
                result_group.push(group);
            } else if (group instanceof Array) {
                result_group.push.apply(result_group, group);
            } else {
                throw new Error('Got invalid groupby {{'
                        + JSON.stringify(group) + '}}');
            }
        });
        return result_group;
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
     * @param {Function} success_callback function to execute on RPC call success
     * @param {Function} error_callback function to execute on RPC call failure
     * @returns {jQuery.Deferred} jquery-provided ajax deferred
     */
    rpc: function(url, params, success_callback, error_callback) {
        var self = this;
        // url can be an $.ajax option object
        if (_.isString(url)) {
            url = { url: url };
        }
        // Construct a JSON-RPC2 request, method is currently unused
        if (this.debug)
            params.debug = 1;
        var payload = {
            jsonrpc: '2.0',
            method: 'call',
            params: params,
            id: _.uniqueId('r')
        };
        var deferred = $.Deferred();
        this.on_rpc_request();
        var aborter = params.aborter;
        delete params.aborter;
        var request = this.rpc_function(url, payload).then(
            function (response, textStatus, jqXHR) {
                self.on_rpc_response();
                if (!response.error) {
                    if (url.url === '/web/session/eval_domain_and_context') {
                        self.test_eval(params, response.result);
                    }
                    deferred.resolve(response["result"], textStatus, jqXHR);
                } else if (response.error.data.type === "session_invalid") {
                    self.uid = false;
                    // TODO deprecate or use a deferred on login.do_ask_login()
                    self.on_session_invalid(function() {
                        self.rpc(url, payload.params,
                            function() { deferred.resolve.apply(deferred, arguments); },
                            function() { deferred.reject.apply(deferred, arguments); });
                    });
                } else {
                    deferred.reject(response.error, $.Event());
                }
            },
            function(jqXHR, textStatus, errorThrown) {
                self.on_rpc_response();
                var error = {
                    code: -32098,
                    message: "XmlHttpRequestError " + errorThrown,
                    data: {type: "xhr"+textStatus, debug: jqXHR.responseText, objects: [jqXHR, errorThrown] }
                };
                deferred.reject(error, $.Event());
            });
        if (aborter) {
            aborter.abort_last = function () {
                if (!(request.isResolved() || request.isRejected())) {
                    deferred.fail(function (error, event) {
                        event.preventDefault();
                    });
                    request.abort();
                }
            };
        }
        // Allow deferred user to disable on_rpc_error in fail
        deferred.fail(function() {
            deferred.fail(function(error, event) {
                if (!event.isDefaultPrevented()) {
                    self.on_rpc_error(error, event);
                }
            });
        }).then(success_callback, error_callback).promise();
        return deferred;
    },
    /**
     * Raw JSON-RPC call
     *
     * @returns {jQuery.Deferred} ajax-webd deferred object
     */
    rpc_json: function(url, payload) {
        var self = this;
        var ajax = _.extend({
            type: "POST",
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify(payload),
            processData: false
        }, url);
        if (this.synch)
        	ajax.async = false;
        return $.ajax(ajax);
    },
    rpc_jsonp: function(url, payload) {
        var self = this;
        // extracted from payload to set on the url
        var data = {
            session_id: this.session_id,
            id: payload.id
        };
        url.url = this.get_url(url.url);
        var ajax = _.extend({
            type: "GET",
            dataType: 'jsonp', 
            jsonp: 'jsonp',
            cache: false,
            data: data
        }, url);
        if (this.synch)
        	ajax.async = false;
        var payload_str = JSON.stringify(payload);
        var payload_url = $.param({r:payload_str});
        if(payload_url.length < 2000) {
            // Direct jsonp request
            ajax.data.r = payload_str;
            return $.ajax(ajax);
        } else {
            // Indirect jsonp request
            var ifid = _.uniqueId('oe_rpc_iframe');
            var display = self.debug ? 'block' : 'none';
            var $iframe = $(_.str.sprintf("<iframe src='javascript:false;' name='%s' id='%s' style='display:%s'></iframe>", ifid, ifid, display));
            var $form = $('<form>')
                        .attr('method', 'POST')
                        .attr('target', ifid)
                        .attr('enctype', "multipart/form-data")
                        .attr('action', ajax.url + '?jsonp=1&' + $.param(data))
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
                    $.ajax(ajax).always(function() {
                        cleanUp();
                    }).then(
                        function() { deferred.resolve.apply(deferred, arguments); },
                        function() { deferred.reject.apply(deferred, arguments); }
                    );
                });
                // now that the iframe can receive data, we fill and submit the form
                $form.submit();
            });
            // append the iframe to the DOM (will trigger the first load)
            $form.after($iframe);
            return deferred;
        }
    },
    on_rpc_request: function() {
    },
    on_rpc_response: function() {
    },
    on_rpc_error: function(error) {
    },
    get_url: function (file) {
        return this.prefix + file;
    },
});

}

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
