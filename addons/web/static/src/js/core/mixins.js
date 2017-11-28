odoo.define('web.mixins', function (require) {
"use strict";

var Class = require('web.Class');
var utils = require('web.utils');
var AbstractService = require('web.AbstractService');

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
    getParent : function () {
        return this.__parentedParent;
    },
    /**
     * Return a list of the children of the current object.
     */
    getChildren : function () {
        return _.clone(this.__parentedChildren);
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
     * @param {$.Deferred} promise The promise representing the asynchronous
     *                             action.
     * @param {bool} [reject=false] If true, the returned promise will be
     *                              rejected with no arguments if the current
     *                              object is destroyed. If false, the
     *                              returned promise will never be resolved
     *                              or rejected.
     * @returns {$.Deferred} A promise that will mirror the given promise if
     *                       everything goes fine but will either be rejected
     *                       with no arguments or never resolved if the
     *                       current object is destroyed.
     */
    alive: function (promise, reject) {
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
    destroy : function () {
        _.each(this.getChildren(), function (el) {
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
    _.extend(this.data, data);
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
var Events = Class.extend({
    on : function (events, callback, context) {
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

    off : function (events, callback, context) {
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

    callbackList: function () {
        var lst = [];
        _.each(this._callbacks || {}, function (el, eventName) {
            var node = el;
            while ((node = node.next) && node.next) {
                lst.push([eventName, node.callback, node.context]);
            }
        });
        return lst;
    },

    trigger : function (events) {
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
});

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
var EventDispatcherMixin = _.extend({}, ParentedMixin, {
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
            if (fn === void 0) {
                throw new Error("Couldn't find method '" + method + "' in widget " + self);
            }
            return fn.apply(self, arguments);
        };
    },
    _delegateCustomEvents: function () {
        if (_.isEmpty(this.custom_events)) { return; }
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
        _.each(events, function (eventName) {
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
        _.each(events, function (eventName) {
            self.__edispatcherEvents.off(eventName, func, dest);
            if (dest && dest.__eventDispatcherMixin) {
                dest.__edispatcherRegisteredEvents = _.filter(dest.__edispatcherRegisteredEvents, function (el) {
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
        this._trigger_up(event);
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
        _.each(this.__edispatcherRegisteredEvents, function (event) {
            event.source.__edispatcherEvents.off(event.name, event.func, self);
        });
        this.__edispatcherRegisteredEvents = [];
        _.each(this.__edispatcherEvents.callbackList(), function (cal) {
            this.off(cal[0], cal[2], cal[1]);
        }, this);
        this.__edispatcherEvents.off();
        ParentedMixin.destroy.call(this);
    }
});

/**
 * @name PropertiesMixin
 * @mixin
 */
var PropertiesMixin = _.extend({}, EventDispatcherMixin, {
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
        _.each(map, function (val, key) {
            var tmp = self.__getterSetterInternalMap[key];
            if (tmp === val)
                return;
            // seriously, why are you doing this? it is obviously a stupid design.
            // the properties mixin should not be concerned with handling fields details.
            // this also has the side effect of introducing a dependency on utils.  Todo:
            // remove this, or move it elsewhere.  Also, learn OO programming.
            if (key === 'value' && self.field && self.field.type === 'float' && tmp && val){
                var digits = self.field.digits;
                if (_.isArray(digits)) {
                    if (utils.float_is_zero(tmp - val, digits[1])) {
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
        });
        if (changed)
            self.trigger("change", self);
    },
    get: function (key) {
        return this.__getterSetterInternalMap[key];
    }
});

var ServiceProvider = {
    services: {},
    init: function () {
        var self = this;
        _.each(AbstractService.prototype.Services, function (Service) {
            var service = new Service();
            self.services[service.name] = service;
        });
        this.custom_events = _.clone(this.custom_events);
        this.custom_events.call_service = this._call_service.bind(this);
    },
    _call_service: function (event) {
        var service = this.services[event.data.service];
        var args = (event.data.args || []).concat(event.target);
        var result = service[event.data.method].apply(service, args);
        event.data.callback(result);
    },
};

return {
    ParentedMixin: ParentedMixin,
    EventDispatcherMixin: EventDispatcherMixin,
    PropertiesMixin: PropertiesMixin,
    ServiceProvider: ServiceProvider,
};

});

odoo.define('web.ServicesMixin', function (require) {
"use strict";

var rpc = require('web.rpc');

/**
 * @mixin
 * @name ServicesMixin
 */
var ServicesMixin = {
    call: function (service, method) {
        var args = Array.prototype.slice.call(arguments, 2);
        var result;
        this.trigger_up('call_service', {
            service: service,
            method: method,
            args: args,
            callback: function (r) {
                result = r;
            },
        });
        return result;
    },
    /**
     * Builds and executes RPC query. Returns a deferred's promise resolved with
     * the RPC result.
     *
     * @param {string} params either a route or a model
     * @param {string} options if a model is given, this argument is a method
     * @returns {Promise}
     */
    _rpc: function (params, options) {
        var query = rpc.buildQuery(params);
        var def = this.call('ajax', 'rpc', query.route, query.params, options);
        return def ? def.promise() : $.Deferred().promise();
    },
    loadFieldView: function (dataset, view_id, view_type, options) {
        return this.loadViews(dataset.model, dataset.get_context().eval(), [[view_id, view_type]], options).then(function (result) {
            return result[view_type];
        });
    },
    loadViews: function (modelName, context, views, options) {
        var def = $.Deferred();
        this.trigger_up('load_views', {
            modelName: modelName,
            context: context,
            views: views,
            options: options,
            on_success: def.resolve.bind(def),
        });
        return def;
    },
    loadFilters: function (dataset, action_id) {
        var def = $.Deferred();
        this.trigger_up('load_filters', {
            dataset: dataset,
            action_id: action_id,
            on_success: def.resolve.bind(def),
        });
        return def;
    },
    // Session stuff
    getSession: function () {
        var session;
        this.trigger_up('get_session', {
            callback: function (result) {
                session = result;
            }
        });
        return session;
    },
    /**
     * Informs the action manager to do an action. This supposes that the action
     * manager can be found amongst the ancestors of the current widget.
     * If that's not the case this method will simply return an unresolved
     * deferred.
     *
     * @param {any} action
     * @param {any} options
     * @returns {Deferred}
     */
    do_action: function (action, options) {
        var def = $.Deferred();

        this.trigger_up('do_action', {
            action: action,
            options: options,
            on_success: function (result) { def.resolve(result); },
            on_fail: function (result) { def.reject(result); },
        });
        return def;
    },
    do_notify: function (title, message, sticky, className) {
        this.trigger_up('notification', {title: title, message: message, sticky: sticky, className: className});
    },
    do_warn: function (title, message, sticky, className) {
        this.trigger_up('warning', {title: title, message: message, sticky: sticky, className: className});
    },
};

return ServicesMixin;

});
