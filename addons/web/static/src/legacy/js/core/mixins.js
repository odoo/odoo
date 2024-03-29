/** @odoo-module **/

import { floatIsZero } from "@web/core/utils/numbers";

/**
 * Mixin to structure objects' life-cycles folowing a parent-children
 * relationship. Each object can a have a parent and multiple children.
 * When an object is destroyed, all its children are destroyed too releasing
 * any resource they could have reserved before.
 *
 * @name ParentedMixin
 * @mixin
 */
var ParentedMixin = {
    __parentedMixin : true,
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
    setParent : function (parent) {
        if (this.getParent()) {
            if (this.getParent().__parentedMixin) {
                const children = this.getParent().getChildren();
                this.getParent().__parentedChildren = children.filter(
                    (child) => child.$el !== this.$el
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
    getParent : function () {
        return this.__parentedParent;
    },
    /**
     * Return a list of the children of the current object.
     */
    getChildren : function () {
        return [...this.__parentedChildren];
    },
    /**
     * Returns true if destroy() was called on the current object.
     */
    isDestroyed : function () {
        return this.__parentedDestroyed;
    },
    /**
     * Utility method to only execute asynchronous actions if the current
     * object has not been destroyed.
     *
     * @param {Promise} promise The promise representing the asynchronous
     *                             action.
     * @param {bool} [shouldReject=false] If true, the returned promise will be
     *                              rejected with no arguments if the current
     *                              object is destroyed. If false, the
     *                              returned promise will never be resolved
     *                              or rejected.
     * @returns {Promise} A promise that will mirror the given promise if
     *                       everything goes fine but will either be rejected
     *                       with no arguments or never resolved if the
     *                       current object is destroyed.
     */
    alive: function (promise, shouldReject) {
        var self = this;

        return new Promise(function (resolve, reject) {
            promise.then(function (result) {
                if (!self.isDestroyed()) {
                    resolve(result);
                } else if (shouldReject) {
                    reject();
                }
            }).catch(function (reason) {
                if (!self.isDestroyed()) {
                    reject(reason);
                } else if (shouldReject) {
                    reject();
                }
            });
        });
    },
    /**
     * Inform the object it should destroy itself, releasing any
     * resource it could have reserved.
     */
    destroy : function () {
        this.getChildren().forEach(function (child) {
            child.destroy();
        });
        this.setParent(undefined);
        this.__parentedDestroyed = true;
    },
    /**
     * Find the closest ancestor matching predicate
     */
    findAncestor: function (predicate) {
        var ancestor = this;
        while (ancestor && !(predicate(ancestor)) && ancestor.getParent) {
            ancestor = ancestor.getParent();
        }
        return ancestor;
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
class Events {
    on(events, callback, context) {
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
    }

    off(events, callback, context) {
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
    }

    callbackList() {
        var lst = [];
        for (const [eventName, el] of Object.entries(this._callbacks || {})) {
            var node = el;
            while ((node = node.next) && node.next) {
                lst.push([eventName, node.callback, node.context]);
            }
        }
        return lst;
    }

    trigger(events) {
        var event, node, calls, tail, args, all, rest;
        if (!(calls = this._callbacks))
            return this;
        all = calls.all;
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
}

/**
 * Mixin containing an event system. Events are also registered by specifying the target object
 * (the object which will receive the event when it is raised). Both the event-emitting object
 * and the target object store or reference to each other. This is used to correctly remove all
 * reference to the event handler when any of the object is destroyed (when the destroy() method
 * from ParentedMixin is called). Removing those references is necessary to avoid memory leak
 * and phantom events (events which are raised and sent to a previously destroyed object).
 *
 * @name EventDispatcherMixin
 * @mixin
 */
var EventDispatcherMixin = Object.assign({}, ParentedMixin, {
    __eventDispatcherMixin: true,
    custom_events: {},
    init: function () {
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
            if (fn === void 0) {
                throw new Error("Couldn't find method '" + method + "' in widget " + self);
            }
            return fn.apply(self, arguments);
        };
    },
    _delegateCustomEvents: function () {
        if (Object.keys(this.custom_events || {}).length === 0) { return; }
        for (var key in this.custom_events) {
            if (!this.custom_events.hasOwnProperty(key)) { continue; }

            var method = this.proxy(this.custom_events[key]);
            this.on(key, this, method);
        }
    },
    on: function (events, dest, func) {
        var self = this;
        if (typeof func !== "function") {
            throw new Error("Event handler must be a function.");
        }
        events = events.split(/\s+/);
        events.forEach((eventName) => {
            self.__edispatcherEvents.on(eventName, func, dest);
            if (dest && dest.__eventDispatcherMixin) {
                dest.__edispatcherRegisteredEvents.push({name: eventName, func: func, source: self});
            }
        });
        return this;
    },
    off: function (events, dest, func) {
        var self = this;
        events = events.split(/\s+/);
        events.forEach((eventName) => {
            self.__edispatcherEvents.off(eventName, func, dest);
            if (dest && dest.__eventDispatcherMixin) {
                dest.__edispatcherRegisteredEvents = dest.__edispatcherRegisteredEvents.filter(el => {
                    return !(el.name === eventName && el.func === func && el.source === self);
                });
            }
        });
        return this;
    },
    once: function (events, dest, func) {
        // similar to this.on(), but func is executed only once
        var self = this;
        if (typeof func !== "function") {
            throw new Error("Event handler must be a function.");
        }
        self.on(events, dest, function what() {
            func.apply(this, arguments);
            self.off(events, dest, what);
        });
    },
    trigger: function () {
        this.__edispatcherEvents.trigger.apply(this.__edispatcherEvents, arguments);
        return this;
    },
    trigger_up: function (name, info) {
        var event = new OdooEvent(this, name, info);
        //console.info('event: ', name, info);
        this._trigger_up(event);
        return event;
    },
    _trigger_up: function (event) {
        var parent;
        this.__edispatcherEvents.trigger(event.name, event);
        if (!event.is_stopped() && (parent = this.getParent())) {
            parent._trigger_up(event);
        }
    },
    destroy: function () {
        var self = this;
        this.__edispatcherRegisteredEvents.forEach((event) => {
            event.source.__edispatcherEvents.off(event.name, event.func, self);
        });
        this.__edispatcherRegisteredEvents = [];
        this.__edispatcherEvents.callbackList().forEach(
            ((cal) => {
                this.off(cal[0], cal[2], cal[1]);
            }).bind(this)
        );
        this.__edispatcherEvents.off();
        ParentedMixin.destroy.call(this);
    },
});

/**
 * @name PropertiesMixin
 * @mixin
 */
var PropertiesMixin = Object.assign({}, EventDispatcherMixin, {
    init: function () {
        EventDispatcherMixin.init.call(this);
        this.__getterSetterInternalMap = {};
    },
    set: function (arg1, arg2, arg3) {
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
        for (const [key, val] of Object.entries(map)) {
            var tmp = self.__getterSetterInternalMap[key];
            if (tmp === val)
                return;
            // seriously, why are you doing this? it is obviously a stupid design.
            // the properties mixin should not be concerned with handling fields details.
            // this also has the side effect of introducing a dependency on utils.  Todo:
            // remove this, or move it elsewhere.  Also, learn OO programming.
            if (key === 'value' && self.field && self.field.type === 'float' && tmp && val){
                var digits = self.field.digits;
                if (Array.isArray(digits)) {
                    if (floatIsZero(tmp - val, digits[1])) {
                        return;
                    }
                }
            }
            changed = true;
            self.__getterSetterInternalMap[key] = val;
            if (! options.silent)
                self.trigger("change:" + key, self, {
                    oldValue: tmp,
                    newValue: val
                });
        }
        if (changed)
            self.trigger("change", self);
    },
    get: function (key) {
        return this.__getterSetterInternalMap[key];
    }
});

export default {
    ParentedMixin: ParentedMixin,
    EventDispatcherMixin: EventDispatcherMixin,
    PropertiesMixin: PropertiesMixin,
};
