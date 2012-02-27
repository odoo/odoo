/*
Copyright (c) 2011, OpenERP S.A.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

nova = (function() {
    var lib = {};
    lib.internal = {};

    /*
     * (Almost) unmodified John Resig's inheritance
     */
    /*
     * Simple JavaScript Inheritance By John Resig http://ejohn.org/ MIT
     * Licensed.
     */
    // Inspired by base2 and Prototype
    (function() {
        var initializing = false, fnTest = /xyz/.test(function() {
            xyz;
        }) ? /\b_super\b/ : /.*/;
        // The base Class implementation (does nothing)
        this.Class = function() {
        };

        // Create a new Class that inherits from this class
        this.Class.extend = function(prop) {
        var _super = this.prototype;

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
    }).call(lib);
    // end of John Resig's code

    lib.DestroyableMixin = {
        init: function() {
            this.__destroyableDestroyed = false;
        },
        isDestroyed : function() {
            return this.__destroyableDestroyed;
        },
        destroy : function() {
            this.__destroyableDestroyed = true;
        }
    };

    lib.ParentedMixin = _.extend({}, lib.DestroyableMixin, {
        __parentedMixin : true,
        init: function() {
            lib.DestroyableMixin.init.call(this);
            this.__parentedChildren = [];
            this.__parentedParent = null;
        },
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
        getParent : function() {
            return this.__parentedParent;
        },
        getChildren : function() {
            return _.clone(this.__parentedChildren);
        },
        destroy : function() {
            _.each(this.getChildren(), function(el) {
                el.destroy();
            });
            this.setParent(undefined);
            lib.DestroyableMixin.destroy.call(this);
        }
    });

    /*
     * Yes, we steal Backbone's events :)
     * 
     * This class just handle the dispatching of events, it is not meant to be extended,
     * nor used directly. All integration with parenting and automatic unregistration of
     * events is done in EventDispatcherMixin.
     */
    // (c) 2010-2012 Jeremy Ashkenas, DocumentCloud Inc.
    // Backbone may be freely distributed under the MIT license.
    // For all details and documentation:
    // http://backbonejs.org
    lib.internal.Events = lib.Class.extend({

        // Bind an event, specified by a string name, `ev`, to a `callback`
        // function. Passing `"all"` will bind the callback to all events fired.
        on : function(events, callback, context) {
            var ev;
            events = events.split(/\s+/);
            var calls = this._callbacks || (this._callbacks = {});
            while (ev = events.shift()) {
                // Create an immutable callback list, allowing traversal during
                // modification. The tail is an empty object that will always be
                // used
                // as the next node.
                var list = calls[ev] || (calls[ev] = {});
                var tail = list.tail || (list.tail = list.next = {});
                tail.callback = callback;
                tail.context = context;
                list.tail = tail.next = {};
            }
            return this;
        },

        // Remove one or many callbacks. If `context` is null, removes all
        // callbacks
        // with that function. If `callback` is null, removes all callbacks for
        // the
        // event. If `ev` is null, removes all bound callbacks for all events.
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
                    // Create a new list, omitting the indicated event/context
                    // pairs.
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

        // Trigger an event, firing all bound callbacks. Callbacks are passed
        // the
        // same arguments as `trigger` is, apart from the event name.
        // Listening for `"all"` passes the true event name as the first
        // argument.
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
            // Traverse each list, stopping when the saved tail is reached.
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
    // end of Backbone's events class
    
    lib.EventDispatcherMixin = _.extend({}, lib.ParentedMixin, {
        __eventDispatcherMixin: true,
        init: function() {
            lib.ParentedMixin.init.call(this);
            this.__edispatcherEvents = new lib.internal.Events();
            this.__edispatcherRegisteredEvents = [];
        },
        bind: function(events, dest, func) {
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
        unbind: function(events, dest, func) {
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
            lib.ParentedMixin.destroy.call(this);
        }
    });
    
    lib.GetterSetterMixin = _.extend({}, lib.EventDispatcherMixin, {
        init: function() {
            lib.EventDispatcherMixin.init.call(this);
            this.__getterSetterInternalMap = {};
        },
        set: function(map) {
            var self = this;
            _.each(map, function(val, key) {
                var tmp = self.__getterSetterInternalMap[key];
                self.__getterSetterInternalMap[key] = val;
                self.trigger("changed:" + key, {
                    oldValue: tmp,
                    newValue: val,
                    source: self
                });
            });
        },
        get: function(key) {
            return this.__getterSetterInternalMap[key];
        }
    });
    
    lib.Widget = lib.Class.extend(_.extend({}, lib.GetterSetterMixin, {
        /**
         * Tag name when creating a default $element.
         * @type string
         */
        tag_name: 'div',
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
            lib.GetterSetterMixin.init.call(this);
            this.$element = $(document.createElement(this.tag_name));
    
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
            lib.GetterSetterMixin.destroy.call(this);
        },
        /**
         * Renders the current widget and appends it to the given jQuery object or Widget.
         *
         * @param target A jQuery object or a Widget instance.
         */
        appendTo: function(target) {
            var self = this;
            return this.__renderAndInsert(function(t) {
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
            return this.__renderAndInsert(function(t) {
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
            return this.__renderAndInsert(function(t) {
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
            return this.__renderAndInsert(function(t) {
                self.$element.insertBefore(t);
            }, target);
        },
        /**
         * Renders the current widget and replaces the given jQuery object.
         *
         * @param target A jQuery object or a Widget instance.
         */
        replace: function(target) {
            return this.__renderAndInsert(_.bind(function(t) {
                this.$element.replaceAll(t);
            }, this), target);
        },
        __renderAndInsert: function(insertion, target) {
            this.render_element();
            insertion(target);
            return this.start();
        },
        /**
         * This is the method to implement to render the Widget.
         */
        render_element: function() {},
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
    }));

    return lib;
})();
