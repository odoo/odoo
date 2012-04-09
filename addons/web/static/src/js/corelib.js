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

openerp.web.corelib = function(openerp) {

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
 * var Person = nova.Class.extend({
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
    openerp.web.Class = function(){};

    /**
     * Subclass an existing class
     *
     * @param {Object} prop class-level properties (class attributes and instance methods) to set on the new class
     */
    openerp.web.Class.extend = function() {
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
                              typeof _super[name] == "function" &&
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

/**
 * Mixin to structure objects' life-cycles folowing a parent-children
 * relationship. Each object can a have a parent and multiple children.
 * When an object is destroyed, all its children are destroyed too releasing
 * any resource they could have reserved before.
 */
openerp.web.ParentedMixin = {
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
 * Backbone's events
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
openerp.web.Events = openerp.web.Class.extend({

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

openerp.web.EventDispatcherMixin = _.extend({}, openerp.web.ParentedMixin, {
    __eventDispatcherMixin: true,
    init: function() {
        openerp.web.ParentedMixin.init.call(this);
        this.__edispatcherEvents = new openerp.web.Events();
        this.__edispatcherRegisteredEvents = [];
    },
    on: function(events, dest, func) {
        var self = this;
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
        this.__edispatcherEvents.off();
        openerp.web.ParentedMixin.destroy.call(this);
    }
});

openerp.web.GetterSetterMixin = _.extend({}, openerp.web.EventDispatcherMixin, {
    init: function() {
        openerp.web.EventDispatcherMixin.init.call(this);
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

openerp.web.CallbackEnabledMixin = {
    init: function() {
        var self = this;
        var callback_maker = function(obj, method) {
            var callback = function() {
                var args = Array.prototype.slice.call(arguments);
                //self.trigger.apply(self, [name].concat(args));
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
                    // openerp.web.callback_stop
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
                args:Array.prototype.slice.call(arguments, 2)
            });
        };
        // Transform on_/do_* methods into callbacks
        for (var name in this) {
            if(typeof(this[name]) == "function") {
                this[name].debug_name = name;
                if((/^on_|^do_/).test(name)) {
                    this[name] = callback_maker(this, this[name]);
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
     * @param {String} method_name name of the method to invoke
     * @returns {Function} proxied method
     */
    proxy: function (method_name) {
        var self = this;
        return function () {
            return self[method_name].apply(self, arguments);
        }
    }
};

openerp.web.CallbackEnabled = openerp.web.Class.extend(openerp.web.GetterSetterMixin, openerp.web.CallbackEnabledMixin, {
    init: function() {
        openerp.web.GetterSetterMixin.init.call(this);
        openerp.web.CallbackEnabledMixin.init.call(this);
    }
});

openerp.web.Widget = openerp.web.Class.extend(openerp.web.GetterSetterMixin, {
    /**
     * Tag name when creating a default $element.
     * @type string
     */
    tagName: 'div',
    /**
     * Constructs the widget and sets its parent if a parent is given.
     *
     * @constructs openerp.web.Widget
     * @extends openerp.web.CallbackEnabled
     *
     * @param {openerp.web.Widget} parent Binds the current instance to the given Widget instance.
     * When that widget is destroyed by calling destroy(), the current instance will be
     * destroyed too. Can be null.
     * @param {String} element_id Deprecated. Sets the element_id. Only useful when you want
     * to bind the current Widget to an already existing part of the DOM, which is not compatible
     * with the DOM insertion methods provided by the current implementation of Widget. So
     * for new components this argument should not be provided any more.
     */
    init: function(parent) {
        openerp.web.GetterSetterMixin.init.call(this);
        this.$element = $(document.createElement(this.tagName));

        this.setParent(parent);
    },
    /**
     * Destroys the current widget, also destroys all its children before destroying itself.
     */
    destroy: function() {
        _.each(this.getChildren(), function(el) {
            el.destroy();
        });
        if(this.$element != null) {
            this.$element.remove();
        }
        openerp.web.GetterSetterMixin.destroy.call(this);
    },
    /**
     * Renders the current widget and appends it to the given jQuery object or Widget.
     *
     * @param target A jQuery object or a Widget instance.
     */
    appendTo: function(target) {
        var self = this;
        return this.__widgetRenderAndInsert(function(t) {
            self.$element.appendTo(t);
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
            self.$element.prependTo(t);
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
            self.$element.insertAfter(t);
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
            self.$element.insertBefore(t);
        }, target);
    },
    /**
     * Renders the current widget and replaces the given jQuery object.
     *
     * @param target A jQuery object or a Widget instance.
     */
    replace: function(target) {
        return this.__widgetRenderAndInsert(_.bind(function(t) {
            this.$element.replaceAll(t);
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
    renderElement: function() {},
    /**
     * Method called after rendering. Mostly used to bind actions, perform asynchronous
     * calls, etc...
     *
     * By convention, the method should return a promise to inform the caller when
     * this widget has been initialized.
     *
     * @returns {jQuery.Deferred}
     */
    start: function() {}
});

openerp.web.Registry = openerp.web.Class.extend({
    /**
     * Stores a mapping of arbitrary key (strings) to object paths (as strings
     * as well).
     *
     * Resolves those paths at query time in order to always fetch the correct
     * object, even if those objects have been overloaded/replaced after the
     * registry was created.
     *
     * An object path is simply a dotted name from the openerp root to the
     * object pointed to (e.g. ``"openerp.web.Connection"`` for an OpenERP
     * connection object).
     *
     * @constructs openerp.web.Registry
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

        var object_match = openerp;
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
     * @returns {openerp.web.Registry} itself
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
        var child = new openerp.web.Registry(mapping);
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

}

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
