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

// Mixins

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
 * TODO al: move into the the mixin
 *
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

openerp.web.Connection = openerp.web.CallbackEnabled.extend( /** @lends openerp.web.Connection# */{
    /**
     * @constructs openerp.web.Connection
     * @extends openerp.web.CallbackEnabled
     *
     * @param {String} [server] JSON-RPC endpoint hostname
     * @param {String} [port] JSON-RPC endpoint port
     */
    init: function() {
        this._super();
        this.server = null;
        this.debug = ($.deparam($.param.querystring()).debug != undefined);
        // TODO: session store in cookie should be optional
        this.name = openerp._session_id;
        this.qweb_mutex = new $.Mutex();
    },
    session_bind: function(origin) {
        var window_origin = location.protocol+"//"+location.host, self=this;
        this.origin = origin ? _.str.rtrim(origin,'/') : window_origin;
        this.prefix = this.origin;
        this.server = this.origin; // keep chs happy
        openerp.web.qweb.default_dict['_s'] = this.origin;
        this.rpc_function = (this.origin == window_origin) ? this.rpc_json : this.rpc_jsonp;
        this.session_id = false;
        this.uid = false;
        this.username = false;
        this.user_context= {};
        this.db = false;
        this.openerp_entreprise = false;
        this.module_list = openerp._modules.slice();
        this.module_loaded = {};
        _(this.module_list).each(function (mod) {
            self.module_loaded[mod] = true;
        });
        this.context = {};
        this.shortcuts = [];
        this.active_id = null;
        return this.session_init();
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
            var ctx = this.test_eval_contexts(source.contexts);
            if (!_.isEqual(ctx, expected.context)) {
                openerp.webclient.notification.warn('Context mismatch, report to xmo',
                    _.str.sprintf(match_template, {
                        source: JSON.stringify(source.contexts),
                        local: JSON.stringify(ctx),
                        remote: JSON.stringify(expected.context)
                    }), true);
            }
        } catch (e) {
            openerp.webclient.notification.warn('Context fail, report to xmo',
                _.str.sprintf(fail_template, {
                    error: e.message,
                    source: JSON.stringify(source.contexts)
                }), true);
        }

        try {
            var dom = this.test_eval_domains(source.domains, this.test_eval_get_context());
            if (!_.isEqual(dom, expected.domain)) {
                openerp.webclient.notification.warn('Domains mismatch, report to xmo',
                    _.str.sprintf(match_template, {
                        source: JSON.stringify(source.domains),
                        local: JSON.stringify(dom),
                        remote: JSON.stringify(expected.domain)
                    }), true);
            }
        } catch (e) {
            openerp.webclient.notification.warn('Domain fail, report to xmo',
                _.str.sprintf(fail_template, {
                    error: e.message,
                    source: JSON.stringify(source.domains)
                }), true);
        }

        try {
            var groups = this.test_eval_groupby(source.group_by_seq);
            if (!_.isEqual(groups, expected.group_by)) {
                openerp.webclient.notification.warn('GroupBy mismatch, report to xmo',
                    _.str.sprintf(match_template, {
                        source: JSON.stringify(source.group_by_seq),
                        local: JSON.stringify(groups),
                        remote: JSON.stringify(expected.group_by)
                    }), true);
            }
        } catch (e) {
            openerp.webclient.notification.warn('GroupBy fail, report to xmo',
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
        params.session_id = this.session_id;
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
            var display = options.openerp.debug ? 'block' : 'none';
            var $iframe = $(_.str.sprintf("<iframe src='javascript:false;' name='%s' id='%s' style='display:%s'></iframe>", ifid, ifid, display));
            var $form = $('<form>')
                        .attr('method', 'POST')
                        .attr('target', ifid)
                        .attr('enctype', "multipart/form-data")
                        .attr('action', ajax.url + '?' + $.param(data))
                        .append($('<input type="hidden" name="r" />').attr('value', payload_str))
                        .hide()
                        .appendTo($('body'));
            var cleanUp = function() {
                if ($iframe) {
                    $iframe.unbind("load").attr("src", "javascript:false;").remove();
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
    /**
     * Init a session, reloads from cookie, if it exists
     */
    session_init: function () {
        var self = this;
        // TODO: session store in cookie should be optional
        this.session_id = this.get_cookie('session_id');
        return this.session_reload().pipe(function(result) {
            var modules = openerp._modules.join(',');
            var deferred = self.rpc('/web/webclient/qweblist', {mods: modules}).pipe(self.do_load_qweb);
            if(self.session_is_valid()) {
                return deferred.pipe(function() { return self.load_modules(); });
            }
            return deferred;
        });
    },
    /**
     * (re)loads the content of a session: db name, username, user id, session
     * context and status of the support contract
     *
     * @returns {$.Deferred} deferred indicating the session is done reloading
     */
    session_reload: function () {
        var self = this;
        return this.rpc("/web/session/get_session_info", {}).then(function(result) {
            // If immediately follows a login (triggered by trying to restore
            // an invalid session or no session at all), refresh session data
            // (should not change, but just in case...)
            _.extend(self, {
                db: result.db,
                username: result.login,
                uid: result.uid,
                user_context: result.context,
                openerp_entreprise: result.openerp_entreprise
            });
        });
    },
    session_is_valid: function() {
        return !!this.uid;
    },
    /**
     * The session is validated either by login or by restoration of a previous session
     */
    session_authenticate: function(db, login, password, _volatile) {
        var self = this;
        var base_location = document.location.protocol + '//' + document.location.host;
        var params = { db: db, login: login, password: password, base_location: base_location };
        return this.rpc("/web/session/authenticate", params).pipe(function(result) {
            _.extend(self, {
                session_id: result.session_id,
                db: result.db,
                username: result.login,
                uid: result.uid,
                user_context: result.context,
                openerp_entreprise: result.openerp_entreprise
            });
            if (!_volatile) {
                self.set_cookie('session_id', self.session_id);
            }
            return self.load_modules();
        });
    },
    session_logout: function() {
        this.set_cookie('session_id', '');
        return this.rpc("/web/session/destroy", {});
    },
    on_session_valid: function() {
    },
    /**
     * Called when a rpc call fail due to an invalid session.
     * By default, it's a noop
     */
    on_session_invalid: function(retry_callback) {
    },
    /**
     * Fetches a cookie stored by an openerp session
     *
     * @private
     * @param name the cookie's name
     */
    get_cookie: function (name) {
        if (!this.name) { return null; }
        var nameEQ = this.name + '|' + name + '=';
        var cookies = document.cookie.split(';');
        for(var i=0; i<cookies.length; ++i) {
            var cookie = cookies[i].replace(/^\s*/, '');
            if(cookie.indexOf(nameEQ) === 0) {
                return JSON.parse(decodeURIComponent(cookie.substring(nameEQ.length)));
            }
        }
        return null;
    },
    /**
     * Create a new cookie with the provided name and value
     *
     * @private
     * @param name the cookie's name
     * @param value the cookie's value
     * @param ttl the cookie's time to live, 1 year by default, set to -1 to delete
     */
    set_cookie: function (name, value, ttl) {
        if (!this.name) { return; }
        ttl = ttl || 24*60*60*365;
        document.cookie = [
            this.name + '|' + name + '=' + encodeURIComponent(JSON.stringify(value)),
            'path=/',
            'max-age=' + ttl,
            'expires=' + new Date(new Date().getTime() + ttl*1000).toGMTString()
        ].join(';');
    },
    /**
     * Load additional web addons of that instance and init them
     *
     * @param {Boolean} [no_session_valid_signal=false] prevents load_module from triggering ``on_session_valid``.
     */
    load_modules: function(no_session_valid_signal) {
        var self = this;
        return this.rpc('/web/session/modules', {}).pipe(function(result) {
            var lang = self.user_context.lang,
                all_modules = _.uniq(self.module_list.concat(result));
            var params = { mods: all_modules, lang: lang};
            var to_load = _.difference(result, self.module_list).join(',');
            self.module_list = all_modules;

            var loaded = $.Deferred().resolve().promise();
            if (to_load.length) {
                loaded = $.when(
                    self.rpc('/web/webclient/csslist', {mods: to_load}, self.do_load_css),
                    self.rpc('/web/webclient/qweblist', {mods: to_load}).pipe(self.do_load_qweb),
                    self.rpc('/web/webclient/translations', params).pipe(function(trans) {
                        openerp.web._t.database.set_bundle(trans);
                        var file_list = ["/web/static/lib/datejs/globalization/" + lang.replace("_", "-") + ".js"];
                        return self.rpc('/web/webclient/jslist', {mods: to_load}).pipe(function(files) {
                            return self.do_load_js(file_list.concat(files));
                        }).then(function () {
                            if (!Date.CultureInfo.pmDesignator) {
                                // If no am/pm designator is specified but the openerp
                                // datetime format uses %i, date.js won't be able to
                                // correctly format a date. See bug#938497.
                                Date.CultureInfo.amDesignator = 'AM';
                                Date.CultureInfo.pmDesignator = 'PM';
                            }
                        });
                    }))
            }
            return loaded.then(function() {
                self.on_modules_loaded();
                if (!no_session_valid_signal) {
                    self.on_session_valid();
                }
            });
        });
    },
    do_load_css: function (files) {
        var self = this;
        _.each(files, function (file) {
            $('head').append($('<link>', {
                'href': self.get_url(file),
                'rel': 'stylesheet',
                'type': 'text/css'
            }));
        });
    },
    do_load_js: function(files) {
        var self = this;
        var d = $.Deferred();
        if(files.length != 0) {
            var file = files.shift();
            var tag = document.createElement('script');
            tag.type = 'text/javascript';
            tag.src = self.get_url(file);
            tag.onload = tag.onreadystatechange = function() {
                if ( (tag.readyState && tag.readyState != "loaded" && tag.readyState != "complete") || tag.onload_done )
                    return;
                tag.onload_done = true;
                self.do_load_js(files).then(function () {
                    d.resolve();
                });
            };
            var head = document.head || document.getElementsByTagName('head')[0];
            head.appendChild(tag);
        } else {
            d.resolve();
        }
        return d;
    },
    do_load_qweb: function(files) {
        var self = this;
        _.each(files, function(file) {
            self.qweb_mutex.exec(function() {
                return self.rpc('/web/proxy/load', {path: file}).pipe(function(xml) {
                    if (!xml) { return; }
                    openerp.web.qweb.add_template(_.str.trim(xml));
                });
            });
        });
        return self.qweb_mutex.def;
    },
    on_modules_loaded: function() {
        for(var j=0; j<this.module_list.length; j++) {
            var mod = this.module_list[j];
            if(this.module_loaded[mod])
                continue;
            openerp[mod] = {};
            // init module mod
            if(openerp._openerp[mod] != undefined) {
                openerp._openerp[mod](openerp);
                this.module_loaded[mod] = true;
            }
        }
    },
    get_url: function (file) {
        return this.prefix + file;
    },
    /**
     * Cooperative file download implementation, for ajaxy APIs.
     *
     * Requires that the server side implements an httprequest correctly
     * setting the `fileToken` cookie to the value provided as the `token`
     * parameter. The cookie *must* be set on the `/` path and *must not* be
     * `httpOnly`.
     *
     * It would probably also be a good idea for the response to use a
     * `Content-Disposition: attachment` header, especially if the MIME is a
     * "known" type (e.g. text/plain, or for some browsers application/json
     *
     * @param {Object} options
     * @param {String} [options.url] used to dynamically create a form
     * @param {Object} [options.data] data to add to the form submission. If can be used without a form, in which case a form is created from scratch. Otherwise, added to form data
     * @param {HTMLFormElement} [options.form] the form to submit in order to fetch the file
     * @param {Function} [options.success] callback in case of download success
     * @param {Function} [options.error] callback in case of request error, provided with the error body
     * @param {Function} [options.complete] called after both ``success`` and ``error` callbacks have executed
     */
    get_file: function (options) {
        // need to detect when the file is done downloading (not used
        // yet, but we'll need it to fix the UI e.g. with a throbber
        // while dump is being generated), iframe load event only fires
        // when the iframe content loads, so we need to go smarter:
        // http://geekswithblogs.net/GruffCode/archive/2010/10/28/detecting-the-file-download-dialog-in-the-browser.aspx
        var timer, token = new Date().getTime(),
            cookie_name = 'fileToken', cookie_length = cookie_name.length,
            CHECK_INTERVAL = 1000, id = _.uniqueId('get_file_frame'),
            remove_form = false;

        var $form, $form_data = $('<div>');

        var complete = function () {
            if (options.complete) { options.complete(); }
            clearTimeout(timer);
            $form_data.remove();
            $target.remove();
            if (remove_form && $form) { $form.remove(); }
        };
        var $target = $('<iframe style="display: none;">')
            .attr({id: id, name: id})
            .appendTo(document.body)
            .load(function () {
                try {
                    if (options.error) {
                        options.error(JSON.parse(
                            this.contentDocument.body.childNodes[1].textContent
                        ));
                    }
                } finally {
                    complete();
                }
            });

        if (options.form) {
            $form = $(options.form);
        } else {
            remove_form = true;
            $form = $('<form>', {
                action: options.url,
                method: 'POST'
            }).appendTo(document.body);
        }

        _(_.extend({}, options.data || {},
                   {session_id: this.session_id, token: token}))
            .each(function (value, key) {
                var $input = $form.find('[name=' + key +']');
                if (!$input.length) {
                    $input = $('<input type="hidden" name="' + key + '">')
                        .appendTo($form_data);
                }
                $input.val(value)
            });

        $form
            .append($form_data)
            .attr('target', id)
            .get(0).submit();

        var waitLoop = function () {
            var cookies = document.cookie.split(';');
            // setup next check
            timer = setTimeout(waitLoop, CHECK_INTERVAL);
            for (var i=0; i<cookies.length; ++i) {
                var cookie = cookies[i].replace(/^\s*/, '');
                if (!cookie.indexOf(cookie_name === 0)) { continue; }
                var cookie_val = cookie.substring(cookie_length + 1);
                if (parseInt(cookie_val, 10) !== token) { continue; }

                // clear cookie
                document.cookie = _.str.sprintf("%s=;expires=%s;path=/",
                    cookie_name, new Date().toGMTString());
                if (options.success) { options.success(); }
                complete();
                return;
            }
        };
        timer = setTimeout(waitLoop, CHECK_INTERVAL);
    },
    synchronized_mode: function(to_execute) {
    	var synch = this.synch;
    	this.synch = true;
    	try {
    		return to_execute();
    	} finally {
    		this.synch = synch;
    	}
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
openerp.web.Widget = openerp.web.Widget.extend(_.extend({}, openerp.web.CallbackEnabledMixin, {
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
        this._super(parent);
        openerp.web.CallbackEnabledMixin.init.call(this);
        this.session = openerp.connection;
    },
    /**
     * Renders the element. The default implementation renders the widget using QWeb,
     * `this.template` must be defined. The context given to QWeb contains the "widget"
     * key that references `this`.
     */
    renderElement: function() {
        var rendered = null;
        if (this.template)
            rendered = openerp.web.qweb.render(this.template, {widget: this});
        if (_.str.trim(rendered)) {
            var elem = $(rendered);
            this.$element.replaceWith(elem);
            this.$element = elem;
        }
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
        openerp.connection.rpc(url, data). then(function() {
            if (!self.isDestroyed())
                def.resolve.apply(def, arguments);
        }, function() {
            if (!self.isDestroyed())
                def.reject.apply(def, arguments);
        });
        return def.promise();
    }
}));

/**
 * @deprecated use :class:`openerp.web.Widget`
 */
openerp.web.OldWidget = openerp.web.Widget.extend({
    init: function(parent, element_id) {
        this._super(parent);
        this.element_id = element_id;
        this.element_id = this.element_id || _.uniqueId('widget-');
        var tmp = document.getElementById(this.element_id);
        this.$element = tmp ? $(tmp) : $(document.createElement(this.tagName));
    },
    renderElement: function() {
        var rendered = this.render();
        if (rendered) {
            var elem = $(rendered);
            this.$element.replaceWith(elem);
            this.$element = elem;
        }
        return this;
    },
    render: function (additional) {
        if (this.template)
            return openerp.web.qweb.render(this.template, _.extend({widget: this}, additional || {}));
        return null;
    }
});

openerp.web.TranslationDataBase = openerp.web.Class.extend(/** @lends openerp.web.TranslationDataBase# */{
    /**
     * @constructs openerp.web.TranslationDataBase
     * @extends openerp.web.Class
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
            this.parameters.grouping = py.eval(
                    this.parameters.grouping);
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
        if (this.db[key])
            return this.db[key];
        return undefined;
    }
});


}

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
